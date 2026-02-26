from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
import json
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="NutriFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

class MealRequest(BaseModel):
    food: str
    meal_time: str
    diet_type: str = "Vegetarian"

DIET_RULES = {
    "Vegetarian": (
        "The user is VEGETARIAN. NEVER suggest meat, chicken, fish, seafood, or beef. "
        "You MAY include dairy (milk, paneer, curd, ghee, cheese), eggs, legumes, lentils, tofu."
    ),
    "Non-Vegetarian": (
        "The user is NON-VEGETARIAN. You MAY include chicken, fish, eggs, lean meat. "
        "Prefer lean proteins like chicken breast, grilled fish, eggs."
    ),
    "Vegan": (
        "The user is STRICTLY VEGAN. NEVER suggest any animal products — no meat, fish, eggs, dairy. "
        "Use ONLY plant-based: tofu, legumes, lentils, chickpeas, nuts, seeds, plant milks."
    ),
}

def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found")
    return json.loads(match.group())

@app.get("/")
def root():
    return {"status": "NutriFlow API is running 🌿"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/suggest")
async def suggest_meals(req: MealRequest):
    if not req.food.strip():
        raise HTTPException(status_code=400, detail="Please provide what you ate.")
    if not client:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured.")
    if req.diet_type not in DIET_RULES:
        raise HTTPException(status_code=400, detail=f"Invalid diet_type.")

    diet_rule = DIET_RULES[req.diet_type]

    prompt = f"""You are an expert Indian nutritionist.

DIET RULE: {diet_rule}

Meal Time : {req.meal_time}
Food Eaten: {req.food}
Diet Type : {req.diet_type}

Suggest 2-3 meals for REMAINING meals of the day.
Respond ONLY with valid JSON, no markdown, no extra text:

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
  "nutritionBalance": {{
    "protein": 65,
    "carbs": 80,
    "fat": 55,
    "fiber": 70,
    "vitamins": 75
  }},
  "healthTip": "A practical health tip."
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert Indian nutritionist. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content
        plan = extract_json(raw)
        return plan
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Parse error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)