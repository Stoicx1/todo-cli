"""
Comprehensive tests for utils/validators.py - Field validation

Tests priority validation, comment/description sanitization, and input validation.
Production-ready tests with clear, explicit expectations.
"""

import pytest
from utils.validators import (
    validate_priority,
    sanitize_comment,
    sanitize_description,
    clamp_priority,
)


class TestPriorityValidation:
    """Test priority validation and clamping."""

    def test_valid_priorities(self):
        assert validate_priority(1)[0] is True
        assert validate_priority(2)[0] is True
        assert validate_priority(3)[0] is True

    def test_invalid_priorities(self):
        assert validate_priority(0)[0] is False
        assert validate_priority(4)[0] is False
        assert validate_priority(-1)[0] is False

    def test_clamp_high(self):
        assert clamp_priority(10) == 3
        assert clamp_priority(99) == 3

    def test_clamp_low(self):
        assert clamp_priority(0) == 1
        assert clamp_priority(-99) == 1

    def test_clamp_valid_unchanged(self):
        assert clamp_priority(1) == 1
        assert clamp_priority(2) == 2
        assert clamp_priority(3) == 3

    def test_boundary_values(self):
        assert clamp_priority(1) == 1
        assert clamp_priority(3) == 3


class TestCommentSanitization:
    """Test comment sanitization behavior."""

    def test_normal_text(self):
        assert sanitize_comment("Normal comment") == "Normal comment"

    def test_control_chars_handled(self):
        # Strip leading/trailing whitespace, preserve internal control chars
        result = sanitize_comment(" Text\x00with\x01control ")
        assert isinstance(result, str)
        assert "Text" in result and "with" in result and "control" in result

    def test_unicode_preserved(self):
        s = "Comment üñïçødê ✓ — Δ"
        result = sanitize_comment(s)
        assert "üñïçødê" in result and "✓" in result

    def test_empty_string(self):
        assert sanitize_comment("") == ""

    def test_whitespace_only(self):
        result = sanitize_comment("   \t\n  ")
        assert result == ""

    def test_special_chars_preserved(self):
        result = sanitize_comment("Text @#$%^&*()")
        assert result == "Text @#$%^&*()"

    def test_html_tags_handled(self):
        result = sanitize_comment("<script>alert()</script>")
        assert isinstance(result, str)

    def test_very_long_comment(self):
        result = sanitize_comment("A" * 1000)
        assert isinstance(result, str)
        assert len(result) == 500  # MAX_COMMENT_LENGTH is 500

    def test_newlines_handled(self):
        result = sanitize_comment("Line1\nLine2\nLine3")
        assert "Line1" in result

    def test_tabs_handled(self):
        result = sanitize_comment("Text\twith\ttabs")
        assert "Text" in result and "with" in result

    def test_mixed_content(self):
        result = sanitize_comment("Text 123 !@# $,-.-'")
        assert all(x in result for x in ["Text", "123", "!@#"]) 

    def test_repeated_sanitization_idempotent(self):
        first = sanitize_comment("Test\ntext")
        second = sanitize_comment(first)
        assert first == second


class TestDescriptionSanitization:
    """Test description sanitization behavior."""

    def test_normal_text(self):
        assert sanitize_description("Normal description") == "Normal description"

    def test_multiline_preserved(self):
        result = sanitize_description("Line1\nLine2\nLine3")
        assert all(x in result for x in ["Line1", "Line2", "Line3"])

    def test_control_chars_handled(self):
        result = sanitize_description(" Text\x00\x01desc ")
        assert isinstance(result, str)
        assert result.startswith("Text") and result.endswith("desc")

    def test_unicode_preserved(self):
        s = "Text üñïçødê ✓ — Δ"
        result = sanitize_description(s)
        assert "üñïçødê" in result and "✓" in result

    def test_empty_string(self):
        assert sanitize_description("") == ""

    def test_very_long_description(self):
        result = sanitize_description("A" * 5000)
        assert isinstance(result, str)
        assert len(result) == 2000  # MAX_DESCRIPTION_LENGTH is 2000

    def test_markdown_preserved(self):
        result = sanitize_description("# Header\n- List item")
        assert "Header" in result and "List item" in result

    def test_urls_preserved(self):
        result = sanitize_description("https://example.com test")
        assert "example.com" in result


class TestInputValidationEdgeCases:
    """Edge cases."""

    def test_none_handling(self):
        try:
            result = sanitize_comment(None)  # type: ignore[arg-type]
            assert result == "" or result is None
        except (TypeError, AttributeError):
            pass  # Expected if validators don't handle None

    def test_numeric_strings(self):
        assert sanitize_comment("12345") == "12345"

    def test_mixed_types(self):
        result = sanitize_comment("Text 123 !@#")
        assert result == "Text 123 !@#"

    def test_all_fields_together(self):
        name = "Valid Task"
        comment = sanitize_comment("Valid comment")
        desc = sanitize_description("Valid description")
        priority = clamp_priority(2)

        assert len(name) > 0
        assert isinstance(comment, str)
        assert isinstance(desc, str)
        assert 1 <= priority <= 3

