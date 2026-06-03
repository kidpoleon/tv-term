#!/usr/bin/env python3
"""
tv-term - Terminal-based IPTV/M3U Stream Validator

A modern, efficient tool for validating IPTV playlists with a beautiful TUI.
Supports M3U/M3U8 files, URLs, and XTREAM API endpoints.

Author: kidpoleon
Version: 1.0.0
License: MIT
"""

import sys
import os
import re
import subprocess
import tempfile
import threading
import signal
import shutil
import argparse
import logging
import configparser
from pathlib import Path
import time
from urllib.parse import urlparse, urljoin, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime

# Third-party libraries
import requests

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich import box
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("ERROR: 'rich' library is required. Install with: pip install rich")
    sys.exit(1)


# Configuration & Constants
VERSION = "1.0.0"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)
AUDIO_USER_AGENT = "iTunes/9.1.1"
MIN_FILE_SIZE_BYTES = 100
WORKER_TIMEOUT_SECONDS = 25
UNCHECKABLE_URL_LENGTH_THRESHOLD = 250
UNCHECKABLE_KEYWORDS = [
    "token",
    "auth",
    "login",
    "key",
    "signature",
    "session",
    "exp",
]
TEMP_FILE_PREFIX = "tv-term-temp-"
YT_DLP_TIMEOUT_SECONDS = 15

# Portable File Paths
APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE_PATH = APP_DIR / "tv_term_config.ini"
LINKS_DB_PATH = APP_DIR / "tv_term_links.ini"
DEBUG_LOG_PATH = APP_DIR / "debug.log"
OUTPUT_DIR = APP_DIR / "output"

# Setup Console
console = Console()


