#!/usr/bin/env python3
"""
Theme configuration for tv-term TUI.

Centralized styling for consistent and maintainable terminal UI.
"""

from rich.box import DOUBLE, ROUNDED, SQUARE


class Theme:
    """Centralized theme configuration for tv-term UI."""

    # ==================== COLORS ====================
    class Colors:
        PRIMARY = "cyan"
        SECONDARY = "blue"
        SUCCESS = "bold green"
        WARNING = "bold yellow"
        ERROR = "bold red"
        INFO = "bold blue"
        TEXT_MUTED = "dim white"
        TEXT_NORMAL = "white"
        BORDER_DEFAULT = "cyan"
        BORDER_SUCCESS = "green"
        BORDER_WARNING = "yellow"
        BORDER_ERROR = "red"

    # ==================== ICONS ====================
    class Icons:
        CHECK = "✓"
        CROSS = "✗"
        ARROW_RIGHT = "→"
        ARROW_LEFT = "←"
        INFO = "ℹ"
        WARNING = "⚠"
        ERROR = "✖"
        SUCCESS = "✓"
        LOADING = "⠋"
        FILE = "📄"
        LINK = "🔗"
        PLAY = "▶"
        STOP = "⏹"

    # ==================== LAYOUT ====================
    class Layout:
        PANEL_PADDING = (1, 2)
        PANEL_BOX_STYLE = DOUBLE
        TABLE_BOX_STYLE = ROUNDED
        TABLE_PADDING = (0, 1)
        PROGRESS_BAR_WIDTH = 40

    # ==================== TEXT STYLES ====================
    class TextStyles:
        TITLE = "bold cyan"
        HEADER = "bold white"
        SUBHEADER = "bold blue"
        INSTRUCTION = "dim"
        PROMPT = "bold white"
        SUCCESS = "bold green"
        WARNING = "bold yellow"
        ERROR = "bold red"
        INFO = "bold blue"
        MUTED = "dim"
        HIGHLIGHT = "bold cyan"

    # ==================== STYLES ====================
    @staticmethod
    def get_panel_style(style_type: str = "default") -> str:
        """Get panel border style based on type."""
        styles = {
            "default": Theme.Colors.BORDER_DEFAULT,
            "success": Theme.Colors.BORDER_SUCCESS,
            "warning": Theme.Colors.BORDER_WARNING,
            "error": Theme.Colors.BORDER_ERROR,
        }
        return styles.get(style_type, Theme.Colors.BORDER_DEFAULT)

    @staticmethod
    def get_text_style(style_type: str = "normal") -> str:
        """Get text style based on type."""
        styles = {
            "default": Theme.TextStyles.TEXT_NORMAL,
            "title": Theme.TextStyles.TITLE,
            "header": Theme.TextStyles.HEADER,
            "subheader": Theme.TextStyles.SUBHEADER,
            "instruction": Theme.TextStyles.INSTRUCTION,
            "success": Theme.TextStyles.SUCCESS,
            "warning": Theme.TextStyles.WARNING,
            "error": Theme.TextStyles.ERROR,
            "info": Theme.TextStyles.INFO,
            "muted": Theme.TextStyles.MUTED,
            "highlight": Theme.TextStyles.HIGHLIGHT,
        }
        return styles.get(style_type, Theme.TextStyles.TEXT_NORMAL)
