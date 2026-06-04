#!/usr/bin/env python3
"""
Controller layer for tv-term.

This module handles business logic for M3U parsing, stream checking,
and file operations.
"""

import re
import subprocess
import configparser
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests

from tvterm.models import Stream, CheckResult, Config, CheckStats
from tvterm.utils import (
    USER_AGENT,
    AUDIO_USER_AGENT,
    sanitize_url,
    get_stream_type,
    resolve_youtube_url,
    is_uncheckable,
    get_iso8601_timestamp,
    extract_domain_name,
    get_source_type,
)


# M3U Parser
class M3UParser:
    """Parser for M3U/M3U8 playlist files."""

    @staticmethod
    def parse(content: str) -> List[Stream]:
        """
        Parse M3U content into Stream objects.
        Handles standard M3U, extended M3U, M3U8, and XTREAM API formats.
        """
        streams = []

        # Pattern 1: Extended M3U with group-title attribute
        pattern1 = re.compile(
            r'#EXTINF:-1\s*group-title="([^"]*)"[^,]*,([^\n]+)\n'
            r'(?:#EXT[^\n]*\n)*'
            r'(https?://[^\s]+)',
            re.IGNORECASE,
        )

        # Pattern 2: Extended M3U with tvg-name
        pattern2 = re.compile(
            r'#EXTINF:-1\s*tvg-name="([^"]*)"[^,]*,([^\n]+)\n'
            r'(?:#EXT[^\n]*\n)*'
            r'(https?://[^\s]+)',
            re.IGNORECASE,
        )

        # Pattern 3: Extended M3U with tvg-logo
        pattern3 = re.compile(
            r'#EXTINF:-1\s*tvg-logo="([^"]*)"[^,]*,([^\n]+)\n'
            r'(?:#EXT[^\n]*\n)*'
            r'(https?://[^\s]+)',
            re.IGNORECASE,
        )

        # Pattern 4: Extended M3U without attributes
        pattern4 = re.compile(
            r'#EXTINF:-1\s*(?:[^,]*,)?\s*([^\n]+)\n'
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

        # Try pattern 1 first (most complete)
        matches = pattern1.findall(content)
        if matches:
            for group, title, url in matches:
                streams.append(
                    Stream(
                        title=title.strip(),
                        url=url.strip(),
                        group=group.strip() or "General",
                    )
                )
            return streams

        # Try pattern 2 (tvg-name)
        matches = pattern2.findall(content)
        if matches:
            for tvg_name, title, url in matches:
                streams.append(
                    Stream(
                        title=title.strip(),
                        url=url.strip(),
                        group=tvg_name.strip() or "General",
                    )
                )
            return streams

        # Try pattern 3 (tvg-logo)
        matches = pattern3.findall(content)
        if matches:
            for logo, title, url in matches:
                streams.append(
                    Stream(
                        title=title.strip(),
                        url=url.strip(),
                        group="General",
                        logo=logo.strip(),
                    )
                )
            return streams

        # Try pattern 4 (extended without group)
        matches = pattern4.findall(content)
        if matches:
            for title, url in matches:
                streams.append(
                    Stream(
                        title=title.strip(),
                        url=url.strip(),
                        group="General",
                    )
                )
            return streams

        # Try pattern 5 (simple)
        matches = pattern5.findall(content)
        if matches:
            for title, url in matches:
                streams.append(
                    Stream(
                        title=title.strip(),
                        url=url.strip(),
                        group="General",
                    )
                )
            return streams

        # Fallback to URL-only
        matches = pattern6.findall(content)
        if matches:
            for i, url in enumerate(matches):
                streams.append(
                    Stream(
                        title=f"Stream_{i + 1}",
                        url=url.strip(),
                        group="General",
                    )
                )

        return streams


# M3U Writer
class M3UWriter:
    """Writer for M3U playlist files."""

    @staticmethod
    def write_header(file_handle) -> None:
        """Write M3U header to file."""
        if file_handle:
            file_handle.write("#EXTM3U\n\n")
            file_handle.flush()

    @staticmethod
    def write_entry(file_handle, stream: Stream) -> None:
        """Write M3U entry to file."""
        if file_handle:
            if stream.logo:
                file_handle.write(
                    f'#EXTINF:-1 tvg-logo="{stream.logo}" '
                    f'group-title="{stream.group}",{stream.title}\n'
                    f"{stream.url}\n\n"
                )
            else:
                file_handle.write(
                    f'#EXTINF:-1 group-title="{stream.group}",{stream.title}\n'
                    f"{stream.url}\n\n"
                )
            file_handle.flush()


# Stream Checker
class StreamChecker:
    """Checker for IPTV streams."""

    def __init__(self, config: Config):
        self.config = config
        self.ffprobe_path = None
        self._check_ffprobe()

    def _check_ffprobe(self) -> None:
        """Check if ffprobe is available."""
        import shutil
        self.ffprobe_path = shutil.which("ffprobe")

    def verify_stream(self, stream: Stream) -> Tuple[bool, str]:
        """
        Verify if a stream is online using ffprobe.
        Returns (is_online, status_message).
        """
        url = sanitize_url(stream.url)

        # Resolve YouTube URLs
        if "youtube.com/" in url or "youtu.be/" in url:
            resolved = resolve_youtube_url(url)
            if resolved:
                url = resolved
            else:
                return False, "YouTube Error"

        # Determine stream type
        check_type = None
        for pattern, type_ in self.config.stream_patterns.items():
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
            timeout_us = str(self.config.timeout * 1000000)

            cmd = [
                self.ffprobe_path,
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
                timeout=25,
            )

            if result.returncode == 0:
                return True, "ON"
            else:
                return False, "OFF"

        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            import logging
            logging.error(f"Error verifying {url}: {e}")
            return False, "Error"


# Content Loader
class ContentLoader:
    """Loader for M3U content from various sources."""

    def __init__(self, config: Config):
        self.config = config

    def load_from_file(self, file_path: str) -> Optional[str]:
        """Load content from local file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            import logging
            logging.error(f"Error loading file: {e}")
            return None

    def load_from_url(self, url: str) -> Optional[str]:
        """Load content from URL with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=20,
                    allow_redirects=True,
                )
                r.raise_for_status()
                content = r.content.decode("utf-8", errors="ignore")
                if not content or content.strip() == "":
                    logging.warning(f"Empty content from URL (attempt {attempt + 1}/{max_retries}): {url}")
                    if attempt == max_retries - 1:
                        return None
                    continue
                return content
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout loading URL (attempt {attempt + 1}/{max_retries}): {url}")
                if attempt == max_retries - 1:
                    return None
            except requests.exceptions.RequestException as e:
                logging.error(f"Error loading URL: {e}")
                return None
        return None

    def load_from_database(self, db_path: Path) -> Optional[str]:
        """Load content from links database with retry logic."""
        try:
            db_manager = IniManager(db_path)
            links = db_manager.load().get("defaultlinks", {})
            if not links:
                logging.warning("No links found in database")
                return None

            content = ""
            for name, url in links.items():
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        r = requests.get(
                            url,
                            headers={"User-Agent": USER_AGENT},
                            timeout=20,
                            allow_redirects=True,
                        )
                        r.raise_for_status()
                        url_content = r.content.decode("utf-8", errors="ignore")
                        if not url_content or url_content.strip() == "":
                            logging.warning(f"Empty content from database link: {name}")
                            continue
                        content += url_content + "\n"
                        break
                    except requests.exceptions.Timeout:
                        import logging
                        logging.warning(
                            f"Timeout loading '{name}' (attempt {attempt + 1}/{max_retries})"
                        )
                        if attempt == max_retries - 1:
                            logging.error(f"Failed to download '{name}' after retries")
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to download '{name}': {e}")
                        break

            return content if content else None
        except Exception as e:
            import logging
            logging.error(f"Error loading database: {e}")
            return None


