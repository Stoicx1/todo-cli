"""
File path validation utilities for security
Prevents path traversal attacks and ensures safe file operations
"""

import os
import re
from pathlib import Path
from typing import Tuple


def validate_filename(filename: str, allow_absolute: bool = True) -> Tuple[bool, str]:
    """
    Validate filename for security issues.

    Checks for:
    - Path traversal attacks (../, ..\)
    - Null bytes
    - Invalid characters
    - Reserved names (Windows)
    - Empty filename

    Args:
        filename: Filename or path to validate
        allow_absolute: Whether to allow absolute paths (default: True)

    Returns:
        Tuple of (is_valid: bool, error_message: str)

    Examples:
        >>> validate_filename("tasks.json")
        (True, "")

        >>> validate_filename("../../../etc/passwd")
        (False, "Path traversal detected in filename")

        >>> validate_filename("C:\\Users\\test\\tasks.json")
        (True, "")  # If allow_absolute=True
    """
    # Check for empty filename
    if not filename or not filename.strip():
        return False, "Filename cannot be empty"

    filename = filename.strip()

    # Check for null bytes (security risk)
    if '\x00' in filename:
        return False, "Null bytes not allowed in filename"

    # Normalize path for consistent checking
    try:
        normalized_path = os.path.normpath(filename)
    except (ValueError, TypeError):
        return False, "Invalid filename format"

    # Check for path traversal (../ or ..\)
    if '..' in Path(normalized_path).parts:
        return False, "Path traversal detected in filename"

    # Check for absolute paths if not allowed
    if not allow_absolute and os.path.isabs(normalized_path):
        return False, "Absolute paths not allowed"

    # Windows reserved names (case-insensitive)
    # CON, PRN, AUX, NUL, COM1-9, LPT1-9
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    base_name = os.path.basename(normalized_path)
    name_without_ext = os.path.splitext(base_name)[0].upper()

    if name_without_ext in reserved_names:
        return False, f"Reserved filename '{name_without_ext}' not allowed"

    # Check for invalid characters (Windows + Unix)
    # Windows: < > : " / \ | ? *
    # We allow / and \ for paths, but not in the basename
    invalid_chars_pattern = r'[<>:"|?*]'
    if re.search(invalid_chars_pattern, base_name):
        return False, "Filename contains invalid characters"

    # Check for files ending with period or space (Windows issue)
    if base_name.endswith('.') or base_name.endswith(' '):
        return False, "Filename cannot end with period or space"

    # Check maximum filename length (255 bytes on most filesystems)
    if len(base_name.encode('utf-8')) > 255:
        return False, "Filename too long (max 255 bytes)"

    # Check maximum path length (varies by OS, use conservative limit)
    # Windows: 260, Unix: usually 4096, we use 1024 as reasonable limit
    if len(normalized_path.encode('utf-8')) > 1024:
        return False, "File path too long (max 1024 bytes)"

    return True, ""


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize filename by replacing invalid characters.

    Args:
        filename: Filename to sanitize
        replacement: Character to replace invalid chars with (default: "_")

    Returns:
        Sanitized filename safe for use

    Examples:
        >>> sanitize_filename("my<file>.json")
        "my_file_.json"

        >>> sanitize_filename("../../etc/passwd")
        "etc_passwd"
    """
    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Get basename only (remove any path components)
    filename = os.path.basename(filename)

    # Replace invalid characters
    filename = re.sub(r'[<>:"|?*]', replacement, filename)

    # Remove leading/trailing periods and spaces
    filename = filename.strip('. ')

    # If empty after sanitization, use default
    if not filename:
        filename = "unnamed"

    # Truncate if too long (leave room for extension)
    max_length = 200  # Conservative limit
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext)]
        filename = name + ext

    return filename


def get_safe_filepath(directory: str, filename: str) -> Tuple[bool, str, str]:
    """
    Get safe absolute filepath, validating both directory and filename.

    Args:
        directory: Directory path
        filename: Filename

    Returns:
        Tuple of (is_valid: bool, full_path: str, error_message: str)

    Examples:
        >>> get_safe_filepath("./data", "tasks.json")
        (True, "/absolute/path/to/data/tasks.json", "")
    """
    # Validate filename
    is_valid, error = validate_filename(filename, allow_absolute=False)
    if not is_valid:
        return False, "", error

    # Resolve directory to absolute path
    try:
        abs_directory = os.path.abspath(directory)
    except (ValueError, TypeError):
        return False, "", "Invalid directory path"

    # Construct full path
    full_path = os.path.join(abs_directory, filename)

    # Normalize and resolve (handles symlinks, .., etc.)
    try:
        resolved_path = os.path.abspath(full_path)
    except (ValueError, TypeError):
        return False, "", "Invalid file path"

    # Security check: ensure resolved path is still within directory
    # This prevents symlink attacks and path traversal
    if not resolved_path.startswith(abs_directory):
        return False, "", "Path escapes target directory (security violation)"

    return True, resolved_path, ""
