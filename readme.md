#  NutriFlow — Setup Guide

## Project Structure
```
nutriflow-backend/
├── main.py          ← FastAPI backend
├── index.html       ← Your frontend
├── .env             ← Your secret API key (never share this)
├── requirements.txt ← Python dependencies
└── README.md
```

---

## Step 1 — Get Your FREE Gemini API Key

1. Go to  https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

---

## Step 2 — Add Key to .env

Open the `.env` file and replace the placeholder:

```
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```

---

## Step 3 — Install Dependencies

Open a terminal in the `nutriflow-backend/` folder and run:

```bash
pip install -r requirements.txt
```

---

## Step 4 — Start the Backend

```bash
uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

 Backend is now running at: http://localhost:8000

---

## Step 5 — Open the Frontend

Simply open `index.html` in **Chrome or Edge** (double-click the file).

That's it! Type or speak your meal and click **Get Meal Suggestions**.

---

## How It Works

```
index.html  →  POST /suggest  →  FastAPI backend  →  Gemini AI  →  JSON response  →  UI
```

---

## Free Tier Limits (Gemini 1.5 Flash)
-  1,500 requests per day
-  1 million tokens per minute
-  Completely free, no credit card needed

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cannot connect to backend" | Make sure `uvicorn` is running in terminal |
| "GEMINI_API_KEY invalid" | Check your `.env` file has the correct key |
| Voice not working | Use Chrome or Edge browser |
| CORS error | Backend already has CORS enabled for all origins |