# 1001tracklists-Spotify Sync

A Python tool to sync tracklists from 1001tracklists.com to Spotify playlists using a simple manual copy-paste workflow.

## Features

- 🎵 **Manual tracklist input** - Copy & paste tracklists from 1001tracklists.com
- 🏷️ **Smart title extraction** - Automatically uses the first line as playlist name
- 🧹 **Label cleanup** - Removes label metadata (NINJA, THIS NEVER HAPPENED, etc.)
- 🔀 **Mashup handling** - Splits mashups into separate tracks
- ⏭️ **ID filtering** - Skips unknown tracks marked as "ID - ID"
- 🎯 **Fuzzy matching** - Smart track matching with Spotify
- 🔄 **Playlist overwrite** - Updates existing playlists instead of creating duplicates
- 📝 **Comprehensive logging** - Tracks unmatched songs and sync progress
- 🎧 **Extended mix support** - Handles remixes and extended versions

## Why Manual Input?

1001tracklists.com uses Cloudflare protection and dynamically loaded content, making automated scraping unreliable. The manual copy-paste approach is:
- ✅ Faster and more reliable
- ✅ Works with any tracklist
- ✅ No need for complex scraping or browser automation
- ✅ Respects website policies

## Installation

### Quick Setup (Recommended)

1. Clone or download this project
2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source activate.sh
   ```

4. Set up your Spotify API credentials:
   ```bash
   python scripts/setup_env.py
   ```

### Manual Setup

1. Clone or download this project
2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your Spotify API credentials:
   ```bash
   python scripts/setup_env.py
   ```
   
   Or manually create a `.env` file with:
   ```
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```

## Getting Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create app"
4. Fill in app details:
   - **App name**: "1001tracklists Sync" (or any name)
   - **App description**: "Personal tracklist sync tool"
   - **Redirect URI**: `http://localhost:8888/callback`
5. Accept terms and click "Save"
6. Click "Settings" to view your Client ID and Client Secret
7. Run `python scripts/setup_env.py` and paste these credentials

## Usage

**Important**: Always activate the virtual environment first:
```bash
source activate.sh
```

### Basic Workflow

1. **Copy tracklist from 1001tracklists.com:**
   - Go to any tracklist page on 1001tracklists.com
   - Select and copy the entire tracklist section (including title)
   - Paste it into a text file (e.g., `my_tracklist.txt`)
   - **The first line should be the tracklist title**

2. **Sync to Spotify:**
   ```bash
   # Dry run first (recommended)
   python sync.py my_tracklist.txt --dry-run
   
   # If results look good, run the actual sync
   python sync.py my_tracklist.txt
   ```

### Input File Structure

The script expects a text file with the following structure:

**Required:**
- **First line:** The tracklist title (becomes the Spotify playlist name with "(Tracklist Sync)" appended)
- **Remaining lines:** Track listings in "Artist - Title" format

**What gets parsed:**
- Lines containing " - " (space, hyphen, space) are identified as tracks
- The script extracts artist and title from these lines
- Everything else is ignored (numbers, timestamps, labels, artwork mentions, etc.)

**Example 1: Minimal Clean Format**
```
My Favorite Mix
Artist 1 - Track Title 1
Artist 2 & Artist 3 - Track Title 2 (Remix)
Artist 4 - Track Title 3
```

**Example 2: Raw Copy from 1001tracklists.com**
```
Lane 8 - Fall 2025 Mixtape 2025-09-24
 Tracklist Media Links
YouTube
Apple Music
SoundCloud
Add
Mix with DJ.Studio
Player 1 [3:15:05]

Niilas & Bicep Alit Artwork
01
Niilas & Bicep - Alit NINJA
4
biscram
(7.4k)
Save 20
artwork placeholder
02
02:34
Lane 8 & Arctic Lake - The Choice (SK Remix) THIS NEVER HAPPENED
5
zinderlong
(24.4k)
Save 15
03
05:29
OLING - Wanna Wou VIVRANT
3
dubshakerz
(8.2k)
```

**What happens to Example 2:**
- **Playlist name:** "Lane 8 - Fall 2025 Mixtape 2025-09-24 (Tracklist Sync)"
- **Tracks extracted:**
  - Track 1: `Niilas & Bicep - Alit` (label "NINJA" removed)
  - Track 2: `Lane 8 & Arctic Lake - The Choice (SK Remix)` (label removed)
  - Track 3: `OLING - Wanna Wou` (label "VIVRANT" removed)
- **Ignored:** All lines without " - " pattern (numbers, timestamps, media links, etc.)

**Note:** You can paste the raw copied text directly from 1001tracklists.com - the script automatically:
- Cleans up label metadata (NINJA, THIS NEVER HAPPENED, ANJUNADEEP, etc.)
- Removes sublabels in parentheses (COLUMBIA (SONY), etc.)
- Filters out non-track lines (artwork, timestamps, track numbers)
- Handles mashups by splitting them into separate tracks

### Advanced Options

