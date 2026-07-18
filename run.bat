@echo off
echo ===================================================
echo   SmartScan AI - Starting Checkout Counter and Parser
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Create Virtual Environment if not exists
if exist .venv goto :activate_env
echo Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create python virtual environment. Make sure python is in PATH.
    pause
    exit /b 1
)

:activate_env
:: 2. Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: 3. Install requirements
echo Installing/upgrading dependencies (this might take a minute)...
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

:: 4. Generate mock receipt images
echo.
echo Generating sample receipt assets for OCR scanner...
python backend\generate_sample_receipts.py

:: 5. Launch web application in default browser
echo.
echo Launching browser to smart checkout register...
start http://127.0.0.1:8000

:: 6. Run FastAPI application
echo.
echo Starting FastAPI application server on port 8000...
uvicorn backend.main:app --host 127.0.0.1 --port 8000
