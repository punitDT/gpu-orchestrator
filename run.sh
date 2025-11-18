#!/bin/bash

# GPU Orchestrator startup script

set -e

echo "🚀 Starting GPU Orchestrator..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your actual credentials before running again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run the application
echo "✅ Starting FastAPI application..."
echo "📍 Server will be available at http://localhost:8080"
echo "📚 API docs at http://localhost:8080/docs"
echo ""

python main.py

