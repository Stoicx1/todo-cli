"""
ContextFooter - Compact, two-line, context-aware footer hints

Clean, cross-platform text (ASCII fallback on Windows) with optional
Unicode bullets when available.
"""

from textual.widgets import Static
from textual.widget import Widget
from config import IS_WINDOWS, USE_UNICODE


class ContextFooter(Static):
    """Renders two lines of key hints based on current focus and mode."""

    DEFAULT_CSS = """
    ContextFooter { background: $primary; color: $text; height: 2; min-height: 2; padding: 0 1; dock: bottom; }
    """

    def on_mount(self) -> None:
        self.update(self._build_text())
        try:
            # Periodically refresh to track focus and mode changes
            self.set_interval(0.25, self.update_from_state)
        except Exception:
            pass

    def _logical_focus_id(self, focused: Widget | None) -> str:
        if not focused:
            return ""
        fid = getattr(focused, "id", "") or focused.__class__.__name__
        known = {"task_table", "note_table", "ai_chat_panel", "command_input", "ai_input"}
        if fid in known or fid.endswith("TaskTable") or fid.endswith("NoteTable"):
            return fid
        # Walk up a few levels to find a known parent container id
        try:
            node = focused.parent
            depth = 0
            while node is not None and depth < 10:
                nid = getattr(node, "id", "") or node.__class__.__name__
                if nid in known or nid.endswith("TaskTable") or nid.endswith("NoteTable"):
                    return nid
                node = getattr(node, "parent", None)
                depth += 1
        except Exception:
            pass
        return fid

    def _build_text(self) -> str:
        app = self.app
        focused = app.focused
        focus_id = self._logical_focus_id(focused)

        unicode_ok = bool(USE_UNICODE and not IS_WINDOWS)
        bullet = " • " if unicode_ok else " | "

        # Line 1: global/navigation
        line1 = bullet.join(["m:mode", "v:view", "n/p", "Ctrl+/:toggle", "/:cmd", "?:ai", "q:quit"])

        # Line 2: context actions
        if focus_id in ("task_table",) or str(focus_id).endswith("TaskTable"):
            ctx = [
                "Enter open",
                "e edit",
                "x/u done/undone",
                "d del",
                "s sort",
                "f filter",
                "Shift+N quick",
                "Ctrl+N note",
            ]
        elif focus_id in ("note_table",) or str(focus_id).endswith("NoteTable"):
            ctx = [
                "Enter open",
                "e edit",
                "Shift+N quick",
                "Ctrl+N new",
                "Ctrl+L/Ctrl+U link/unlink",
                "Ctrl+D dup",
                "Del del",
                "/ notes clear",
            ]
        elif focus_id in ("ai_chat_panel",) or str(focus_id).endswith("AIChatPanel"):
            ctx = [
                "? ask",
                "Ctrl+A toggle",
                "Ctrl+Shift+C clear",
                "Ctrl+Shift+Y copy",
                "Up/Down scroll",
            ]
        elif focus_id in ("ai_input",) or str(focus_id).endswith("AIInput"):
            ctx = [
                "Enter send",
                "Up/Down history",
                "Esc cancel",
            ]
        elif focus_id in ("command_input",) or str(focus_id).endswith("CommandInput"):
            ctx = [
                "Enter run",
                "Tab complete",
                "Esc clear",
            ]
        else:
            ctx = ["Tab:focus next", "Shift+Tab:focus prev"]

        line2 = bullet.join(ctx)

        # Add explicit hint when command bar is hidden
        try:
            from textual_widgets.command_input import CommandInput  # type: ignore

            cmd = app.query_one(CommandInput)
            if not getattr(cmd, "display", True) and not (
                focus_id in ("command_input",) or str(focus_id).endswith("CommandInput")
            ):
                line2 += bullet + "[dim]Press / for command bar[/dim]"
        except Exception:
            pass

        return f"{line1}\n{line2}"

    def update_from_state(self) -> None:
        self.update(self._build_text())


