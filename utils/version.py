from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _repo_root() -> Path:
    # utils/ is one level below repo root
    return Path(__file__).resolve().parent.parent


def _read_version_file() -> str | None:
    try:
        ver_path = _repo_root() / "VERSION"
        if ver_path.exists():
            text = ver_path.read_text(encoding="utf-8").strip()
            return text or None
    except Exception:
        pass
    return None


def _git_describe() -> str | None:
    root = _repo_root()
    try:
        # Use git describe to get nearest tag and dirty marker
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--dirty", "--always"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore").strip()
        return out or None
    except Exception:
        return None


def _from_git_describe(desc: str) -> str:
    # Cases:
    # - v1.2.3                -> 1.2.3
    # - v1.2.3-4-gabc123      -> 1.2.3-dev+abc123
    # - v1.2.3-4-gabc123-dirty-> 1.2.3-dev+abc123-dirty
    # - gabc123               -> 0.0.0-dev+gabc123
    m = _SEMVER_RE.match(desc)
    if m:
        # Exact tag or tag with pre/build included
        major, minor, patch = m.groups()
        base = f"{major}.{minor}.{patch}"
        if desc.startswith("v") and desc == f"v{base}":
            return base
        # Contains suffix like -4-gabc123 or pre-release/build
        sha = None
        dirty_suffix = "-dirty" if desc.endswith("-dirty") else ""
        msha = re.search(r"g([0-9a-f]{6,})", desc)
        if msha:
            sha = msha.group(1)
        if sha:
            return f"{base}-dev+{sha}{dirty_suffix}"
        return f"{base}-dev{dirty_suffix}"
    # Fallback if no tag found: treat as dev with whatever describe returned
    dirty_suffix = "-dirty" if desc.endswith("-dirty") else ""
    # Extract short sha if present
    msha = re.search(r"([0-9a-f]{6,})", desc)
    if msha:
        return f"0.0.0-dev+{msha.group(1)}{dirty_suffix}"
    return f"0.0.0-dev{dirty_suffix}"


def get_version() -> str:
    """Return the application version string.

    Precedence:
    1) VERSION file at repo root (exact release or pre-release).
    2) git describe-derived dev version when not on a tag.
    3) Fallback to 0.0.0-dev when offline.
    """
    # 1) VERSION file
    v = _read_version_file()
    if v:
        return v

    # 2) git describe
    desc = _git_describe()
    if desc:
        return _from_git_describe(desc)

    # 3) safe default
    return "0.0.0-dev"

