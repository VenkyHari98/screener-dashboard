@echo off
title India Stock Screener - Local Mode
echo.
echo  ========================================
echo   India Stock Screener - Local Launcher
echo   Unlimited scans, no GitHub minutes used
echo  ========================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [+] Checking dependencies...
pip install yfinance --quiet 2>nul
pip install pkscreener --quiet 2>nul

:: Start server once (foreground) and open browser after a short delay.
echo [+] Starting local server on http://localhost:5000 ...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000/"

echo.
echo  Dashboard is running at http://localhost:5000/
echo  Press Ctrl+C in this window to stop.
echo.

python server.py