```bash
# Custom playlist name (overrides first line)
python sync.py tracklist.txt --name "My Custom Playlist"

# Dry run (preview matches without creating playlist)
python sync.py tracklist.txt --dry-run

# Adjust matching confidence (0.0 to 1.0)
python sync.py tracklist.txt --confidence 0.9

# Disable duration filtering
python sync.py tracklist.txt --no-duration-filter
```

## How It Works

1. **Text Parsing**: 
   - Reads the first line as the playlist title
   - Extracts track information from remaining lines
   - Removes label metadata (NINJA, THIS NEVER HAPPENED, etc.)
   - Filters out non-track lines (artwork, metadata, etc.)

2. **Track Processing**: 
   - Skips "ID - ID" unknown tracks
   - Splits mashups into separate tracks (e.g., "Artist1 vs. Artist2 - Track1 vs. Track2")
   - Cleans up remix and extended mix formatting

3. **Spotify Matching**: 
   - Uses fuzzy matching to find tracks on Spotify
   - Handles artist name variations
   - Accounts for different remix formats

4. **Playlist Creation**: 
   - Checks if playlist with same name already exists
   - Overwrites existing playlist (clears tracks and adds new ones)
   - Creates new playlist if it doesn't exist
   - Adds "(Tracklist Sync)" suffix to playlist name

## Special Features

### Automatic Label Removal
The tool automatically removes label names and metadata:
- `Niilas & Bicep - Alit NINJA` → `Niilas & Bicep - Alit`
- `Tame Impala - End Of Summer COLUMBIA (SONY)` → `Tame Impala - End Of Summer`
- `Weska - Helix TRUESOUL` → `Weska - Helix`

### Mashup Handling
The tool automatically detects and splits mashups:
- Input: `Christian Löffler vs. Jeremy Olander - Beside You vs. Samus (Lane 8 Mashup)`
- Output: Two separate tracks:
  - `Beside You` by `Christian Löffler`
  - `Samus` by `Jeremy Olander`

### Playlist Overwrite Protection
- If a playlist with the same name exists, it will be updated instead of creating a duplicate
- All existing tracks are removed and replaced with the new tracklist
- Logs indicate whether a playlist was created or updated

### Unmatched Track Logging
Tracks that couldn't be found on Spotify are logged for reference:
```
⚠️  UNMATCHED TRACKS (11 tracks):
  ❌ Lane 8 & Arctic Lake - The Choice (SK Remix)
  ❌ Massane & Qrion - ID
  ❌ Colyn - ID
```

## Logging

The tool creates detailed logs in the `logs/` directory, showing:
- Parsed tracks and cleanup operations
- Spotify search results
- Match confidence scores
- Unmatched tracks
- Playlist creation/update status

## Requirements

- Python 3.7+
- Spotify Developer Account (free)
- Internet connection

## Dependencies

- `requests` - HTTP requests to Spotify API
- `python-dotenv` - Environment variable management
- `rapidfuzz` - Fuzzy string matching for track names

## Troubleshooting

### Authentication Issues
- Make sure your Spotify credentials are correct
- Check that your redirect URI is exactly `http://localhost:8888/callback`
- Try running the setup script again: `python scripts/setup_env.py`
- Delete `tokens/spotify.json` and re-authenticate

### No Tracks Found
- Check that your text file has the tracklist content
- Make sure tracks are in "Artist - Title" format
- Check the logs for detailed parsing information

### Poor Matching Results
- Try adjusting the confidence threshold with `--confidence 0.7` (lower = more lenient)
- Use `--no-duration-filter` to disable duration-based filtering
- Some tracks may not be available on Spotify (shows in unmatched tracks)
- Tracks marked as "ID" are unreleased and won't be found

### Playlist Not Updating
- Check that you're using the exact same tracklist name
- Look for the "Will overwrite it" message in the output
- If you want a new playlist, change the first line (title) in your text file

## Project Structure

```
1001tracklists-spotify-sync/
├── sync.py                    # Main sync script
├── app/
│   ├── models.py             # Data models (Track, Playlist, etc.)
│   ├── match.py              # Fuzzy matching logic
│   ├── auth_flow.py          # Spotify OAuth flow
│   └── providers/
│       ├── spotify.py        # Spotify API provider
│       └── manual_tracklist.py  # Manual text parsing
├── scripts/
│   ├── setup_env.py          # Credential setup wizard
│   └── install_dependencies.py  # Dependency installer
├── logs/                     # Sync logs (auto-created)
├── tokens/                   # Spotify tokens (auto-created)
├── requirements.txt          # Python dependencies
├── .env                      # Spotify credentials (you create)
└── README.md                 # This file
```

## Tips

- **Keep your text files**: Save tracklists for future re-syncs
- **Use descriptive titles**: The first line becomes your playlist name
- **Run dry runs first**: Always preview matches before creating playlists
- **Check unmatched tracks**: Some tracks may need manual searching on Spotify
- **Update existing playlists**: Just run the sync again with the same title

## License

This project is for personal use. Please respect 1001tracklists.com's terms of service and Spotify's API usage policies.

## Contributing

This is a personal tool, but suggestions and improvements are welcome! Open an issue or submit a pull request.
