@echo off
echo [*] Setting up fresh Python environment for Adobe Hackathon Finale...

REM Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv_new" (
    echo [*] Creating new virtual environment 'venv_new'...
    python -m venv venv_new
) else (
    echo [*] 'venv_new' already exists.
)

REM Activate virtual environment
call venv_new\Scripts\activate
REM Upgrade pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [*] Installing dependencies...
call venv_new\Scripts\python backend\scripts\check_hosted_embedding_policy.py
if %errorlevel% neq 0 exit /b %errorlevel%
call venv_new\Scripts\python -m pip install --requirement backend\requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%
call venv_new\Scripts\python -c "import spacy; spacy.load('en_core_web_sm')"
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [OK] Environment setup complete!
echo.
echo To run the backend with this environment:
echo 1. call venv_new\Scripts\activate
echo 2. uvicorn backend.app.main:app --reload --port 8000
echo.
pause
