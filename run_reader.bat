@echo off
setlocal enabledelayedexpansion
title StoryCrafter Reader Launcher

echo ========================================================
echo        StoryCrafter Sleek Desktop Book Reader
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Ensure .gitignore excludes .venv
if not exist ".gitignore" (
    echo .venv/ > .gitignore
    echo venv/ >> .gitignore
    echo __pycache__/ >> .gitignore
    echo *.py[cod] >> .gitignore
    echo .reader_config.json >> .gitignore
    echo [GIT] Created .gitignore with .venv excluded.
) else (
    findstr /i "\.venv" .gitignore >nul 2>&1
    if errorlevel 1 (
        echo.>> .gitignore
        echo .venv/ >> .gitignore
        echo [GIT] Added .venv to .gitignore.
    )
)

:: 2. Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARN] Python not found in PATH.
        echo [SETUP] Attempting silent installation via winget...
        winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo [ERROR] Automatic Python installation failed. Please install Python 3.10+ from python.org.
            pause
            exit /b 1
        )
    )
)

:: 3. Create .venv if not present
if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment (.venv)...
    python -m venv .venv 2>nul || py -m venv .venv 2>nul
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: 4. Install dependencies inside .venv
if exist "requirements.txt" (
    echo [SETUP] Verifying dependencies...
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

:: 5. Launch Reader App
echo [LAUNCH] Starting StoryCrafter Desktop Reader...
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" reader_app.py
) else (
    ".venv\Scripts\python.exe" reader_app.py
)

exit /b 0
