"""
Emoji/Unicode helper utilities.

Provides a single function to select between a Unicode string and an ASCII
fallback based on terminal support. Centralizing this avoids inconsistent
checks across the codebase and prevents mojibake on Windows terminals that
aren't truly UTF-8.
"""

import os
import sys


def _supports_unicode() -> bool:
    """Best-effort detection of Unicode/UTF-8 support.

    Heuristics:
    - If PYTHONIOENCODING is set and contains 'utf', prefer Unicode.
    - If sys.stdout.encoding contains 'utf' (e.g., 'utf-8', 'utf8', 'utf-8-sig').
    - On Windows, code page 65001 often reports as 'cp65001' — treat as UTF-8.
    Falls back to False if encoding is unknown.
    """
    # Environment override
    io_enc = os.environ.get("PYTHONIOENCODING", "")
    if io_enc and "utf" in io_enc.lower():
        return True

    enc = getattr(sys.stdout, "encoding", None) or ""
    enc_low = enc.lower()

    if "utf" in enc_low:
        return True

    # Windows UTF-8 code page
    if enc_low == "cp65001":
        return True

    return False


SUPPORTS_UNICODE: bool = _supports_unicode()


def emoji(unicode_text: str, ascii_fallback: str) -> str:
    """Return Unicode text if supported, otherwise ASCII fallback."""
    return unicode_text if SUPPORTS_UNICODE else ascii_fallback

