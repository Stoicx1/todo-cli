import pytest

from utils.tag_parser import parse_tags


def test_parse_tags_normalizes_and_limits(monkeypatch):
    warnings = []

    def warn(msg: str):
        warnings.append(msg)

    # duplicates and extra beyond limit should be handled
    tags = parse_tags("Backend, API, Urgent, api, extra", max_tags=3, warn_callback=warn)
    assert tags == ["backend", "api", "urgent"]
    # Should warn about duplicate and limit
    assert any("Duplicate" in w or "limit" in w.lower() for w in warnings)


def test_parse_tags_invalid_characters_warn():
    warnings = []

    def warn(msg: str):
        warnings.append(msg)

    tags = parse_tags("ok, invalid@tag, also-ok", warn_callback=warn)
    assert tags == ["ok", "also-ok"]
    assert any("Invalid tag" in w for w in warnings)

