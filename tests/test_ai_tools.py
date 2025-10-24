import os
from pathlib import Path

import pytest

from core.state import AppState
from core import ai_tools


def test_edit_task_tag_normalization_updates_tags_and_index(tmp_path, monkeypatch):
    # Prepare state with a single task
    state = AppState()
    state.add_task(name="Test", comment="", description="", priority=2, tag="initial")

    # Point saves to a temp file to avoid polluting repo
    tasks_file = tmp_path / "tasks.json"
    monkeypatch.setattr("config.DEFAULT_TASKS_FILE", str(tasks_file))

    # Initialize tools with state
    ai_tools.set_app_state(state)

    # Edit tags via AI tool
    res = ai_tools.edit_task(task_id=1, field="tag", value="alpha, beta, gamma")
    assert "Updated task #1" in res or "Updated task #1".lower() in res.lower()

    # Verify tags normalized and legacy field synced
    task = state.get_task_by_id(1)
    assert task is not None
    assert task.tags == ["alpha", "beta", "gamma"]
    assert task.tag == "alpha"

    # Verify tag index updated (lookup by tag)
    by_tag = state.get_tasks_by_tag("beta")
    assert any(t.id == task.id for t in by_tag)


def test_create_task_uses_appstate_and_multitags(tmp_path, monkeypatch):
    state = AppState()

    # Point saves to a temp file to avoid polluting repo
    tasks_file = tmp_path / "tasks.json"
    monkeypatch.setattr("config.DEFAULT_TASKS_FILE", str(tasks_file))

    ai_tools.set_app_state(state)

    # Create task with multiple tags
    res = ai_tools.create_task(
        name="MultiTag",
        priority=1,
        tag="webasto, psdc, fa070",
        description="desc",
        comment="cmt",
    )
    # Response should include ID and name
    assert "Created task #" in res

    # Validate last task
    task = state.tasks[-1]
    assert task.name == "MultiTag"
    assert task.priority == 1
    assert task.tags == ["webasto", "psdc", "fa070"]
    assert task.tag == "webasto"

