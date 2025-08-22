@echo off
echo 🚀 Deploying VoiceAI Frontend to Vercel...
echo.
echo ✅ Backend URL: https://voiceai-backend-production-81d6.up.railway.app
echo ✅ Backend Status: Healthy and Running
echo.

REM Check if in frontend directory
if not exist "package.json" (
    echo ❌ Error: Run this script from the frontend directory
    pause
    exit /b 1
)

REM Install Vercel CLI if not installed
where vercel >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 Installing Vercel CLI...
    npm install -g vercel
)

REM Build the project
echo 🔨 Building project...
npm run build

if %errorlevel% neq 0 (
    echo ❌ Build failed. Please fix errors before deploying.
    pause
    exit /b 1
)

echo ✅ Build successful!

REM Deploy to Vercel
echo 🌐 Deploying to Vercel...
vercel --prod

echo.
echo 🎉 Deployment complete!
echo.
echo 📋 Next steps after Vercel deployment:
echo 1. Copy your Vercel URL from the output above
echo 2. Add these environment variables in Vercel Dashboard:
echo    - REACT_APP_API_URL = https://voiceai-backend-production-81d6.up.railway.app
echo    - REACT_APP_ENVIRONMENT = production
echo.
echo 3. Update Railway CORS settings to include your Vercel URL
echo.
echo 🔗 Useful links:
echo - Vercel Dashboard: https://vercel.com/dashboard
echo - Railway Dashboard: https://railway.app/dashboard
echo - Your Backend Health: https://voiceai-backend-production-81d6.up.railway.app/health
echo.
pause