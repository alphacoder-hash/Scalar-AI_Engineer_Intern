@echo off
echo ============================================================
echo    Sam - AI Persona for Vaibhav Pandey
echo    Scaler AI Engineer Screening Assignment
echo ============================================================
echo.

echo Step 1: Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies!
    pause
    exit /b 1
)

echo.
echo Step 2: Running data ingestion...
python scripts\ingest_data_groq.py
if %errorlevel% neq 0 (
    echo Error during data ingestion!
    pause
    exit /b 1
)

echo.
echo Step 3: Starting backend server...
echo.
echo Backend will start at: http://localhost:8000
echo Chat API: http://localhost:8000/chat
echo Health check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
