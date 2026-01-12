@echo off
REM Startup script for C.L.E.O. backend (Windows)

echo Starting C.L.E.O. Backend API...
echo Make sure you've installed dependencies: pip install -r requirements.txt
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found. Using defaults.
    echo Copy .env.example to .env to customize settings.
    echo.
)

REM Run the server
python main.py

