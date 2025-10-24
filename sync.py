#!/usr/bin/env python3
"""
Practical tracklist sync that works with real-world limitations
"""
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from app.utils.log import setup_logger

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.models import Track, Playlist
from app.providers.spotify import SpotifyProvider
from app.auth_flow import SpotifyAuth
from app.match import find_matches

def get_tracklist_practical(tracklist_input: str, logger, file_path: str = None) -> Optional[Playlist]:
    """Get tracklist data using practical methods that actually work"""
    
    # Method 1: Try to scrape (likely to fail)
    if tracklist_input.startswith('http'):
        logger.info("🔍 Attempting to scrape tracklist...")
        try:
            from app.providers.tracklist_scraper_selenium import SeleniumTracklistScraper
            with SeleniumTracklistScraper(headless=True) as scraper:
                tracklist = scraper.get_tracklist_info(tracklist_input)
                if tracklist and tracklist.tracks:
                    logger.info(f"✅ Scraping successful: {len(tracklist.tracks)} tracks")
                    return tracklist
        except Exception as e:
            logger.warning(f"⚠️  Scraping failed: {e}")
    
    # Method 2: Direct file input (non-interactive)
    if tracklist_input == 'file':
        logger.info("📁 Using file input mode...")
        return get_tracklist_from_file(logger, file_path)
    
    # Method 3: Manual entry (always works)
    logger.info("📝 Falling back to manual entry...")
    print("\n" + "="*60)
    print("📝 MANUAL TRACKLIST ENTRY")
    print("="*60)
    print("Since automated scraping is blocked, please enter the tracklist manually.")
    print()
    print("Options:")
    print("1. Type 'paste' to paste tracklist text")
    print("2. Type 'file' to import from file")
    print("3. Type 'manual' for interactive entry")
    print("4. Type 'quit' to exit")
    print()
    
    choice = input("Choose option: ").strip().lower()
    
    if choice == 'paste':
        return get_tracklist_from_paste(logger)
    elif choice == 'file':
        return get_tracklist_from_file(logger)
    elif choice == 'manual':
        return get_tracklist_manual(logger)
    elif choice == 'quit':
        return None
    else:
        print("Invalid choice, using manual entry...")
        return get_tracklist_manual(logger)

def get_tracklist_from_paste(logger) -> Optional[Playlist]:
    """Get tracklist from pasted text"""
    print("\n📋 Paste your tracklist text (press Ctrl+D when done):")
    print("Format: Artist - Title (one per line)")
    print("-" * 40)
    
    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n⏹️  Entry cancelled")
        return None
    
    text = '\n'.join(lines)
    return parse_tracklist_text(text, "Pasted Tracklist", logger)

def get_tracklist_from_file(logger, file_path: str = None) -> Optional[Playlist]:
    """Get tracklist from file"""
    if not file_path:
        file_path = input("Enter file path: ").strip()
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Extract tracklist name from first line
        lines = text.strip().split('\n')
        if lines and lines[0].strip():
            tracklist_name = f"{lines[0].strip()} (Tracklist Sync)"
            logger.info(f"📝 Using tracklist name: {tracklist_name}")
        else:
            tracklist_name = f"File: {os.path.basename(file_path)} (Tracklist Sync)"
        
        # Use raw copy parser for better handling of copied text
        return parse_raw_copy_text(text, tracklist_name, logger)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

def get_tracklist_manual(logger) -> Optional[Playlist]:
    """Get tracklist through interactive entry"""
    from app.providers.manual_tracklist import ManualTracklistProvider
    
    provider = ManualTracklistProvider()
    tracklist_name = input("Tracklist name: ").strip() or "Manual Tracklist"
    return provider.get_tracklist_interactive(tracklist_name)

