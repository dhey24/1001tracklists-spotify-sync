# Changelog

## [1.0.0] - 2025-10-07

### Project Refactored to Manual Workflow

This release represents a major refactoring of the project to focus on a reliable manual copy-paste workflow instead of automated web scraping.

### Why the Change?

1001tracklists.com uses Cloudflare protection and dynamically loaded JavaScript content, making automated scraping unreliable and complex. The manual approach is:
- Faster and more reliable
- Respects website policies
- Works with any tracklist
- Requires no browser automation

### Added

- **Manual text parsing** - Copy & paste tracklists directly from 1001tracklists.com
- **Smart label cleanup** - Automatically removes label metadata (NINJA, THIS NEVER HAPPENED, VIVRANT, etc.)
- **Title extraction** - Uses first line as playlist name
- **Playlist suffix** - Automatically adds "(Tracklist Sync)" to playlist names
- **Unmatched track logging** - Clear warnings for tracks not found on Spotify
- **Playlist overwrite** - Updates existing playlists instead of creating duplicates
- **Example tracklist file** - Template for manual input
- **Comprehensive README** - Detailed instructions for manual workflow

### Changed

- Renamed `sync_tracklist_practical.py` to `sync.py` for simplicity
- Updated README with manual workflow documentation
- Improved regex patterns for better label/metadata cleanup
- Enhanced track title cleaning to handle parentheses with sublabels

### Removed

- All scraper implementations (non-functional due to Cloudflare/JS)
  - `tracklist_scraper.py`
  - `tracklist_scraper_enhanced.py`
  - `tracklist_scraper_selenium.py`
- Scraper test scripts
  - `test_all_scrapers.py`
  - `test_scraper.py`
  - `test_enhanced_scraper.py`
  - `test_selenium_scraper.py`
  - `test_complete_workflow.py`
  - `demo_tracklist.py`
- Temporary debug/test files
  - `debug_parser.py`
  - `simple_debug.py`
  - `parse_html_source.py`
  - `parse_html_tracks.py`
  - `parse_manual_*.py` files
  - `parse_raw_copy.py`
  - `test_parsing.py`
  - `test_dry_run.py`
  - `sync_lane8.py`
- Old sync scripts
  - `sync_tracklist.py`
  - `sync_tracklist_robust.py`
- Test data files
  - `manual_copy_test.txt`
  - `lane8_tracks.txt`
  - `full_page_source_test.html`
- Documentation for scraping approaches
  - `SCRAPING_SOLUTIONS.md`
  - `ALTERNATIVE_SOURCES.md`

### Technical Details

#### Label Cleanup Patterns
The parser now removes:
- All-caps words at the end (e.g., `NINJA`, `TRUESOUL`)
- Sublabels in parentheses (e.g., `COLUMBIA (SONY)`)
- Bracketed content (e.g., `[THIS NEVER HAPPENED]`)
- "Info Link" and trailing metadata

#### Track Format Support
- Standard format: `Artist - Title`
- Remixes: `Artist - Title (Remix)`
- Mashups: `Artist1 vs. Artist2 - Title1 vs. Title2 (Mashup)` (splits into 2 tracks)
- Featured artists: `Artist ft. Featured - Title`
- Multiple artists: `Artist1 & Artist2 - Title`

#### Match Results
Typical success rate: 75-80% of tracks matched to Spotify

### Project Structure

```
1001tracklists-spotify-sync/
├── sync.py                    # Main sync script (renamed from sync_tracklist_practical.py)
├── app/                       # Core application code
│   ├── models.py             # Data models
│   ├── match.py              # Fuzzy matching
│   ├── auth_flow.py          # OAuth flow
│   └── providers/
│       ├── spotify.py        # Spotify API
│       └── manual_tracklist.py  # Text parsing
├── scripts/
│   ├── setup_env.py          # Credential setup
│   └── install_dependencies.py
├── logs/                     # Auto-created sync logs
├── tokens/                   # Auto-created Spotify tokens
├── example_tracklist.txt     # Example file format
├── requirements.txt
├── .gitignore
└── README.md
```

### Migration Guide

If you were using the old scraper-based workflow:

**Old way:**
```bash
python sync_tracklist_robust.py "https://www.1001tracklists.com/tracklist/..."
```

**New way:**
```bash
# 1. Copy tracklist text from 1001tracklists.com
# 2. Paste into a text file (e.g., my_tracklist.txt)
# 3. Run sync
python sync.py my_tracklist.txt
```

### Credits

Based on the beatport-sync project workflow. Special thanks to the Spotify and Python communities for excellent libraries and documentation.

