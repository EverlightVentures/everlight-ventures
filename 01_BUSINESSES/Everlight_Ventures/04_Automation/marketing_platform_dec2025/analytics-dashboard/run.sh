#!/bin/bash

# Everlight Ventures Analytics Dashboard Startup Script

echo "🚀 Starting Everlight Ventures Analytics Dashboard..."

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
pip install -r requirements.txt --quiet

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found! Creating from example..."
    cp .env.example .env
    echo "❗ Please edit .env with your DATABASE_URL before continuing."
    echo "   Run: nano .env"
    exit 1
fi

# Run Streamlit
echo "✅ Starting dashboard..."
echo "📊 Dashboard will open at: http://localhost:8501"
echo ""
streamlit run app.py