def parse_tracklist_text(text: str, tracklist_name: str, logger) -> Optional[Playlist]:
    """Parse tracklist from text"""
    from app.providers.manual_tracklist import ManualTracklistProvider
    
    provider = ManualTracklistProvider()
    tracklist = provider.get_tracklist_from_text(text, tracklist_name)
    
    if tracklist and tracklist.tracks:
        logger.info(f"✅ Parsed tracklist: {len(tracklist.tracks)} tracks")
        return tracklist
    else:
        logger.error("❌ Failed to parse tracklist")
        return None

def parse_raw_copy_text(text: str, tracklist_name: str, logger) -> Optional[Playlist]:
    """Parse raw copied tracklist text from 1001tracklists"""
    import re
    lines = text.strip().split('\n')
    tracks = []
    
    logger.info("🎵 Parsing raw copied tracklist...")
    
    # Skip the first line (title) and process remaining lines
    track_lines = lines[1:] if len(lines) > 1 else lines
    
    # Process each line to find tracks
    for i, line in enumerate(track_lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Skip obvious non-track lines
        if is_non_track_line(line):
            continue
            
        # Try to extract track from this line
        track = extract_track_from_raw_line(line, i)
        if track:
            tracks.append(track)
            logger.info(f"  ✅ Track {len(tracks)}: {track}")
    
    logger.info(f"✅ Extracted {len(tracks)} tracks")
    
    return Playlist(
        name=tracklist_name,
        tracks=tracks,
        source="raw_copy",
        description="Parsed from raw copied text"
    )

def is_non_track_line(line: str) -> bool:
    """Check if line is clearly not a track"""
    import re
    line_lower = line.lower()
    
    # Skip patterns
    skip_patterns = [
        r'^tracklist media links$',
        r'^youtube$',
        r'^apple music$',
        r'^soundcloud$',
        r'^add$',
        r'^mix with dj\.studio$',
        r'^player 1.*$',
        r'^artwork$',
        r'^artwork placeholder$',
        r'^save \d+$',
        r'^pre-save \d+$',
        r'^biscram$',
        r'^zinderlong$',
        r'^dubshakerz$',
        r'^litchay$',
        r'^guest$',
        r'^like this tracklist$',
        r'^\d+$',  # Just numbers
        r'^\d+:\d+$',  # Time format
        r'^\(\d+\.\d+k\)$',  # User counts
        r'^\[.*\]$',  # Labels in brackets
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, line_lower):
            return True
    
    return False

def extract_track_from_raw_line(line: str, line_number: int) -> Optional[Track]:
    """Extract track from raw copied line"""
    import re
    
    # Skip if too short
    if len(line) < 10:
        return None
    
    # Look for "Artist - Title" pattern
    if ' - ' in line:
        parts = line.split(' - ', 1)
        if len(parts) == 2:
            artist = parts[0].strip()
            title = parts[1].strip()
            
            # Store original title before cleanup (for label extraction)
            original_title = title
            
            # Clean up the title - remove common label/metadata patterns
            # Remove labels with sublabels: LABEL (SUBLABEL) or LABEL/SUBLABEL
            title = re.sub(r'\s+[A-Z][A-Z/\-&\'\s]+\s*\([A-Z][A-Z/\-&\s]+\)$', '', title)
            # Remove single labels at end: AFTERLIFE/INTERSCOPE, BUSTIN', NINJA, etc.
            title = re.sub(r'\s+[A-Z][A-Z/\-&\'\s]+$', '', title)
            # Remove brackets and everything after
            title = re.sub(r'\s*\[.*?\].*$', '', title)
            # Remove "Info Link" and after
            title = re.sub(r'Info Link.*$', '', title)
            # Clean up labels after closing parentheses (but keep remix info)
            title = re.sub(r'\)\s+[A-Z][A-Z/\-&\'\s]+$', ')', title)
            title = title.strip()
            
            # Extract label if present (difference between original and cleaned)
            label = None
            if original_title != title:
                # Label is the removed part
                label_match = re.search(r'\s+([A-Z][A-Z/\-&\'\s()]+)$', original_title)
                if label_match:
                    label = label_match.group(1).strip()
            
            # Skip if either part is too short
            if len(artist) < 2 or len(title) < 2:
                return None
            
            # Skip ID - ID tracks
            if 'ID - ID' in f"{artist} - {title}":
                return None
            
            # Skip if contains unwanted text
            if any(skip in artist.lower() or skip in title.lower() for skip in [
                'artwork', 'save', 'pre-save', 'biscram', 'zinderlong',
                'dubshakerz', 'litchay', 'guest', 'like this'
            ]):
                return None
            
            return Track(
                title=title,
                artist=artist,
                source="raw_copy",
                external_id=f"raw_{line_number}",
                label=label
            )
    
    return None

def sync_tracklist_practical(tracklist_input: str, spotify_playlist_name: str = None, 
                           min_confidence: float = 0.8, dry_run: bool = False,
                           no_duration_filter: bool = False, file_path: str = None):
    """
    Practical tracklist sync that works with real limitations
    """
    logger = setup_logger()
    logger.info(f"🎵 Practical tracklist sync: {tracklist_input}")
    
    # Step 1: Get tracklist data
    logger.info("\n📥 Getting tracklist data...")
    tracklist_playlist = get_tracklist_practical(tracklist_input, logger, file_path)
    
    if not tracklist_playlist:
        logger.error("❌ Failed to get tracklist data")
        return False
    
    logger.info(f"✅ Got tracklist: {tracklist_playlist.name}")
    logger.info(f"📊 Found {len(tracklist_playlist.tracks)} tracks")
    
    # Log extracted tracks summary
    for i, t in enumerate(tracklist_playlist.tracks, 1):
        logger.info(f"  #{i}: {t.artist} - {t.title}")
    
    # Step 2: Authenticate with Spotify
    logger.info("\n🔐 Authenticating with Spotify...")
    auth = SpotifyAuth()
    tokens = auth.authenticate()
    
    # Step 3: Search for tracks on Spotify
    logger.info("\n🔍 Searching for tracks on Spotify...")
    spotify = SpotifyProvider(tokens['access_token'], enable_duration_filter=not no_duration_filter, logger=logger)
    
    all_spotify_tracks = []
    for i, track in enumerate(tracklist_playlist.tracks, 1):
        logger.info(f"  Searching {i}/{len(tracklist_playlist.tracks)}: {track}")
        spotify_tracks = spotify.search_track(track)
        logger.info(f"    → Found {len(spotify_tracks)} candidates for: {track}")
        all_spotify_tracks.extend(spotify_tracks)
    
    logger.info(f"✅ Found {len(all_spotify_tracks)} potential Spotify tracks")
    
    # Step 4: Match tracks
    logger.info("\n🎯 Matching tracks...")
    matches = find_matches(tracklist_playlist.tracks, all_spotify_tracks, min_confidence)
    
    # Analyze results
    exact_matches = [m for m in matches if m.status.value == "exact"]
    fuzzy_matches = [m for m in matches if m.status.value == "fuzzy"]
    no_matches = [m for m in matches if m.status.value == "no_match"]
    
    logger.info(f"📊 Match Results:")
    logger.info(f"  ✅ Exact matches: {len(exact_matches)}")
    logger.info(f"  🔍 Fuzzy matches: {len(fuzzy_matches)}")
    logger.info(f"  ❌ No matches: {len(no_matches)}")
    
    # Show detailed results
    logger.info("\n📋 Detailed Results:")
    for match in matches:
        logger.info(f"  {match}")
    
    # Log unmatched tracks for future reference
    if no_matches:
        logger.warning(f"\n⚠️  UNMATCHED TRACKS ({len(no_matches)} tracks):")
        for match in no_matches:
            logger.warning(f"  ❌ {match.tracklist_track.artist} - {match.tracklist_track.title}")
        logger.warning("💡 These tracks could not be found on Spotify and were not added to the playlist.")
    
    if dry_run:
        logger.info("\n🧪 Dry run - no playlist created")
        return True
    
    # Step 5: Create Spotify playlist
    if not exact_matches and not fuzzy_matches:
        logger.error("\n❌ No matches found - cannot create playlist")
        return False
    
    logger.info(f"\n📝 Creating Spotify playlist...")
    playlist_name = spotify_playlist_name or f"Tracklist Sync: {tracklist_playlist.name}"

    # Check if playlist already exists and overwrite it
    existing_playlists = spotify.get_user_playlists()
    existing_playlist = None
    for playlist in existing_playlists:
        if playlist.name == playlist_name:
            existing_playlist = playlist
            break
    
    if existing_playlist:
        logger.info(f"ℹ️ Playlist '{playlist_name}' already exists. Will overwrite it.")
        playlist_id = existing_playlist.external_id
        spotify.clear_playlist_tracks(playlist_id)
    else:
        logger.info(f"ℹ️ Creating new playlist: {playlist_name}")
        playlist_id = spotify.create_playlist(
            name=playlist_name,
            description=f"Synced tracklist: {tracklist_playlist.name}",
            public=False
        )
    
    if not playlist_id:
        logger.error("❌ Failed to create Spotify playlist")
        return False
    
    logger.info(f"✅ Created playlist: {playlist_name}")
    
    # Step 6: Add tracks to playlist
    logger.info(f"\n➕ Adding tracks to playlist...")
    track_ids = []
    
    # Add exact matches first
    for match in exact_matches:
        if match.spotify_track and match.spotify_track.external_id:
            track_ids.append(match.spotify_track.external_id)
    
    # Add fuzzy matches
    for match in fuzzy_matches:
        if match.spotify_track and match.spotify_track.external_id:
            track_ids.append(match.spotify_track.external_id)
    
    if track_ids:
        success = spotify.add_tracks_to_playlist(playlist_id, track_ids)
        if success:
            logger.info(f"✅ Added {len(track_ids)} tracks to playlist")
        else:
            logger.error("❌ Failed to add some tracks to playlist")
    else:
        logger.warning("⚠️  No tracks to add to playlist")
    
    logger.info(f"\n🎉 Sync complete!")
    if existing_playlist:
        logger.info(f"📱 Check your Spotify app for the updated playlist: {playlist_name}")
    else:
        logger.info(f"📱 Check your Spotify app for the new playlist: {playlist_name}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Practical tracklist sync to Spotify")
    parser.add_argument("tracklist_input", nargs='?', default="manual", 
                       help="Tracklist URL, 'manual', 'paste', 'file', or path to tracklist file")
    parser.add_argument("--name", help="Name for the Spotify playlist")
    parser.add_argument("--confidence", type=float, default=0.8, 
                       help="Minimum confidence for fuzzy matches (0.0-1.0)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Don't actually create the playlist, just show what would happen")
    parser.add_argument("--no-duration-filter", action="store_true",
                       help="Disable duration filtering when evaluating Spotify search results")
    
    args = parser.parse_args()
    
    # Check if tracklist_input is a file path
    if args.tracklist_input and os.path.exists(args.tracklist_input):
        # It's a file path, use it directly
        tracklist_input = "file"
        file_path = args.tracklist_input
    else:
        tracklist_input = args.tracklist_input
        file_path = None
    
    # Load environment variables
    load_dotenv()
    
    # Check if credentials are set
    if not os.getenv('SPOTIFY_CLIENT_ID') or not os.getenv('SPOTIFY_CLIENT_SECRET'):
        print("❌ Spotify credentials not found")
        print("📝 Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file")
        print("🔧 Run: python scripts/setup_env.py")
        return 1
    
    try:
        success = sync_tracklist_practical(
            tracklist_input=tracklist_input,
            spotify_playlist_name=args.name,
            min_confidence=args.confidence,
            dry_run=args.dry_run,
            no_duration_filter=args.no_duration_filter,
            file_path=file_path
        )
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Sync cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
