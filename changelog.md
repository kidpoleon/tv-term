# tv-term Changelog

## v1.0.2 (2026-06-04)

**Enhanced output naming and documentation**

- Updated output naming convention to TYPE_DOMAIN-NAME_STATUS_ISO-8601.EXT
  - TYPE can be LOCAL, URL, XTREAM, or DATABASE
  - Only uses custom prefix if specified by user in interactive wizard
- Updated email to kidpoleon@proton.me throughout codebase
- Improved README.md with more badges and better organization
- Added screenshots to README.md
- Added hyperlink to peterpt/IPTV-Check repository in credits
- Improved error handling with retry logic for URL loading
- Enhanced graceful Ctrl+C termination protocol
- Updated version to 1.0.2

## v1.0.1 (2026-06-04)

**Major improvements and fixes**

- Removed old monolithic tv_term.py script (1,146 lines deleted)
- Cleaned up unnecessary files (build/, output/, debug.log, test output files)
- Fixed output naming convention to include domain name from source
- Added graceful Ctrl+C termination protocol with shutdown_event
- Added retry logic for URL loading (3 retries with timeout handling)
- Added retry logic for database loading
- Improved error handling with specific exception types
- Added allow_redirects=True for better URL handling
- Enhanced logging for timeout and retry scenarios
- Updated version to 1.0.1

## v1.0.0 (2026-06-04)

**Complete rewrite and modernization**

- Renamed project from IPTV-Check to tv-term
- Refactored codebase to MVC architecture (models, views, controllers, utils)
- Removed GUI and OCR functionality for simplicity and speed
- Implemented TUI-only design using rich library
- Added XTREAM API endpoint support
- Implemented organized output structure (online/offline/unreachable directories)
- Improved M3U/M3U8 parsing with multiple regex patterns
- Optimized stream verification using ffprobe only
- Refactored codebase to follow PEP 8 guidelines
- Updated file naming to professional GitHub standards
- Enhanced TUI with better layout and features
- Improved error handling and logging
- Added support for .m3u and .m3u8 files
- Added YouTube URL resolution via yt-dlp
- Implemented smart filtering (skip duplicates, uncheckable streams)
- Added links database manager
- Cross-platform compatibility (Windows, macOS, Linux)
- Changed author to kidpoleon
- Updated version to 1.0.0

## Previous Versions (IPTV-Check)

* v3.0 - Fully python3 integrated app, all functionalities from previous version in CLI and GUI mode, added website finder m3u to find m3u links inside websites
* v2.1b - Ffmpeg full implementation on capturing video streams to be checked ahead, also added "EXTVLCOPT" to the filters before parsing the links to ffmpeg to test them out
* v2.0 - OCR Detection on working streaming channels to detect if that channel is really online or is just a bad login
* v1.0 - Few changes in m3u files
* v1.0 - Implemented automatic detection of xml iptv files
* v1.0 - Bug fix & implementation, changed how iptv-check filters the m3u file lists and from now will autoremove repeated urls on lists to scan
* v1.0 - Bug fix, waiting for data was change from 2s to 4s because servers may take sometime to start sending data
* v1.0 - First Release
