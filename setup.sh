#!/bin/bash
# Setup script for Grok Monitor

echo "🔧 Setting up Grok Monitor..."

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Uninstall old Google SDK if it exists
echo "🧹 Cleaning up old packages..."
pip uninstall -y google-generativeai 2>/dev/null || true

# Install requirements
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Installed packages:"
pip list | grep -E "(google-genai|python-dotenv)"
echo ""
echo "🚀 To run the monitor:"
echo "   source .venv/bin/activate"
echo "   python3 grok_monitor.py"
