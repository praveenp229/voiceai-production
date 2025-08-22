# Quick Twilio Integration Deployment

## Problem
Railway is running the old backend without Twilio webhooks. Your call gets the default Twilio message because the webhook endpoints don't exist.

## Solution
Deploy the updated backend with Twilio integration.

## Option 1: Railway CLI (Recommended)

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login to Railway:
```bash
railway login
```

3. Link to your project:
```bash
cd backend
railway link
```

4. Deploy:
```bash
railway up
```

## Option 2: GitHub Push (if you can bypass secret scanning)

1. Remove sensitive data from git history:
```bash
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch backend/.env' --prune-empty --tag-name-filter cat -- --all
```

2. Push again:
```bash
git push --force-with-lease origin main
```

## Option 3: Manual File Upload

1. Go to Railway dashboard
2. Settings → Deploy → Manual Deploy
3. Upload these files:
   - `backend/multitenant_saas_app.py` (updated with Twilio)
   - `backend/twilio_integration.py` (new file)
   - `backend/requirements.txt` (should include twilio)

## Verification

After deployment, test:
```bash
curl -X POST https://voiceai-backend-production-81d6.up.railway.app/api/v1/twilio/voice \
  -d "CallSid=test" -d "From=+1234567890" -d "To=+1234567890"
```

Should return TwiML XML, not 404.

## Current Status
- ❌ Railway has old backend (no Twilio webhooks)
- ✅ Local backend has Twilio integration
- ✅ Frontend is deployed and working

## Next Steps
1. Deploy backend using one of the options above
2. Test Twilio call again
3. Check call logs in dashboard