# Setup Debug Logging
def setup_logging() -> None:
    """Configure debug logging to file."""
    logging.basicConfig(
        filename=DEBUG_LOG_PATH,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.info(f"tv-term v{VERSION} started.")


# Dependency Checks
FFMPEG_PATH = shutil.which("ffmpeg")
FFPROBE_PATH = shutil.which("ffprobe")
YT_DLP_PATH = shutil.which("yt-dlp")
GIT_PATH = shutil.which("git")


def check_dependencies() -> List[str]:
    """Check for required external dependencies."""
    essential_deps = {
        "ffmpeg": FFMPEG_PATH,
        "ffprobe": FFPROBE_PATH,
        "yt-dlp": YT_DLP_PATH,
    }
    missing_essential = [name for name, path in essential_deps.items() if not path]
    return missing_essential


# Cleanup on Start
def cleanup_stale_temp_files() -> None:
    """Remove temporary files from previous runs."""
    try:
        temp_dir = tempfile.gettempdir()
        for f_name in [
            f for f in os.listdir(temp_dir) if f.startswith(TEMP_FILE_PREFIX)
        ]:
            try:
                os.remove(os.path.join(temp_dir, f_name))
            except OSError as e:
                logging.warning(
                    f"Could not remove stale temp file: {f_name}. Reason: {e}"
                )
    except Exception as e:
        logging.error(
            f"Error during initial temp file cleanup: {e}", exc_info=True
        )


# Ensure Output Directory Structure
def ensure_output_dirs() -> None:
    """Create output directory structure if it doesn't exist."""
    online_dir = OUTPUT_DIR / "online"
    offline_dir = OUTPUT_DIR / "offline"
    unreachable_dir = OUTPUT_DIR / "unreachable"

    for directory in [online_dir, offline_dir, unreachable_dir]:
        directory.mkdir(parents=True, exist_ok=True)


# Configuration Management
class IniManager:
    """Manages INI configuration files."""

    def __init__(self, path: Path):
        self.path = path

    def load(self, defaults_map: Optional[Dict] = None) -> Dict:
        """Load configuration from INI file."""
        config = configparser.ConfigParser()
        if self.path.exists():
            try:
                config.read(self.path, encoding="utf-8")
            except configparser.Error as e:
                logging.error(
                    f"Error reading config file {self.path}: {e}. "
                    "A new one will be created."
                )
                config = configparser.ConfigParser()

        needs_save = False
        if defaults_map:
            for section, defaults in defaults_map.items():
                if not config.has_section(section):
                    config.add_section(section)
                    for key, value in defaults.items():
                        config.set(section, key, value)
                    needs_save = True

        if needs_save:
            self.save(config)

        return {
            section.lower(): dict(config.items(section))
            for section in config.sections()
        }

    def save(self, config_obj: configparser.ConfigParser) -> None:
        """Save configuration to INI file."""
        try:
            with open(self.path, "w", encoding="utf-8") as configfile:
                config_obj.write(configfile)
        except Exception as e:
            logging.error(
                f"Failed to save INI file at {self.path}: {e}", exc_info=True
            )
            console.print(
                f"[red]Could not save settings to {self.path}. "
                "Please check permissions.[/red]"
            )


# Improved M3U Parser with XTREAM API Support
def is_xtream_api_url(url: str) -> bool:
    """Check if URL is an XTREAM API endpoint."""
    parsed = urlparse(url)
    return (
        "get.php" in parsed.path
        and "username" in parsed.query
        and "password" in parsed.query
    )


def parse_m3u(content: str) -> List[Dict[str, str]]:
    """
    Improved M3U parser with multiple regex patterns for better compatibility.
    Handles standard M3U, extended M3U, M3U8, and XTREAM API formats.
    """
    streams = []

    # Pattern 1: Extended M3U with group-title
    pattern1 = re.compile(
        r'#EXTINF:-1\s*(?:[^,]*,)?\s*([^\n]+)\n'
        r'(?:#EXT[^\n]*\n)*'
        r'(https?://[^\s]+)',
        re.IGNORECASE,
    )

    # Pattern 2: Extended M3U with group-title attribute
    pattern2 = re.compile(
        r'#EXTINF:-1\s*group-title="([^"]*)"[^,]*,([^\n]+)\n'
        r'(?:#EXT[^\n]*\n)*'
        r'(https?://[^\s]+)',
        re.IGNORECASE,
    )

    # Pattern 3: Extended M3U with tvg-name
    pattern3 = re.compile(
        r'#EXTINF:-1\s*tvg-name="([^"]*)"[^,]*,([^\n]+)\n'
        r'(?:#EXT[^\n]*\n)*'
        r'(https?://[^\s]+)',
        re.IGNORECASE,
    )

    # Pattern 4: Extended M3U with logo
    pattern4 = re.compile(
        r'#EXTINF:-1\s*tvg-logo="([^"]*)"[^,]*,([^\n]+)\n'
        r'(?:#EXT[^\n]*\n)*'
        r'(https?://[^\s]+)',
        re.IGNORECASE,
    )

    # Pattern 5: Simple M3U (title, url)
    pattern5 = re.compile(
        r'#EXTINF:-1\s*,([^\n]+)\n' r'(https?://[^\s]+)',
        re.IGNORECASE,
    )

    # Pattern 6: URL-only lines (fallback)
    pattern6 = re.compile(r'^(https?://[^\s]+)$', re.MULTILINE)

    # Try pattern 2 first (most complete)
    matches = pattern2.findall(content)
    if matches:
        for group, title, url in matches:
            streams.append({
                "title": title.strip(),
                "url": url.strip(),
                "group": group.strip() or "General",
            })
        return streams

    # Try pattern 3 (tvg-name)
    matches = pattern3.findall(content)
    if matches:
        for tvg_name, title, url in matches:
            streams.append({
                "title": title.strip(),
                "url": url.strip(),
                "group": tvg_name.strip() or "General",
            })
        return streams

    # Try pattern 4 (tvg-logo)
    matches = pattern4.findall(content)
    if matches:
        for logo, title, url in matches:
            streams.append({
                "title": title.strip(),
                "url": url.strip(),
                "group": "General",
                "logo": logo.strip(),
            })
        return streams

    # Try pattern 1 (extended without group)
    matches = pattern1.findall(content)
    if matches:
        for title, url in matches:
            streams.append({
                "title": title.strip(),
                "url": url.strip(),
                "group": "General",
            })
        return streams

    # Try pattern 5 (simple)
    matches = pattern5.findall(content)
    if matches:
        for title, url in matches:
            streams.append({
                "title": title.strip(),
                "url": url.strip(),
                "group": "General",
            })
        return streams

    # Fallback to URL-only
    matches = pattern6.findall(content)
    if matches:
        for i, url in enumerate(matches):
            streams.append({
                "title": f"Stream_{i + 1}",
                "url": url.strip(),
                "group": "General",
            })

    return streams


def write_m3u_header(file_handle) -> None:
    """Write M3U header to file."""
    if file_handle:
        file_handle.write("#EXTM3U\n\n")
        file_handle.flush()


def write_m3u_entry(file_handle, stream_info: Dict) -> None:
    """Write M3U entry to file."""
    if file_handle:
        group = stream_info.get("group", "General")
        title = stream_info.get("title", "Unknown")
        url = stream_info.get("url", "")
        logo = stream_info.get("logo", "")

        if logo:
            file_handle.write(
                f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{title}\n'
                f"{url}\n\n"
            )
        else:
            file_handle.write(
                f'#EXTINF:-1 group-title="{group}",{title}\n{url}\n\n'
            )
        file_handle.flush()


# URL Sanitization
def sanitize_url(url: str) -> str:
    """Sanitize URL by removing ad parameters and query strings."""
    try:
        # Remove ad-related query parameters from .m3u8 URLs
        m3u8_query_index = url.find(".m3u8?")
        if m3u8_query_index != -1 and "ads." in url[m3u8_query_index:]:
            sanitized_url = url[: m3u8_query_index + len(".m3u8")]
            logging.info(f"Sanitized URL: '{url}' -> '{sanitized_url}'")
            return sanitized_url
    except Exception as e:
        logging.warning(f"Error during URL sanitization: {e}")
    return url


# Stream Type Detection
def get_stream_type(url: str) -> str:
    """
    Detect stream type (video/audio) using ffprobe.
    Returns 'video', 'audio', or 'unknown'.
    """
    if not FFPROBE_PATH:
        return "unknown"

    try:
        cmd = [FFPROBE_PATH, "-v", "quiet", "-user_agent", AUDIO_USER_AGENT, "-i", url]
        result = subprocess.run(
            cmd, capture_output=True, text=True, errors="ignore", timeout=10
        )
        output = result.stderr

        if "Stream #" in output and "Video:" in output:
            return "video"
        if "Stream #" in output and "Audio:" in output:
            return "audio"
        return "unknown"
    except (subprocess.TimeoutExpired, Exception):
        return "unknown"


# YouTube URL Resolution
def resolve_youtube_url(url: str) -> Optional[str]:
    """Resolve YouTube URL to direct stream URL using yt-dlp."""
    if not YT_DLP_PATH:
        return None

    try:
        cmd = [YT_DLP_PATH, "--get-url", url]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=YT_DLP_TIMEOUT_SECONDS
        )
        if result.returncode == 0 and result.stdout.strip():
            direct_url = result.stdout.strip().splitlines()[0]
            logging.debug(f"yt-dlp resolved: {url} -> {direct_url}")
            return direct_url
    except Exception as e:
        logging.error(f"yt-dlp failed for {url}: {e}")
    return None


