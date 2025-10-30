from core.commands import COMMAND_ALIASES


def test_no_single_letter_destructive_typed_aliases():
    banned_targets = {"remove", "delete"}
    offenders = {k: v for k, v in COMMAND_ALIASES.items() if len(k) == 1 and v in banned_targets}
    assert offenders == {}, f"Single-letter typed aliases for destructive actions are not allowed: {offenders}"

