@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Celery Beat Scheduler Startup
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

echo Starting Celery beat scheduler...
echo.
echo ⏰ Scheduled tasks:
echo    • Health checks (every 5 minutes)
echo    • Appointment reminders (every 30 minutes) 
echo    • Cleanup old logs (daily)
echo    • Sync calendars (hourly)
echo.
echo Press Ctrl+C to stop the scheduler
echo.

celery -A app.tasks.celery_app beat --loglevel=info

echo.
echo Beat scheduler stopped.
pause