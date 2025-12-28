#!/usr/bin/env python3
"""
Flask web application for 1001tracklists → Spotify sync
Provides an easy UI for pasting tracklists and syncing to Spotify
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
from flask_caching import Cache
from flask_session import Session
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.models import Track, Playlist
from app.providers.spotify import SpotifyProvider
from app.auth_flow import SpotifyAuth
from app.match import find_matches
from app.utils.log import setup_logger

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production-12345')

# Configure server-side file sessions (fixes cookie size issues)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies in same-site requests
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

# Initialize session
Session(app)

# Set up caching (in-memory, works locally and deployed)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Set up logger
logger = setup_logger()


def get_track_cache_key(track_index, artist, title):
    """Generate a stable cache key for a track based on its content"""
    # Hash the artist and title to create a stable key
    content = f"{artist}::{title}".lower()
    track_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"alt_{track_hash}_{track_index}"


def parse_tracklist_text(text):
    """Parse tracklist from pasted text"""
    import re
    lines = text.strip().split('\n')
    tracks = []
    
    if not lines:
        return None, []
    
    # First line is the playlist name
    playlist_name = lines[0].strip()
    if not playlist_name:
        playlist_name = "Untitled Tracklist"
    
    # Process remaining lines
    track_lines = lines[1:] if len(lines) > 1 else lines
    
    for i, line in enumerate(track_lines, 1):
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Skip non-track lines
        if is_non_track_line(line):
            continue
        
        # Extract track
        track = extract_track_from_line(line, i)
        if track:
            tracks.append(track)
    
    return playlist_name, tracks


def is_non_track_line(line):
    """Check if line is not a track"""
    import re
    line_lower = line.lower()
    
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
        r'^\d+$',
        r'^\d+:\d+$',
        r'^\(\d+\.\d+k\)$',
        r'^\[.*\]$',
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, line_lower):
            return True
    
    return False


def extract_track_from_line(line, line_number):
    """Extract track from line"""
    import re
    
    if ' - ' not in line:
        return None
    
    parts = line.split(' - ', 1)
    if len(parts) != 2:
        return None
    
    artist = parts[0].strip()
    title = parts[1].strip()
    
    # Store original title before cleanup (for label extraction)
    original_title = title
    
    # Clean up title - remove labels
    # Remove labels with sublabels: LABEL (SUBLABEL) or LABEL/SUBLABEL
    title = re.sub(r'\s+[A-ZÀ-ÿ][A-ZÀ-ÿ/\-&\'\s\.]+\s*\([A-ZÀ-ÿ][A-ZÀ-ÿ/\-&\s\.]+\)$', '', title)
    # Remove single labels at end: AFTERLIFE/INTERSCOPE, BUSTIN', NINJA, TEXT REC., CÉCILLE, XL, etc.
    # Handles periods, accented characters, and mixed case
    # Pattern: space(s) + uppercase word(s) (at least 2 chars total) + optional period at end
    title = re.sub(r'\s+[A-ZÀ-ÿ][A-ZÀ-ÿ/\-&\'\s\.]{1,}\.?$', '', title)
    # Remove brackets and everything after
    title = re.sub(r'\s*\[.*?\].*$', '', title)
    # Remove "Info Link" and after
    title = re.sub(r'Info Link.*$', '', title)
    # Clean up labels after closing parentheses (but keep remix info)
    title = re.sub(r'\)\s+[A-ZÀ-ÿ][A-ZÀ-ÿ/\-&\'\s\.]{1,}\.?$', ')', title)
    title = title.strip()
    
    # Extract label if present (difference between original and cleaned)
    label = None
    if original_title != title:
        # Label is the removed part
        label_match = re.search(r'\s+([A-Z][A-Z/\-&\'\s()]+)$', original_title)
        if label_match:
            label = label_match.group(1).strip()
    
    if len(artist) < 2 or len(title) < 2:
        return None
    
    # Skip ID tracks
    if 'ID - ID' in f"{artist} - {title}":
        return None
    
    return Track(
        title=title,
        artist=artist,
        source="web_paste",
        external_id=f"web_{line_number}",
        label=label
    )


@app.route('/')
def index():
    """Main page with paste form"""
    return render_template('index.html')


@app.route('/start_preview', methods=['POST'])
def start_preview():
    """Store preview data in session and return session ID for streaming"""
    try:
        # Don't clear - just overwrite. Session will handle cleanup.
        session.permanent = True
        
        data = request.json
        tracklist_text = data.get('tracklist', '')
        playlist_name_override = data.get('playlist_name', '')
        confidence = float(data.get('confidence', 0.8))
        duration_filter = data.get('duration_filter', True)
        
        # Store in session for the stream endpoint
        session['preview_data'] = {
            'tracklist_text': tracklist_text,
            'playlist_name_override': playlist_name_override,
            'confidence': confidence,
            'duration_filter': duration_filter
        }
        session.modified = True
        
        return jsonify({'status': 'ready'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/preview_stream')
def preview_stream():
    """Preview matches with real-time progress updates via Server-Sent Events"""
    def generate():
        try:
            # Get data from session
            preview_data = session.get('preview_data')
            if not preview_data:
                yield f"data: {json.dumps({'error': 'No preview data in session'})}\n\n"
                return
            
            tracklist_text = preview_data.get('tracklist_text', '')
            playlist_name_override = preview_data.get('playlist_name_override', '')
            confidence = float(preview_data.get('confidence', 0.8))
            duration_filter = preview_data.get('duration_filter', True)
            
            if not tracklist_text:
                yield f"data: {json.dumps({'error': 'No tracklist provided'})}\n\n"
                return
            
            # Parse tracklist
            playlist_name, tracks = parse_tracklist_text(tracklist_text)
            
            if playlist_name_override:
                playlist_name = playlist_name_override
            
            if not tracks:
                yield f"data: {json.dumps({'error': 'No tracks found in tracklist'})}\n\n"
                return
            
            # Add suffix
            playlist_name = f"{playlist_name} (Tracklist Sync)"
            
            # Send initial progress
            yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': len(tracks), 'message': 'Starting search...'})}\n\n"
            
            # Authenticate with Spotify
            auth = SpotifyAuth()
            tokens = auth.authenticate()
            
            spotify = SpotifyProvider(
                tokens['access_token'],
                enable_duration_filter=duration_filter,
                logger=logger
            )
            
            # Search for tracks with progress updates
            logger.info(f"\n🔍 Searching for {len(tracks)} tracks on Spotify...")
            all_spotify_tracks = []
            
            for i, track in enumerate(tracks):
                logger.info(f"  Searching {i+1}/{len(tracks)}: {track.artist} - {track.title}")
                
                # Send progress update
                yield f"data: {json.dumps({'type': 'progress', 'current': i+1, 'total': len(tracks), 'message': f'Searching: {track.artist} - {track.title}'})}\n\n"
                
                spotify_tracks = spotify.search_track(track)
                logger.info(f"    → Found {len(spotify_tracks)} candidates")
                all_spotify_tracks.extend(spotify_tracks)
                
                # Cache top 5 results with stable key
                cache_key = get_track_cache_key(i, track.artist, track.title)
                cache.set(cache_key, spotify_tracks[:5], timeout=3600)
                logger.info(f"    ✅ Cached {len(spotify_tracks[:5])} alternatives (key: {cache_key})")
            
            # Match tracks
            yield f"data: {json.dumps({'type': 'progress', 'current': len(tracks), 'total': len(tracks), 'message': 'Matching tracks...'})}\n\n"
            
            logger.info(f"\n🎯 Matching tracks...")
            matches = find_matches(tracks, all_spotify_tracks, confidence)
            
            # Categorize and log results
            exact_matches = [m for m in matches if m.status.value == "exact"]
            fuzzy_matches = [m for m in matches if m.status.value == "fuzzy"]
            no_matches = [m for m in matches if m.status.value == "no_match"]
            
            logger.info(f"\n📊 Match Results:")
            logger.info(f"  ✅ Exact matches: {len(exact_matches)}")
            logger.info(f"  🔍 Fuzzy matches: {len(fuzzy_matches)}")
            logger.info(f"  ❌ No matches: {len(no_matches)}")
            
            logger.info(f"\n📋 Detailed Match Results:")
            for match in matches:
                if match.spotify_track:
                    logger.info(f"  {match.status.value.upper()}: {match.tracklist_track} → {match.spotify_track} ({match.confidence:.2f})")
                else:
                    logger.info(f"  NO_MATCH: {match.tracklist_track}")
            
            # Format results
            match_results = []
            for i, m in enumerate(matches):
                match_data = {
                    'track_index': i,
                    'tracklist_track': {
                        'artist': m.tracklist_track.artist,
                        'title': m.tracklist_track.title,
                        'label': m.tracklist_track.label
                    },
                    'spotify_track': {
                        'artist': m.spotify_track.artist,
                        'title': m.spotify_track.title,
                        'album': m.spotify_track.album,
                        'id': m.spotify_track.external_id
                    } if m.spotify_track else None,
                    'confidence': m.confidence,
                    'status': m.status.value
                }
                match_results.append(match_data)
            
            results = {
                'type': 'complete',
                'playlist_name': playlist_name,
                'total_tracks': len(tracks),
                'exact_matches': len(exact_matches),
                'fuzzy_matches': len(fuzzy_matches),
                'no_matches': len(no_matches),
                'matches': match_results
            }
            
            # Store in session (mark as permanent to persist across reloads)
            session.permanent = True
            session['tracklist'] = [{'artist': t.artist, 'title': t.title, 'label': t.label} for t in tracks]
            session['playlist_name'] = playlist_name
            session['confidence'] = confidence
            session['duration_filter'] = duration_filter
            session.modified = True  # Force save
            
            logger.info(f"\n💾 Saved to session:")
            logger.info(f"   {len(session['tracklist'])} tracks")
            logger.info(f"   Playlist: {playlist_name}")
            logger.info(f"   Session keys: {list(session.keys())}")
            
            # Send final results
            yield f"data: {json.dumps(results)}\n\n"
            
        except Exception as e:
            logger.error(f"Preview stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/preview', methods=['POST'])
def preview():
    """Preview matches with all candidates for user review"""
    try:
        # Don't clear - just overwrite. Session will handle cleanup.
        session.permanent = True
        
        data = request.json
        tracklist_text = data.get('tracklist', '')
        playlist_name_override = data.get('playlist_name', '')
        confidence = float(data.get('confidence', 0.8))
        duration_filter = data.get('duration_filter', True)
        
        if not tracklist_text:
            return jsonify({'error': 'No tracklist provided'}), 400
        
        # Parse tracklist
        playlist_name, tracks = parse_tracklist_text(tracklist_text)
        
        if playlist_name_override:
            playlist_name = playlist_name_override
        
        if not tracks:
            return jsonify({'error': 'No tracks found in tracklist'}), 400
        
        # Add suffix
        playlist_name = f"{playlist_name} (Tracklist Sync)"
        
        # Authenticate with Spotify
        auth = SpotifyAuth()
        tokens = auth.authenticate()
        
        # Search for tracks on Spotify
        spotify = SpotifyProvider(
            tokens['access_token'],
            enable_duration_filter=duration_filter,
            logger=logger
        )
        
        # Search for tracks on Spotify and cache alternatives
        logger.info(f"\n🔍 Searching for {len(tracks)} tracks on Spotify...")
        all_spotify_tracks = []
        for i, track in enumerate(tracks):
            logger.info(f"  Searching {i+1}/{len(tracks)}: {track.artist} - {track.title}")
            spotify_tracks = spotify.search_track(track)
            logger.info(f"    → Found {len(spotify_tracks)} candidates")
            all_spotify_tracks.extend(spotify_tracks)
            
            # Cache top 5 results with stable key
            cache_key = get_track_cache_key(i, track.artist, track.title)
            cache.set(cache_key, spotify_tracks[:5], timeout=3600)
            logger.info(f"    ✅ Cached {len(spotify_tracks[:5])} alternatives (key: {cache_key})")
        
        # Match tracks
        logger.info(f"\n🎯 Matching tracks...")
        matches = find_matches(tracks, all_spotify_tracks, confidence)
        
        # Categorize results
        exact_matches = [m for m in matches if m.status.value == "exact"]
        fuzzy_matches = [m for m in matches if m.status.value == "fuzzy"]
        no_matches = [m for m in matches if m.status.value == "no_match"]
        
        logger.info(f"\n📊 Match Results:")
        logger.info(f"  ✅ Exact matches: {len(exact_matches)}")
        logger.info(f"  🔍 Fuzzy matches: {len(fuzzy_matches)}")
        logger.info(f"  ❌ No matches: {len(no_matches)}")
        
        # Log detailed results
        logger.info(f"\n📋 Detailed Match Results:")
        for match in matches:
            if match.spotify_track:
                logger.info(f"  {match.status.value.upper()}: {match.tracklist_track} → {match.spotify_track} ({match.confidence:.2f})")
            else:
                logger.info(f"  NO_MATCH: {match.tracklist_track}")
        
        # Format results for JSON with alternatives
        match_results = []
        for i, m in enumerate(matches):
            match_data = {
                'track_index': i,
                'tracklist_track': {
                    'artist': m.tracklist_track.artist,
                    'title': m.tracklist_track.title,
                    'label': m.tracklist_track.label
                },
                'spotify_track': {
                    'artist': m.spotify_track.artist,
                    'title': m.spotify_track.title,
                    'album': m.spotify_track.album,
                    'id': m.spotify_track.external_id
                } if m.spotify_track else None,
                'confidence': m.confidence,
                'status': m.status.value
            }
            match_results.append(match_data)
        
        results = {
            'playlist_name': playlist_name,
            'total_tracks': len(tracks),
            'exact_matches': len(exact_matches),
            'fuzzy_matches': len(fuzzy_matches),
            'no_matches': len(no_matches),
            'matches': match_results
        }
        
        # Store minimal data in session (just track info, no alternatives pre-loaded)
        session.permanent = True
        session['tracklist'] = [{'artist': t.artist, 'title': t.title, 'label': t.label} for t in tracks]
        session['playlist_name'] = playlist_name
        session['confidence'] = confidence
        session['duration_filter'] = duration_filter
        session.modified = True  # Force save
        
        logger.info(f"\n💾 Saved to session:")
        logger.info(f"   {len(session['tracklist'])} tracks")
        logger.info(f"   Playlist: {playlist_name}")
        logger.info(f"   Session keys: {list(session.keys())}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sync', methods=['POST'])
def sync():
    """Create Spotify playlist"""
    try:
        data = request.json
        tracklist_text = data.get('tracklist', '')
        playlist_name_override = data.get('playlist_name', '')
        confidence = float(data.get('confidence', 0.8))
        duration_filter = data.get('duration_filter', True)
        
        if not tracklist_text:
            return jsonify({'error': 'No tracklist provided'}), 400
        
        # Parse tracklist
        playlist_name, tracks = parse_tracklist_text(tracklist_text)
        
        if playlist_name_override:
            playlist_name = playlist_name_override
        
        if not tracks:
            return jsonify({'error': 'No tracks found in tracklist'}), 400
        
        # Add suffix
        playlist_name = f"{playlist_name} (Tracklist Sync)"
        
        # Authenticate with Spotify
        auth = SpotifyAuth()
        tokens = auth.authenticate()
        
        # Search for tracks on Spotify
        spotify = SpotifyProvider(
            tokens['access_token'],
            enable_duration_filter=duration_filter,
            logger=logger
        )
        
        all_spotify_tracks = []
        for track in tracks:
            spotify_tracks = spotify.search_track(track)
            all_spotify_tracks.extend(spotify_tracks)
        
        # Match tracks
        matches = find_matches(tracks, all_spotify_tracks, confidence)
        
        # Get matched tracks
        exact_matches = [m for m in matches if m.status.value == "exact"]
        fuzzy_matches = [m for m in matches if m.status.value == "fuzzy"]
        
        if not exact_matches and not fuzzy_matches:
            return jsonify({'error': 'No matches found - cannot create playlist'}), 400
        
        # Check if playlist exists
        existing_playlists = spotify.get_user_playlists()
        existing_playlist = None
        for playlist in existing_playlists:
            if playlist.name == playlist_name:
                existing_playlist = playlist
                break
        
        # Create or update playlist
        if existing_playlist:
            playlist_id = existing_playlist.external_id
            spotify.clear_playlist_tracks(playlist_id)
            action = "updated"
        else:
            playlist_id = spotify.create_playlist(
                name=playlist_name,
                description=f"Synced from 1001tracklists",
                public=False
            )
            action = "created"
        
        if not playlist_id:
            return jsonify({'error': 'Failed to create playlist'}), 500
        
        # Add tracks to playlist
        track_ids = []
        for match in exact_matches + fuzzy_matches:
            if match.spotify_track and match.spotify_track.external_id:
                track_ids.append(match.spotify_track.external_id)
        
        if track_ids:
            success = spotify.add_tracks_to_playlist(playlist_id, track_ids)
            if not success:
                return jsonify({'error': 'Failed to add tracks to playlist'}), 500
        
        return jsonify({
            'success': True,
            'action': action,
            'playlist_name': playlist_name,
            'tracks_added': len(track_ids),
            'playlist_id': playlist_id
        })
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/get_alternatives', methods=['POST'])
def get_alternatives():
    """Get alternative matches for a specific track - uses cache when available"""
    try:
        data = request.json
        track_index = int(data.get('track_index', 0))
        
        # Debug: Log session contents
        logger.info(f"🔍 Getting alternatives for track {track_index}")
        logger.info(f"   Session keys: {list(session.keys())}")
        logger.info(f"   Session ID: {id(session)}")
        
        # Get the original tracklist track info from session
        tracklist = session.get('tracklist', [])
        logger.info(f"   Tracklist in session: {len(tracklist)} tracks")
        
        if track_index < len(tracklist):
            tracklist_track = tracklist[track_index]
            logger.info(f"   Found track: {tracklist_track}")
        else:
            # Fallback if index is out of bounds
            logger.warning(f"❌ Track index {track_index} out of bounds, tracklist length: {len(tracklist)}")
            logger.warning(f"   Available session data: {session.keys()}")
            return jsonify({'error': 'Track not found in session'}), 404
        
        # Ensure we have the required fields
        if not tracklist_track or 'artist' not in tracklist_track or 'title' not in tracklist_track:
            logger.error(f"Invalid track data: {tracklist_track}")
            return jsonify({'error': 'Invalid track data'}), 400
        
        # Try to get from cache first  
        cache_key = get_track_cache_key(track_index, tracklist_track['artist'], tracklist_track['title'])
        cached_tracks = cache.get(cache_key)
        
        if cached_tracks:
            logger.info(f"✅ Using cached alternatives for track {track_index}")
            alternatives = [
                {
                    'artist': t.artist,
                    'title': t.title,
                    'album': t.album,
                    'id': t.external_id
                }
                for t in cached_tracks
            ]
        else:
            # Cache miss - do a fresh search
            logger.info(f"🔍 Cache miss, searching for alternatives for track {track_index}")
            
            auth = SpotifyAuth()
            tokens = auth.authenticate()
            
            spotify = SpotifyProvider(
                tokens['access_token'],
                enable_duration_filter=session.get('duration_filter', True),
                logger=logger
            )
            
            # Create track object for search
            from app.models import Track
            search_track = Track(
                title=tracklist_track['title'],
                artist=tracklist_track['artist'],
                label=tracklist_track.get('label'),
                source="alternatives_search"
            )
            
            # Search and cache results
            spotify_tracks = spotify.search_track(search_track)
            cache.set(cache_key, spotify_tracks[:5], timeout=3600)
            
            alternatives = [
                {
                    'artist': t.artist,
                    'title': t.title,
                    'album': t.album,
                    'id': t.external_id
                }
                for t in spotify_tracks[:5]
            ]
        
        return jsonify({
            'track_index': track_index,
            'tracklist_track': tracklist_track,
            'alternatives': alternatives
        })
        
    except Exception as e:
        logger.error(f"Get alternatives error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/search_custom', methods=['POST'])
def search_custom():
    """Search Spotify with custom query (edited by user)"""
    try:
        data = request.json
        track_index = int(data.get('track_index', 0))
        custom_title = data.get('title', '')
        custom_artist = data.get('artist', '')
        
        if not custom_title or not custom_artist:
            return jsonify({'error': 'Title and artist required'}), 400
        
        # Authenticate with Spotify
        auth = SpotifyAuth()
        tokens = auth.authenticate()
        
        # Search with custom query
        spotify = SpotifyProvider(
            tokens['access_token'],
            enable_duration_filter=session.get('duration_filter', True),
            logger=logger
        )
        
        # Create temporary track for search
        from app.models import Track
        search_track = Track(
            title=custom_title,
            artist=custom_artist,
            source="custom_search"
        )
        
        spotify_tracks = spotify.search_track(search_track)
        
        # Cache the custom search results with stable key (based on edited query)
        cache_key = get_track_cache_key(track_index, custom_artist, custom_title)
        cache.set(cache_key, spotify_tracks[:5], timeout=3600)
        logger.info(f"✅ Cached custom search results for track {track_index} (key: {cache_key})")
        
        alternatives = [
            {
                'artist': t.artist,
                'title': t.title,
                'album': t.album,
                'id': t.external_id
            }
            for t in spotify_tracks[:5]
        ]
        
        return jsonify({
            'track_index': track_index,
            'alternatives': alternatives
        })
        
    except Exception as e:
        logger.error(f"Custom search error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/confirm', methods=['POST'])
def confirm():
    """Create playlist with user-confirmed tracks"""
    try:
        data = request.json
        selected_tracks = data.get('tracks', [])  # List of {track_index, spotify_id}
        
        if not selected_tracks:
            return jsonify({'error': 'No tracks selected'}), 400
        
        # Get playlist info from session
        playlist_name = session.get('playlist_name')
        if not playlist_name:
            return jsonify({'error': 'Session expired, please preview again'}), 400
        
        # Authenticate with Spotify
        auth = SpotifyAuth()
        tokens = auth.authenticate()
        
        spotify = SpotifyProvider(
            tokens['access_token'],
            enable_duration_filter=session.get('duration_filter', True),
            logger=logger
        )
        
        # Check if playlist exists
        existing_playlists = spotify.get_user_playlists()
        existing_playlist = None
        for playlist in existing_playlists:
            if playlist.name == playlist_name:
                existing_playlist = playlist
                break
        
        # Create or update playlist
        if existing_playlist:
            playlist_id = existing_playlist.external_id
            spotify.clear_playlist_tracks(playlist_id)
            action = "updated"
        else:
            playlist_id = spotify.create_playlist(
                name=playlist_name,
                description=f"Synced from 1001tracklists",
                public=False
            )
            action = "created"
        
        if not playlist_id:
            return jsonify({'error': 'Failed to create playlist'}), 500
        
        # Add selected tracks to playlist
        track_ids = [t['spotify_id'] for t in selected_tracks if t.get('spotify_id')]
        
        if track_ids:
            success = spotify.add_tracks_to_playlist(playlist_id, track_ids)
            if not success:
                return jsonify({'error': 'Failed to add tracks to playlist'}), 500
        
        return jsonify({
            'success': True,
            'action': action,
            'playlist_name': playlist_name,
            'tracks_added': len(track_ids),
            'playlist_id': playlist_id
        })
        
    except Exception as e:
        logger.error(f"Confirm error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # Check if credentials are set
    if not os.getenv('SPOTIFY_CLIENT_ID') or not os.getenv('SPOTIFY_CLIENT_SECRET'):
        print("❌ Spotify credentials not found")
        print("📝 Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file")
        print("🔧 Run: python scripts/setup_env.py")
        sys.exit(1)
    
    print("\n🎵 1001tracklists → Spotify Sync Web UI")
    print("🌐 Starting server...")
    print("📱 Open http://127.0.0.1:5000 in your browser")
    print("🛑 Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)