# Stream Verification
def verify_stream(stream_info: Dict, config: Dict) -> Tuple[bool, str]:
    """
    Verify if a stream is online using ffprobe.
    Returns (is_online, status_message).
    """
    url = sanitize_url(stream_info["url"])

    # Resolve YouTube URLs
    if "youtube.com/" in url or "youtu.be/" in url:
        resolved = resolve_youtube_url(url)
        if resolved:
            url = resolved
        else:
            return False, "YouTube Error"

    # Determine stream type
    check_type = None
    for pattern, type_ in config.get("stream_patterns", {}).items():
        if pattern in url:
            check_type = type_
            break

    if check_type is None and re.search(r":\d+(?:/[^.]*)?$", url):
        check_type = "audio"

    if check_type is None:
        probe_result = get_stream_type(url)
        check_type = "video" if probe_result == "video" else "audio"

    # Verify stream
    try:
        user_agent = AUDIO_USER_AGENT if check_type == "audio" else USER_AGENT
        timeout_us = str(config.get("timeout", 5) * 1000000)

        cmd = [
            FFPROBE_PATH,
            "-v",
            "error",
            "-user_agent",
            user_agent,
            "-timeout",
            timeout_us,
            "-i",
            url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="ignore",
            timeout=WORKER_TIMEOUT_SECONDS,
        )

        if result.returncode == 0:
            return True, "ON"
        else:
            return False, "OFF"

    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        logging.error(f"Error verifying {url}: {e}")
        return False, "Error"


