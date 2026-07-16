from datetime import datetime, timezone

def format_iso8601(dt: datetime) -> str:
    """
    Format a datetime object to an ISO 8601 string with a trailing 'Z' (Zulu time).
    Example: 2026-07-11T11:20:44Z
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

import re

def slugify(text: str) -> str:
    """Converts a string to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text