# Configuration Manager
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
                import logging
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
            import logging
            from tvterm.views import print_error
            logging.error(
                f"Failed to save INI file at {self.path}: {e}", exc_info=True
            )
            print_error(
                f"Could not save settings to {self.path}. "
                "Please check permissions."
            )


# Main Checker Controller
class CheckerController:
    """Main controller for stream checking."""

    def __init__(self, config: Config):
        self.config = config
        self.parser = M3UParser()
        self.writer = M3UWriter()
        self.checker = StreamChecker(config)
        self.loader = ContentLoader(config)

        self.stats = CheckStats()
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()

        # Output files
        self.online_file = None
        self.offline_file = None
        self.unreachable_file = None

    def get_known_good_urls(self, output_path: str) -> Set[str]:
        """Get set of URLs already in output file for skipping."""
        if not Path(output_path).exists():
            return set()

        try:
            with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            streams = self.parser.parse(content)
            return {s.url for s in streams}
        except Exception as e:
            import logging
            logging.warning(f"Could not read output file for skipping: {e}")
            return set()

    def check_stream(self, stream: Stream) -> Tuple[Stream, bool, str]:
        """Check a single stream and return result."""
        if self.shutdown_event.is_set():
            return stream, False, "Cancelled"
        is_online, status = self.checker.verify_stream(stream)
        return stream, is_online, status

    def run_check(
        self,
        content: str,
        input_source: str = "unknown",
        output_prefix: str = "tv-term",
        is_recheck: bool = False,
        recheck_file: Optional[str] = None,
    ) -> Dict[str, str]:
        """Run stream checking on content."""
        # Parse M3U
        streams = self.parser.parse(content)
        if not streams:
            return {}

        self.stats.total = len(streams)

        # Determine output paths with new naming convention: TYPE_DOMAIN-NAME_STATUS_ISO-8601.EXT
        timestamp = get_iso8601_timestamp()
        output_dir = Path(self.config.output_dir)
        domain_name = extract_domain_name(input_source)
        source_type = get_source_type(input_source)

        # Use custom prefix only if specified by user, otherwise use source type
        if output_prefix == "tv-term":
            prefix = source_type
        else:
            prefix = output_prefix

        online_path = output_dir / f"{prefix}_{domain_name}_online_{timestamp}.m3u"
        offline_path = output_dir / f"{prefix}_{domain_name}_offline_{timestamp}.m3u"
        unreachable_path = output_dir / f"{prefix}_{domain_name}_unreachable_{timestamp}.m3u"

        # Skip known good URLs
        known_good_urls = set()
        if not is_recheck and self.config.skip_known:
            output_file = recheck_file if recheck_file else str(online_path)
            known_good_urls = self.get_known_good_urls(output_file)

        streams_to_check = [s for s in streams if s.url not in known_good_urls]

        if known_good_urls:
            skipped = len(streams) - len(streams_to_check)
            from tvterm.views import print_info
            print_info(f"Skipping {skipped} already-verified streams.")

        if not streams_to_check:
            return {}

        self.stats.total = len(streams_to_check)
        from tvterm.views import print_info
        print_info(f"Checking {self.stats.total} new streams...")

        # Setup output files
        try:
            self.online_file = open(online_path, "w", encoding="utf-8-sig")
            self.offline_file = open(offline_path, "w", encoding="utf-8-sig")
            self.unreachable_file = open(unreachable_path, "w", encoding="utf-8-sig")
            self.writer.write_header(self.online_file)
            self.writer.write_header(self.offline_file)
            self.writer.write_header(self.unreachable_file)
        except Exception as e:
            from tvterm.views import print_error
            print_error(f"Error creating output files: {e}")
            return {}

        # Progress tracking
        from tvterm.views import create_progress_bar
        with create_progress_bar(self.stats.total) as progress:
            task = progress.add_task(
                "[cyan]Checking streams...", total=self.stats.total
            )

            # Use ThreadPoolExecutor for parallel checking
            with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                future_to_stream = {
                    executor.submit(self.check_stream, stream): stream
                    for stream in streams_to_check
                }

                # Process results as they complete
                for future in as_completed(future_to_stream):
                    # Check if shutdown was requested
                    if self.shutdown_event.is_set():
                        break

                    stream, is_online, status = future.result()

                    with self.lock:
                        # Skip if stream's group is in skipped groups
                        if stream.group in self.stats.skipped_groups:
                            continue

                        self.stats.processed += 1

                        # Track group statistics
                        group = stream.group or "General"
                        if group not in self.stats.group_stats:
                            self.stats.group_stats[group] = {"checked": 0, "online": 0, "offline": 0, "consecutive_failures": 0}
                        self.stats.group_stats[group]["checked"] += 1

                        if is_online:
                            self.stats.online += 1
                            self.stats.group_stats[group]["online"] += 1
                            self.stats.group_stats[group]["consecutive_failures"] = 0
                            if (
                                ".mp3" in stream.url
                                or ".aac" in stream.url
                            ):
                                stream.group = "Radios"
                            self.writer.write_entry(self.online_file, stream)
                        else:
                            self.stats.offline += 1
                            self.stats.group_stats[group]["offline"] += 1
                            self.stats.group_stats[group]["consecutive_failures"] += 1

                            # Check if group should be skipped (4-6 consecutive failures)
                            if self.stats.group_stats[group]["consecutive_failures"] >= 4:
                                self.stats.skipped_groups.add(group)
                                from tvterm.views import print_warning
                                print_warning(f"Skipping group '{group}' due to consecutive failures (will retry later)")

                            if is_uncheckable(stream.url):
                                self.writer.write_entry(
                                    self.unreachable_file, stream
                                )
                                self.stats.unreachable += 1
                            else:
                                self.writer.write_entry(self.offline_file, stream)

                        progress.update(
                            task,
                            advance=1,
                            description=f"[cyan]Checking... {self.stats.online} online, {self.stats.offline} offline",
                        )

        # Close files
        if self.online_file:
            self.online_file.close()
        if self.offline_file:
            self.offline_file.close()
        if self.unreachable_file:
            self.unreachable_file.close()

        # Retry skipped groups if any
        if self.stats.skipped_groups:
            from tvterm.views import print_info
            print_info(f"Retrying {len(self.stats.skipped_groups)} skipped groups...")

            # Collect streams from skipped groups
            skipped_streams = [s for s in streams if s.group in self.stats.skipped_groups and s.url not in known_good_urls]

            if skipped_streams:
                # Reset skipped groups for retry
                self.stats.skipped_groups.clear()

                # Reopen output files
                with (
                    open(online_path, "a", encoding="utf-8-sig") as self.online_file,
                    open(offline_path, "a", encoding="utf-8-sig") as self.offline_file,
                    open(unreachable_path, "a", encoding="utf-8-sig") as self.unreachable_file,
                ):
                    # Retry skipped streams
                    with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                        future_to_stream = {
                            executor.submit(self.check_stream, stream): stream
                            for stream in skipped_streams
                        }

                        for future in as_completed(future_to_stream):
                            if self.shutdown_event.is_set():
                                break

                            stream, is_online, status = future.result()

                            with self.lock:
                                if is_online:
                                    self.stats.online += 1
                                    self.writer.write_entry(self.online_file, stream)
                                else:
                                    self.stats.offline += 1
                                    if is_uncheckable(stream.url):
                                        self.writer.write_entry(self.unreachable_file, stream)
                                        self.stats.unreachable += 1
                                    else:
                                        self.writer.write_entry(self.offline_file, stream)

        return {
            "online": str(online_path),
            "offline": str(offline_path),
            "unreachable": str(unreachable_path),
        }

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.online_file:
            try:
                self.online_file.close()
            except Exception:
                pass
        if self.offline_file:
            try:
                self.offline_file.close()
            except Exception:
                pass
        if self.unreachable_file:
            try:
                self.unreachable_file.close()
            except Exception:
                pass
