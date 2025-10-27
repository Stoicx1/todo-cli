import pytest

from core.state import AppState


def _add(state: AppState, name: str = "T", prio: int = 2, tag: str = ""):
    state.add_task(name=name, comment="", description="", priority=prio, tag=tag)


def test_filter_cache_invalidates_on_add_task():
    s = AppState()
    s.filter = "none"
    _ = s.filtered_tasks
    assert s._filtered_tasks_cache is not None
    _add(s, tag="a")
    assert s._filter_cache_dirty is True


def test_filter_cache_invalidates_on_remove_task():
    s = AppState()
    _add(s)
    _ = s.filtered_tasks
    t = s.tasks[0]
    s.remove_task(t)
    assert s._filter_cache_dirty is True


def test_filter_cache_invalidates_on_edit_task():
    s = AppState()
    _add(s, tag="a")
    _ = s.filtered_tasks
    t = s.tasks[0]
    old = list(t.tags)
    t.tags = ["b"]
    s._update_tag_index_for_task(t, old_tags=old)
    s.invalidate_filter_cache()
    assert s._filter_cache_dirty is True


def test_filter_cache_hit_on_repeated_access():
    s = AppState()
    for i in range(10):
        _add(s, tag="x")
    s.filter = "tag=x"
    first = s.filtered_tasks
    assert s._filter_cache_dirty is False
    second = s.filtered_tasks
    assert first is second


def test_filter_cache_key_includes_filter_string():
    s = AppState()
    _add(s, tag="a")
    _add(s, tag="b")
    s.filter = "tag=a"
    a = s.filtered_tasks
    s.filter = "tag=b"
    b = s.filtered_tasks
    assert a != b

