from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Note:
    id: str
    title: str
    body_md: str = ""
    tags: List[str] = field(default_factory=list)
    task_ids: List[int] = field(default_factory=list)  # links to current int task IDs
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str = ""

    def excerpt(self, length: int = 120) -> str:
        text = (self.body_md or "").strip().replace("\r", "")
        if not text:
            return ""
        # first non-empty line
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
        ex = first_line[:length]
        return ex + ("…" if len(first_line) > length else "")

