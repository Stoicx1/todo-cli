"""
Unit tests for core/theme_config.py

Tests the simple config-based theme system.
"""

import json
import pytest
from pathlib import Path
from core.theme_config import (
    get_theme_config,
    create_default_theme_config,
    validate_theme_config,
    get_theme_config_path,
    DEFAULT_THEME,
    VALID_THEMES,
)


@pytest.fixture
def temp_theme_config(tmp_path, monkeypatch):
    """
    Fixture that creates a temporary theme config file path.

    Monkeypatches get_theme_config_path to use temp directory.
    """
    theme_file = tmp_path / ".todo_cli_theme.json"

    # Monkeypatch the get_theme_config_path function
    def mock_get_path():
        return theme_file

    monkeypatch.setattr("core.theme_config.get_theme_config_path", mock_get_path)

    yield theme_file

    # Cleanup
    if theme_file.exists():
        theme_file.unlink()


class TestGetThemeConfig:
    """Tests for get_theme_config() function."""

    def test_default_theme_when_config_missing(self, temp_theme_config):
        """Should return default theme when config file doesn't exist."""
        theme = get_theme_config()
        assert theme == DEFAULT_THEME

        # Should also create the config file
        assert temp_theme_config.exists()

    def test_loads_valid_dark_theme(self, temp_theme_config):
        """Should load 'dark' theme from valid config."""
        temp_theme_config.write_text('{"theme": "dark"}', encoding='utf-8')

        theme = get_theme_config()
        assert theme == "dark"

    def test_loads_valid_light_theme(self, temp_theme_config):
        """Should load 'light' theme from valid config."""
        temp_theme_config.write_text('{"theme": "light"}', encoding='utf-8')

        theme = get_theme_config()
        assert theme == "light"

    def test_falls_back_on_invalid_theme(self, temp_theme_config):
        """Should return default theme when config has invalid theme value."""
        temp_theme_config.write_text('{"theme": "invalid"}', encoding='utf-8')

        theme = get_theme_config()
        assert theme == DEFAULT_THEME

    def test_falls_back_on_malformed_json(self, temp_theme_config):
        """Should return default theme when config has malformed JSON."""
        temp_theme_config.write_text('{"theme": "dark"', encoding='utf-8')  # Missing closing brace

        theme = get_theme_config()
        assert theme == DEFAULT_THEME

    def test_falls_back_on_missing_theme_key(self, temp_theme_config):
        """Should return default theme when config missing 'theme' key."""
        temp_theme_config.write_text('{"other": "value"}', encoding='utf-8')

        theme = get_theme_config()
        assert theme == DEFAULT_THEME

    def test_falls_back_on_empty_file(self, temp_theme_config):
        """Should return default theme when config file is empty."""
        temp_theme_config.write_text('', encoding='utf-8')

        theme = get_theme_config()
        assert theme == DEFAULT_THEME

    def test_handles_theme_with_comment(self, temp_theme_config):
        """Should load theme correctly even with _comment field."""
        config_data = {
            "theme": "light",
            "_comment": "Valid values: 'dark' or 'light'"
        }
        temp_theme_config.write_text(json.dumps(config_data), encoding='utf-8')

        theme = get_theme_config()
        assert theme == "light"


class TestCreateDefaultThemeConfig:
    """Tests for create_default_theme_config() function."""

    def test_creates_config_file(self, temp_theme_config):
        """Should create config file with default theme."""
        create_default_theme_config()

        assert temp_theme_config.exists()

    def test_creates_valid_json(self, temp_theme_config):
        """Should create valid JSON config."""
        create_default_theme_config()

        data = json.loads(temp_theme_config.read_text(encoding='utf-8'))
        assert isinstance(data, dict)

    def test_sets_default_theme(self, temp_theme_config):
        """Should set theme to default in created config."""
        create_default_theme_config()

        data = json.loads(temp_theme_config.read_text(encoding='utf-8'))
        assert data["theme"] == DEFAULT_THEME

    def test_includes_helpful_comment(self, temp_theme_config):
        """Should include helpful comment in created config."""
        create_default_theme_config()

        data = json.loads(temp_theme_config.read_text(encoding='utf-8'))
        assert "_comment" in data
        assert "restart" in data["_comment"].lower()

    def test_overwrites_existing_file(self, temp_theme_config):
        """Should overwrite existing file when called."""
        # Create initial file
        temp_theme_config.write_text('{"theme": "light"}', encoding='utf-8')

        # Create default (should overwrite)
        create_default_theme_config()

        data = json.loads(temp_theme_config.read_text(encoding='utf-8'))
        assert data["theme"] == DEFAULT_THEME

    def test_handles_permission_errors_gracefully(self, temp_theme_config, monkeypatch):
        """Should handle permission errors without raising exception."""
        # Monkeypatch tempfile.mkstemp to raise PermissionError
        import tempfile
        original_mkstemp = tempfile.mkstemp

        def mock_mkstemp(*args, **kwargs):
            raise PermissionError("No permission")

        monkeypatch.setattr("tempfile.mkstemp", mock_mkstemp)

        # Should not raise exception
        create_default_theme_config()


