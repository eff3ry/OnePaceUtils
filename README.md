# OnePace Utils

A collection of Python utilities for managing OnePace anime episodes, including torrent scraping, metadata collection, subtitle management, and NFO file updates for media servers like Jellyfin and Plex.

## Table of Contents

- [Overview](#overview)
- [Scripts](#scripts)
  - [torrentScraper.py](#torrentscraper)
  - [MetaScraper_NewSite.py](#metascrapernewsite)
  - [MetaScraper_OldSite.py](#metascraperoldsite)
  - [subScraper.py](#subscraperpy)
  - [nfoUpdater.py](#nfoupdaterpy)
- [Generated Files](#generated-files)
- [Requirements](#requirements)
- [Usage Examples](#usage-examples)

## Overview

OnePace Utils provides comprehensive tools for managing OnePace content, a fan-edited version of the One Piece anime that removes filler content. These scripts help automate the collection of torrents, metadata, subtitles, and NFO file management for media organization.

## Scripts

### torrentScraper.py

**Purpose**: Scrapes OnePace torrent information from nyaa.si/user/Galaxy9000

**Features**:
- Extracts torrent metadata: file names, magnet links, file sizes, upload dates, seeders/leechers
- Detects batch torrents vs single episodes using file extensions
- Extracts file lists for batch torrents
- Handles pagination automatically
- Saves data to `generated/torrents.json`

**Key Functions**:
- `NyaaScraper.scrape_all_pages()` - Main scraping function
- `extract_magnet_link()` - Extracts magnet links from torrent pages
- `extract_file_list()` - Gets file lists for batch torrents
- `is_batch_torrent()` - Determines if torrent is batch (no file extension) or single episode

**Usage**:
```python
from torrentScraper import NyaaScraper

scraper = NyaaScraper()
scraper.scrape_all_pages()
```

**Output**: Creates `generated/torrents.json` with comprehensive torrent data

---

### MetaScraper_NewSite.py

**Purpose**: Scrapes arc and episode metadata from the current OnePace website (onepace.net)

**Features**:
- Extracts arc information: names, descriptions, episodes, quality levels
- Collects download links for different qualities (480p, 720p, 1080p)
- Handles both subtitled and dubbed versions
- Uses Selenium for JavaScript-heavy content
- Saves comprehensive metadata to JSON

**Key Functions**:
- `findArcDivs()` - Locates arc containers on the website
- Data extraction for plot summaries, background images, and download links
- Quality detection and link categorization

**Dependencies**: 
- Selenium WebDriver
- Chrome/Chromium browser

**Usage**:
```python
# Run the script directly
python MetaScraper_NewSite.py
```

**Output**: Creates `generated/siteMetadata.json` with current site data

---

### MetaScraper_OldSite.py

**Purpose**: Scrapes metadata from the archived OnePace website for historical data

**Features**:
- Collects legacy arc and episode information
- Maintains compatibility with older OnePace releases
- Preserves historical metadata for discontinued episodes
- Selenium-based scraping for archived content

**Usage**:
```python
# Run the script directly
python MetaScraper_OldSite.py
```

**Output**: Creates `generated/old/siteMetadata.json` with archived site data

---

### subScraper.py

**Purpose**: Manages subtitle titles and NFO file updates from OnePace GitHub repository

**Features**:
- Scrapes subtitle/episode titles from GitHub repository
- Matches episodes to local file directories
- Creates new NFO files for missing episodes
- Updates existing NFO files with correct metadata
- Handles multiple arc types and naming conventions

**Key Functions**:
- `scrapeSubtitles()` - Main scraping function for GitHub data
- `create_nfo_file()` - Creates new NFO files with basic metadata
- `find_best_folder_match()` - Matches GitHub data to local directories
- `set_nfo_title()` - Updates NFO title tags
- `set_nfo_episode_number()` - Updates episode numbers in NFO files

**NFO File Structure**:
```xml
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<episodedetails>
  <title>Episode Title</title>
  <showtitle>One Pace</showtitle>
  <episode>1</episode>
</episodedetails>
```

**Usage**:
```python
# Run the script directly for interactive mode
python subScraper.py
```

**Features**:
- Interactive folder matching
- Automatic NFO file creation
- Episode numbering management
- GitHub repository integration

---

### nfoUpdater.py

**Purpose**: Updates NFO files with metadata from scraped site data

**Features**:
- Bulk updates NFO files with episode descriptions and titles
- Integrates with scraped metadata JSON files
- Interactive arc/season selection
- Automatic episode number detection from filenames
- Updates both episode and season-level NFO files

**Key Functions**:
- `modify_plot_outline_nfo()` - Updates plot and outline tags
- `modify_single_nfo()` - Updates individual NFO tags
- `get_nfo_episode_number()` - Extracts episode numbers from NFO files
- `get_regex_episode_number()` - Detects episode numbers from filenames
- `update_season_description()` - Updates season-level descriptions

**Configuration**:
- `metaJsonFile` - Path to metadata JSON file (default: "./meta.json")
- `rootFolder` - Path to OnePace episode directories (default: "./One Pace/")

**Usage**:
```python
# Run the script directly for interactive mode
python nfoUpdater.py
```

**Interactive Features**:
- Arc/season selection menu
- Directory matching assistance
- Confirmation prompts for updates
- Episode-by-episode processing

## Generated Files

### `generated/torrents.json`
Contains comprehensive torrent data with structure:
```json
{
  "scraper_info": {
    "scraper_version": "1.0",
    "last_updated": "2024-01-01T12:00:00Z",
    "total_torrents": 150
  },
  "torrents": [
    {
      "title": "[One Pace][1080-1081] Egghead 14 [1080p][3C0010BE].mkv",
      "magnet_link": "magnet:?xt=urn:btih:...",
      "file_size": "1.2 GiB",
      "upload_date": "2024-01-01",
      "seeders": 10,
      "leechers": 2,
      "is_batch": false,
      "files": []
    }
  ]
}
```

### `generated/siteMetadata.json`
Current OnePace website metadata with arc and episode information

### `generated/old/siteMetadata.json`
Archived OnePace website metadata for historical episodes

## Requirements

**Python Packages**:
```bash
pip install requests beautifulsoup4 selenium lxml
```

**System Requirements**:
- Python 3.7+
- Chrome/Chromium browser (for Selenium scripts)
- ChromeDriver (automatically managed by newer Selenium versions)

**Optional Dependencies**:
- `pathlib` (built-in Python 3.4+)
- `json` (built-in)
- `re` (built-in)
- `xml.etree.ElementTree` (built-in)

## Usage Examples

### Individual Script Usage

**Each script is designed to run independently and should be executed separately:**

1. **Scrape Current Torrents**:
```bash
python torrentScraper.py
```

2. **Collect Current Site Metadata**:
```bash
python MetaScraper_NewSite.py
```

3. **Collect Legacy Site Metadata**:
```bash
python MetaScraper_OldSite.py
```

4. **Update NFO Files with Scraped Metadata**:
```bash
python nfoUpdater.py
```

5. **Manage Subtitle Information from GitHub**:
```bash
python subScraper.py
```

### Script Execution Notes

- **Run each script individually** - Scripts are not designed to import each other
- **No dependencies between scripts** - Each can be run in any order
- **Interactive scripts** - `nfoUpdater.py` and `subScraper.py` require user input
- **Automated scripts** - `torrentScraper.py` and both MetaScraper scripts run fully automated

### Individual Function Usage

**For advanced users who want to use specific functions:**

```python
# Example: Using torrentScraper functions individually
from torrentScraper import NyaaScraper

scraper = NyaaScraper()
scraper.scrape_all_pages()
```

```python
# Example: Using nfoUpdater functions individually  
from nfoUpdater import modify_single_nfo
from pathlib import Path

# Update a single NFO file
nfo_path = Path("episode.nfo")
modify_single_nfo(nfo_path, "title", "New Episode Title")
```

**Note**: Most users should run the scripts directly rather than importing functions.

## File Structure

```
OnePaceUtils/
├── torrentScraper.py          # Torrent data collection
├── MetaScraper_NewSite.py     # Current site metadata
├── MetaScraper_OldSite.py     # Legacy site metadata
├── subScraper.py              # Subtitle and NFO management
├── nfoUpdater.py              # NFO file updates
├── generated/                 # Output directory
│   ├── torrents.json         # Torrent data
│   ├── siteMetadata.json     # Current metadata
│   └── old/                  # Legacy data
│       └── siteMetadata.json # Archived metadata
└── README.md                 # This file
```

## Notes

- **Rate Limiting**: Scripts include delays to respect website rate limits
- **Error Handling**: Comprehensive error handling for network and parsing issues
- **Data Persistence**: All scraped data is saved in JSON format for reuse
- **Batch Detection**: Uses file extension presence to distinguish batch vs single torrents
- **NFO Compatibility**: Generated NFO files work with Jellyfin, Plex, and other media servers
- **Interactive Mode**: Several scripts provide interactive prompts for user control

## License

This project is for educational and personal use. Respect the terms of service of the websites being scraped.
