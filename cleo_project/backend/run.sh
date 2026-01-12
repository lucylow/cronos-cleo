#!/bin/bash
# Startup script for C.L.E.O. backend

echo "Starting C.L.E.O. Backend API..."
echo "Make sure you've installed dependencies: pip install -r requirements.txt"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Using defaults."
    echo "Copy .env.example to .env to customize settings."
    echo ""
fi

# Run the server
python main.py