# Main Checker Class
class TVTermChecker:
    """Main class for tv-term stream checking functionality."""

    def __init__(self, args):
        self.args = args
        self.config_manager = IniManager(CONFIG_FILE_PATH)
        self.links_db_manager = IniManager(LINKS_DB_PATH)

        # Load configuration
        defaults = {
            "Settings": {},
            "StreamPatterns": {
                ".m3u8": "video",
                ".m3u": "video",
                ".ts": "video",
                ".mp4": "video",
                ".mp3": "audio",
                ".aac": "audio",
                "/stream": "audio",
            },
        }
        all_configs = self.config_manager.load(defaults)
        self.stream_patterns = all_configs.get("streampatterns", {})

        # Statistics
        self.total_streams = 0
        self.online_count = 0
        self.offline_count = 0
        self.unreachable_count = 0
        self.processed_count = 0
        self.lock = threading.Lock()

        # Output files
        self.online_file = None
        self.offline_file = None
        self.unreachable_file = None

    def load_content(self) -> Optional[str]:
        """Load M3U content from file, URL, or database."""
        content = ""

        try:
            if self.args.file:
                if urlparse(self.args.file).scheme in ("http", "https"):
                    # Check if it's an XTREAM API URL
                    if is_xtream_api_url(self.args.file):
                        console.print(
                            f"[cyan]Loading XTREAM API playlist: {self.args.file}[/cyan]"
                        )
                    else:
                        console.print(f"[cyan]Downloading: {self.args.file}[/cyan]")

                    r = requests.get(
                        self.args.file, headers={"User-Agent": USER_AGENT}, timeout=20
                    )
                    r.raise_for_status()
                    content = r.content.decode("utf-8", errors="ignore")
                else:
                    operation = "Re-checking" if self.args.recheck else "Reading"
                    console.print(f"[cyan]{operation} local file: {self.args.file}[/cyan]")
                    with open(self.args.file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

            elif self.args.database:
                console.print("[cyan]Loading playlists from database...[/cyan]")
                links = self.links_db_manager.load().get("defaultlinks", {})
                if not links:
                    console.print("[red]No links found in database.[/red]")
                    return None

                for name, url in links.items():
                    try:
                        console.print(f"  → Downloading '{name}'...")
                        r = requests.get(
                            url, headers={"User-Agent": USER_AGENT}, timeout=20
                        )
                        r.raise_for_status()
                        content += r.content.decode("utf-8", errors="ignore") + "\n"
                    except Exception as e:
                        console.print(f"  [red]Failed to download '{name}': {e}[/red]")

        except Exception as e:
            console.print(f"[red]Error loading content: {e}[/red]")
            logging.error(f"Error loading content: {e}", exc_info=True)
            return None

        return content

    def get_known_good_urls(self, output_path: str) -> Set[str]:
        """Get set of URLs already in output file for skipping."""
        if not os.path.exists(output_path):
            return set()

        try:
            with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            streams = parse_m3u(content)
            return {s["url"] for s in streams}
        except Exception as e:
            logging.warning(f"Could not read output file for skipping: {e}")
            return set()

    def is_uncheckable(self, url: str) -> bool:
        """Check if URL is likely uncheckable (tokens, auth, etc.)."""
        return len(url) > UNCHECKABLE_URL_LENGTH_THRESHOLD or any(
            kw in url.lower() for kw in UNCHECKABLE_KEYWORDS
        )

    def check_stream(
        self, stream: Dict, config: Dict
    ) -> Tuple[Dict, bool, str]:
        """Check a single stream and return result."""
        is_online, status = verify_stream(stream, config)
        return stream, is_online, status

    def run(self) -> None:
        """Main execution method."""
        console.print(
            Panel(
                f"[bold cyan]tv-term v{VERSION}[/bold cyan]\n"
                "Terminal-based IPTV/M3U Stream Validator\n"
                "Author: kidpoleon",
                box=box.DOUBLE,
            )
        )

        # Load content
        content = self.load_content()
        if not content:
            console.print("[red]No content to process.[/red]")
            return

        # Parse M3U
        streams = parse_m3u(content)
        if not streams:
            console.print("[yellow]No streams found in M3U content.[/yellow]")
            return

        console.print(f"[green]Found {len(streams)} streams in playlist.[/green]")

        # Determine output path
        is_recheck = bool(self.args.recheck)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.args.recheck if is_recheck else self.args.output

        # Skip known good URLs
        known_good_urls = set()
        if not is_recheck and not self.args.no_skip:
            known_good_urls = self.get_known_good_urls(output_path)
            if known_good_urls:
                console.print(
                    f"[cyan]Found {len(known_good_urls)} known good URLs to skip.[/cyan]"
                )

        streams_to_check = [s for s in streams if s["url"] not in known_good_urls]

        if known_good_urls:
            skipped = len(streams) - len(streams_to_check)
            console.print(f"[green]Skipping {skipped} already-verified streams.[/green]")

        if not streams_to_check:
            console.print("[yellow]No new streams to check.[/yellow]")
            return

        self.total_streams = len(streams_to_check)
        console.print(f"[cyan]Checking {self.total_streams} new streams...[/cyan]")

        # Setup output files in output directory
        online_path = OUTPUT_DIR / "online" / f"online_{timestamp}.m3u"
        offline_path = OUTPUT_DIR / "offline" / f"offline_{timestamp}.m3u"
        unreachable_path = OUTPUT_DIR / "unreachable" / f"unreachable_{timestamp}.m3u"

        try:
            self.online_file = open(online_path, "w", encoding="utf-8-sig")
            self.offline_file = open(offline_path, "w", encoding="utf-8-sig")
            self.unreachable_file = open(unreachable_path, "w", encoding="utf-8-sig")
            write_m3u_header(self.online_file)
            write_m3u_header(self.offline_file)
            write_m3u_header(self.unreachable_file)
        except Exception as e:
            console.print(f"[red]Error creating output files: {e}[/red]")
            return

        # Configuration for workers
        config = {
            "stream_patterns": self.stream_patterns,
            "timeout": self.args.timeout,
        }

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                "[cyan]Checking streams...", total=self.total_streams
            )

            # Use ThreadPoolExecutor for parallel checking
            with ThreadPoolExecutor(max_workers=self.args.workers) as executor:
                # Submit all tasks
                future_to_stream = {
                    executor.submit(self.check_stream, stream, config): stream
                    for stream in streams_to_check
                }

                # Process results as they complete
                for future in as_completed(future_to_stream):
                    stream, is_online, status = future.result()

                    with self.lock:
                        self.processed_count += 1

                        if is_online:
                            self.online_count += 1
                            if (
                                config["stream_patterns"].get(".mp3") in stream["url"]
                                or config["stream_patterns"].get(".aac") in stream["url"]
                            ):
                                stream["group"] = "Radios"
                            write_m3u_entry(self.online_file, stream)
                        else:
                            self.offline_count += 1
                            if self.is_uncheckable(stream["url"]):
                                write_m3u_entry(self.unreachable_file, stream)
                                self.unreachable_count += 1
                            else:
                                write_m3u_entry(self.offline_file, stream)

                        progress.update(
                            task,
                            advance=1,
                            description=f"[cyan]Checking... {self.online_count} online, {self.offline_count} offline",
                        )

        # Close files
        if self.online_file:
            self.online_file.close()
        if self.offline_file:
            self.offline_file.close()
        if self.unreachable_file:
            self.unreachable_file.close()

        # Display summary
        self.display_summary(online_path, offline_path, unreachable_path)

    def display_summary(
        self, online_path: Path, offline_path: Path, unreachable_path: Path
    ) -> None:
        """Display final summary table."""
        table = Table(title="Check Summary", box=box.DOUBLE)
        table.add_column("Metric", style="cyan", justify="right")
        table.add_column("Value", style="green", justify="left")

        table.add_row("Total Streams", str(self.total_streams))
        table.add_row("Online", str(self.online_count))
        table.add_row("Offline", str(self.offline_count))
        table.add_row("Unreachable", str(self.unreachable_count))
        table.add_row(
            "Success Rate",
            f"{(self.online_count / self.total_streams * 100):.1f}%",
        )

        console.print(table)

        console.print("\n[bold]Output Files:[/bold]")
        console.print(f"  [green]Online:[/green] {online_path}")
        console.print(f"  [red]Offline:[/red] {offline_path}")
        if self.unreachable_count > 0:
            console.print(f"  [yellow]Unreachable:[/yellow] {unreachable_path}")


