@echo off
title India Stock Screener - Local Mode
echo.
echo  ========================================
echo   India Stock Screener - Local Launcher
echo   Unlimited scans, no GitHub minutes used
echo  ========================================
echo.

cd /d "%~dp0"

:: Resolve Python interpreter (prefer 3.11 because pkscreener is installed there)
set "PYTHON_EXE="
py -3.11 -c "import sys; print(sys.version)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -3.11"
) else (
    py -3 -c "import sys; print(sys.version)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py -3"
    ) else (
        python --version >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
            pause
            exit /b 1
        )
        set "PYTHON_EXE=python"
    )
)

echo [+] Using interpreter: %PYTHON_EXE%

:: Install dependencies if needed
echo [+] Checking dependencies...
%PYTHON_EXE% -m pip install yfinance --quiet 2>nul
%PYTHON_EXE% -m pip install pkscreener --quiet 2>nul

:: Pre-flight checks
echo.
echo [+] Running pre-flight checks...

%PYTHON_EXE% -c "import pkscreener" >nul 2>&1
if errorlevel 1 (
    echo [WARN] pkscreener not importable with %PYTHON_EXE% — scans may fail.
) else (
    echo [OK]  pkscreener importable.
)

netstat -ano | findstr ":5000 " >nul 2>&1
if not errorlevel 1 (
    echo [WARN] Port 5000 already in use — server may fail to start.
) else (
    echo [OK]  Port 5000 is free.
)

echo.

:: Start server once (foreground) and open browser after a short delay.
echo [+] Starting local server on http://localhost:5000 ...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000/"

echo.
echo  Dashboard is running at http://localhost:5000/
echo  Press Ctrl+C in this window to stop.
echo.

%PYTHON_EXE% server.py
