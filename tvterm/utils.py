#!/usr/bin/env python3
"""
Utility functions for tv-term.

This module contains helper functions for file operations, URL handling,
and other common tasks.
"""

import os
import re
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse


# Constants
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)
AUDIO_USER_AGENT = "iTunes/9.1.1"
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


def get_app_dir() -> Path:
    """Get the application directory."""
    return Path(__file__).resolve().parent.parent


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_app_dir() / "tv_term_config.ini"


def get_links_db_path() -> Path:
    """Get the links database file path."""
    return get_app_dir() / "tv_term_links.ini"


def get_debug_log_path() -> Path:
    """Get the debug log file path."""
    return get_app_dir() / "debug.log"


def setup_logging(log_path: Path) -> None:
    """Configure debug logging to file."""
    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def check_dependencies() -> List[str]:
    """Check for required external dependencies."""
    essential_deps = {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "yt-dlp": shutil.which("yt-dlp"),
    }
    missing_essential = [name for name, path in essential_deps.items() if not path]
    return missing_essential


def is_xtream_api_url(url: str) -> bool:
    """Check if URL is an XTREAM API endpoint."""
    parsed = urlparse(url)
    return (
        "get.php" in parsed.path
        and "username" in parsed.query
        and "password" in parsed.query
    )


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


def get_stream_type(url: str) -> str:
    """
    Detect stream type (video/audio) using ffprobe.
    Returns 'video', 'audio', or 'unknown'.
    """
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        return "unknown"

    try:
        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-user_agent",
            AUDIO_USER_AGENT,
            "-i",
            url,
        ]
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


def resolve_youtube_url(url: str) -> Optional[str]:
    """Resolve YouTube URL to direct stream URL using yt-dlp."""
    yt_dlp_path = shutil.which("yt-dlp")
    if not yt_dlp_path:
        return None

    try:
        cmd = [yt_dlp_path, "--get-url", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            direct_url = result.stdout.strip().splitlines()[0]
            logging.debug(f"yt-dlp resolved: {url} -> {direct_url}")
            return direct_url
    except Exception as e:
        logging.error(f"yt-dlp failed for {url}: {e}")
    return None


def is_uncheckable(url: str) -> bool:
    """Check if URL is likely uncheckable (tokens, auth, etc.)."""
    return len(url) > UNCHECKABLE_URL_LENGTH_THRESHOLD or any(
        kw in url.lower() for kw in UNCHECKABLE_KEYWORDS
    )


def get_iso8601_timestamp() -> str:
    """Get current timestamp in ISO-8601 format."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def validate_output_dir(output_dir: str) -> Path:
    """Validate and create output directory if needed."""
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    except Exception as e:
        logging.error(f"Failed to create output directory: {e}")
        # Fallback to current directory
        return Path.cwd()


def extract_domain_name(input_source: str) -> str:
    """
    Extract domain name from input source (URL or file path).
    Returns a sanitized domain name for use in output filenames.
    """
    try:
        if input_source.startswith(("http://", "https://")):
            # Extract domain from URL
            parsed = urlparse(input_source)
            domain = parsed.netloc.replace("www.", "")
            # Remove port if present
            domain = domain.split(":")[0]
        else:
            # Extract filename from local file path
            path = Path(input_source)
            domain = path.stem
            # Remove common extensions if present
            domain = domain.replace("_", "-").replace(".", "-")
        
        # Sanitize domain name
        domain = re.sub(r"[^a-zA-Z0-9-]", "-", domain)
        domain = domain.strip("-")
        
        # Fallback if domain is empty
        if not domain:
            domain = "unknown"
        
        return domain
    except Exception as e:
        logging.warning(f"Could not extract domain name: {e}")
        return "unknown"
