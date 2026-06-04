#!/usr/bin/env python3
"""
Data models for tv-term.

This module contains data structures and configuration classes.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from datetime import datetime


@dataclass
class Stream:
    """Represents a single IPTV stream."""

    title: str
    url: str
    group: str = "General"
    logo: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Convert stream to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "group": self.group,
            "logo": self.logo,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Stream":
        """Create stream from dictionary."""
        return cls(
            title=data.get("title", "Unknown"),
            url=data.get("url", ""),
            group=data.get("group", "General"),
            logo=data.get("logo", ""),
        )


@dataclass
class CheckResult:
    """Represents the result of checking a stream."""

    stream: Stream
    is_online: bool
    status: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Config:
    """Application configuration."""

    stream_patterns: Dict[str, str] = field(default_factory=dict)
    timeout: int = 5
    workers: int = 10
    output_dir: str = "."
    skip_known: bool = True

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "stream_patterns": self.stream_patterns,
            "timeout": self.timeout,
            "workers": self.workers,
            "output_dir": self.output_dir,
            "skip_known": self.skip_known,
        }


@dataclass
class CheckStats:
    """Statistics for stream checking."""

    total: int = 0
    online: int = 0
    offline: int = 0
    unreachable: int = 0
    processed: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.online / self.total) * 100
