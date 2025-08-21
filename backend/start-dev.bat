@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Development Server Startup
echo ================================================
echo.

cd /d "%~dp0"

echo Checking environment...
if not exist ".env" (
    echo ❌ .env file not found!
    echo Please run setup.py first or copy .env.example to .env
    pause
    exit /b 1
)

echo Starting FastAPI development server...
echo.
echo 🚀 Server will be available at:
echo    • API: http://localhost:8000
echo    • Docs: http://localhost:8000/docs  
echo    • Health: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

echo.
echo Server stopped.
pause