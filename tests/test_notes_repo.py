import os
from pathlib import Path

from services.notes import FileNoteRepository


def test_notes_repo_create_and_roundtrip(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    monkeypatch.setattr("config.DEFAULT_NOTES_DIR", str(notes_dir))

    repo = FileNoteRepository(str(notes_dir))
    title = 'Design: OAuth2 "Flow" \\ Issues'
    body = "Line1\nLine2"
    tags = ["backend", "auth"]
    note = repo.create(title=title, body_md=body, tags=tags, task_ids=[12])

    # Ensure file created
    files = list(Path(notes_dir).glob("*.md"))
    assert files, "note file should exist"

    # Read back via repo.get (by id prefix)
    fetched = repo.get(note.id[:8])
    assert fetched is not None
    assert fetched.title == title
    assert fetched.body_md == body
    assert fetched.tags == tags
    assert 12 in fetched.task_ids


def test_notes_repo_link_unlink(tmp_path):
    repo = FileNoteRepository(str(tmp_path))
    n = repo.create(title="t", body_md="", tags=["a"], task_ids=[1])
    repo.link_task(n, 2)
    assert 2 in n.task_ids
    repo.unlink_task(n, 1)
    assert 1 not in n.task_ids