class TestValidateThemeConfig:
    """Tests for validate_theme_config() function."""

    def test_validates_correct_config(self, temp_theme_config):
        """Should return (True, '') for valid config."""
        temp_theme_config.write_text('{"theme": "dark"}', encoding='utf-8')

        is_valid, error = validate_theme_config()
        assert is_valid is True
        assert error == ""

    def test_detects_missing_file(self, temp_theme_config):
        """Should return (False, error) when file doesn't exist."""
        is_valid, error = validate_theme_config()
        assert is_valid is False
        assert "missing" in error.lower()

    def test_detects_invalid_json(self, temp_theme_config):
        """Should return (False, error) for malformed JSON."""
        temp_theme_config.write_text('{"theme": "dark"', encoding='utf-8')

        is_valid, error = validate_theme_config()
        assert is_valid is False
        assert "json" in error.lower()

    def test_detects_missing_theme_key(self, temp_theme_config):
        """Should return (False, error) when 'theme' key missing."""
        temp_theme_config.write_text('{"other": "value"}', encoding='utf-8')

        is_valid, error = validate_theme_config()
        assert is_valid is False
        assert "theme" in error.lower()

    def test_detects_invalid_theme_value(self, temp_theme_config):
        """Should return (False, error) for invalid theme value."""
        temp_theme_config.write_text('{"theme": "invalid"}', encoding='utf-8')

        is_valid, error = validate_theme_config()
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_validates_both_valid_themes(self, temp_theme_config):
        """Should validate both 'dark' and 'light' themes."""
        for theme in VALID_THEMES:
            temp_theme_config.write_text(f'{{"theme": "{theme}"}}', encoding='utf-8')

            is_valid, error = validate_theme_config()
            assert is_valid is True, f"Theme '{theme}' should be valid"


class TestConstants:
    """Tests for module constants."""

    def test_default_theme_is_dark(self):
        """DEFAULT_THEME should be 'dark'."""
        assert DEFAULT_THEME == "dark"

    def test_valid_themes_contains_both(self):
        """VALID_THEMES should contain both 'dark' and 'light'."""
        assert "dark" in VALID_THEMES
        assert "light" in VALID_THEMES
        assert len(VALID_THEMES) == 2


class TestIntegration:
    """Integration tests for theme config workflow."""

    def test_first_run_creates_config_and_returns_default(self, temp_theme_config):
        """First run should create config file and return default theme."""
        # Ensure config doesn't exist
        assert not temp_theme_config.exists()

        # First call should create config and return default
        theme = get_theme_config()
        assert theme == DEFAULT_THEME
        assert temp_theme_config.exists()

        # Verify file contents
        data = json.loads(temp_theme_config.read_text(encoding='utf-8'))
        assert data["theme"] == DEFAULT_THEME

    def test_subsequent_runs_use_saved_theme(self, temp_theme_config):
        """Subsequent runs should use saved theme from config."""
        # First run creates default
        theme1 = get_theme_config()
        assert theme1 == DEFAULT_THEME

        # Manually change to light theme
        temp_theme_config.write_text('{"theme": "light"}', encoding='utf-8')

        # Second run should use saved light theme
        theme2 = get_theme_config()
        assert theme2 == "light"

    def test_corruption_recovery(self, temp_theme_config):
        """Corrupted config should fall back to default without breaking."""
        # Create valid config
        temp_theme_config.write_text('{"theme": "light"}', encoding='utf-8')
        assert get_theme_config() == "light"

        # Corrupt the config
        temp_theme_config.write_text('corrupted {{{', encoding='utf-8')

        # Should fall back to default
        theme = get_theme_config()
        assert theme == DEFAULT_THEME
