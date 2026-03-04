from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pymongo import MongoClient
from datetime import datetime, timezone
import os, json, re, jwt, uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────
MONGO_URI       = os.environ.get("MONGO_URI", "")
GOOGLE_CLIENT_ID= os.environ.get("GOOGLE_CLIENT_ID", "")
JWT_SECRET      = os.environ.get("JWT_SECRET", "nutriflow-secret-change-this")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")

# ── MongoDB ───────────────────────────────────────────────────────
import certifi
mongo   = MongoClient(MONGO_URI, tlsCAFile=certifi.where()) if MONGO_URI else None
db      = mongo["nutriflow"] if mongo is not None else None
users   = db["users"]   if db is not None else None
meals   = db["meals"]   if db is not None else None
profiles= db["profiles"] if db is not None else None

# ── Groq ──────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

app = FastAPI(title="NutriFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── JWT Helpers ───────────────────────────────────────────────────
def create_jwt(user_id: str, email: str, name: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "email": email, "name": name},
        JWT_SECRET, algorithm="HS256"
    )

def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization.split(" ")[1]
    return verify_jwt(token)

# ── Schemas ───────────────────────────────────────────────────────
class GoogleAuthRequest(BaseModel):
    token: str

class MealRequest(BaseModel):
    food: str
    meal_time: str
    diet_type: str = "Vegetarian"

class SaveMealRequest(BaseModel):
    food: str
    meal_time: str
    diet_type: str
    plan: dict

class ProfileRequest(BaseModel):
    name: str = ""
    age: int = 0
    weight: float = 0
    height: float = 0
    diet_type: str = "Vegetarian"
    goal: str = "Balanced"

# ── Diet Rules ────────────────────────────────────────────────────
DIET_RULES = {
    "Vegetarian": "VEGETARIAN — no meat/fish/seafood. Dairy, eggs, legumes, paneer allowed.",
    "Non-Vegetarian": "NON-VEGETARIAN — chicken, fish, eggs, lean meat all allowed. Balance with vegetables.",
    "Vegan": "STRICTLY VEGAN — absolutely no animal products. Only plant-based ingredients.",
}

def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found")
    return json.loads(match.group())

# ══════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════

@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest):
    """Verify Google token, create/find user, return JWT"""
    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
        if not req.token:
            raise HTTPException(status_code=400, detail="No token provided")

        print(f"[AUTH] Verifying Google token (length={len(req.token)})...")

        # Verify Google token
        import requests as http_requests
        session = http_requests.Session()
        google_request = google_requests.Request(session=session)

        info = id_token.verify_oauth2_token(
            req.token,
            google_request,
            GOOGLE_CLIENT_ID
        )
        print(f"[AUTH] Token verified for: {info.get('email')}")
        email   = info["email"]
        name    = info.get("name", email.split("@")[0])
        picture = info.get("picture", "")
        google_id = info["sub"]

        # Find or create user in MongoDB
        if users is not None:
            user = users.find_one({"google_id": google_id})
            if not user:
                user_id = str(uuid.uuid4())
                users.insert_one({
                    "user_id":   user_id,
                    "google_id": google_id,
                    "email":     email,
                    "name":      name,
                    "picture":   picture,
                    "created_at": datetime.now(timezone.utc)
                })
                # Create default profile
                profiles.insert_one({
                    "user_id":   user_id,
                    "name":      name,
                    "age":       0,
                    "weight":    0,
                    "height":    0,
                    "diet_type": "Vegetarian",
                    "goal":      "Balanced",
                })
            else:
                user_id = user["user_id"]
                # Update name/picture on each login
                users.update_one(
                    {"google_id": google_id},
                    {"$set": {"name": name, "picture": picture}}
                )
        else:
            # No DB — demo mode
            user_id = google_id

        token = create_jwt(user_id, email, name)
        return {"token": token, "name": name, "email": email, "picture": picture, "user_id": user_id}

    except HTTPException:
        raise
    except ValueError as e:
        print(f"[AUTH ERROR] ValueError: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")
    except Exception as e:
        import traceback
        print(f"[AUTH ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

# ══════════════════════════════════════════════════════════════════
# SUGGEST ROUTE
# ══════════════════════════════════════════════════════════════════

@app.post("/suggest")
async def suggest_meals(req: MealRequest):
    if not req.food.strip():
        raise HTTPException(status_code=400, detail="Please provide what you ate.")
    if not groq_client:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured.")
    if req.diet_type not in DIET_RULES:
        raise HTTPException(status_code=400, detail="Invalid diet_type.")

    prompt = f"""You are an expert Indian nutritionist.
DIET RULE: {DIET_RULES[req.diet_type]}
Meal Time : {req.meal_time}
Food Eaten: {req.food}
Diet Type : {req.diet_type}

Suggest 2-3 meals for REMAINING meals of the day.
Respond ONLY with valid JSON:
{{
  "summary": "One sentence about nutritional gap",
  "meals": [
    {{
      "time": "Lunch",
      "emoji": "🍛",
      "title": "Meal name",
      "description": "2-3 sentences about what to eat and why",
      "nutrients": ["Protein", "Iron"],
      "highlightNutrient": "Protein"
    }}
  ],
  "nutritionBalance": {{"protein": 65, "carbs": 80, "fat": 55, "fiber": 70, "vitamins": 75}},
  "healthTip": "A practical health tip."
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Expert Indian nutritionist. JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=1024,
        )
        return extract_json(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Parse error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ══════════════════════════════════════════════════════════════════
# MEAL HISTORY ROUTES
# ══════════════════════════════════════════════════════════════════

@app.post("/meals/save")
async def save_meal(req: SaveMealRequest, user=Depends(get_current_user)):
    if meals is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    meal_doc = {
        "user_id":   user["user_id"],
        "food":      req.food,
        "meal_time": req.meal_time,
        "diet_type": req.diet_type,
        "plan":      req.plan,
        "logged_at": datetime.now(timezone.utc),
        "date_str":  datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    meals.insert_one(meal_doc)
    return {"success": True}

@app.get("/meals/history")
async def get_history(user=Depends(get_current_user)):
    if meals is None:
        return {"meals": []}
    user_meals = list(
        meals.find(
            {"user_id": user["user_id"]},
            {"_id": 0}
        ).sort("logged_at", -1).limit(42)  # last 6 weeks
    )
    # Convert datetime to string for JSON
    for m in user_meals:
        if isinstance(m.get("logged_at"), datetime):
            m["logged_at"] = m["logged_at"].isoformat()
    return {"meals": user_meals}

# ══════════════════════════════════════════════════════════════════
# PROFILE ROUTES
# ══════════════════════════════════════════════════════════════════

@app.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    if profiles is None:
        return {"name": user["name"], "diet_type": "Vegetarian"}
    profile = profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return profile or {"name": user["name"], "diet_type": "Vegetarian"}

@app.put("/profile")
async def update_profile(req: ProfileRequest, user=Depends(get_current_user)):
    if profiles is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": req.dict()},
        upsert=True
    )
    return {"success": True}

# ══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "NutriFlow API is running 🌿"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)