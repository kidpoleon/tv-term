#!/usr/bin/env python3
"""
Theme configuration for tv-term TUI.

Centralized styling for consistent and beautiful terminal UI.
"""

from rich.box import Box, DOUBLE, SIMPLE, ROUNDED


class Theme:
    """Centralized theme configuration for tv-term UI."""

    # ==================== COLORS ====================
    class Colors:
        PRIMARY = "cyan"
        SUCCESS = "green"
        WARNING = "yellow"
        ERROR = "red"
        INFO = "blue"
        TEXT_MUTED = "dim white"
        TEXT_BOLD = "bold white"
        BORDER_DEFAULT = "cyan"
        BORDER_SUCCESS = "green"
        BORDER_WARNING = "yellow"
        BORDER_ERROR = "red"

    # ==================== ICONS ====================
    class Icons:
        SUCCESS = "✓"
        ERROR = "✗"
        WARNING = "⚠"
        INFO = "ℹ"
        FILE = "📄"
        DATABASE = "🗄️"
        NETWORK = "🌐"
        CHECK = "✓"
        CROSS = "✗"
        ARROW_RIGHT = "→"
        ARROW_LEFT = "←"

    # ==================== LAYOUT ====================
    class Layout:
        PANEL_PADDING = (1, 2)
        PANEL_BOX_STYLE = DOUBLE
        TABLE_BOX_STYLE = DOUBLE
        SIMPLE_TABLE_BOX_STYLE = SIMPLE
        ROUNDED_BOX_STYLE = ROUNDED

    # ==================== TEXT STYLES ====================
    class TextStyles:
        TITLE = "bold cyan"
        HEADER = "bold white"
        INSTRUCTION = "dim"
        PROMPT = "cyan"
        SUCCESS = "bold green"
        WARNING = "bold yellow"
        ERROR = "bold red"
        INFO = "bold blue"
        MUTED = "dim white"
        BOLD = "bold"

    # ==================== TABLE STYLES ====================
    class TableStyles:
        HEADER = "cyan"
        COLUMN = "cyan"
        VALUE = "green"
        HIGHLIGHT = "yellow"
