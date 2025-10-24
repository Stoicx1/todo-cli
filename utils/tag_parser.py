"""
Tag Parsing Utilities
Centralized tag parsing, validation, and normalization
"""

import re
from typing import List, Optional, Callable
from config import validation


def validate_tag_format(tag: str) -> bool:
    """
    Validate tag format.
    Tags must be alphanumeric with hyphens/underscores only.

    Args:
        tag: Tag string to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_tag_format("backend")
        True
        >>> validate_tag_format("api-v2")
        True
        >>> validate_tag_format("tag with spaces")
        False
    """
    if not tag:
        return False

    if len(tag) < validation.MIN_TAG_LENGTH or len(tag) > validation.MAX_TAG_LENGTH:
        return False

    # Only allow: letters, numbers, hyphens, underscores
    return bool(re.match(r'^[a-z0-9_-]+$', tag))


def normalize_tag(tag: str) -> str:
    """
    Normalize tag: lowercase, strip whitespace.

    Args:
        tag: Tag string to normalize

    Returns:
        Normalized tag string

    Example:
        >>> normalize_tag("  Backend  ")
        'backend'
    """
    return tag.strip().lower()


def parse_tags(
    tag_str: str,
    max_tags: int = None,
    warn_callback: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    Parse comma-separated tags and normalize them.

    Args:
        tag_str: Comma-separated tag string (e.g., "tag1, tag2, tag3")
        max_tags: Maximum number of tags to return (default: from config)
        warn_callback: Optional callback for warnings (receives message string)

    Returns:
        List of unique, normalized, validated tags

    Example:
        >>> parse_tags("Backend, API, Urgent")
        ['backend', 'api', 'urgent']

        >>> parse_tags("tag1, tag1, tag2, tag3, tag4", max_tags=3)
        ['tag1', 'tag2', 'tag3']

        >>> def warn(msg): print(msg)
        >>> parse_tags("invalid@tag, valid-tag", warn_callback=warn)
        [yellow]⚠ Invalid tag 'invalid@tag' skipped...[/yellow]
        ['valid-tag']
    """
    if max_tags is None:
        max_tags = validation.MAX_TAGS_PER_TASK

    if not tag_str:
        return []

    # Split by comma if present
    if ',' in tag_str:
        raw_tags = tag_str.split(',')
    else:
        # Single tag
        raw_tags = [tag_str]

    # Normalize and validate
    normalized = []
    seen = set()

    for idx, tag in enumerate(raw_tags):
        tag = normalize_tag(tag)

        if not tag:
            continue

        # Skip duplicates
        if tag in seen:
            if warn_callback:
                warn_callback(f"[yellow]⚠ Duplicate tag '{tag}' skipped[/yellow]")
            continue

        # Validate format
        if not validate_tag_format(tag):
            if warn_callback:
                warn_callback(
                    f"[yellow]⚠ Invalid tag '{tag}' skipped "
                    f"(use alphanumeric, hyphens, underscores only)[/yellow]"
                )
            continue

        # Add to result
        seen.add(tag)
        normalized.append(tag)

        # Respect max limit
        if len(normalized) >= max_tags:
            # Warn about dropped tags
            remaining = len([t for t in raw_tags[idx+1:] if normalize_tag(t)])
            if remaining > 0 and warn_callback:
                warn_callback(
                    f"[yellow]⚠ Tag limit reached ({max_tags} max), "
                    f"{remaining} tag(s) dropped[/yellow]"
                )
            break

    return normalized


def tags_to_string(tags: List[str]) -> str:
    """
    Convert tag list to comma-separated string.

    Args:
        tags: List of tag strings

    Returns:
        Comma-separated string

    Example:
        >>> tags_to_string(['backend', 'api', 'urgent'])
        'backend, api, urgent'
        >>> tags_to_string([])
        ''
    """
    return ', '.join(tags) if tags else ''


def merge_tags(existing: List[str], new: List[str], max_tags: int = None) -> List[str]:
    """
    Merge two tag lists, removing duplicates and respecting max limit.

    Args:
        existing: Current tags
        new: Tags to add
        max_tags: Maximum total tags (default: from config)

    Returns:
        Merged list of unique tags

    Example:
        >>> merge_tags(['tag1', 'tag2'], ['tag3'], max_tags=3)
        ['tag1', 'tag2', 'tag3']
        >>> merge_tags(['tag1'], ['tag1', 'tag2'])
        ['tag1', 'tag2']
    """
    if max_tags is None:
        max_tags = validation.MAX_TAGS_PER_TASK

    # Use dict to preserve order while removing duplicates
    merged = {}
    for tag in existing + new:
        if tag not in merged and len(merged) < max_tags:
            merged[tag] = True

    return list(merged.keys())
