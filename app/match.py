import re, unicodedata
from rapidfuzz import fuzz
from typing import List, Tuple
from .models import Track, MatchResult, MatchStatus

def normalize_text(text: str) -> str:
    """Normalize text for better matching"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common words that might interfere with matching
    common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    words = text.split()
    words = [word for word in words if word not in common_words]
    text = ' '.join(words)
    
    return text

def calculate_track_similarity(track1: Track, track2: Track) -> float:
    """Calculate similarity between two tracks"""
    # Normalize the text
    title1 = normalize_text(track1.title)
    title2 = normalize_text(track2.title)
    artist1 = normalize_text(track1.artist)
    artist2 = normalize_text(track2.artist)
    
    # Calculate title similarity
    title_similarity = fuzz.ratio(title1, title2) / 100.0
    
    # Calculate artist similarity
    artist_similarity = fuzz.ratio(artist1, artist2) / 100.0
    
    # Weighted combination (title is more important)
    similarity = (title_similarity * 0.7) + (artist_similarity * 0.3)
    
    return similarity

def find_matches(tracklist_tracks: List[Track], spotify_tracks: List[Track], 
                min_confidence: float = 0.8) -> List[MatchResult]:
    """
    Find matches between 1001tracklists and Spotify tracks
    
    Args:
        tracklist_tracks: List of tracks from 1001tracklists
        spotify_tracks: List of tracks from Spotify
        min_confidence: Minimum confidence threshold for fuzzy matches
    
    Returns:
        List of MatchResult objects
    """
    matches = []
    
    for tracklist_track in tracklist_tracks:
        best_match = None
        best_confidence = 0.0
        
        # For Extended Mix tracks, create a base track for matching
        match_track = tracklist_track
        if tracklist_track.mix_name and 'extended' in tracklist_track.mix_name.lower():
            # Create a base track with the core title (without Extended Mix)
            base_title = tracklist_track.title
            if '(' in base_title and 'Extended' in base_title:
                # Remove the Extended Mix part from title
                base_title = base_title.split('(')[0].strip()
            
            match_track = Track(
                title=base_title,
                artist=tracklist_track.artist,
                album=tracklist_track.album,
                duration=tracklist_track.duration,
                external_id=tracklist_track.external_id,
                source=tracklist_track.source,
                isrc=tracklist_track.isrc,
                mix_name=None,  # Remove mix name for matching
                label=tracklist_track.label,
                year=tracklist_track.year,
                remixers=tracklist_track.remixers or []
            )
        
        for spotify_track in spotify_tracks:
            confidence = calculate_track_similarity(match_track, spotify_track)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = spotify_track
        
        # Determine match status
        if best_confidence >= 0.95:
            status = MatchStatus.EXACT
        elif best_confidence >= min_confidence:
            status = MatchStatus.FUZZY
        else:
            status = MatchStatus.NO_MATCH
            best_match = None
        
        # Create match result
        match_result = MatchResult(
            tracklist_track=tracklist_track,  # Use original track for display
            spotify_track=best_match,
            confidence=best_confidence,
            status=status,
            reason="No close match found" if status == MatchStatus.NO_MATCH else ""
        )
        
        matches.append(match_result)
    
    return matches
