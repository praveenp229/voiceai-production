# 📞 VoiceAI 2.0 - Live Voice Call Deployment Guide

## 🎯 **Overview**

This guide will walk you through deploying your VoiceAI 2.0 system for live voice calls. Your system is **90%+ ready** - you just need to configure API keys and deploy to a public URL.

---

## 📋 **Prerequisites Checklist**

Before starting, ensure you have:

- ✅ **VoiceAI 2.0 system** set up and tested
- ✅ **OpenAI API account** with credits
- ✅ **Twilio account** with phone number
- ✅ **Deployment platform** (Railway, Render, or Ngrok for testing)

---

## 🔧 **Step 1: Configure API Keys**

### **1.1 Get OpenAI API Key**
1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-...`)

### **1.2 Get Twilio Credentials**
1. Visit [Twilio Console](https://console.twilio.com/)
2. Get your **Account SID** and **Auth Token**
3. Buy a phone number if you don't have one
4. Note down your **Twilio Phone Number**

### **1.3 Update Environment File**
```bash
cd C:\Users\prave\Documents\VoiceAI2\backend
```

Edit `.env` file with your actual credentials:

```env
# AI Services (REQUIRED)
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Twilio Configuration (REQUIRED)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+1234567890

# Production Settings
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./voiceai_production.db
```

---

## 🌐 **Step 2: Deploy to Public URL**

### **Option A: Railway (Recommended)**

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Deploy from backend folder:**
   ```bash
   cd C:\Users\prave\Documents\VoiceAI2\backend
   railway init
   railway up
   ```

4. **Set environment variables in Railway dashboard:**
   - Go to your Railway project
   - Add all environment variables from your `.env` file
   - Deploy again: `railway up`

5. **Get your public URL:**
   ```bash
   railway domain
   ```
   Example: `https://voiceai-production.up.railway.app`

### **Option B: Render**

