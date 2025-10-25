"""
Input Validation Utilities
Validate and sanitize user input to prevent errors and security issues
"""

from typing import Optional, Tuple
from config import validation


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


def validate_task_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate task name.

    Args:
        name: Task name to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_task_name("Valid Task")
        (True, None)

        >>> validate_task_name("")
        (False, "Task name cannot be empty")

        >>> validate_task_name("x" * 300)
        (False, "Task name too long (max 200 characters)")
    """
    name = name.strip()

    if not name:
        return False, "Task name cannot be empty"

    if len(name) < validation.MIN_TASK_NAME_LENGTH:
        return False, f"Task name must be at least {validation.MIN_TASK_NAME_LENGTH} character(s)"

    if len(name) > validation.MAX_TASK_NAME_LENGTH:
        return False, f"Task name too long (max {validation.MAX_TASK_NAME_LENGTH} characters)"

    return True, None


def validate_priority(priority: any) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate and normalize priority.

    Args:
        priority: Priority value (int or str)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)

    Example:
        >>> validate_priority("2")
        (True, None, 2)

        >>> validate_priority(1)
        (True, None, 1)

        >>> validate_priority(999)
        (False, "Priority must be between 1 and 3", None)

        >>> validate_priority("invalid")
        (False, "Priority must be a number", None)
    """
    # Try to convert to int
    try:
        p = int(priority)
    except (ValueError, TypeError):
        return False, "Priority must be a number", None

    # Validate range
    if p < validation.MIN_PRIORITY or p > validation.MAX_PRIORITY:
        return False, f"Priority must be between {validation.MIN_PRIORITY} and {validation.MAX_PRIORITY}", None

    return True, None, p


def validate_task_id(task_id: any) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate task ID.

    Args:
        task_id: Task ID value (int or str)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)

    Example:
        >>> validate_task_id("5")
        (True, None, 5)

        >>> validate_task_id(-1)
        (False, "Task ID must be positive", None)

        >>> validate_task_id("abc")
        (False, "Task ID must be a number", None)
    """
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return False, "Task ID must be a number", None

    if tid < 1:
        return False, "Task ID must be positive", None

    if tid > validation.MAX_TASK_ID:
        return False, f"Task ID too large (max {validation.MAX_TASK_ID})", None

    return True, None, tid


def sanitize_text(text: str, max_length: int, allow_empty: bool = True) -> str:
    """
    Sanitize text input: strip whitespace, enforce length limit.

    Args:
        text: Text to sanitize
        max_length: Maximum length to allow
        allow_empty: Whether empty string is allowed

    Returns:
        Sanitized text (truncated if too long)

    Raises:
        ValidationError: If text is empty and allow_empty is False

    Example:
        >>> sanitize_text("  hello  ", 100)
        'hello'

        >>> sanitize_text("x" * 150, 100)
        'xxx...xxx'  # Truncated to 100 chars
    """
    text = text.strip()

    if not allow_empty and not text:
        raise ValidationError("Text cannot be empty")

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]

    return text


def sanitize_comment(comment: str) -> str:
    """
    Sanitize comment field.

    Args:
        comment: Comment text

    Returns:
        Sanitized comment

    Example:
        >>> sanitize_comment("  This is a comment  ")
        'This is a comment'
    """
    return sanitize_text(comment, validation.MAX_COMMENT_LENGTH, allow_empty=True)


def sanitize_description(description: str) -> str:
    """
    Sanitize description field.

    Args:
        description: Description text

    Returns:
        Sanitized description

    Example:
        >>> sanitize_description("  Detailed description  ")
        'Detailed description'
    """
    return sanitize_text(description, validation.MAX_DESCRIPTION_LENGTH, allow_empty=True)


def clamp_priority(priority: int) -> int:
    """
    Clamp priority to valid range [1, 3].
    Use this when you want to auto-correct instead of error.

    Args:
        priority: Priority value (may be out of range)

    Returns:
        Clamped priority within valid range

    Example:
        >>> clamp_priority(999)
        3
        >>> clamp_priority(-5)
        1
        >>> clamp_priority(2)
        2
    """
    return max(validation.MIN_PRIORITY, min(validation.MAX_PRIORITY, priority))
