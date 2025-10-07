import re
from typing import List, Optional
from ..models import Track, Playlist

class ManualTracklistProvider:
    """Manual tracklist entry provider as fallback when scraping fails"""
    
    def __init__(self):
        pass
    
    def get_tracklist_from_text(self, text: str, tracklist_name: str = "Manual Tracklist") -> Playlist:
        """Parse tracklist from text input"""
        tracks = []
        lines = text.strip().split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Skip obvious non-track lines
            if self._is_non_track_line(line):
                continue
            
            track = self._parse_track_line(line, i)
            if track and not self._is_unknown_track(track):
                if self._is_mashup(track):
                    mashup_tracks = self._split_mashup_track(track)
                    tracks.extend(mashup_tracks)
                    print(f"  🔀 Split mashup: {track} → {len(mashup_tracks)} tracks")
                else:
                    tracks.append(track)
                    print(f"  🎵 Track {len(tracks)}: {track}")
        
        return Playlist(
            name=tracklist_name,
            tracks=tracks,
            source="manual",
            description="Manually entered tracklist"
        )
    
    def get_tracklist_interactive(self, tracklist_name: str = "Manual Tracklist") -> Playlist:
        """Interactive tracklist entry"""
        print(f"\n📝 Manual Tracklist Entry: {tracklist_name}")
        print("Enter tracks in format: Artist - Title")
        print("For mashups: Artist1 vs. Artist2 - Track1 vs. Track2")
        print("Press Enter twice to finish")
        print("-" * 50)
        
        tracks = []
        track_number = 1
        
        while True:
            try:
                track_input = input(f"Track {track_number}: ").strip()
                if not track_input:
                    break
                
                # Skip obvious non-track lines
                if self._is_non_track_line(track_input):
                    print("  ⏭️  Skipping non-track line")
                    continue
                
                track = self._parse_track_line(track_input, track_number)
                if track and not self._is_unknown_track(track):
                    if self._is_mashup(track):
                        mashup_tracks = self._split_mashup_track(track)
                        tracks.extend(mashup_tracks)
                        print(f"    🔀 Split mashup into {len(mashup_tracks)} tracks")
                        for mashup_track in mashup_tracks:
                            print(f"      🎵 {mashup_track}")
                    else:
                        tracks.append(track)
                        print(f"    ✅ Added: {track}")
                else:
                    print("    ⏭️  Skipping unknown track")
                
                track_number += 1
                
            except KeyboardInterrupt:
                print("\n⏹️  Entry cancelled")
                break
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue
        
        print(f"\n✅ Manual entry complete: {len(tracks)} tracks")
        return Playlist(
            name=tracklist_name,
            tracks=tracks,
            source="manual",
            description="Manually entered tracklist"
        )
    
    def _is_non_track_line(self, line: str) -> bool:
        """Check if line is clearly not a track"""
        line_lower = line.lower()
        
        # Skip patterns
        skip_patterns = [
            r'^\d+$',  # Just numbers
            r'^\d+:\d+$',  # Time format
            r'^tracklist',  # Headers
            r'^artist',  # Headers
            r'^title',  # Headers
            r'^time',  # Headers
            r'^duration',  # Headers
            r'^1001tracklists',  # Site name
            r'^home',  # Navigation
            r'^search',  # Navigation
            r'^login',  # Navigation
            r'^register',  # Navigation
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, line_lower):
                return True
        
        return False
    
    def _parse_track_line(self, line: str, track_number: int) -> Optional[Track]:
        """Parse a track line into a Track object"""
        if not line or len(line) < 3:
            return None
        
        # Clean up the text
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Try to extract artist and title
        artist, title = self._extract_artist_and_title(line)
        
        if not artist or not title:
            return None
        
        # Create track object
        track = Track(
            title=title,
            artist=artist,
            source="manual",
            external_id=f"manual_{track_number}"
        )
        
        return track
    
    def _extract_artist_and_title(self, text: str) -> tuple:
        """Extract artist and title from track text"""
        # Handle various formats
        
        # Format 1: "Artist - Title"
        if ' - ' in text:
            parts = text.split(' - ', 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        
        # Format 2: "Artist vs. Artist - Title vs. Title" (mashup)
        if ' vs. ' in text and ' - ' in text:
            return self._extract_mashup_artist_title(text)
        
        # Format 3: "Artist feat. Artist - Title"
        if ' feat. ' in text and ' - ' in text:
            parts = text.split(' - ', 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        
        # Format 4: Just "Title" (no artist separator)
        return "Unknown Artist", text
    
    def _extract_mashup_artist_title(self, text: str) -> tuple:
        """Extract artist and title from mashup text"""
        return "Mashup", text
    
    def _is_unknown_track(self, track: Track) -> bool:
        """Check if track is marked as unknown (ID - ID)"""
        if not track.title or not track.artist:
            return True
        
        # Check for "ID - ID" pattern
        if re.match(r'^ID\s*-\s*ID$', track.title, re.IGNORECASE):
            return True
        
        if re.match(r'^ID\s*-\s*ID$', track.artist, re.IGNORECASE):
            return True
        
        return False
    
    def _is_mashup(self, track: Track) -> bool:
        """Check if track is a mashup"""
        if not track.title or not track.artist:
            return False
        
        # Look for mashup indicators
        mashup_patterns = [
            r' vs\. ',
            r' vs ',
            r' mashup',
            r' mashup\)',
            r'\(.*mashup.*\)',
        ]
        
        text = f"{track.artist} - {track.title}".lower()
        for pattern in mashup_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _split_mashup_track(self, track: Track) -> List[Track]:
        """Split a mashup track into separate tracks"""
        tracks = []
        
        text = f"{track.artist} - {track.title}"
        
        # Try to parse mashup format: "Artist1 vs. Artist2 - Title1 vs. Title2"
        vs_match = re.search(r'^(.+?)\s+vs\.\s+(.+?)\s+-\s+(.+?)\s+vs\.\s+(.+?)(?:\s+\(.*\))?$', text, re.IGNORECASE)
        if vs_match:
            artist1, artist2, title1, title2 = vs_match.groups()
            
            track1 = Track(
                title=title1.strip(),
                artist=artist1.strip(),
                source=track.source,
                external_id=f"{track.external_id}_1"
            )
            
            track2 = Track(
                title=title2.strip(),
                artist=artist2.strip(),
                source=track.source,
                external_id=f"{track.external_id}_2"
            )
            
            tracks.extend([track1, track2])
            return tracks
        
        # Fallback: if we can't parse the mashup, return the original track
        return [track]
