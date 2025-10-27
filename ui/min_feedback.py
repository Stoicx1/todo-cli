"""
Minimal feedback helpers without Rich dependency.

Provides confirm() and OperationSummary used by core.commands in a
console-agnostic way so tests don’t require Rich.
"""

from __future__ import annotations

from typing import Optional, Any


def _print(console: Any | None, message: str) -> None:
    try:
        if console is None:
            return
        if hasattr(console, "print"):
            console.print(message)
        else:
            print(message)
    except Exception:
        pass


def confirm(message: str, default: bool = False) -> bool:
    """Return default without interactive prompt.

    Tests can monkeypatch core.commands.confirm to control behavior.
    """
    return default


class OperationSummary:
    def __init__(self, operation: str, success_count: int, failure_count: int = 0, console: Any | None = None):
        self.operation = operation
        self.success_count = success_count
        self.failure_count = failure_count
        self.console = console

    def show(self) -> None:
        if self.failure_count and self.success_count:
            msg = f"[info] {self.operation}: {self.success_count} ok, {self.failure_count} failed"
        elif self.failure_count and not self.success_count:
            msg = f"[error] {self.operation}: {self.failure_count} failed"
        else:
            msg = f"[ok] {self.operation}: {self.success_count} succeeded"
        _print(self.console, msg)

    @staticmethod
    def show_summary(operation: str, success_count: int, failure_count: int = 0, console: Any | None = None) -> None:
        OperationSummary(operation, success_count, failure_count, console).show()

