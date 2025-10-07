#!/bin/bash
# Complete setup script for 1001tracklists-spotify-sync

echo "🎵 Setting up 1001tracklists-Spotify Sync"
echo "=" * 50

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set up environment variables
echo "🔧 Setting up environment..."
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your Spotify credentials"
    echo "   Run: python scripts/setup_env.py"
else
    echo "✅ .env file already exists"
fi

# Test installation
echo "🧪 Testing installation..."
export PYTHONPATH="/Users/davidhey/code/1001tracklists-spotify-sync:$PYTHONPATH"
python scripts/demo_tracklist.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set up Spotify credentials:"
echo "   source activate.sh"
echo "   python scripts/setup_env.py"
echo ""
echo "2. Test the system:"
echo "   source activate.sh"
echo "   python scripts/test_all_scrapers.py"
echo ""
echo "3. Sync a tracklist:"
echo "   source activate.sh"
echo "   python sync_tracklist_robust.py <tracklist_url>"
echo ""
echo "💡 Note: For best results, install ChromeDriver:"
echo "   https://chromedriver.chromium.org/"
