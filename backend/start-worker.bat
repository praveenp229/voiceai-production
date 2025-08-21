@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Celery Worker Startup
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

echo Starting Celery worker...
echo.
echo 🔄 Worker queues: voice, notifications, calendar, maintenance
echo 📊 Monitoring: http://localhost:5555 (if Flower is installed)
echo.
echo Press Ctrl+C to stop the worker
echo.

celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

echo.
echo Worker stopped.
pause