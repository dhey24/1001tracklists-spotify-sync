#!/usr/bin/env python3
"""
Setup script to help configure environment variables
"""
import os
from pathlib import Path

def main():
    print("🔧 1001tracklists-Spotify Sync Setup")
    print("=" * 40)
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        print("📄 .env file already exists")
        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("ℹ️  Keeping existing .env file")
            return
    
    print("\n📝 Please provide your Spotify API credentials:")
    print("   Get these from: https://developer.spotify.com/dashboard")
    print()
    
    client_id = input("Spotify Client ID: ").strip()
    client_secret = input("Spotify Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Both Client ID and Client Secret are required")
        return
    
    # Create .env file
    env_content = f"""# Spotify API credentials
SPOTIFY_CLIENT_ID={client_id}
SPOTIFY_CLIENT_SECRET={client_secret}

# Optional: Spotify redirect URI (defaults to http://localhost:8080/callback)
SPOTIFY_REDIRECT_URI=http://localhost:8080/callback

# Optional: Spotify refresh token (if you have one)
# SPOTIFY_REFRESH_TOKEN=your_refresh_token_here
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully!")
    print("\n📋 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the sync: python sync_tracklist.py <tracklist_url>")
    print("\n🎵 Happy syncing!")

if __name__ == "__main__":
    main()
