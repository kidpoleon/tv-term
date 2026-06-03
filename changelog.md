# tv-term Changelog

## v1.0.0 (2026-06-04)

**Complete rewrite and modernization**

- Renamed project from IPTV-Check to tv-term
- Updated version to 1.0.0
- Changed author to kidpoleon
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

## Previous Versions (IPTV-Check)

* v3.0 - Fully python3 integrated app, all functionalities from previous version in CLI and GUI mode, added website finder m3u to find m3u links inside websites
* v2.1b - Ffmpeg full implementation on capturing video streams to be checked ahead, also added "EXTVLCOPT" to the filters before parsing the links to ffmpeg to test them out
* v2.0 - OCR Detection on working streaming channels to detect if that channel is really online or is just a bad login
* v1.0 - Few changes in m3u files
* v1.0 - Implemented automatic detection of xml iptv files
* v1.0 - Bug fix & implementation, changed how iptv-check filters the m3u file lists and from now will autoremove repeated urls on lists to scan
* v1.0 - Bug fix, waiting for data was change from 2s to 4s because servers may take sometime to start sending data
* v1.0 - First Release
