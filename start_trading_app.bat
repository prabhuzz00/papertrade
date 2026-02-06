@echo off
REM NIFTY 50 Live Trading Application Launcher
REM Quick launch script for Windows

echo ================================================================
echo   NIFTY 50 LIVE TRADING APPLICATION
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.7 or later from python.org
    pause
    exit /b 1
)

echo Python detected: 
python --version
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo.
    echo PyQt5 not installed. Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies
        echo Please run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
)

echo.
echo ================================================================
echo   Starting Trading Application...
echo ================================================================
echo.
echo [Press Ctrl+C to stop the application]
echo.

REM Launch the application
python trading_app.py

if errorlevel 1 (
    echo.
    echo ================================================================
    echo   Application closed with error
    echo ================================================================
    echo.
    echo Troubleshooting:
    echo   1. Run test: python test_components.py
    echo   2. Check logs above for errors
    echo   3. Verify internet connection
    echo.
    pause
) else (
    echo.
    echo ================================================================
    echo   Application closed successfully
    echo ================================================================
    echo.
)

pause
