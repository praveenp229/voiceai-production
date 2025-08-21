@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Railway Deployment
echo ================================================
echo.

cd /d "%~dp0"

echo 🚂 Step 1: Installing Railway CLI...
npm install -g @railway/cli
if errorlevel 1 (
    echo ❌ Failed to install Railway CLI
    echo Please install Node.js first: https://nodejs.org/
    pause
    exit /b 1
)

echo.
echo 🔑 Step 2: Login to Railway...
echo Opening Railway login in browser...
railway login
if errorlevel 1 (
    echo ❌ Login failed or cancelled
    pause
    exit /b 1
)

echo.
echo 📋 Step 3: Deploy to Railway...
echo Note: Railway will automatically detect your app
railway deploy
if errorlevel 1 (
    echo ❌ Deployment failed
    echo Try manual deployment: https://railway.app
    pause
    exit /b 1
)

echo.
echo 🔧 Step 4: Set environment variables...
echo.
echo IMPORTANT: Add these environment variables in Railway dashboard:
echo.
echo   OPENAI_API_KEY=%OPENAI_API_KEY%
echo   TWILIO_ACCOUNT_SID=%TWILIO_ACCOUNT_SID%
echo   TWILIO_AUTH_TOKEN=%TWILIO_AUTH_TOKEN%
echo   TWILIO_PHONE_NUMBER=%TWILIO_PHONE_NUMBER%
echo   ENVIRONMENT=production
echo   DEBUG=false
echo.
echo 📱 Step 5: Get deployment URL...
railway status

echo.
echo Your webhook URL will be:
echo   https://YOUR_DOMAIN/api/v1/voice/YOUR_TENANT_ID
echo.
echo Run 'python get_tenant_info.py' to get your tenant ID
echo.
echo 🎉 Deployment complete! Configure Twilio webhook and test!
echo.
pause