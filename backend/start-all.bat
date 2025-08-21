@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Complete System Startup
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

echo Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo ❌ Redis not running!
    echo Please start Redis server first
    echo.
    echo Windows: Download from https://redis.io/download
    echo Docker: docker run -p 6379:6379 redis:alpine
    pause
    exit /b 1
)

echo ✅ Redis is running

echo.
echo Starting VoiceAI 2.0 complete system...
echo.
echo This will start:
echo   1. FastAPI server (port 8000)
echo   2. Celery worker (background tasks)
echo   3. Celery beat (scheduled tasks)
echo.
echo 🌐 API will be available at: http://localhost:8000
echo 📚 Documentation: http://localhost:8000/docs
echo 💓 Health check: http://localhost:8000/health
echo.

echo Starting in 3 seconds...
timeout /t 3 >nul

:: Start all services
start "VoiceAI FastAPI" /min python main.py
start "VoiceAI Worker" /min celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
start "VoiceAI Beat" /min celery -A app.tasks.celery_app beat --loglevel=info

echo.
echo ✅ All services started!
echo.
echo Check the individual windows for logs
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping all services...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im celery.exe >nul 2>&1

echo Services stopped.
pause