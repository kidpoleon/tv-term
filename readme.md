# tv-term

<div align="center">

<img src="icon/png.png" alt="tv-term icon" width="128">

**Terminal-based IPTV/M3U Stream Validator**

A modern, efficient tool for validating IPTV playlists with a beautiful TUI.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-green.svg)](https://www.python.org/dev/peps/pep-0008/)
[![Version](https://img.shields.io/badge/version-1.0.3-orange.svg)](https://github.com/kidpoleon/tv-term/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/kidpoleon/tv-term)
[![GitHub Stars](https://img.shields.io/github/stars/kidpoleon/tv-term?style=social)](https://github.com/kidpoleon/tv-term/stargazers)

</div>

## Description

tv-term is a complete rewrite focused on speed, accuracy, and simplicity. It features a modern Terminal User Interface (TUI) powered by the `rich` library, providing beautiful progress bars, tables, and real-time statistics in your terminal.

It reads M3U/M3U8 playlists from local files or URLs (including XTREAM API endpoints), checks each stream to see if it's online using optimized ffprobe verification, and saves the results to organized output directories.

## Screenshots

<div align="center">

### Interactive Wizard
<img src="screenshots/01_ex_wizard.png" alt="tv-term interactive wizard" width="800">

### Local File Check
<img src="screenshots/02_ex_local.png" alt="tv-term local file check" width="800">

### URL Check
<img src="screenshots/03_ex_url.png" alt="tv-term URL check" width="800">

### XTREAM API Check
<img src="screenshots/04_ex_xtream.png" alt="tv-term XTREAM API check" width="800">

### Progress Display
<img src="screenshots/05_ex_progress.png" alt="tv-term progress display" width="800">

### Final Report
<img src="screenshots/06_ex_report.png" alt="tv-term final report" width="800">

</div>

## Key Features

- **TUI-Only Design**: Clean, modern terminal interface with rich formatting and progress tracking
- **High-Performance Concurrency**: Utilizes ThreadPoolExecutor for efficient parallel stream checking (1-20 workers)
- **Improved M3U/M3U8 Parsing**: Multiple regex patterns for better compatibility with various M3U formats
- **XTREAM API Support**: Native support for XTREAM Codes API endpoints
- **Optimized Verification**: Fast ffprobe-based stream validation without unnecessary overhead
- **Organized Output**: Streams are automatically categorized into `online/`, `offline/`, and `unreachable/` directories
- **Smart Filtering**:
  - Skip Duplicates: Reads existing output file to skip known-good URLs
  - YouTube Support: Resolves YouTube links via yt-dlp
  - Uncheckable Filter: Isolates streams with tokens/auth into separate files
- **Links Database**: Built-in database manager for storing favorite M3U URLs
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **PEP 8 Compliant**: Clean, professional code following Python best practices

## Requirements

### 1. External Dependencies

The following command-line tools must be installed on your system and accessible in your system's PATH:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg ffprobe yt-dlp

# macOS (with Homebrew)
brew install ffmpeg yt-dlp

# Windows (using Chocolatey)
choco install ffmpeg yt-dlp
```

- **ffmpeg**: Video/audio stream processing
- **ffprobe**: Stream analysis and verification
- **yt-dlp**: YouTube URL resolution

### 2. Python Dependencies

The script requires Python 3.7+ and the following third-party libraries:

```bash
pip install -r requirements.txt
```

Required libraries:
- `requests`: HTTP requests
- `rich`: Terminal UI formatting

## Installation

### Option 1: Using the Executable (Windows)

Download the latest `tv-term.exe` from the [Releases](https://github.com/kidpoleon/tv-term/releases) page. No installation required - just run the executable.

**Note**: The executable requires ffmpeg, ffprobe, and yt-dlp to be installed and in your system PATH. See [External Dependencies](#1-external-dependencies) below.

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/kidpoleon/tv-term.git
cd tv-term

# Install Python dependencies
pip install -r requirements.txt

# Ensure external dependencies are in your PATH
```

### Building the Executable

To build the executable yourself:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller tv_term.spec

# The executable will be in dist/tv-term.exe
```

## Usage

### Using the Executable (Windows)

```bash
# Run in interactive mode (no arguments required)
tv-term.exe

# Check a local M3U file
tv-term.exe -f playlist.m3u

# Check a remote URL
tv-term.exe -f "http://example.com/playlist.m3u"

# Check an XTREAM API endpoint
tv-term.exe -f "http://your-server.com/get.php?username=YOUR_USER&password=YOUR_PASS&type=m3u_plus"

# Check with custom output filename
tv-term.exe -f "playlist.m3u" -o "my_checked.m3u"

# Re-check an existing output file
tv-term.exe -r "my_checked.m3u"

# Check all playlists from the database
tv-term.exe -d -o "all_checked.m3u"

# Use 20 workers with 10-second timeout
tv-term.exe -f "playlist.m3u" -w 20 -t 10

# Show version
tv-term.exe --version
```

### Using Python (Cross-Platform)

```bash
# Run in interactive mode (no arguments required)
python main.py

# Check a local M3U file
python main.py -f playlist.m3u

# Check a remote URL
python main.py -f "http://example.com/playlist.m3u"

# Check an XTREAM API endpoint
python main.py -f "http://your-server.com/get.php?username=YOUR_USER&password=YOUR_PASS&type=m3u_plus"

# Check with custom output filename
python main.py -f "playlist.m3u" -o "my_checked.m3u"

# Re-check an existing output file
python main.py -r "my_checked.m3u"

# Check all playlists from the database
python main.py -d -o "all_checked.m3u"

# Use 20 workers with 10-second timeout
python main.py -f "playlist.m3u" -w 20 -t 10

# Show version
python main.py --version
```

### Manage Links Database

```bash
# Interactive database manager
tv-term.exe --manage-db
# or
python main.py --manage-db
```

### All Command-Line Arguments

```
-h, --help            Show help message and exit
-f FILE, --file FILE  Path or URL to M3U/M3U8 playlist file
-d, --database        Use links database as input
-r RECHECK, --recheck RECHECK
                      Re-check existing output file
-o OUTPUT, --output OUTPUT
                      Output file (default: updated.m3u)
-w WORKERS, --workers WORKERS
                      Parallel workers (1-20, default: 10)
-t TIMEOUT, --timeout TIMEOUT
                      Timeout per stream in seconds (default: 5)
--no-skip             Disable skipping known good URLs
--manage-db           Manage links database interactively
--version             Show version and exit
-i, --interactive     Run in interactive mode
```

## Output Structure

tv-term automatically organizes checked streams with the naming convention: `TYPE_DOMAIN-NAME_STATUS_ISO-8601.EXT`

Where:
- **TYPE**: LOCAL, URL, XTREAM, or DATABASE (source type)
- **DOMAIN-NAME**: Extracted domain or filename from source
- **STATUS**: online, offline, or unreachable
- **ISO-8601**: Timestamp in ISO-8601 format (e.g., 20260604T090000)
- **EXT**: .m3u file extension

Examples:
- `LOCAL_aria_online_20260604T090931.m3u`
- `URL_192-168-0-100_offline_20260604T091113.m3u`
- `XTREAM_myserver_online_20260604T092000.m3u`

**Note**: Custom prefixes are only used if specified by the user in interactive mode.

## Configuration

The application automatically creates configuration files on first run:

- **tv_term_config.ini**: Stream pattern definitions
- **tv_term_links.ini**: Links database for favorite M3U URLs

## XTREAM API Support

tv-term natively supports XTREAM Codes API endpoints. Simply provide the full URL:

```bash
python main.py -f "http://your-server.com/get.php?username=YOUR_USER&password=YOUR_PASS&type=m3u_plus"
```

The tool will automatically detect the XTREAM API format and handle it appropriately.

## What's New

### v1.0.2
- Enhanced output naming convention: TYPE_DOMAIN-NAME_STATUS_ISO-8601.EXT
- Added source type detection (LOCAL, URL, XTREAM, DATABASE)
- Custom prefix only used if specified in interactive mode
- Updated email to kidpoleon@proton.me
- Added screenshots to documentation
- Improved README.md with more badges and better organization
- Added hyperlink to peterpt/IPTV-Check repository in credits
- Improved error handling with retry logic for URL loading
- Enhanced graceful Ctrl+C termination protocol

### v1.0.1
- Removed old monolithic tv_term.py script
- Cleaned up unnecessary files
- Fixed output naming convention to include domain name
- Added graceful Ctrl+C termination protocol
- Added retry logic for URL loading (3 retries)
- Added retry logic for database loading
- Improved error handling with specific exception types
- Enhanced logging for timeout and retry scenarios

### v1.0.0
- Complete rewrite with TUI-only design
- Removed GUI and OCR functionality for simplicity and speed
- Improved M3U/M3U8 parsing with multiple regex patterns
- Added XTREAM API endpoint support
- Optimized stream verification using ffprobe only
- Modern terminal UI with rich library
- PEP 8 compliant codebase
- Better error handling and logging
- Interactive mode - no CLI arguments required
- Windows executable with custom icon
- Python version checking
- Enhanced error handling with user-friendly messages
- Input validation and timeout limits
- Graceful keyboard interrupt handling
- --version flag for quick version info

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**kidpoleon**

## Credits

- Originally based on [IPTV-Check](https://github.com/peterpt/IPTV-Check) by peterpt
- Complete rewrite and modernization by kidpoleon
