# 1001tracklists → Spotify Sync

A Python tool that syncs tracklists from 1001tracklists.com to Spotify playlists using a simple copy-paste workflow.

## Why Manual Copy-Paste?

**TL;DR: Automated scraping of 1001tracklists.com doesn't work reliably.**

1001tracklists.com uses Cloudflare protection and dynamically loaded JavaScript content, which makes automated scraping extremely difficult and unreliable. After trying multiple scraping approaches (requests, BeautifulSoup, Selenium), the manual copy-paste workflow proved to be:

- **More reliable** - Works 100% of the time, no captchas or blocks
- **Faster** - No waiting for page loads or browser automation
- **Simpler** - No complex dependencies or browser drivers
- **Respectful** - Doesn't violate website policies or terms of service

The tool handles all the messy parsing, label cleanup, and Spotify matching for you—you just provide the raw text.

## Quick Start

### Prerequisites

- Python 3.7 or higher
- A Spotify account
- Spotify Developer credentials ([get them here](https://developer.spotify.com/dashboard))

### Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/yourusername/1001tracklists-spotify-sync.git
   cd 1001tracklists-spotify-sync
   ```

2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source activate.sh
   ```

4. Set up your Spotify credentials:
   ```bash
   python scripts/setup_env.py
   ```
   
   Follow the prompts to enter your Client ID and Client Secret from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

### Basic Usage

**Option 1: Web UI (Recommended)**

1. Start the web server:
   ```bash
   python web_app.py
   ```

2. Open http://localhost:5000 in your browser

3. Paste your tracklist, preview matches, and sync!

**Option 2: Command Line**

1. **Copy a tracklist** from 1001tracklists.com (see detailed instructions below)
2. **Paste it into a text file** (e.g., `my_tracklist.txt`)
3. **Run the sync**:
   ```bash
   # Always do a dry run first to preview matches
   python sync.py my_tracklist.txt --dry-run
   
   # If it looks good, create the playlist
   python sync.py my_tracklist.txt
   ```

That's it! Check your Spotify app for the new playlist.

## Web UI

The web interface provides an easy, visual way to sync tracklists without using the command line.

### Features

- **Large paste area** - Just copy and paste your tracklist
- **Live preview** - See match results before creating the playlist
- **Visual feedback** - Color-coded match quality (green = exact, yellow = fuzzy, red = not found)
- **Adjustable settings** - Fine-tune confidence and filtering
- **Match statistics** - See how many tracks matched at a glance
- **Direct Spotify links** - Open your new playlist immediately

### Running the Web UI

```bash
# Make sure you're in the virtual environment
source activate.sh

# Start the server
python web_app.py
```

Then open http://localhost:5000 in your browser.

### How to Use

1. **Paste your tracklist** - Copy the entire tracklist from 1001tracklists.com and paste it into the large text area
2. **Optional: Override playlist name** - Leave blank to use the first line of the tracklist
3. **Optional: Adjust settings** - Click "Advanced Settings" to change match confidence or disable duration filtering
4. **Preview matches** - Click "Preview Matches" to see what tracks will be added
5. **Sync to Spotify** - If the results look good, click "Sync to Spotify" to create the playlist

The web UI uses the same parsing and matching logic as the command-line tool, just with a friendlier interface!

## How to Get a Tracklist

### Step-by-Step Instructions

1. **Go to any tracklist page** on [1001tracklists.com](https://1001tracklists.com)
   - Example: A DJ mix, radio show, or live set

2. **Select and copy the tracklist content**
   - Click at the start of the tracklist title
   - Drag to select the entire tracklist (title + all tracks)
   - Copy with `Cmd+C` (Mac) or `Ctrl+C` (Windows)

3. **Paste into a text file**
   - Create a new file: `touch my_tracklist.txt`
   - Open it and paste: `Cmd+V` or `Ctrl+V`
   - Save the file

4. **What to copy**: Include everything from the title through all the tracks
   - The tracklist title (first line)
   - All track listings
   - Don't worry about timestamps, track numbers, labels, or other metadata—the tool filters those out automatically

### Example Input File

Here's what your text file might look like after copying from 1001tracklists.com:

```
Lane 8 - Fall 2025 Mixtape 2025-09-24
Tracklist Media Links
YouTube
Apple Music
01
Niilas & Bicep - Alit NINJA
Save 20
02
02:34
Lane 8 & Arctic Lake - The Choice (SK Remix) THIS NEVER HAPPENED
Save 15
03
05:29
OLING - Wanna Wou VIVRANT
```

**What the tool extracts:**
- **Playlist name**: "Lane 8 - Fall 2025 Mixtape 2025-09-24 (Tracklist Sync)"
- **Tracks**:
  - `Niilas & Bicep - Alit` (label "NINJA" removed)
  - `Lane 8 & Arctic Lake - The Choice (SK Remix)` (label removed)
  - `OLING - Wanna Wou` (label "VIVRANT" removed)

The tool automatically:
- Uses the first line as the playlist name
- Removes label metadata (NINJA, THIS NEVER HAPPENED, ANJUNADEEP, etc.)
- Removes sublabels in parentheses (COLUMBIA (SONY), etc.)
- Filters out track numbers, timestamps, and non-track lines
- Splits mashups into separate tracks
- Skips unknown tracks marked as "ID - ID"

See [`example_tracklist.txt`](example_tracklist.txt) for a complete example.

## Usage Examples

### Dry Run (Recommended First Step)

Always preview matches before creating a playlist:

```bash
python sync.py my_tracklist.txt --dry-run
```

This shows you:
- How many tracks were found and parsed
- Which tracks matched on Spotify (and with what confidence)
- Which tracks couldn't be found
- No playlist is created

### Create a Playlist

If the dry run looks good:

```bash
python sync.py my_tracklist.txt
```

The playlist will be created in your Spotify account with "(Tracklist Sync)" appended to the name.

### Custom Playlist Name

Override the first line of the file:

```bash
python sync.py my_tracklist.txt --name "My Custom Playlist Name"
```

### Adjust Match Sensitivity

Lower the confidence threshold to find more matches (may include false positives):

```bash
python sync.py my_tracklist.txt --confidence 0.7
```

Default is 0.8. Range is 0.0 to 1.0.

### Disable Duration Filtering

By default, the tool filters out tracks with very different durations. Disable this:

```bash
python sync.py my_tracklist.txt --no-duration-filter
```

### Update an Existing Playlist

Run the sync again with the **same tracklist name** (first line of your file):

```bash
python sync.py my_tracklist.txt
```

The tool will detect the existing playlist and overwrite it with the new tracks instead of creating a duplicate.

## Advanced Options

All available command-line options:

```bash
python sync.py <file_path> [OPTIONS]

Arguments:
  file_path              Path to your tracklist text file

Options:
  --name TEXT           Custom playlist name (overrides first line)
  --confidence FLOAT    Match confidence threshold (0.0-1.0, default: 0.8)
  --dry-run            Preview matches without creating playlist
  --no-duration-filter  Disable duration-based filtering
```

## How It Works

### 1. Text Parsing
- Reads the first line as the playlist title
- Extracts tracks from remaining lines using pattern matching
- Removes label metadata and non-track content
- Splits mashups into separate tracks

### 2. Track Processing
- Skips unknown tracks ("ID - ID")
- Cleans up remix and extended mix formatting
- Handles various artist formats (feat., vs., &, etc.)

### 3. Spotify Matching
- Uses fuzzy string matching to find tracks
- Handles artist name variations
- Accounts for different remix formats
- Filters by duration to avoid mismatches

### 4. Playlist Creation
- Checks for existing playlist with the same name
- Overwrites if found (clears and repopulates)
- Creates new playlist if not found
- Adds all matched tracks in order

### Special Features

**Automatic Label Removal**
```
Input:  Niilas & Bicep - Alit NINJA
Output: Niilas & Bicep - Alit

Input:  Tame Impala - End Of Summer COLUMBIA (SONY)
Output: Tame Impala - End Of Summer
```

**Mashup Handling**
```
Input:  Christian Löffler vs. Jeremy Olander - Beside You vs. Samus (Lane 8 Mashup)
Output: Two tracks:
  - Beside You by Christian Löffler
  - Samus by Jeremy Olander
```

**Playlist Overwrite Protection**
- Existing playlists are updated, not duplicated
- All tracks replaced with new tracklist
- Logs indicate whether playlist was created or updated

### Typical Match Rate

Based on testing with real-world tracklists:
- **75-80%** of tracks successfully matched
- Unmatched tracks are usually:
  - Unreleased tracks marked as "ID"
  - Region-restricted content
  - Very obscure releases not on Spotify
  - Tracks with significantly different naming on Spotify

All unmatched tracks are logged so you can manually search for them if needed.

## Troubleshooting

### Authentication Issues

**Problem**: "Authentication failed" or "Invalid credentials"

**Solutions**:
- Verify your credentials at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Make sure Redirect URI is exactly `http://localhost:8888/callback`
- Run the setup wizard again: `python scripts/setup_env.py`
- Delete `tokens/spotify.json` and re-authenticate

### No Tracks Found

**Problem**: "Found 0 tracks"

**Solutions**:
- Check that your text file has content
- Make sure tracks are in "Artist - Title" format
- Look for the " - " (space-hyphen-space) separator
- Check the logs in `logs/` for parsing details

### Poor Matching Results

**Problem**: Many tracks showing as "not found"

**Solutions**:
- Try lowering confidence: `--confidence 0.7`
- Disable duration filter: `--no-duration-filter`
- Check if tracks are actually on Spotify (search manually)
- Some unreleased tracks (marked "ID") won't be found
- Regional restrictions may prevent some matches

### Playlist Not Updating

**Problem**: Running sync creates a new playlist instead of updating

**Solutions**:
- Ensure the **first line** of your text file exactly matches the existing playlist name
- The tool looks for playlists ending with "(Tracklist Sync)"
- Check your Spotify for the exact playlist name
- If you want a new playlist, change the first line (title)

### Virtual Environment Issues

**Problem**: Command not found or import errors

**Solutions**:
- Make sure you activated the virtual environment: `source activate.sh`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.7+)

### Logs and Debugging

All sync operations are logged to `logs/sync_YYYYMMDD_HHMMSS.log`. Check these for:
- Detailed parsing information
- Spotify search results
- Match confidence scores
- API errors

## Getting Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click **"Create app"**
4. Fill in the app details:
   - **App name**: "1001tracklists Sync" (or any name you like)
   - **App description**: "Personal tracklist sync tool"
   - **Redirect URI**: `http://localhost:8888/callback` (important!)
5. Accept the terms and click **"Save"**
6. Click **"Settings"** to view your **Client ID** and **Client Secret**
7. Run `python scripts/setup_env.py` and paste these credentials when prompted

The credentials are stored in a `.env` file and never shared.

## Project Structure

```
1001tracklists-spotify-sync/
├── sync.py                    # Command-line sync tool
├── web_app.py                 # Web UI (Flask app)
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── example_tracklist.txt      # Example input format
├── setup.sh                   # Quick setup script
├── activate.sh                # Venv activation helper
├── templates/                 # Web UI templates
│   ├── base.html             # Base template
│   └── index.html            # Main page
├── static/                    # Web UI assets
│   ├── style.css             # Styling
│   └── script.js             # JavaScript
├── app/
│   ├── models.py             # Data models (Track, Playlist, etc.)
│   ├── match.py              # Fuzzy matching logic
│   ├── auth_flow.py          # Spotify OAuth flow
│   ├── providers/
│   │   ├── spotify.py        # Spotify API client
│   │   └── manual_tracklist.py  # Text parsing
│   └── utils/
│       └── log.py            # Logging utilities
├── scripts/
│   ├── setup_env.py          # Credential setup wizard
│   └── install_dependencies.py
├── logs/                     # Auto-created sync logs
└── tokens/                   # Auto-created auth tokens
```

## Tips for Best Results

- **Always run `--dry-run` first** to preview matches
- **Keep your text files** for easy re-syncing later
- **Use descriptive titles** in the first line for better playlist organization
- **Check unmatched tracks** in the logs—some may need manual searching
- **Update existing playlists** by using the same title (first line)
- **Lower confidence threshold** if you're getting too many "not found" results
- **Copy generously** from 1001tracklists.com—the tool filters out junk automatically

## Dependencies

- `requests` - HTTP requests to Spotify API
- `python-dotenv` - Environment variable management
- `rapidfuzz` - Fuzzy string matching for track names

## License

This project is for personal use. Please respect 1001tracklists.com's terms of service and Spotify's API usage policies.

## Version History

**v1.0** (October 2025)
- Initial release with manual copy-paste workflow
- Smart label cleanup and track parsing
- Fuzzy matching with Spotify
- Playlist overwrite functionality
- Comprehensive logging and error handling

## Contributing

This is a personal tool, but suggestions and improvements are welcome! Feel free to open an issue or submit a pull request.

---

**Questions or issues?** Check the [Troubleshooting](#troubleshooting) section or open an issue on GitHub.