# Database Management
def manage_database() -> None:
    """Simple TUI for managing the links database."""
    db_manager = IniManager(LINKS_DB_PATH)
    links = db_manager.load({"DefaultLinks": {}}).get("defaultlinks", {})

    console.print(
        Panel("[bold cyan]Links Database Manager[/bold cyan]", box=box.DOUBLE)
    )

    while True:
        console.print("\n[bold]Options:[/bold]")
        console.print("  1. List all links")
        console.print("  2. Add a link")
        console.print("  3. Remove a link")
        console.print("  4. Exit")

        choice = console.input("\n[cyan]Choose option (1-4): [/cyan]").strip()

        if choice == "1":
            if not links:
                console.print("[yellow]No links in database.[/yellow]")
            else:
                table = Table(title="Stored Links", box=box.SIMPLE)
                table.add_column("Name", style="cyan")
                table.add_column("URL", style="green")
                for name, url in sorted(links.items()):
                    table.add_row(
                        name,
                        url[:60] + "..." if len(url) > 60 else url,
                    )
                console.print(table)

        elif choice == "2":
            url = console.input("[cyan]Enter M3U URL: [/cyan]").strip()
            if url:
                name = console.input("[cyan]Enter name (optional): [/cyan]").strip()
                if not name:
                    try:
                        name = (
                            Path(urlparse(url).path)
                            .stem.replace("-", " ")
                            .title()
                        )
                    except Exception:
                        name = f"link_{int(time.time())}"
                key = name.lower().replace(" ", "_")
                links[key] = url
                db_manager.save(configparser.ConfigParser({"DefaultLinks": links}))
                console.print(f"[green]Added '{name}' to database.[/green]")

        elif choice == "3":
            if not links:
                console.print("[yellow]No links to remove.[/yellow]")
            else:
                table = Table(title="Select link to remove", box=box.SIMPLE)
                table.add_column("#", style="cyan")
                table.add_column("Name", style="cyan")
                table.add_column("URL", style="green")
                for i, (name, url) in enumerate(sorted(links.items()), 1):
                    table.add_row(
                        str(i),
                        name,
                        url[:50] + "..." if len(url) > 50 else url,
                    )
                console.print(table)

                idx = console.input("[cyan]Enter # to remove: [/cyan]").strip()
                try:
                    idx = int(idx)
                    if 1 <= idx <= len(links):
                        key_to_remove = sorted(links.keys())[idx - 1]
                        del links[key_to_remove]
                        db_manager.save(
                            configparser.ConfigParser({"DefaultLinks": links})
                        )
                        console.print(f"[green]Removed link.[/green]")
                except ValueError:
                    console.print("[red]Invalid input.[/red]")

        elif choice == "4":
            break

        else:
            console.print("[red]Invalid option.[/red]")


