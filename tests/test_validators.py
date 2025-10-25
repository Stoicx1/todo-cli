from utils.validators import (
    validate_task_name,
    validate_priority,
    clamp_priority,
)


def test_validate_task_name():
    ok, err = validate_task_name("Task")
    assert ok and err is None

    ok, err = validate_task_name("")
    assert not ok and "cannot be empty" in err.lower()


def test_validate_priority_and_clamp():
    ok, err, p = validate_priority("2")
    assert ok and p == 2

    ok, err, p = validate_priority("x")
    assert not ok and p is None

    # Clamp out-of-range
    assert clamp_priority(999) == 3
    assert clamp_priority(-5) == 1

