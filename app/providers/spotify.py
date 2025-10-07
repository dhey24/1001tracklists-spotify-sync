import os, webbrowser, time, json, re
import requests
from typing import List, Optional, Dict, Any
from ..models import Track, Playlist
from ..auth_flow import SpotifyAuth

class SpotifyProvider:
    """Handle Spotify API operations"""
    VERSION = "1.3-ext-fastpath"
    
    def __init__(self, access_token: Optional[str] = None, enable_duration_filter: bool = True, logger=None):
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.session = requests.Session()
        self.enable_duration_filter = enable_duration_filter
        self.logger = logger
        
        if access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}'
            })
        # Version banner to confirm runtime code path in logs
        try:
            banner_msg = f"🆔 SpotifyProvider {self.VERSION} | duration_filter={'on' if self.enable_duration_filter else 'off'} | ext_mix_fastpath=on"
            if self.logger:
                self.logger.info(banner_msg)
            else:
                print(banner_msg)
        except Exception:
            pass
    
    def set_access_token(self, access_token: str):
        """Set or update the access token"""
        self.access_token = access_token
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}'
        })
    
    def search_track(self, track: Track) -> List[Track]:
        """Search for a track on Spotify with enhanced matching.
        Strategy: ISRC first (when available), then fall back to text queries
        and duration filtering.
        """
        if not self.access_token:
            raise ValueError("Access token not set")
        
        # Normalize obviously malformed titles before any querying
        normalized_title = track.title
        if isinstance(normalized_title, str) and "(" in normalized_title:
            # If there's an opening parenthesis with no closing one after it, add a closing
            open_idx = normalized_title.rfind("(")
            if open_idx != -1 and ")" not in normalized_title[open_idx:]:
                normalized_title = normalized_title + ")"
        # Collapse stray whitespace
        if isinstance(normalized_title, str):
            normalized_title = re.sub(r"\s+", " ", normalized_title).strip()
        if normalized_title != track.title:
            norm_msg = f"🧼 Normalized title: '{track.title}' → '{normalized_title}'"
            if self.logger:
                self.logger.info(norm_msg)
            else:
                print(norm_msg)
            track = Track(
                title=normalized_title,
                artist=track.artist,
                album=track.album,
                duration=track.duration,
                external_id=track.external_id,
                source=track.source,
                isrc=track.isrc,
                mix_name=track.mix_name,
                label=track.label,
                year=track.year,
                remixers=track.remixers or [],
            )
        
        # Strategy 1: ISRC search (exact when available in Spotify catalog)
        if track.isrc:
            try:
                isrc_results = self._search_by_isrc(track.isrc)
                if isrc_results:
                    print(f"✅ ISRC hit for {track}: {track.isrc}")
                    return isrc_results
                else:
                    print(f"ℹ️ No ISRC hit for {track.isrc}; falling back to text search")
            except Exception as e:
                print(f"⚠️ ISRC lookup error for {track.isrc}: {e}")

        # Strategy 1.5: For Extended Mix tracks without ISRC hits, immediately strip Extended Mix
        if track.mix_name and 'extended' in track.mix_name.lower():
            ext_msg = f"🎯 Extended Mix detected - immediately stripping Extended Mix for search..."
            if self.logger:
                self.logger.info(ext_msg)
            else:
                print(ext_msg)
            base_title = self._strip_extended_from_title(track.title)
            if base_title != track.title:
                base_msg = f"ℹ️ Searching for base track: '{track.title}' → '{base_title}'"
                if self.logger:
                    self.logger.info(base_msg)
                else:
                    print(base_msg)
                
                # Create a modified track with the base title
                base_track = Track(
                    title=base_title,
                    artist=track.artist,
                    album=track.album,
                    duration=track.duration,
                    external_id=track.external_id,
                    source=track.source,
                    isrc=track.isrc,
                    mix_name=None,  # Remove mix name for base search
                    label=track.label,
                    year=track.year,
                    remixers=track.remixers or [],
                )
                
                # Search with the base track
                base_queries = self._build_enhanced_queries(base_track)
                for i, query in enumerate(base_queries):
                    try:
                        print(f"🎯 Base track query {i+1}/{len(base_queries)}: {query}")
                        params = { 'q': query, 'type': 'track', 'limit': 50 }
                        response = self.session.get(f"{self.base_url}/search", params=params)
                        response.raise_for_status()
                        data = response.json()
                        spotify_tracks = []
                        for item in data.get('tracks', {}).get('items', []):
                            spotify_tracks.append(Track(
                                title=item['name'],
                                artist=', '.join([a['name'] for a in item['artists']]),
                                album=item['album']['name'],
                                duration=item['duration_ms'] // 1000,
                                external_id=item['id'],
                                year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                                source="spotify",
                            ))
                        if spotify_tracks:
                            # Accept any results for base track search (no duration filtering)
                            print(f"✅ Found {len(spotify_tracks)} results with base track search: {query}")
                            return spotify_tracks
                    except Exception as e:
                        print(f"❌ Error with base track query '{query}': {e}")

        # Strategy 2: Enhanced queries with metadata
        queries = self._build_enhanced_queries(track)
           
        for i, query in enumerate(queries):
            try:
                print(f"🔍 Trying query {i+1}/{len(queries)}: {query}")
                params = {
                    'q': query,
                    'type': 'track',
                    'limit': 50  # Get more results for better filtering
                }
                
                response = self.session.get(f"{self.base_url}/search", params=params)
                response.raise_for_status()
                
                data = response.json()
                spotify_tracks = []
                
                for item in data.get('tracks', {}).get('items', []):
                    spotify_track = Track(
                        title=item['name'],
                        artist=', '.join([artist['name'] for artist in item['artists']]),
                        album=item['album']['name'],
                        duration=item['duration_ms'] // 1000,  # Convert to seconds
                        external_id=item['id'],
                        year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                        source="spotify"
                    )
                    spotify_tracks.append(spotify_track)
                
                if spotify_tracks:
                    # Prefer exact title and artist overlap before any duration filtering
                    preferred = self._prefer_exact_title_and_artist(spotify_tracks, track)
                    if preferred:
                        print(f"✅ Found {len(preferred)} preferred results (exact title/artist overlap) for query: {query}")
                        return preferred
                    # Filter by duration if enabled
                    use_duration_filter = self.enable_duration_filter
                    # If mix explicitly says Extended, relax duration filtering
                    if track.mix_name and 'extended' in track.mix_name.lower():
                        use_duration_filter = False
                    filtered_tracks = (
                        self._filter_by_duration(spotify_tracks, track)
                        if use_duration_filter else spotify_tracks
                    )
                    if filtered_tracks:
                        print(f"✅ Found {len(filtered_tracks)} results with query: {query}")
                        return filtered_tracks
                    else:
                        print(f"❌ No duration matches for query: {query}")
                else:
                    print(f"❌ No results for query: {query}")
                    
            except Exception as e:
                print(f"❌ Error with query '{query}': {e}")
                continue
        
        # Fallback A: Try per-artist variants in case Spotify lists a different primary artist
        individual_artists = []
        if track.artist:
            # Split on commas and ampersands, preserve '+' (e.g., 'Sultan + Shepard')
            individual_artists = [a.strip() for a in re.split(r",|&", track.artist) if a.strip()]
        if individual_artists:
            per_artist_queries = []
            title_plain = f'"{track.title}"'
            title_with_mix = None
            if track.mix_name and track.mix_name != "Original Mix":
                # Check if mix name is already in the title to avoid double parentheses
                if f"({track.mix_name})" in track.title or f"({track.mix_name}" in track.title:
                    title_with_mix = f'"{track.title}"'
                else:
                    title_with_mix = f'"{track.title} ({track.mix_name})"'
            for artist_name in individual_artists:
                per_artist_queries.append(f"{title_plain} artist:\"{artist_name}\"")
                if title_with_mix:
                    per_artist_queries.append(f"{title_with_mix} artist:\"{artist_name}\"")

            for i, query in enumerate(per_artist_queries):
                try:
                    print(f"👤 Per-artist fallback {i+1}/{len(per_artist_queries)}: {query}")
                    params = { 'q': query, 'type': 'track', 'limit': 50 }
                    response = self.session.get(f"{self.base_url}/search", params=params)
                    response.raise_for_status()
                    data = response.json()
                    spotify_tracks = []
                    for item in data.get('tracks', {}).get('items', []):
                        spotify_tracks.append(Track(
                            title=item['name'],
                            artist=', '.join([a['name'] for a in item['artists']]),
                            album=item['album']['name'],
                            duration=item['duration_ms'] // 1000,
                            external_id=item['id'],
                            year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                            source="spotify",
                        ))
                    if spotify_tracks:
                        # Do NOT duration-filter in per-artist fallback
                        print(f"✅ Found {len(spotify_tracks)} results with per-artist fallback: {query}")
                        return spotify_tracks
                    else:
                        print(f"❌ No results for per-artist fallback: {query}")
                except Exception as e:
                    print(f"❌ Error with per-artist fallback '{query}': {e}")

        # Strategy 2.5: Extended Mix Special Handling - try base track search as fallback
        if track.mix_name and 'extended' in track.mix_name.lower():
            ext_msg = f"🎯 Extended Mix detected - trying base track search as fallback..."
            if self.logger:
                self.logger.info(ext_msg)
            else:
                print(ext_msg)
            base_title = self._strip_extended_from_title(track.title)
            if base_title != track.title:
                base_msg = f"ℹ️ Searching for base track: '{track.title}' → '{base_title}'"
                if self.logger:
                    self.logger.info(base_msg)
                else:
                    print(base_msg)
                
                # Try base title with artists
                base_queries = [
                    f'"{base_title}" artist:"{track.artist}"',
                    f'"{base_title}" {track.artist}',
                    f'"{base_title}"'
                ]
                
                # Add per-artist variants for base title
                individual_artists = []
                if track.artist:
                    individual_artists = [a.strip() for a in re.split(r",|&", track.artist) if a.strip()]
                
                for artist_name in individual_artists:
                    base_queries.append(f'"{base_title}" artist:"{artist_name}"')
                    base_queries.append(f'"{base_title}" "{artist_name}"')
                
                for i, query in enumerate(base_queries):
                    try:
                        print(f"🎯 Base track query {i+1}/{len(base_queries)}: {query}")
                        params = { 'q': query, 'type': 'track', 'limit': 50 }
                        response = self.session.get(f"{self.base_url}/search", params=params)
                        response.raise_for_status()
                        data = response.json()
                        spotify_tracks = []
                        for item in data.get('tracks', {}).get('items', []):
                            spotify_tracks.append(Track(
                                title=item['name'],
                                artist=', '.join([a['name'] for a in item['artists']]),
                                album=item['album']['name'],
                                duration=item['duration_ms'] // 1000,
                                external_id=item['id'],
                                year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                                source="spotify",
                            ))
                        if spotify_tracks:
                            # Accept any results for base track search (no duration filtering)
                            print(f"✅ Found {len(spotify_tracks)} results with base track search: {query}")
                            return spotify_tracks
                    except Exception as e:
                        print(f"❌ Error with base track query '{query}': {e}")

        # Fallback: if mix contains length qualifiers (e.g., Extended, Edit, Club Mix),
        # try again with a trimmed mix name and relaxed matching.
        if track.mix_name:
            trimmed = self._strip_length_qualifiers(track.mix_name)
            if trimmed != track.mix_name:
                print(f"ℹ️ Retrying with trimmed mix name: '{track.mix_name}' → '{trimmed}'")
                track_fallback = Track(
                    title=track.title,
                    artist=track.artist,
                    album=track.album,
                    duration=track.duration,
                    external_id=track.external_id,
                    source=track.source,
                    isrc=track.isrc,
                    mix_name=trimmed,
                    label=track.label,
                    year=track.year,
                    remixers=track.remixers or [],
                )
                queries2 = self._build_enhanced_queries(track_fallback)
                # Also add title + primary remixer keyword if available
                primary_remixer = self._primary_remixer_from_mix(trimmed)
                if primary_remixer:
                    queries2.append(f'"{track.title}" "{primary_remixer}"')
                for i, query in enumerate(queries2):
                    try:
                        print(f"🔁 Fallback query {i+1}/{len(queries2)}: {query}")
                        params = { 'q': query, 'type': 'track', 'limit': 50 }
                        response = self.session.get(f"{self.base_url}/search", params=params)
                        response.raise_for_status()
                        data = response.json()
                        spotify_tracks = []
                        for item in data.get('tracks', {}).get('items', []):
                            spotify_tracks.append(Track(
                                title=item['name'],
                                artist=', '.join([a['name'] for a in item['artists']]),
                                album=item['album']['name'],
                                duration=item['duration_ms'] // 1000,
                                external_id=item['id'],
                                year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                                source="spotify",
                            ))
                        if spotify_tracks:
                            # Do NOT duration-filter in fallback
                            print(f"✅ Found {len(spotify_tracks)} results with fallback query: {query}")
                            return spotify_tracks
                    except Exception as e:
                        print(f"❌ Error with fallback query '{query}': {e}")


        # Fallback B (last resort): Title-only and title + per-artist as plain keywords
        last_resort_queries = []
        last_resort_queries.append(f'"{track.title}"')
        if individual_artists:
            for artist_name in individual_artists:
                last_resort_queries.append(f'"{track.title}" "{artist_name}"')

        for i, query in enumerate(last_resort_queries):
            try:
                print(f"🛟 Last-resort fallback {i+1}/{len(last_resort_queries)}: {query}")
                params = { 'q': query, 'type': 'track', 'limit': 50 }
                response = self.session.get(f"{self.base_url}/search", params=params)
                response.raise_for_status()
                data = response.json()
                spotify_tracks = []
                for item in data.get('tracks', {}).get('items', []):
                    spotify_tracks.append(Track(
                        title=item['name'],
                        artist=', '.join([a['name'] for a in item['artists']]),
                        album=item['album']['name'],
                        duration=item['duration_ms'] // 1000,
                        external_id=item['id'],
                        year=item['album'].get('release_date', '')[:4] if item['album'].get('release_date') else None,
                        source="spotify",
                    ))
                if spotify_tracks:
                    print(f"✅ Found {len(spotify_tracks)} results with last-resort fallback: {query}")
                    return spotify_tracks
            except Exception as e:
                print(f"❌ Error with last-resort fallback '{query}': {e}")

        print(f"❌ No results found for track: {track}")
        return []
    
    def _search_by_isrc(self, isrc: str) -> List[Track]:
        """Search by ISRC code for exact matching"""
        try:
            params = {
                'q': f'isrc:{isrc}',
                'type': 'track',
                'limit': 1
            }
            
            response = self.session.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            tracks = []
            
            for item in data.get('tracks', {}).get('items', []):
                spotify_track = Track(
                    title=item['name'],
                    artist=', '.join([artist['name'] for artist in item['artists']]),
                    album=item['album']['name'],
                    duration=item['duration_ms'] // 1000,
                    external_id=item['id'],
                    source="spotify"
                )
                tracks.append(spotify_track)
            
            return tracks
            
        except Exception as e:
            print(f"❌ ISRC search error: {e}")
            return []

    def _prefer_exact_title_and_artist(self, candidates: List[Track], tracklist_track: Track) -> List[Track]:
        """Return candidates that have exact title match (ignoring case and trivial suffixes)
        and include at least one of the tracklist artists (supporting re-ordered primaries).
        Example: Tracklist 'Sultan + Shepard, Colyn - 1973 (Extended Mix)'
        should prefer Spotify 'Colyn, Sultan + Shepard - 1973'.
        """
        def normalize_title(value: str) -> str:
            v = (value or "").strip().lower()
            # Strip parentheses suffixes like (Extended Mix), (ABGT...) - Mixed
            if "(" in v:
                v = v.split("(")[0].strip()
            return v

        bp_title_core = normalize_title(tracklist_track.title)

        # Build list of acceptable exact titles: prefer plain title, also allow exact title token like '1973'
        acceptable_titles = {bp_title_core}

        # Build artist tokens from tracklist
        bp_artists = [a.strip() for a in re.split(r",|&", tracklist_track.artist or "") if a.strip()]
        bp_artists_lower = [a.lower() for a in bp_artists]

        preferred: List[Track] = []
        for c in candidates:
            c_title_core = normalize_title(c.title)
            # Title must match exactly after normalization
            if c_title_core not in acceptable_titles:
                continue
            # Require at least one artist overlap
            c_artist_lower = (c.artist or "").lower()
            if any(a in c_artist_lower for a in bp_artists_lower):
                preferred.append(c)

        return preferred
    
    def _build_enhanced_queries(self, track: Track) -> List[str]:
        """Build enhanced search queries using all available metadata"""
        queries = []
        
        # Title core and optional mix suffix (clean parentheses once)
        def build_title(with_mix: bool) -> str:
            if with_mix and track.mix_name and track.mix_name != "Original Mix":
                # Check if mix name is already in the title to avoid double parentheses
                if f"({track.mix_name})" in track.title or f"({track.mix_name}" in track.title:
                    return f'"{track.title}"'
                return f'"{track.title} ({track.mix_name})"'
            return f'"{track.title}"'
        title_with_mix = build_title(True)
        title_plain = build_title(False)

        # Simple cleaners for album/label to avoid broken quotes
        def sanitize(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            return str(value).replace('"', '').strip()

        album_name = sanitize(track.album)
        label_name = sanitize(track.label)
        
        if track.year:
            queries.append(f'{title_with_mix} artist:"{track.artist}" year:{track.year}')
            queries.append(f'{title_with_mix} artist:"{track.artist}" year:{track.year-1}-{track.year+1}')
        
        # Query 3: Title + artist + year (without quotes for broader search)
        if track.year:
            queries.append(f'{track.title} {track.artist} year:{track.year}')
        
        # Query 4: Title + artist (quoted title)
        queries.append(f'{title_plain} artist:"{track.artist}"')
        
        # Query 5: Title + artist (no quotes)
        queries.append(f'{track.title} {track.artist}')
        
        # Query 6: Just title with mix
        if track.mix_name and track.mix_name != "Original Mix":
            queries.append(title_with_mix)
        
        # Query 7: Just title
        queries.append(title_plain)
        
        # Query 8: Title + remixers (if any)
        if track.remixers:
            for remixer in track.remixers:
                queries.append(f'"{track.title}" "{remixer}"')

        # Query 9: Include album hint when available
        if album_name:
            # With artist and year if present
            if track.year:
                queries.append(f'{title_plain} artist:"{track.artist}" album:"{album_name}" year:{track.year}')
            queries.append(f'{title_plain} artist:"{track.artist}" album:"{album_name}"')
            # Album-only fallback
            queries.append(f'album:"{album_name}" {track.title}')

        # Query 10: Add label text as plain term (no field on Spotify)
        if label_name:
            queries.append(f'{title_plain} artist:"{track.artist}" {label_name}')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        return unique_queries

    def _strip_length_qualifiers(self, mix_name: str) -> str:
        """Remove length/style qualifiers like 'Extended', 'Edit', 'Club Mix', 'Radio', 'Dub', 'VIP' from a mix name.
        Keeps remixer names and the word 'Remix' if present.
        Examples: 'DJ Tennis Extended Remix' → 'DJ Tennis Remix'; 'Extended Mix' → 'Mix'.
        """
        if not mix_name:
            return mix_name
        lowered = mix_name
        tokens = [
            'extended', 'edit', 'club', 'club mix', 'radio', 'radio edit', 'dub', 'vip', 'version'
        ]
        out = lowered
        for t in tokens:
            out = out.replace(t, '').replace(t.title(), '')
        # Normalize spaces
        out = ' '.join(out.split())
        # Ensure 'Remix' kept if present anywhere
        if 'remix' in mix_name.lower() and 'remix' not in out.lower():
            out = (out + ' Remix').strip()
        return out.strip()

    def _strip_extended_from_title(self, title: str) -> str:
        """Remove Extended Mix qualifiers from track titles to find base tracks.
        Examples: 'I'm Gone (Extended Mix)' → 'I'm Gone'; 'The Shiver (Extended)' → 'The Shiver'
        """
        if not title:
            return title
        
        # Remove common Extended Mix patterns from title
        patterns = [
            r'\s*\(Extended\s+Mix\)',  # (Extended Mix)
            r'\s*\(Extended\)',        # (Extended)
            r'\s*\(Extended\s+Edit\)', # (Extended Edit)
            r'\s*\(Extended\s+Version\)', # (Extended Version)
            r'\s*\(Extended\s+Rework\)', # (Extended Rework)
            r'\s*Extended\s+Mix',      # Extended Mix (no parentheses)
            r'\s*Extended',            # Extended (no parentheses)
        ]
        
        result = title
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Clean up extra spaces and trailing punctuation
        result = re.sub(r'\s+', ' ', result).strip()
        # Remove trailing parentheses and punctuation
        result = re.sub(r'\s*[\(\[]\s*$', '', result).strip()
        
        return result

    def _primary_remixer_from_mix(self, mix_name: str) -> Optional[str]:
        """Best-effort extraction of the primary remixer name from a mix label.
        E.g., 'DJ Tennis Remix' → 'DJ Tennis'. Returns None if not obvious.
        """
        if not mix_name:
            return None
        parts = mix_name.split('Remix')[0].strip()
        if parts and len(parts.split()) <= 4:
            return parts
        return None
    
    def _filter_by_duration(self, spotify_tracks: List[Track], tracklist_track: Track) -> List[Track]:
        """Filter Spotify tracks by duration if tracklist track has duration"""
        if not tracklist_track.duration:
            return spotify_tracks
        
        # Allow ±5 seconds tolerance
        tolerance = 5
        min_duration = tracklist_track.duration - tolerance
        max_duration = tracklist_track.duration + tolerance
        
        filtered = []
        for track in spotify_tracks:
            if track.duration and min_duration <= track.duration <= max_duration:
                filtered.append(track)
        
        # If no duration matches, return original list
        return filtered if filtered else spotify_tracks
    
    def search_tracks(self, tracks: List[Track]) -> List[Track]:
        """Search for multiple tracks on Spotify"""
        all_spotify_tracks = []
        
        for track in tracks:
            spotify_tracks = self.search_track(track)
            all_spotify_tracks.extend(spotify_tracks)
        
        return all_spotify_tracks
    
    def create_playlist(self, name: str, description: str = "", public: bool = False) -> Optional[str]:
        """Create a new playlist on Spotify"""
        if not self.access_token:
            raise ValueError("Access token not set")
        
        # Get current user ID
        user_id = self._get_current_user_id()
        if not user_id:
            return None
        
        data = {
            'name': name,
            'description': description,
            'public': public
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/users/{user_id}/playlists",
                json=data
            )
            response.raise_for_status()
            
            playlist_data = response.json()
            return playlist_data['id']
            
        except Exception as e:
            print(f"Error creating playlist: {e}")
            return None
    
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Add tracks to a playlist"""
        if not self.access_token:
            raise ValueError("Access token not set")
        
        if not track_ids:
            return True
        
        # Spotify API allows max 100 tracks per request
        batch_size = 100
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i + batch_size]
            
            # Convert track IDs to Spotify URIs
            uris = [f"spotify:track:{track_id}" for track_id in batch]
            
            data = {'uris': uris}
            
            try:
                response = self.session.post(
                    f"{self.base_url}/playlists/{playlist_id}/tracks",
                    json=data
                )
                response.raise_for_status()
                
            except Exception as e:
                print(f"Error adding tracks to playlist: {e}")
                return False
        
        return True
    
    def get_user_playlists(self) -> List[Playlist]:
        """Get user's playlists"""
        if not self.access_token:
            raise ValueError("Access token not set")
        
        try:
            response = self.session.get(f"{self.base_url}/me/playlists")
            response.raise_for_status()
            
            data = response.json()
            playlists = []
            
            for item in data.get('items', []):
                playlist = Playlist(
                    name=item['name'],
                    tracks=[],  # Would need separate call to get tracks
                    external_id=item['id'],
                    source="spotify",
                    description=item.get('description', '')
                )
                playlists.append(playlist)
            
            return playlists
            
        except Exception as e:
            print(f"Error getting playlists: {e}")
            return []
    
    def _get_current_user_id(self) -> Optional[str]:
        """Get current user's ID"""
        try:
            response = self.session.get(f"{self.base_url}/me")
            response.raise_for_status()
            
            data = response.json()
            return data.get('id')
            
        except Exception as e:
            print(f"Error getting user ID: {e}")
            return None

    def clear_playlist_tracks(self, playlist_id: str) -> bool:
        """Clear all tracks from a playlist"""
        if not self.access_token:
            raise ValueError("Access token not set")
        
        try:
            # First, get all tracks in the playlist
            response = self.session.get(f"{self.base_url}/playlists/{playlist_id}/tracks")
            response.raise_for_status()
            
            data = response.json()
            track_uris = []
            
            for item in data.get('items', []):
                track_uris.append(item['track']['uri'])
            
            if not track_uris:
                print("ℹ️ Playlist is already empty")
                return True
            
            # Remove all tracks in batches of 100 (Spotify API limit)
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                response = self.session.delete(
                    f"{self.base_url}/playlists/{playlist_id}/tracks",
                    json={"tracks": [{"uri": uri} for uri in batch]}
                )
                response.raise_for_status()
            
            print(f"✅ Cleared {len(track_uris)} tracks from playlist")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing playlist tracks: {e}")
            return False