# Interactive Mode
def interactive_mode() -> argparse.Namespace:
    """Run tv-term in interactive mode with user prompts."""
    console.print(
        Panel(
            "[bold cyan]Interactive Mode[/bold cyan]\n"
            "Follow the prompts to configure your stream check.",
            box=box.DOUBLE,
        )
    )

    # Input source
    console.print("\n[bold]Select input source:[/bold]")
    console.print("  1. Local M3U/M3U8 file")
    console.print("  2. Remote URL")
    console.print("  3. XTREAM API endpoint")
    console.print("  4. Links database")
    console.print("  5. Re-check existing file")

    choice = console.input("\n[cyan]Choose option (1-5): [/cyan]").strip()

    file_path = None
    use_database = False
    recheck_file = None

    if choice == "1":
        file_path = console.input("[cyan]Enter file path: [/cyan]").strip()
        if not os.path.exists(file_path):
            console.print("[red]File not found.[/red]")
            sys.exit(1)
    elif choice == "2":
        file_path = console.input("[cyan]Enter URL: [/cyan]").strip()
        if not file_path.startswith(("http://", "https://")):
            console.print("[red]Invalid URL.[/red]")
            sys.exit(1)
    elif choice == "3":
        host = console.input("[cyan]Enter server host (e.g., your-server.com): [/cyan]").strip()
        username = console.input("[cyan]Enter username: [/cyan]").strip()
        password = console.input("[cyan]Enter password: [/cyan]").strip()
        file_path = f"http://{host}/get.php?username={username}&password={password}&type=m3u_plus"
    elif choice == "4":
        use_database = True
    elif choice == "5":
        recheck_file = console.input("[cyan]Enter file path to re-check: [/cyan]").strip()
        if not os.path.exists(recheck_file):
            console.print("[red]File not found.[/red]")
            sys.exit(1)
    else:
        console.print("[red]Invalid option.[/red]")
        sys.exit(1)

    # Workers
    workers = console.input(
        "[cyan]Number of parallel workers (1-20, default: 10): [/cyan]"
    ).strip()
    try:
        workers = int(workers) if workers else 10
        if workers < 1 or workers > 20:
            console.print("[red]Workers must be between 1 and 20.[/red]")
            sys.exit(1)
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        sys.exit(1)

    # Timeout
    timeout = console.input(
        "[cyan]Timeout per stream in seconds (default: 5): [/cyan]"
    ).strip()
    try:
        timeout = int(timeout) if timeout else 5
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        sys.exit(1)

    # Skip known good URLs
    skip = console.input("[cyan]Skip known good URLs? (Y/n, default: Y): [/cyan]").strip()
    no_skip = skip.lower() == "n"

    # Output file
    if not recheck_file:
        output = console.input(
            "[cyan]Output file name (default: updated.m3u): [/cyan]"
        ).strip()
        output = output if output else "updated.m3u"

    # Create args namespace
    args = argparse.Namespace(
        file=file_path,
        database=use_database,
        recheck=recheck_file,
        output=output if not recheck_file else recheck_file,
        workers=workers,
        timeout=timeout,
        no_skip=no_skip,
        manage_db=False,
    )

    return args


