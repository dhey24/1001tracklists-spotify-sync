from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class MatchStatus(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    NO_MATCH = "no_match"

@dataclass
class Track:
    """Represents a music track"""
    title: str
    artist: str
    album: str = ""
    duration: Optional[int] = None  # in seconds
    external_id: Optional[str] = None  # Spotify ID, etc.
    source: str = ""  # "spotify", "1001tracklists", etc.
    isrc: Optional[str] = None  # ISRC code for exact matching
    mix_name: Optional[str] = None  # Remix/Edit name
    label: Optional[str] = None  # Record label
    year: Optional[int] = None  # Release year
    remixers: List[str] = None  # List of remixer names
    
    def __post_init__(self):
        if self.remixers is None:
            self.remixers = []
    
    def __str__(self):
        return f"{self.artist} - {self.title}"

@dataclass
class Playlist:
    """Represents a music playlist"""
    name: str
    tracks: List[Track]
    external_id: Optional[str] = None
    source: str = ""
    description: str = ""
    
    def __str__(self):
        return f"{self.name} ({len(self.tracks)} tracks)"

@dataclass
class MatchResult:
    """Represents a match between two tracks"""
    tracklist_track: Track
    spotify_track: Optional[Track]
    confidence: float  # 0.0 to 1.0
    status: MatchStatus
    reason: str = ""
    
    def __str__(self):
        if self.spotify_track:
            return f"✅ {self.tracklist_track} → {self.spotify_track} ({self.confidence:.2f})"
        else:
            return f"❌ {self.tracklist_track} → No match ({self.reason})"
