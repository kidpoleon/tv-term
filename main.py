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
import argparse
import configparser
import signal
import time
from pathlib import Path
from urllib.parse import urlparse

from tvterm import __version__, __author__
from tvterm.models import Config, CheckStats
from tvterm.utils import (
    get_config_path,
    get_links_db_path,
    get_debug_log_path,
    setup_logging,
    check_dependencies,
    is_xtream_api_url,
    validate_output_dir,
)
from tvterm.views import (
    console,
    display_header,
    display_interactive_mode,
    display_input_options,
    display_database_manager,
    display_database_options,
    display_links_table,
    display_remove_links_table,
    display_summary,
    print_error,
    print_success,
    print_warning,
    print_info,
    input_prompt,
)
from tvterm.controllers import (
    CheckerController,
    IniManager,
    ContentLoader,
)


def interactive_mode() -> argparse.Namespace:
    """Run tv-term in interactive mode with user prompts."""
    display_interactive_mode()

    # Input source
    display_input_options()
    choice = input_prompt("\nChoose option (1-5): ")

    file_path = None
    use_database = False
    recheck_file = None

    if choice == "1":
        file_path = input_prompt("Enter file path: ")
        if not os.path.exists(file_path):
            print_error("File not found.")
            sys.exit(1)
    elif choice == "2":
        file_path = input_prompt("Enter URL: ")
        if not file_path.startswith(("http://", "https://")):
            print_error("Invalid URL.")
            sys.exit(1)
    elif choice == "3":
        host = input_prompt("Enter server host (e.g., your-server.com): ")
        username = input_prompt("Enter username: ")
        password = input_prompt("Enter password: ")
        file_path = f"http://{host}/get.php?username={username}&password={password}&type=m3u_plus"
    elif choice == "4":
        use_database = True
    elif choice == "5":
        recheck_file = input_prompt("Enter file path to re-check: ")
        if not os.path.exists(recheck_file):
            print_error("File not found.")
            sys.exit(1)
    else:
        print_error("Invalid option.")
        sys.exit(1)

    # Output directory
    output_dir = input_prompt(
        "Output directory (default: current directory): "
    )
    output_dir = output_dir if output_dir else "."

    # Workers
    workers = input_prompt("Number of parallel workers (1-20, default: 10): ")
    try:
        workers = int(workers) if workers else 10
        if workers < 1 or workers > 20:
            print_error("Workers must be between 1 and 20.")
            sys.exit(1)
    except ValueError:
        print_error("Invalid number.")
        sys.exit(1)

    # Timeout
    timeout = input_prompt("Timeout per stream in seconds (default: 5): ")
    try:
        timeout = int(timeout) if timeout else 5
    except ValueError:
        print_error("Invalid number.")
        sys.exit(1)

    # Skip known good URLs
    skip = input_prompt("Skip known good URLs? (Y/n, default: Y): ")
    no_skip = skip.lower() == "n"

    # Output file prefix
    if not recheck_file:
        output_prefix = input_prompt(
            "Output file prefix (default: tv-term): "
        )
        output_prefix = output_prefix if output_prefix else "tv-term"
    else:
        output_prefix = "tv-term"

    # Create args namespace
    args = argparse.Namespace(
        file=file_path,
        database=use_database,
        recheck=recheck_file,
        output_prefix=output_prefix,
        output_dir=output_dir,
        workers=workers,
        timeout=timeout,
        no_skip=no_skip,
        manage_db=False,
    )

    return args


def manage_database() -> None:
    """Simple TUI for managing the links database."""
    db_manager = IniManager(get_links_db_path())
    links = db_manager.load({"DefaultLinks": {}}).get("defaultlinks", {})

    display_database_manager()

    while True:
        display_database_options()
        choice = input_prompt("\nChoose option (1-4): ")

        if choice == "1":
            display_links_table(links)

        elif choice == "2":
            url = input_prompt("Enter M3U URL: ")
            if url:
                name = input_prompt("Enter name (optional): ")
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
                db_manager.save(
                    configparser.ConfigParser({"DefaultLinks": links})
                )
                print_success(f"Added '{name}' to database.")

        elif choice == "3":
            if not links:
                print_warning("No links to remove.")
            else:
                display_remove_links_table(links)
                idx = input_prompt("Enter # to remove: ")
                try:
                    idx = int(idx)
                    if 1 <= idx <= len(links):
                        key_to_remove = sorted(links.keys())[idx - 1]
                        del links[key_to_remove]
                        db_manager.save(
                            configparser.ConfigParser({"DefaultLinks": links})
                        )
                        print_success("Removed link.")
                except ValueError:
                    print_error("Invalid input.")

        elif choice == "4":
            break

        else:
            print_error("Invalid option.")


