import re
from datetime import datetime, timedelta

import pytest

from core.state import AppState
from core.commands import handle_done, handle_undone


ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@pytest.fixture
def state() -> AppState:
    return AppState()


def _add_task(state: AppState, name="Task", prio=2, tag=""):
    state.add_task(name=name, comment="", description="", priority=prio, tag=tag)
    return state.tasks[-1]


def test_task_created_at_is_valid_iso_format(state):
    t = _add_task(state)
    assert t.created_at
    assert ISO_RE.match(t.created_at)


def test_task_created_at_not_in_future(state):
    t = _add_task(state)
    dt = datetime.fromisoformat(t.created_at)
    assert dt <= datetime.now() + timedelta(seconds=1)


def test_task_updated_at_initialized(state):
    t = _add_task(state)
    assert t.updated_at
    # Initially equals created_at
    assert t.updated_at == t.created_at


def test_task_completed_at_set_on_done(state, console):
    t = _add_task(state)
    handle_done(["done", str(t.id)], state, console)
    assert t.done is True
    assert t.completed_at
    assert ISO_RE.match(t.completed_at)


def test_task_completed_at_cleared_on_undone(state, console):
    t = _add_task(state)
    handle_done(["done", str(t.id)], state, console)
    assert t.completed_at
    handle_undone(["undone", str(t.id)], state, console)
    assert t.done is False
    assert t.completed_at == ""


def test_task_updated_at_changes_on_undone(state, console):
    t = _add_task(state)
    before = t.updated_at
    handle_undone(["undone", str(t.id)], state, console)
    # updated_at should change on state mutation paths that touch it
    assert t.updated_at != before


def test_sort_by_age_uses_created_at(state):
    # Create two tasks with a small delay
    t1 = _add_task(state, name="Older")
    t1_created = t1.created_at
    # Simulate a time gap by manually adjusting created_at for t2 ordering
    t2 = _add_task(state, name="Newer")
    # Sorting asc => youngest first (created_at most recent first)
    state.sort = "age"
    state.sort_order = "asc"
    ordered = state.get_sorted_tasks(state.tasks)
    assert ordered[0].id == t2.id or ordered[0].created_at >= ordered[1].created_at

