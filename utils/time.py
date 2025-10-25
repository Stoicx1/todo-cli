"""
Time utilities for humanizing durations and parsing age expressions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def humanize_age(iso_timestamp: str) -> str:
    """Return compact age like '5m', '3h', '2d', '1y' from an ISO timestamp.

    Returns '-' if input is falsy or invalid.
    """
    try:
        if not iso_timestamp:
            return "-"
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(dt.tzinfo) if getattr(dt, "tzinfo", None) else datetime.now()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60:
            return f"{s}s"
        m = s // 60
        if m < 60:
            return f"{m}m"
        h = m // 60
        if h < 24:
            return f"{h}h"
        d = h // 24
        if d < 365:
            return f"{d}d"
        y = d // 365
        return f"{y}y"
    except Exception:
        return "-"


def parse_duration(value: str) -> Optional[int]:
    """Parse duration strings like '30m', '2h', '3d', '1y' into seconds.

    Returns None if invalid.
    """
    if not value:
        return None
    v = value.strip().lower()
    try:
        if v.endswith("s"):
            return int(v[:-1])
        if v.endswith("m"):
            return int(v[:-1]) * 60
        if v.endswith("h"):
            return int(v[:-1]) * 3600
        if v.endswith("d"):
            return int(v[:-1]) * 86400
        if v.endswith("y"):
            return int(v[:-1]) * 31536000
        # Default: treat as seconds if pure int
        return int(v)
    except Exception:
        return None


def age_seconds(iso_timestamp: str) -> Optional[int]:
    """Return age in seconds given an ISO timestamp, or None if invalid."""
    try:
        if not iso_timestamp:
            return None
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(dt.tzinfo) if getattr(dt, "tzinfo", None) else datetime.now()
        return int((now - dt).total_seconds())
    except Exception:
        return None

