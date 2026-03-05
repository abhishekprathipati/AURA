@echo off
echo ========================================
echo    AURA - Student Wellness Platform
echo ========================================
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: .venv not found, using system Python
)

REM Check argument: dev or prod (default: dev)
set MODE=%1
if "%MODE%"=="" set MODE=dev

if "%MODE%"=="prod" (
    echo Mode: PRODUCTION
    echo Server: waitress
    echo.
    python wsgi.py
) else (
    echo Mode: DEVELOPMENT
    echo Server: Flask dev (debug=on)
    echo URL: http://localhost:5000
    echo.
    set FLASK_DEBUG=true
    python run.py
)

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo ERROR: Application crashed! Check logs above.
    pause
)
