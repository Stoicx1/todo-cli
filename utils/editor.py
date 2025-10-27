import os
import subprocess
import shlex
from typing import Optional
from config import IS_WINDOWS


def get_editor_cmd() -> str:
    # Respect VISUAL then EDITOR
    for var in ("VISUAL", "EDITOR"):
        val = os.environ.get(var)
        if val:
            return val
    # Fallbacks by platform
    if IS_WINDOWS:
        return "notepad"
    # Prefer vim, fallback to nano
    return "vim"


def open_in_editor(path: str, editor_cmd: Optional[str] = None) -> int:
    cmd = editor_cmd or get_editor_cmd()
    # Allow quoted/with args
    if isinstance(cmd, str):
        try:
            parts = shlex.split(cmd)
        except Exception:
            parts = [cmd]
    else:
        parts = [str(cmd)]
    parts.append(path)
    try:
        completed = subprocess.run(parts)
        return completed.returncode
    except Exception:
        return 1

