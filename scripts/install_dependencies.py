#!/usr/bin/env python3
"""
Install dependencies for the 1001tracklists-spotify-sync project
"""
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install required dependencies"""
    print("🔧 Installing dependencies for 1001tracklists-Spotify Sync")
    print("=" * 60)
    
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        print("📦 Installing Python packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        
        print("✅ Dependencies installed successfully!")
        print("\n📋 Next steps:")
        print("1. Set up Spotify credentials: python scripts/setup_env.py")
        print("2. Test the scraper: python scripts/test_complete_workflow.py")
        print("3. Run a sync: python sync_tracklist.py <tracklist_url>")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

if __name__ == "__main__":
    install_dependencies()