# Main Entry Point
def main() -> None:
    """Main entry point for tv-term."""
    # Check Python version
    if sys.version_info < (3, 7):
        console.print(
            "[red]ERROR: Python 3.7 or higher is required.[/red]"
        )
        console.print(f"[yellow]Current version: {sys.version}[/yellow]")
        sys.exit(1)

    setup_logging()
    cleanup_stale_temp_files()
    ensure_output_dirs()

    missing_deps = check_dependencies()
    if missing_deps:
        console.print(
            f"[red]FATAL ERROR: Missing required dependencies: "
            f'{", ".join(missing_deps)}[/red]'
        )
        console.print("[yellow]Please install: ffmpeg, ffprobe, yt-dlp[/yellow]")
        console.print("[yellow]On Ubuntu/Debian:[/yellow]")
        console.print("  sudo apt install ffmpeg ffprobe yt-dlp")
        console.print("[yellow]On macOS (Homebrew):[/yellow]")
        console.print("  brew install ffmpeg yt-dlp")
        console.print("[yellow]On Windows (Chocolatey):[/yellow]")
        console.print("  choco install ffmpeg yt-dlp")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=f"tv-term v{VERSION} - Terminal-based IPTV/M3U Stream Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tv_term.py -f playlist.m3u
  python tv_term.py -f http://example.com/playlist.m3u -o checked.m3u
  python tv_term.py -f http://your-server.com/get.php?username=USER&password=PASS&type=m3u_plus
  python tv_term.py -d -o all_checked.m3u
  python tv_term.py -r updated.m3u
  python tv_term.py --manage-db
  python tv_term.py --version
  
