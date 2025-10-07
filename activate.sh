#!/bin/bash
# Activation script for 1001tracklists-spotify-sync virtual environment

echo "🔧 Activating 1001tracklists-spotify-sync virtual environment..."
source venv/bin/activate
export PYTHONPATH="/Users/davidhey/code/1001tracklists-spotify-sync:$PYTHONPATH"

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
pip list | grep -E "(requests|beautifulsoup4|selenium|rapidfuzz|python-dotenv)"

echo ""
echo "🎵 Available commands:"
echo "  python sync_tracklist_robust.py <tracklist_url>  # Robust sync with fallbacks"
echo "  python scripts/test_all_scrapers.py              # Test all scraping methods"
echo "  python scripts/demo_tracklist.py                 # Demo with sample data"
echo ""
echo "💡 Note: ChromeDriver may be needed for Selenium scraping"
echo "   Download from: https://chromedriver.chromium.org/"