def main() -> None:
    """Main entry point for tv-term."""
    # Check Python version
    if sys.version_info < (3, 7):
        print_error("ERROR: Python 3.7 or higher is required.")
        print_warning(f"Current version: {sys.version}")
        sys.exit(1)

    # Setup logging
    setup_logging(get_debug_log_path())

    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print_error(
            f"FATAL ERROR: Missing required dependencies: "
            f'{", ".join(missing_deps)}'
        )
        print_warning("Please install: ffmpeg, ffprobe, yt-dlp")
        print_warning("On Ubuntu/Debian:")
        print_warning("  sudo apt install ffmpeg ffprobe yt-dlp")
        print_warning("On macOS (Homebrew):")
        print_warning("  brew install ffmpeg yt-dlp")
        print_warning("On Windows (Chocolatey):")
        print_warning("  choco install ffmpeg yt-dlp")
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description=f"tv-term v{__version__} - Terminal-based IPTV/M3U Stream Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -f playlist.m3u
  python main.py -f http://example.com/playlist.m3u -o checked.m3u
  python main.py -f http://your-server.com/get.php?username=USER&password=PASS&type=m3u_plus
  python main.py -d -o all_checked.m3u
  python main.py -r updated.m3u
  python main.py --manage-db
  python main.py --version

Interactive Mode:
  python main.py
        """,
    )

    parser.add_argument("-f", "--file", help="Path or URL to M3U/M3U8 playlist file")
    parser.add_argument(
        "-d", "--database", action="store_true", help="Use links database as input"
    )
    parser.add_argument("-r", "--recheck", help="Re-check existing output file")
    parser.add_argument(
        "-o",
        "--output-prefix",
        default="tv-term",
        help="Output file prefix (default: tv-term)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory (default: current directory)",
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
        console.print(f"[bold cyan]tv-term v{__version__}[/bold cyan]")
        console.print(f"[dim]Author: {__author__}[/dim]")
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
        print_error("Workers must be between 1 and 20.")
        sys.exit(1)

    # Validate timeout
    if args.timeout < 1 or args.timeout > 60:
        print_error("Timeout must be between 1 and 60 seconds.")
        sys.exit(1)

    # Validate output directory
    output_dir = validate_output_dir(args.output_dir)
    args.output_dir = str(output_dir)

    # Load configuration
    config_manager = IniManager(get_config_path())
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
    all_configs = config_manager.load(defaults)
    stream_patterns = all_configs.get("streampatterns", {})

    # Create config
    config = Config(
        stream_patterns=stream_patterns,
        timeout=args.timeout,
        workers=args.workers,
        output_dir=args.output_dir,
        skip_known=not args.no_skip,
    )

    # Create controller
    controller = CheckerController(config)
    loader = ContentLoader(config)

    # Display header
    display_header(__version__, __author__)

    # Load content
    content = ""
    try:
        if args.file:
            if urlparse(args.file).scheme in ("http", "https"):
                # Check if it's an XTREAM API URL
                if is_xtream_api_url(args.file):
                    print_info(f"Loading XTREAM API playlist: {args.file}")
                else:
                    print_info(f"Downloading: {args.file}")

                content = loader.load_from_url(args.file)
            else:
                operation = "Re-checking" if args.recheck else "Reading"
                print_info(f"{operation} local file: {args.file}")
                content = loader.load_from_file(args.file)

        elif args.database:
            print_info("Loading playlists from database...")
            content = loader.load_from_database(get_links_db_path())
            if not content:
                print_error("No links found in database.")
                sys.exit(1)

    except Exception as e:
        print_error(f"Error loading content: {e}")
        sys.exit(1)

    if not content:
        print_error("No content to process.")
        sys.exit(1)

    # Signal handling
    def signal_handler(sig, frame):
        print_warning("\nInterrupted. Cleaning up...")
        controller.shutdown_event.set()
        controller.cleanup()
        print_success("Cleanup complete.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Run check
        is_recheck = bool(args.recheck)
        input_source = args.file if args.file else "database"
        output_files = controller.run_check(
            content,
            input_source=input_source,
            output_prefix=args.output_prefix,
            is_recheck=is_recheck,
            recheck_file=args.recheck,
        )

        if output_files:
            # Display summary
            display_summary(controller.stats, output_files)
        else:
            print_warning("No streams to check.")

    except KeyboardInterrupt:
        signal_handler(None, None)
    except FileNotFoundError as e:
        print_error(f"File not found: {e}")
        sys.exit(1)
    except PermissionError as e:
        print_error(f"Permission denied: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
