@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Environment Configuration
echo ================================================
echo.

cd /d "%~dp0"

echo 🔑 Step 1: Configure API Keys
echo.
echo Please update the .env file with your actual API keys:
echo.
echo   1. OpenAI API Key (required for AI features)
echo   2. Twilio Account SID and Auth Token (required for voice calls)
echo   3. Twilio Phone Number (your purchased Twilio number)
echo.

echo Opening .env file for editing...
notepad .env

echo.
echo 📋 Step 2: Get your tenant information
echo.
echo Running script to get your webhook URL...
python get_tenant_info.py

echo.
echo 🌐 Step 3: Next Steps
echo.
echo After configuring your API keys:
echo   1. Deploy to a public URL (Railway, Render, or Ngrok)
echo   2. Update Twilio webhook with your public URL
echo   3. Test by calling your Twilio number
echo.
echo For detailed instructions, see: LIVE_VOICE_DEPLOYMENT_GUIDE.md
echo.
pause