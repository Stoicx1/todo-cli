from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from models.note import Note
from utils.ids import uuid_v7


class FileNoteRepository:
    def __init__(self, notes_dir: str = "notes"):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Serialization ----------
    def _serialize(self, note: Note) -> str:
        # Minimal YAML-like front matter writer with basic quoting
        def q(s: str) -> str:
            s = (s or "")
            s = s.replace('\\', r'\\')
            s = s.replace('"', '\\"')
            return f'"{s}"'

        def qlist(items: list[str]) -> str:
            return ", ".join(q(x) for x in items)

        lines = [
            "---",
            f"id: {note.id}",
            f"title: {q(note.title)}",
            f"created_at: {q(note.created_at)}",
            f"updated_at: {q(note.updated_at)}",
            f"tags: [{qlist(note.tags)}]",
            f"task_ids: [{', '.join(str(x) for x in note.task_ids)}]",
            "---",
            note.body_md or "",
        ]
        return "\n".join(lines)

    def _parse_front_matter(self, text: str) -> tuple[Dict[str, str], str]:
        # very simple front matter parser: expects --- ... --- at top
        if not text.startswith("---"):
            return {}, text
        parts = text.split("\n")
        data: Dict[str, str] = {}
        body_start = 0
        if parts and parts[0].strip() == "---":
            for i in range(1, len(parts)):
                line = parts[i]
                if line.strip() == "---":
                    body_start = i + 1
                    break
                # parse key: value or key: [a, b]
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip()
        body = "\n".join(parts[body_start:])
        return data, body

    def _deserialize(self, text: str) -> Note:
        meta, body = self._parse_front_matter(text)
        def _unquote(s: str) -> str:
            s = s.strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            s = s.replace('\\"', '"')
            s = s.replace(r'\\', '\\')
            return s

        def _parse_list(s: str) -> List[str]:
            s = (s or "").strip()
            if s.startswith("[") and s.endswith("]"):
                s = s[1:-1]
            items: List[str] = []
            buf = ''
            in_quote = False
            quote_char = ''
            for ch in s:
                if ch in ('"', "'"):
                    if not in_quote:
                        in_quote = True
                        quote_char = ch
                    elif quote_char == ch:
                        in_quote = False
                    buf += ch
                elif ch == ',' and not in_quote:
                    if buf.strip():
                        items.append(_unquote(buf.strip()))
                    buf = ''
                else:
                    buf += ch
            if buf.strip():
                items.append(_unquote(buf.strip()))
            return items

        def _strip_brackets(s: str) -> List[str]:
            """Return comma-split items from a bracketed list string.

            Examples:
            "[1, 2]" -> ["1", "2"],
            "[]" -> [],
            "1,2" -> ["1", "2"]
            """
            s = (s or "").strip()
            if s.startswith("[") and s.endswith("]"):
                s = s[1:-1]
            if not s:
                return []
            return [part.strip() for part in s.split(',') if part.strip()]

        tags = _parse_list(meta.get("tags", ""))
        task_ids = []
        for x in _strip_brackets(meta.get("task_ids", "")):
            try:
                task_ids.append(int(x))
            except Exception:
                pass
        return Note(
            id=meta.get("id", uuid_v7()),
            title=_unquote(meta.get("title", "Untitled")),
            body_md=body,
            tags=tags,
            task_ids=task_ids,
            created_at=_unquote(meta.get("created_at", "")),
            updated_at=_unquote(meta.get("updated_at", "")),
            deleted_at="",
        )

    def _slug(self, title: str) -> str:
        return "-".join([w for w in (title or "").lower().split() if w])[:40]

    def _note_path(self, note_id: str, title: str = "") -> Path:
        slug = self._slug(title)
        name = f"{note_id}"
        if slug:
            name += f"-{slug}"
        return self.notes_dir / f"{name}.md"

    def _ensure_filename(self, note: Note, current_path: Path) -> Path:
        """Ensure filename matches note title slug; rename or cleanup duplicates.

        Returns the path where the note should live.
        """
        desired = self._note_path(note.id, note.title)
        try:
            if current_path.resolve() == desired.resolve():
                return desired
        except Exception:
            # On some platforms resolve() may fail; fallback to name compare
            if current_path.name == desired.name:
                return desired
        # Create destination first (write current content) if missing
        try:
            if not desired.exists():
                desired.write_text(self._serialize(note), encoding="utf-8")
        except Exception:
            pass
        # Remove other variants for this id except desired
        try:
            for p in self.notes_dir.glob(f"{note.id}*.md"):
                if p.name != desired.name:
                    try:
                        p.unlink()
                    except Exception:
                        pass
        except Exception:
            pass
        return desired

    # ---------- CRUD ----------
    def create(self, title: str, tags: Optional[List[str]] = None, task_ids: Optional[List[int]] = None, body_md: str = "") -> Note:
        now = datetime.now().isoformat()
        note = Note(
            id=uuid_v7(),
            title=title.strip() or "Untitled",
            body_md=body_md or "",
            tags=[t.strip().lower() for t in (tags or []) if t.strip()],
            task_ids=list(dict.fromkeys(task_ids or [])),  # unique, preserve order
            created_at=now,
            updated_at=now,
        )
        path = self._note_path(note.id, note.title)
        path.write_text(self._serialize(note), encoding="utf-8")
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTES] Created note file: {path.name} (tags={note.tags}, tasks={note.task_ids})")
        except Exception:
            pass
        return note

    def update(self, note: Note) -> None:
        note.updated_at = datetime.now().isoformat()
        # Write to desired path based on current title
        path = self._note_path(note.id, note.title)
        path.write_text(self._serialize(note), encoding="utf-8")
        # Cleanup any stale files with old slugs
        try:
            for p in self.notes_dir.glob(f"{note.id}*.md"):
                if p.name != path.name:
                    try:
                        p.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def get(self, note_id: str) -> Optional[Note]:
        # find by id prefix in filenames
        for p in self.notes_dir.glob("*.md"):
            name = p.name
            if name.startswith(note_id):
                try:
                    text = p.read_text(encoding="utf-8")
                    return self._deserialize(text)
                except Exception:
                    continue
        return None

    def list_all(self) -> List[Note]:
        notes: List[Note] = []
        for p in sorted(self.notes_dir.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8")
                n = self._deserialize(text)
                # Normalize filenames to current title slug
                self._ensure_filename(n, p)
                notes.append(n)
            except Exception:
                continue
        return notes

    def delete(self, note_id_prefix: str) -> bool:
        """Delete note file(s) matching the id prefix. Returns True if any deleted."""
        deleted = False
        try:
            for p in self.notes_dir.glob(f"{note_id_prefix}*.md"):
                try:
                    p.unlink()
                    deleted = True
                except Exception:
                    pass
        except Exception:
            pass
        return deleted

    # ---------- Linking ----------
    def link_task(self, note: Note, task_id: int) -> Note:
        if task_id not in note.task_ids:
            note.task_ids.append(task_id)
        self.update(note)
        return note

    def unlink_task(self, note: Note, task_id: int) -> Note:
        if task_id in note.task_ids:
            note.task_ids = [x for x in note.task_ids if x != task_id]
        self.update(note)
        return note

    # ---------- Search ----------
    def list_by_task(self, task_id: int) -> List[Note]:
        return [n for n in self.list_all() if task_id in (n.task_ids or [])]

    def search(self, q: str) -> List[Note]:
        ql = (q or "").lower()
        res: List[Note] = []
        for n in self.list_all():
            if ql in n.title.lower() or ql in (n.body_md or "").lower() or any(ql in t for t in n.tags):
                res.append(n)
        return res
