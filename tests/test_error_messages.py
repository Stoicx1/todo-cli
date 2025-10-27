import pytest

from core.state import AppState
from core.commands import handle_command


@pytest.fixture
def state():
    return AppState()


def _last_msg(state):
    return state.messages[-1] if state.messages else ""


def test_missing_task_id_error_shows_usage(state, console):
    handle_command("remove", state, console)
    assert "usage" in _last_msg(state).lower()


def test_invalid_command_error_shows_suggestions(state, console):
    handle_command("invalid_command", state, console)
    msg = _last_msg(state).lower()
    assert "unknown" in msg or "help" in msg or "usage" in msg


def test_validation_error_shows_field_name(state, console):
    handle_command('add ""', state, console)
    msg = _last_msg(state).lower()
    assert "usage" in msg or "name" in msg


def test_unmatched_quotes_reports_error(state, console):
    import pytest as _pytest
    with _pytest.raises(ValueError):
        handle_command('add "Unclosed', state, console)


def test_remove_no_ids_reports_error(state, console):
    handle_command("remove", state, console)
    assert "no valid task ids" in _last_msg(state).lower() or "usage" in _last_msg(state).lower()


def test_done_no_ids_reports_error(state, console):
    handle_command("done", state, console)
    assert "usage" in _last_msg(state).lower()


def test_undone_no_ids_reports_error(state, console):
    handle_command("undone", state, console)
    assert "usage" in _last_msg(state).lower()


def test_show_invalid_filter_reports_error(state, console):
    handle_command("show invalid:filter", state, console)
    msg = _last_msg(state).lower()
    assert "error" in msg or "invalid" in msg or "usage" in msg

