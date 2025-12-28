# Tracklists Directory

This directory is the default location for tracklist text files.

## Usage

Place your tracklist `.txt` files here, then reference them by filename:

```bash
# Activate virtual environment
source activate.sh

# Preview matches (recommended first step)
python sync.py my_tracklist.txt --dry-run

# Create the playlist
python sync.py my_tracklist.txt
```

## File Format

Your tracklist files should have:
- **First line**: Playlist name (e.g., "Lane 8 - Fall 2025 Mixtape 2025-09-24")
- **Remaining lines**: Tracks in "Artist - Title" format

You can copy-paste directly from 1001tracklists.com - the tool automatically filters out:
- Labels (NINJA, AFTERLIFE, etc.)
- Timestamps
- Track numbers
- Other metadata

## Example

See `../example_tracklist.txt` for a complete example.

## Alternative Locations

You can still use absolute paths or relative paths from the project root:

```bash
# Absolute path
python sync.py /path/to/tracklist.txt

# Relative path
python sync.py ../other_tracklist.txt
```

