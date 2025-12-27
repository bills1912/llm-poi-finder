@echo off
REM HeyPico Maps LLM - Windows Start Script
REM Run this script to start all services

echo ==========================================
echo   HeyPico Maps LLM - Starting Services
echo ==========================================
echo.

REM Check if Ollama is running
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Ollama is not running!
    echo Please start Ollama first: ollama serve
    echo.
    pause
    exit /b 1
)
echo [OK] Ollama is running

REM Check for .env file
if not exist "backend\.env" (
    echo [WARNING] backend\.env not found!
    echo Please copy backend\.env.example to backend\.env and add your API keys
    pause
    exit /b 1
)

REM Start Backend
echo.
echo Starting backend server...
cd backend

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate and install dependencies
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM Start uvicorn in new window
start "HeyPico Backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

cd ..

REM Wait for backend
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start Frontend
echo.
echo Starting frontend server...
cd frontend
start "HeyPico Frontend" cmd /k "python -m http.server 3000"
cd ..

echo.
echo ==========================================
echo   All Services Started!
echo ==========================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo Close the terminal windows to stop services.
echo.
pause