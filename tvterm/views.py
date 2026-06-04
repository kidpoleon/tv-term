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


console = Console()


def display_header(version: str, author: str) -> None:
    """Display application header."""
    console.print(
        Panel(
            f"[bold cyan]tv-term v{version}[/bold cyan]\n"
            "Terminal-based IPTV/M3U Stream Validator\n"
            f"Author: {author}",
            box=box.DOUBLE,
        )
    )


def display_interactive_mode() -> None:
    """Display interactive mode header."""
    console.print(
        Panel(
            "[bold cyan]Interactive Mode[/bold cyan]\n"
            "Follow the prompts to configure your stream check.",
            box=box.DOUBLE,
        )
    )


def display_input_options() -> None:
    """Display input source options."""
    console.print("\n[bold]Select input source:[/bold]")
    console.print("  1. Local M3U/M3U8 file")
    console.print("  2. Remote URL")
    console.print("  3. XTREAM API endpoint")
    console.print("  4. Links database")
    console.print("  5. Re-check existing file")


def display_database_manager() -> None:
    """Display database manager header."""
    console.print(
        Panel("[bold cyan]Links Database Manager[/bold cyan]", box=box.DOUBLE)
    )


def display_database_options() -> None:
    """Display database manager options."""
    console.print("\n[bold]Options:[/bold]")
    console.print("  1. List all links")
    console.print("  2. Add a link")
    console.print("  3. Remove a link")
    console.print("  4. Exit")


def display_links_table(links: dict) -> None:
    """Display stored links in a table."""
    if not links:
        console.print("[yellow]No links in database.[/yellow]")
        return

    table = Table(title="Stored Links", box=box.SIMPLE)
    table.add_column("Name", style="cyan")
    table.add_column("URL", style="green")
    for name, url in sorted(links.items()):
        table.add_row(name, url[:60] + "..." if len(url) > 60 else url)
    console.print(table)


def display_remove_links_table(links: dict) -> None:
    """Display links for removal."""
    if not links:
        console.print("[yellow]No links to remove.[/yellow]")
        return

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


def display_summary(stats: CheckStats, output_files: dict) -> None:
    """Display final summary table."""
    table = Table(title="Check Summary", box=box.DOUBLE)
    table.add_column("Metric", style="cyan", justify="right")
    table.add_column("Value", style="green", justify="left")

    table.add_row("Total Streams", str(stats.total))
    table.add_row("Online", str(stats.online))
    table.add_row("Offline", str(stats.offline))
    table.add_row("Unreachable", str(stats.unreachable))
    table.add_row(
        "Success Rate",
        f"{stats.success_rate:.1f}%",
    )

    console.print(table)

    console.print("\n[bold]Output Files:[/bold]")
    console.print(f"  [green]Online:[/green] {output_files.get('online', 'N/A')}")
    console.print(f"  [red]Offline:[/red] {output_files.get('offline', 'N/A')}")
    if stats.unreachable > 0:
        console.print(
            f"  [yellow]Unreachable:[/yellow] {output_files.get('unreachable', 'N/A')}"
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
    console.print(f"[red]{message}[/red]")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[cyan]{message}[/cyan]")


def input_prompt(prompt: str) -> str:
    """Get user input with styled prompt."""
    return console.input(f"[cyan]{prompt}[/cyan]").strip()
