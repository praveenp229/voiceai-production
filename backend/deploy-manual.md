# 🚀 Manual Railway Deployment (Recommended)

## Option 1: Railway Web Interface (Easiest)

### Step 1: Push to GitHub
```bash
# In your backend folder
git init
git add .
git commit -m "VoiceAI 2.0 initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/voiceai-backend.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Select your `voiceai-backend` repository
5. Railway auto-detects Python and deploys!

### Step 3: Add Environment Variables
In Railway dashboard:
- Go to **Variables** tab
- Add these variables:
```
OPENAI_API_KEY=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
TWILIO_ACCOUNT_SID=ACd274a72fbd773fef918d075cca0a6043
TWILIO_AUTH_TOKEN=77a9c40bb46fb965f342c92362aee906
TWILIO_PHONE_NUMBER=+18775103029
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./voiceai.db
```

### Step 4: Get Your URL
- Click **"Deployments"** tab
- Copy your app URL (e.g., `https://voiceai-backend-production.up.railway.app`)

---

## Option 2: Ngrok (Quickest for Testing)

### Step 1: Install Ngrok
1. Download from [ngrok.com](https://ngrok.com/download)
2. Extract to a folder
3. Sign up for free account

### Step 2: Start Local Server
```bash
cd C:\Users\prave\Documents\VoiceAI2\backend
python main.py
```

### Step 3: Expose with Ngrok
```bash
# In another terminal
ngrok http 8000
```

### Step 4: Copy Public URL
- Copy the `https://abc123.ngrok.io` URL
- This is your webhook URL!

---

## Option 3: Render (100% Free)

### Step 1: Push to GitHub (same as Railway)

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`

### Step 3: Add Environment Variables
Add the same variables as Railway

---

## 🎯 Recommendation

**For testing:** Use **Ngrok** (fastest setup, 2 minutes)
**For demo/production:** Use **Railway** or **Render** (free tier)

**Which option would you like to try first?**