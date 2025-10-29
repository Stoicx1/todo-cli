"""
Theme configuration management.

Simple, config-file based approach for theme selection.
No runtime switching - users edit config and restart app.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Valid theme names
ThemeName = Literal["dark", "light"]
VALID_THEMES: list[ThemeName] = ["dark", "light"]
DEFAULT_THEME: ThemeName = "dark"


@dataclass
class ThemeConfig:
    """Theme configuration."""
    name: ThemeName


def get_theme_config_path() -> Path:
    """Get path to theme configuration file."""
    return Path.home() / ".todo_cli_theme.json"


def migrate_legacy_theme() -> ThemeName | None:
    """
    Migrate theme from old settings file to new theme config.

    Checks ~/.todo_cli_settings.json for legacy "theme" key.
    If found and valid, returns the theme name (does NOT create config file).

    Returns:
        Theme name if found and valid, None otherwise
    """
    try:
        from pathlib import Path
        old_settings = Path.home() / ".todo_cli_settings.json"

        if not old_settings.exists():
            return None

        data = json.loads(old_settings.read_text(encoding='utf-8'))
        legacy_theme = data.get("theme")

        if legacy_theme and legacy_theme in VALID_THEMES:
            return legacy_theme

        return None

    except Exception:
        return None


def get_theme_config() -> ThemeName:
    """
    Load theme configuration from file.

    Returns:
        Theme name ("dark" or "light"). Defaults to "dark" if config missing/invalid.

    Notes:
        - Reads from ~/.todo_cli_theme.json
        - Returns DEFAULT_THEME on any error (missing file, parse error, invalid value)
        - Creates default config file if missing (silent, no error)
        - Migrates from old settings file if new config doesn't exist
    """
    config_path = get_theme_config_path()

    # If config missing, check for legacy theme and migrate
    if not config_path.exists():
        legacy_theme = migrate_legacy_theme()
        if legacy_theme:
            # Create config with migrated theme
            create_theme_config_with_value(legacy_theme)
            return legacy_theme
        else:
            # No legacy theme, create default
            create_default_theme_config()
            return DEFAULT_THEME

    # Read and parse config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        theme_name = data.get("theme", DEFAULT_THEME)

        # Validate theme name
        if theme_name not in VALID_THEMES:
            return DEFAULT_THEME

        return theme_name

    except (json.JSONDecodeError, OSError, KeyError):
        # Any error: fall back to default theme
        return DEFAULT_THEME


def create_default_theme_config() -> None:
    """
    Create default theme configuration file.

    Creates ~/.todo_cli_theme.json with dark theme as default.
    Uses atomic write pattern for safety.
    """
    config_path = get_theme_config_path()

    config_data = {
        "theme": DEFAULT_THEME,
        "_comment": "Valid values: 'dark' or 'light'. Restart app to apply changes."
    }

    try:
        # Atomic write: temp file + replace
        import tempfile
        import os

        # Write to temp file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=config_path.parent,
            prefix=".todo_cli_theme_",
            suffix=".json.tmp"
        )

        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                f.write('\n')  # Trailing newline

            # Atomic replace
            os.replace(temp_path, config_path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    except Exception:
        # Silent failure - app will use default theme
        pass


def create_theme_config_with_value(theme: ThemeName) -> None:
    """
    Create theme configuration file with specified theme.

    Args:
        theme: Theme name to use ("dark" or "light")

    Creates ~/.todo_cli_theme.json with the specified theme.
    Uses atomic write pattern for safety.
    """
    config_path = get_theme_config_path()

    config_data = {
        "theme": theme,
        "_comment": "Valid values: 'dark' or 'light'. Restart app to apply changes."
    }

    try:
        # Atomic write: temp file + replace
        import tempfile
        import os

        # Write to temp file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=config_path.parent,
            prefix=".todo_cli_theme_",
            suffix=".json.tmp"
        )

        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                f.write('\n')  # Trailing newline

            # Atomic replace
            os.replace(temp_path, config_path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    except Exception:
        # Silent failure - app will use default theme
        pass


def validate_theme_config() -> tuple[bool, str]:
    """
    Validate theme configuration file.

    Returns:
        Tuple of (is_valid, error_message).
        If valid: (True, "")
        If invalid: (False, "error description")

    Useful for diagnostics/debugging.
    """
    config_path = get_theme_config_path()

    # Check file exists
    if not config_path.exists():
        return False, f"Config file missing: {config_path}"

    # Check readable
    if not config_path.is_file():
        return False, f"Config path is not a file: {config_path}"

    # Parse JSON
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except OSError as e:
        return False, f"Cannot read file: {e}"

    # Validate structure
    if not isinstance(data, dict):
        return False, "Config must be JSON object"

    if "theme" not in data:
        return False, "Missing 'theme' key"

    theme_name = data["theme"]
    if theme_name not in VALID_THEMES:
        return False, f"Invalid theme '{theme_name}'. Valid: {', '.join(VALID_THEMES)}"

    return True, ""
