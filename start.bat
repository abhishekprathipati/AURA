@echo off
echo ========================================
echo    AURA - Student Wellness Platform
echo    Starting Application...
echo ========================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if MongoDB is required
echo Checking dependencies...

REM Display startup info
echo.
echo Environment: Development
echo Port: 5000
echo URL: http://localhost:5000
echo.
echo ========================================
echo Application starting...
echo ========================================
echo.

REM Run the application
python run.py

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Application crashed!
    echo Check the logs above for details.
    echo ========================================
    pause
)