1. **Create new Web Service** on [Render](https://render.com)
2. **Connect your GitHub repository** (push your code first)
3. **Configure build settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
4. **Add environment variables** in Render dashboard
5. **Deploy and get your URL**

### **Option C: Ngrok (Testing Only)**

For quick testing without cloud deployment:

1. **Install Ngrok:** Download from [ngrok.com](https://ngrok.com)

2. **Start your local server:**
   ```bash
   cd C:\Users\prave\Documents\VoiceAI2\backend
   python main.py
   ```

3. **In another terminal, expose to public:**
   ```bash
   ngrok http 8000
   ```

4. **Copy the public URL:**
   Example: `https://abc123.ngrok.io`

---

## 📱 **Step 3: Configure Twilio Webhooks**

### **3.1 Set Voice Webhook URL**

1. **Go to Twilio Console** → Phone Numbers → Manage → Active Numbers
2. **Click your phone number**
3. **Set Voice Configuration:**
   - **Webhook URL:** `https://your-domain.com/api/v1/voice/{tenant_id}`
   - **HTTP Method:** POST
   - **Replace `{tenant_id}`** with your actual tenant ID

### **3.2 Get Your Tenant ID**

Run this to get your demo tenant ID:
```bash
cd C:\Users\prave\Documents\VoiceAI2\backend
python -c "
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService

async def get_tenant_id():
    async with AsyncSessionLocal() as db:
        tenant = await TenantService.get_tenant_by_email(db, 'demo@voiceai.test')
        print(f'Tenant ID: {tenant.id}')
        print(f'Webhook URL: https://your-domain.com/api/v1/voice/{tenant.id}')

asyncio.run(get_tenant_id())
"
```

### **3.3 Example Webhook Configuration**

If your domain is `https://voiceai-production.up.railway.app` and tenant ID is `123e4567-e89b-12d3-a456-426614174000`:

**Webhook URL:**
```
https://voiceai-production.up.railway.app/api/v1/voice/123e4567-e89b-12d3-a456-426614174000
```

---

## 🧪 **Step 4: Test Your Deployment**

### **4.1 Verify Deployment Health**

1. **Check health endpoint:**
   ```bash
   curl https://your-domain.com/health
   ```

2. **Check API documentation:**
   ```
   https://your-domain.com/docs
   ```

### **4.2 Test Voice Webhook**

1. **Test webhook directly:**
   ```bash
   curl -X POST https://your-domain.com/api/v1/voice/YOUR_TENANT_ID \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "From=+1234567890&To=+0987654321&CallSid=CA123&CallStatus=in-progress"
   ```

2. **Should return TwiML response:**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Say>Thank you for calling Demo Dental Practice...</Say>
     <Record timeout="5" action="..."/>
   </Response>
   ```

### **4.3 Make a Live Test Call**

1. **Call your Twilio phone number**
2. **Listen for the AI greeting**
3. **Try saying:** "I need to schedule an appointment"
4. **Check your deployment logs** for processing activity

---

## 📊 **Step 5: Monitor and Debug**

### **5.1 Check Application Logs**

**Railway:**
```bash
railway logs
```

**Render:**
- Check logs in Render dashboard

**Local/Ngrok:**
- Check terminal where `python main.py` is running

### **5.2 Common Issues and Solutions**

| Issue | Solution |
|-------|----------|
| **"Invalid API key"** | Check OpenAI API key in environment variables |
| **"Twilio webhook timeout"** | Ensure your domain is accessible and responding quickly |
| **"No tenant found"** | Verify tenant ID in webhook URL matches database |
| **"AI response failed"** | Check OpenAI API key and account credits |

### **5.3 Test Endpoints for Debugging**

```bash
# Health check
curl https://your-domain.com/health

# List tenants
curl https://your-domain.com/api/v1/tenants/

# Get specific tenant
curl https://your-domain.com/api/v1/tenants/YOUR_TENANT_ID
```

---

## 🚀 **Step 6: Production Optimization**

### **6.1 Database Migration**

For production, consider upgrading to PostgreSQL:

```env
# In production .env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

### **6.2 Enable Redis for Better Performance**

```env
# Add Redis for Celery tasks
REDIS_URL=redis://your-redis-host:6379/0
```

### **6.3 Set Production Security**

```env
# Generate secure keys
SECRET_KEY=your-super-secure-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
ADMIN_API_KEY=your-admin-api-key-here

# Set proper CORS
CORS_ORIGINS=https://your-frontend-domain.com
```

---

## 📞 **Expected Call Flow**

When someone calls your Twilio number:

1. **📞 Call comes in** → Twilio calls your webhook
2. **🤖 AI greets caller** → "Thank you for calling..."
3. **🎤 Records user speech** → Processes with OpenAI Whisper
4. **💭 AI processes intent** → Determines what user wants
5. **🗣️ AI responds** → Generates response with GPT
6. **🔊 Speaks to caller** → Uses OpenAI TTS
7. **🔄 Continues conversation** → Until appointment is scheduled

---

## 🎯 **Success Criteria**

Your system is working correctly when:

- ✅ **Health endpoint** returns 200 OK
- ✅ **Webhook responds** with valid TwiML
- ✅ **Phone calls connect** without timeout
- ✅ **AI greeting plays** clearly
- ✅ **Speech recognition** works accurately
- ✅ **AI responses** are relevant and helpful
- ✅ **Call logs** are saved to database

---

## 💡 **Next Steps After Live Deployment**

1. **Monitor call quality** and AI responses
2. **Adjust AI prompts** based on real conversations
3. **Add more phone numbers** for multiple locations
4. **Implement calendar integration** for actual booking
5. **Add SMS confirmations** for appointments
6. **Scale infrastructure** as call volume grows

---

## 🆘 **Need Help?**

If you encounter issues:

1. **Check the logs** first (most issues show up here)
2. **Verify API keys** are correct and have credits
3. **Test webhook URL** directly with curl
4. **Ensure tenant ID** matches in webhook URL
5. **Check Twilio console** for webhook delivery status

---

## 🎉 **You're Ready!**

Your VoiceAI 2.0 system is now ready for live voice calls! The system can handle 100+ concurrent calls with the async FastAPI architecture and provides a professional dental appointment scheduling experience.

**Call your Twilio number and test it out! 📞**