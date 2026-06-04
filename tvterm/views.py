#!/usr/bin/env python3
"""
View layer for tv-term.

This module handles all TUI display logic using the rich library.
"""

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
from rich import box

from tvterm.models import CheckStats
from tvterm.theme import Theme


console = Console()
theme = Theme()


def display_header(version: str, author: str) -> None:
    """Display application header."""
    console.print(
        Panel(
            f"[{theme.TextStyles.TITLE}]tv-term v{version}[/{theme.TextStyles.TITLE}]\n"
            "Terminal-based IPTV/M3U Stream Validator\n"
            f"Author: {author}",
            box=theme.Layout.PANEL_BOX_STYLE,
            border_style=theme.Colors.BORDER_DEFAULT,
            padding=theme.Layout.PANEL_PADDING,
        )
    )


def display_interactive_mode() -> None:
    """Display interactive mode header."""
    console.print(
        Panel(
            f"[{theme.TextStyles.TITLE}]Interactive Mode[/{theme.TextStyles.TITLE}]\n"
            f"[{theme.TextStyles.INSTRUCTION}]Follow the prompts to configure your stream check.[/{theme.TextStyles.INSTRUCTION}]",
            box=theme.Layout.PANEL_BOX_STYLE,
            border_style=theme.Colors.BORDER_DEFAULT,
            padding=theme.Layout.PANEL_PADDING,
        )
    )


def display_input_options() -> None:
    """Display input source options."""
    console.print(f"\n[{theme.TextStyles.HEADER}]Select input source:[/{theme.TextStyles.HEADER}]")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Local M3U/M3U8 file")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Remote URL")
    console.print(f"  {theme.Icons.ARROW_RIGHT} XTREAM API endpoint")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Links database")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Re-check existing file")


def display_database_manager() -> None:
    """Display database manager header."""
    console.print(
        Panel(
            f"[{theme.TextStyles.TITLE}]Links Database Manager[/{theme.TextStyles.TITLE}]",
            box=theme.Layout.PANEL_BOX_STYLE,
            border_style=theme.Colors.BORDER_DEFAULT,
            padding=theme.Layout.PANEL_PADDING,
        )
    )


def display_database_options() -> None:
    """Display database manager options."""
    console.print(f"\n[{theme.TextStyles.HEADER}]Options:[/{theme.TextStyles.HEADER}]")
    console.print(f"  {theme.Icons.ARROW_RIGHT} List all links")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Add a link")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Remove a link")
    console.print(f"  {theme.Icons.ARROW_RIGHT} Exit")


def display_links_table(links: dict) -> None:
    """Display stored links in a table."""
    if not links:
        console.print(f"[{theme.TextStyles.WARNING}]No links in database.[/{theme.TextStyles.WARNING}]")
        return

    table = Table(title="Stored Links", box=theme.Layout.TABLE_BOX_STYLE)
    table.add_column("Name", style=theme.Colors.PRIMARY)
    table.add_column("URL", style=theme.Colors.SUCCESS)
    for name, url in sorted(links.items()):
        table.add_row(name, url[:60] + "..." if len(url) > 60 else url)
    console.print(table)


def display_remove_links_table(links: dict) -> None:
    """Display links for removal."""
    if not links:
        console.print(f"[{theme.TextStyles.WARNING}]No links to remove.[/{theme.TextStyles.WARNING}]")
        return

    table = Table(title="Select link to remove", box=theme.Layout.TABLE_BOX_STYLE)
    table.add_column("#", style=theme.Colors.PRIMARY)
    table.add_column("Name", style=theme.Colors.PRIMARY)
    table.add_column("URL", style=theme.Colors.SUCCESS)
    for i, (name, url) in enumerate(sorted(links.items()), 1):
        table.add_row(
            str(i),
            name,
            url[:50] + "..." if len(url) > 50 else url,
        )
    console.print(table)


def display_summary(stats: CheckStats, output_files: dict) -> None:
    """Display final summary table."""
    table = Table(title="Check Summary", box=theme.Layout.PANEL_BOX_STYLE)
    table.add_column("Metric", style=theme.Colors.PRIMARY, justify="right")
    table.add_column("Value", style=theme.Colors.SUCCESS, justify="left")

    table.add_row("Total Streams", str(stats.total))
    table.add_row("Online", str(stats.online))
    table.add_row("Offline", str(stats.offline))
    table.add_row("Unreachable", str(stats.unreachable))
    table.add_row(
        "Success Rate",
        f"{stats.success_rate:.1f}%",
    )

    console.print(table)

    console.print(f"\n[{theme.TextStyles.HEADER}]Output Files:[/{theme.TextStyles.HEADER}]")
    console.print(f"  {theme.Icons.SUCCESS} [{theme.Colors.SUCCESS}]Online:[/{theme.Colors.SUCCESS}] {output_files.get('online', 'N/A')}")
    console.print(f"  {theme.Icons.CROSS} [{theme.Colors.ERROR}]Offline:[/{theme.Colors.ERROR}] {output_files.get('offline', 'N/A')}")
    if stats.unreachable > 0:
        console.print(
            f"  {theme.Icons.WARNING} [{theme.Colors.WARNING}]Unreachable:[/{theme.Colors.WARNING}] {output_files.get('unreachable', 'N/A')}"
        )


def create_progress_bar(total: int) -> Progress:
    """Create a progress bar for stream checking."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"{theme.Icons.ERROR} [{theme.TextStyles.ERROR}]{message}[/{theme.TextStyles.ERROR}]")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"{theme.Icons.SUCCESS} [{theme.TextStyles.SUCCESS}]{message}[/{theme.TextStyles.SUCCESS}]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"{theme.Icons.WARNING} [{theme.TextStyles.WARNING}]{message}[/{theme.TextStyles.WARNING}]")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"{theme.Icons.INFO} [{theme.TextStyles.INFO}]{message}[/{theme.TextStyles.INFO}]")


def input_prompt(prompt: str) -> str:
    """Get user input with styled prompt."""
    return console.input(f"[{theme.TextStyles.PROMPT}]{prompt}[/{theme.TextStyles.PROMPT}]").strip()
