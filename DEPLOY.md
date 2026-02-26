# 🚀 NutriFlow — Complete Deployment Guide

## Project Structure (Final)
```
nutriflow/
├── index.html        ← Frontend (PWA + Reminders)
├── sw.js             ← Service Worker (offline + PWA)
├── manifest.json     ← PWA manifest (app name, icons, colors)
├── icons/
│   ├── icon-192.png  ← App icon (home screen)
│   └── icon-512.png  ← App icon (splash screen)
├── main.py           ← FastAPI backend
├── requirements.txt  ← Python dependencies
├── vercel.json       ← Vercel frontend config
├── railway.json      ← Railway backend config
├── Procfile          ← Railway start command
├── runtime.txt       ← Python version for Railway
└── .env              ← Secret keys (never push to GitHub!)
```

---

## PART 1 — Deploy Backend to Railway (Free)

### Step 1 — Create GitHub Repository
```bash
git init
git add .
git commit -m "Initial NutriFlow commit"
```
Create a repo on github.com and push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/nutriflow.git
git push -u origin main
```

### Step 2 — Deploy to Railway
1. Go to 👉 https://railway.app
2. Sign up with GitHub (free)
3. Click **"New Project"** → **"Deploy from GitHub Repo"**
4. Select your `nutriflow` repository
5. Railway auto-detects Python and installs requirements.txt

### Step 3 — Add Environment Variable
1. In Railway dashboard → your project → **Variables** tab
2. Click **"Add Variable"**
3. Name: `GROQ_API_KEY`  Value: `your_groq_key_here`

### Step 4 — Get Your Backend URL
1. Go to **Settings** tab → **Domains**
2. Click **"Generate Domain"**
3. Copy your URL — looks like: `https://nutriflow-production.up.railway.app`

✅ Backend is now live!

---

## PART 2 — Update Frontend with Backend URL

Open `index.html` and find this line:
```javascript
const BACKEND_URL = 'http://localhost:8000';
```
Replace with your Railway URL:
```javascript
const BACKEND_URL = 'https://nutriflow-production.up.railway.app';
```

Commit and push again:
```bash
git add index.html
git commit -m "Update backend URL to Railway"
git push
```

---

## PART 3 — Deploy Frontend to Vercel (Free)

### Step 1 — Deploy to Vercel
1. Go to 👉 https://vercel.com
2. Sign up with GitHub (free)
3. Click **"Add New Project"**
4. Import your `nutriflow` GitHub repository
5. Framework Preset: **Other**
6. Click **"Deploy"**

### Step 2 — Get Your Live URL
Vercel gives you a URL like:
`https://nutriflow.vercel.app`

✅ Frontend is now live!

---

## PART 4 — PWA Installation (for users)

### On Android (Chrome):
1. Visit your Vercel URL on Chrome
2. Tap the 3-dot menu → **"Add to Home screen"**
3. OR wait 3 seconds — install banner appears automatically
4. Tap **"Install"**

### On iPhone (Safari):
1. Visit your Vercel URL on Safari
2. Tap the **Share** button (box with arrow)
3. Scroll down → **"Add to Home Screen"**
4. Tap **"Add"**

### On Desktop (Chrome/Edge):
1. Visit your Vercel URL
2. Click the install icon in the address bar (📥)
3. Click **"Install"**

---

## PART 5 — Meal Reminders Setup (for users)

1. Open NutriFlow (installed or browser)
2. Scroll to **"🔔 Meal Reminders"** section
3. Toggle the switch ON
4. Allow notifications when browser asks
5. Done! You'll get notified at:
   - 🌅 8:00 AM — Breakfast
   - 🌤️ 1:00 PM — Lunch  
   - 🌆 7:00 PM — Dinner

---

## Interview Talking Points

**Q: What is a PWA?**
A: Progressive Web App — a website that can be installed on a phone like a native app.
It uses a manifest.json (app metadata) and a service worker (background script for caching/offline).

**Q: What is a Service Worker?**
A: A JavaScript file that runs in the background, separate from the main page.
It intercepts network requests, caches assets for offline use, and handles push notifications.

**Q: How do browser notifications work?**
A: We call Notification.requestPermission() to ask the user. If granted, we use
new Notification(title, options) to show a system notification. We use setInterval
to check the time every minute and fire reminders at 8AM, 1PM, 7PM.

**Q: What is Railway? Why not Heroku?**
A: Railway is a modern Platform-as-a-Service (PaaS) that auto-detects Python projects,
installs dependencies, and deploys with zero config. Heroku removed its free tier in 2022.
Railway has a generous free tier perfect for student projects.

**Q: What is Vercel?**
A: Vercel is a frontend hosting platform. It connects to GitHub and auto-deploys
whenever you push code. It serves static files (HTML/CSS/JS) globally via CDN,
making your app fast worldwide. Perfect for frontend-only deployments.