@echo off
echo.
echo ================================================
echo   VoiceAI 2.0 - Quick Setup and Test
echo ================================================
echo.

cd /d "%~dp0"

echo 📋 Step 1: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo 📋 Step 2: Initializing database...
python init_db.py
if errorlevel 1 (
    echo ❌ Database initialization failed
    pause
    exit /b 1
)

echo.
echo 📋 Step 3: Running implementation tests...
python test_implementation.py

echo.
echo 📋 Step 4: Ready to start!
echo.
echo To start the system:
echo   python main.py                 (FastAPI server)
echo   start-worker.bat              (Celery worker - optional)
echo   start-all.bat                 (Everything at once)
echo.
echo Visit: http://localhost:8000/docs
echo.
pause