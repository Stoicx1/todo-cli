import os
from pathlib import Path

from core.state import AppState
from core import ai_tools


def setup_state(tmp_path, monkeypatch):
    # Temp tasks file
    tasks_file = tmp_path / "tasks.json"
    monkeypatch.setattr("config.DEFAULT_TASKS_FILE", str(tasks_file))
    # Temp notes dir
    notes_dir = tmp_path / "notes"
    monkeypatch.setattr("config.DEFAULT_NOTES_DIR", str(notes_dir))
    state = AppState()
    ai_tools.set_app_state(state)
    return state


def test_create_and_link_note_tool(tmp_path, monkeypatch):
    state = setup_state(tmp_path, monkeypatch)
    # Create a task to link
    state.add_task(name="T1", comment="", description="", priority=2, tag="a")

    res = ai_tools.create_note(title="Minutes", body_md="Line", tags="x,y", task_ids="1")
    assert "Created note" in res

    # Link another task id and then unlink
    state.add_task(name="T2", comment="", description="", priority=2, tag="b")
    nid = res.split()[3][:8] if res else ""
    lr = ai_tools.link_note(note_id=nid, task_id=2)
    assert "Linked" in lr
    ur = ai_tools.unlink_note(note_id=nid, task_id=1)
    assert "Unlinked" in ur


def test_edit_note_tags_add_remove(tmp_path, monkeypatch):
    state = setup_state(tmp_path, monkeypatch)
    res = ai_tools.create_note(title="Tags", body_md="", tags="one,two", task_ids="")
    nid = res.split()[3][:8]
    # Add tag with +three and remove -one
    er = ai_tools.edit_note(note_id=nid, field="tags", value="+three -one")
    assert "Updated note" in er
    # Fetch details to confirm
    dr = ai_tools.get_note_details(nid)
    assert "tags:" in dr and "three" in dr and "one" not in dr


def test_search_notes_and_delete_guard(tmp_path, monkeypatch):
    state = setup_state(tmp_path, monkeypatch)
    ai_tools.create_note(title="FindMe", body_md="webasto", tags="z", task_ids="")
    s = ai_tools.search_notes(query="webasto")
    assert "FindMe" in s
    # Short prefix delete should be guarded
    dr = ai_tools.delete_note(note_id_prefix="ab", force=False)
    assert "Prefix too short" in dr or "too short" in dr