Interactive Mode:
  python tv_term.py
        """,
    )

    parser.add_argument("-f", "--file", help="Path or URL to M3U/M3U8 playlist file")
    parser.add_argument(
        "-d", "--database", action="store_true", help="Use links database as input"
    )
    parser.add_argument("-r", "--recheck", help="Re-check existing output file")
    parser.add_argument(
        "-o",
        "--output",
        default="updated.m3u",
        help="Output file (default: updated.m3u)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=10,
        help="Parallel workers (1-20, default: 10)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=5,
        help="Timeout per stream in seconds (default: 5)",
    )
    parser.add_argument(
        "--no-skip", action="store_true", help="Disable skipping known good URLs"
    )
    parser.add_argument(
        "--manage-db", action="store_true", help="Manage links database"
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    args = parser.parse_args()

    # Show version
    if args.version:
        console.print(f"[bold cyan]tv-term v{VERSION}[/bold cyan]")
        console.print(f"[dim]Author: kidpoleon[/dim]")
        console.print(f"[dim]Python: {sys.version}[/dim]")
        sys.exit(0)

    # Manage database
    if args.manage_db:
        manage_database()
        return

    # Interactive mode or no arguments
    if args.interactive or not any([args.file, args.database, args.recheck]):
        args = interactive_mode()

    # Validate workers
    if args.workers < 1 or args.workers > 20:
        console.print("[red]Workers must be between 1 and 20.[/red]")
        sys.exit(1)

    # Validate timeout
    if args.timeout < 1 or args.timeout > 60:
        console.print("[red]Timeout must be between 1 and 60 seconds.[/red]")
        sys.exit(1)

    # Run checker
    checker = TVTermChecker(args)

    # Signal handling
    def signal_handler(sig, frame):
        console.print("\n[yellow]Interrupted. Cleaning up...[/yellow]")
        if checker.online_file:
            try:
                checker.online_file.close()
            except Exception:
                pass
        if checker.offline_file:
            try:
                checker.offline_file.close()
            except Exception:
                pass
        if checker.unreachable_file:
            try:
                checker.unreachable_file.close()
            except Exception:
                pass
        console.print("[green]Cleanup complete.[/green]")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        checker.run()
    except KeyboardInterrupt:
        signal_handler(None, None)
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e}[/red]")
        logging.error(f"File not found: {e}", exc_info=True)
        sys.exit(1)
    except PermissionError as e:
        console.print(f"[red]Permission denied: {e}[/red]")
        logging.error(f"Permission denied: {e}", exc_info=True)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Network error: {e}[/red]")
        logging.error(f"Network error: {e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logging.error(f"Unexpected error: {e}", exc_info=True)
        console.print("[yellow]Check debug.log for details.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
