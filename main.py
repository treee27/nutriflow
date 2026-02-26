from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
import json
import re

# Only load .env locally — Railway uses real environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="NutriFlow API")

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Groq client ───────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY environment variable is not set!")
client = Groq(api_key=api_key)


# ── Request schema ────────────────────────────────────────────────
class MealRequest(BaseModel):
    food: str
    meal_time: str
    diet_type: str = "Vegetarian"


# ── Diet-specific prompt rules ────────────────────────────────────
DIET_RULES = {
    "Vegetarian": (
        "The user is VEGETARIAN. "
        "NEVER suggest meat, chicken, fish, seafood, or beef. "
        "You MAY include dairy (milk, paneer, curd, ghee, cheese), eggs, legumes, lentils, tofu, and all plant foods. "
        "Focus on paneer, dal, rajma, chana, curd, nuts, seeds, and eggs for protein."
    ),
    "Non-Vegetarian": (
        "The user is NON-VEGETARIAN. "
        "You MAY include chicken, fish, eggs, lean meat, and all other foods. "
        "Prefer lean proteins like chicken breast, grilled fish, eggs, and turkey. "
        "Balance with vegetables, whole grains, and dairy."
    ),
    "Vegan": (
        "The user is STRICTLY VEGAN. "
        "NEVER suggest any animal products — no meat, no fish, no eggs, no dairy. "
        "Use ONLY plant-based ingredients: tofu, tempeh, legumes, lentils, chickpeas, nuts, seeds, "
        "plant milks, nutritional yeast, and all vegetables and fruits. "
        "Pay special attention to B12, iron, calcium, and omega-3 from plant sources."
    ),
}


# ── Helper: extract JSON ──────────────────────────────────────────
def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in model response")
    return json.loads(match.group())


# ── Health check ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "NutriFlow API is running 🌿"}


# ── /suggest endpoint ─────────────────────────────────────────────
@app.post("/suggest")
async def suggest_meals(req: MealRequest):
    if not req.food.strip():
        raise HTTPException(status_code=400, detail="Please provide what you ate.")

    if req.diet_type not in DIET_RULES:
        raise HTTPException(status_code=400, detail=f"Invalid diet_type. Choose from: {list(DIET_RULES.keys())}")

    diet_rule = DIET_RULES[req.diet_type]

    prompt = f"""You are an expert Indian nutritionist and dietitian.

IMPORTANT DIET RULE (follow strictly, no exceptions):
{diet_rule}

The person just had this meal:
- Meal Time : {req.meal_time}
- Food Eaten: {req.food}
- Diet Type : {req.diet_type}

Suggest what they should eat for their REMAINING meals of the day so their body gets
complete nutrition — proteins, complex carbs, healthy fats, fiber, vitamins, and minerals.

Respond ONLY with a valid JSON object. No markdown, no text outside the JSON:

{{
  "summary": "One sentence summarising the nutritional gap after their meal",
  "meals": [
    {{
      "time": "Lunch",
      "emoji": "🍛",
      "title": "Meal name (1-4 words)",
      "description": "2-3 sentences: what to eat and exactly why it helps.",
      "nutrients": ["Protein", "Iron", "Vitamin C"],
      "highlightNutrient": "Protein"
    }}
  ],
  "nutritionBalance": {{
    "protein":  65,
    "carbs":    80,
    "fat":      55,
    "fiber":    70,
    "vitamins": 75
  }},
  "healthTip": "A warm, practical health tip (2-3 sentences)."
}}

Rules:
- Give 2-3 meal suggestions for meals AFTER {req.meal_time}
- STRICTLY follow the {req.diet_type} diet rule
- nutritionBalance values are 0-100 percentages
- Suggest real commonly available Indian ingredients
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are an expert Indian nutritionist specialising in {req.diet_type} diets. "
                        "Always respond with valid JSON only. No extra text, no markdown."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        raw  = response.choices[0].message.content
        plan = extract_json(raw)
        return plan

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Could not parse AI response: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))