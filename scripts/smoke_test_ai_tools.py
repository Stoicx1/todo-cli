import sys
from pathlib import Path

from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.state import AppState
from core import ai_tools


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

def test_edit_task_tag_normalization(tmpdir: Path):
    state = AppState()
    state.add_task(name="Test", comment="", description="", priority=2, tag="initial")

    # Point default tasks path to tmp file
    import config as _cfg
    _cfg.DEFAULT_TASKS_FILE = str(tmpdir / "tasks.json")

    ai_tools.set_app_state(state)

    res = ai_tools.edit_task.func(task_id=1, field="tag", value="alpha, beta, gamma")
    assert_true("Updated task #1" in res or "updated task #1" in res.lower(), f"Unexpected response: {res}")

    task = state.get_task_by_id(1)
    assert_true(task is not None, "Task not found after edit")
    assert_true(task.tags == ["alpha", "beta", "gamma"], f"Tags not normalized: {task.tags}")
    assert_true(task.tag == "alpha", f"Legacy tag not synced: {task.tag}")

    by_tag = state.get_tasks_by_tag("beta")
    assert_true(any(t.id == task.id for t in by_tag), "Tag index not updated for 'beta'")


def test_create_task_multitags(tmpdir: Path):
    state = AppState()

    import config as _cfg
    _cfg.DEFAULT_TASKS_FILE = str(tmpdir / "tasks.json")

    ai_tools.set_app_state(state)

    res = ai_tools.create_task.func(
        name="MultiTag",
        priority=1,
        tag="webasto, psdc, fa070",
        description="desc",
        comment="cmt",
    )
    assert_true("Created task #" in res, f"Unexpected response: {res}")

    task = state.tasks[-1]
    assert_true(task.name == "MultiTag", f"Name mismatch: {task.name}")
    assert_true(task.priority == 1, f"Priority mismatch: {task.priority}")
    assert_true(task.tags == ["webasto", "psdc", "fa070"], f"Tags mismatch: {task.tags}")
    assert_true(task.tag == "webasto", f"Legacy tag mismatch: {task.tag}")



def test_backup_recovery(tmpdir: Path):
    # Dummy console to avoid needing rich
    class _C:
        def print(self, *args, **kwargs):
            pass
    console = _C()

    state = AppState()
    import config as _cfg
    _cfg.DEFAULT_TASKS_FILE = str(tmpdir / "tasks.json")

    # First save with 1 task
    state.add_task(name="One", comment="", description="", priority=2, tag="t")
    state.save_to_file(_cfg.DEFAULT_TASKS_FILE, console)

    # Second save with 2 tasks (creates backup of first save)
    state.add_task(name="Two", comment="", description="", priority=2, tag="t")
    state.save_to_file(_cfg.DEFAULT_TASKS_FILE, console)

    # Corrupt primary
    Path(_cfg.DEFAULT_TASKS_FILE).write_text("corrupt", encoding="utf-8")

    # Load into fresh state; should recover from backup -> 1 task
    new_state = AppState()
    new_state.load_from_file(_cfg.DEFAULT_TASKS_FILE, console)
    assert_true(len(new_state.tasks) == 1, f"Expected recovery to 1 task, got {len(new_state.tasks)}")


def test_concurrent_saves_serialized(tmpdir: Path):
    class _C:
        def print(self, *args, **kwargs):
            pass
    console = _C()

    import threading, time, json

    state = AppState()
    import config as _cfg
    _cfg.DEFAULT_TASKS_FILE = str(tmpdir / "tasks.json")

    # Initial task then save once to create file
    state.add_task(name="A", comment="", description="", priority=2, tag="x")

    def save_after(delay):
        time.sleep(delay)
        state.save_to_file(_cfg.DEFAULT_TASKS_FILE, console)

    t1 = threading.Thread(target=save_after, args=(0.05,), name="t1")
    t1.start()

    # Change state and ensure second save happens last
    state.add_task(name="B", comment="", description="", priority=2, tag="y")
    t2 = threading.Thread(target=save_after, args=(0.10,), name="t2")
    t2.start()

    t1.join(); t2.join()

    # File should be valid JSON and reflect the last save (2 tasks)
    data = Path(_cfg.DEFAULT_TASKS_FILE).read_text(encoding="utf-8")
    try:
        arr = json.loads(data)
    except Exception as e:
        raise AssertionError(f"Final file not valid JSON: {e}")
    assert_true(len(arr) == 2, f"Expected 2 tasks saved, got {len(arr)}")


def main():
    tmpdir = Path(".tmp_smoke")
    tmpdir.mkdir(exist_ok=True)

    try:
        test_edit_task_tag_normalization(tmpdir)
        test_create_task_multitags(tmpdir)
        test_backup_recovery(tmpdir)
        test_concurrent_saves_serialized(tmpdir)
    except AssertionError as e:
        print(f"SMOKE TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"SMOKE TEST ERROR: {type(e).__name__}: {e}")
        sys.exit(2)
    else:
        print("SMOKE TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
