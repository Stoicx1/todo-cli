from __future__ import annotations

from typing import Optional, List, Dict
from dataclasses import asdict
from pathlib import Path
from enum import Enum
import json

from typing import Any

from models.task import Task
from models.note import Note
from models.ai_message import AIMessage
from utils.tag_parser import parse_tags, normalize_tag
from core.file_safety import (
    SafeFileManager,
    FileLockTimeoutError,
    FileCorruptionError,
)
from config import ui, performance, USE_UNICODE, DEFAULT_SETTINGS_FILE


# AI Conversation limits
MAX_CONVERSATION_MESSAGES = 100


class LeftPanelMode(Enum):
    """Left panel view modes for dynamic content switching"""
    LIST_TASKS = "list_tasks"
    DETAIL_TASK = "detail_task"
    EDIT_TASK = "edit_task"
    LIST_NOTES = "list_notes"
    DETAIL_NOTE = "detail_note"
    EDIT_NOTE = "edit_note"


class AppState:
    def __init__(self):
        # Tasks and basics
        self.tasks: List[Task] = []
        self.next_id: int = 1
        self.page: int = 0
        self.page_size: int = 5
        self.view_mode: str = "compact"
        self.messages: List[str] = []
        self.filter: str = "none"
        self.sort: str = "priority"
        self.sort_order: str = "asc"  # 'asc' or 'desc'

        # Notes & mode
        self.notes: List[Note] = []
        self.entity_mode: str = "tasks"  # tasks | notes
        self._note_index: Dict[str, Note] = {}
        self._notes_by_task: Dict[int, List[str]] = {}
        self.selected_task_id: int | None = None
        self.selected_note_id: str | None = None  # NEW - for panel system
        self.notes_query: str = ""
        self.notes_task_id_filter: int | None = None

        # Left panel state (NEW - for vim-style panel switching)
        self.left_panel_mode: LeftPanelMode = LeftPanelMode.LIST_TASKS
        self.edit_mode_is_new: bool = False  # Tracks create vs edit in EDIT modes

        # AI panel state (for live output rendering in Rich UI)
        self.ai_text: str = ""
        self.ai_scroll: int = 0
        self.ai_streaming: bool = False

        # Conversation state and file manager
        self.ai_conversation: List[AIMessage] = []
        self._ai_file_manager: Optional[SafeFileManager] = None

        # Indices
        self._task_index: Optional[Dict[int, Task]] = (
            {} if performance.USE_TASK_INDEX else None
        )
        self._tag_index: Dict[str, List[Task]] = {}

        # File manager for tasks
        self._file_manager: Optional[SafeFileManager] = None

        # Filter cache
        self._filtered_tasks_cache: Optional[List[Task]] = None
        self._filter_cache_dirty: bool = True
        self._current_filter: str = "none"

        # Data integrity tracking
        self._last_saved_count: int = 0

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------
    def add_task(self, name: str, comment: str, description: str, priority: int, tag: str):
        tag_list = parse_tags(tag, warn_callback=lambda msg: print(f"Warning: {msg}"))
        task = Task(
            id=self.next_id,
            name=(name or "").strip(),
            comment=(comment or "").strip(),
            description=(description or "").strip(),
            priority=priority,
            tag=tag_list[0] if tag_list else "",
            tags=tag_list,
        )
        self.tasks.append(task)

        if self._task_index is not None:
            self._task_index[task.id] = task

        for t in task.tags:
            self._tag_index.setdefault(t, []).append(task)

        self.next_id += 1
        self.invalidate_filter_cache()

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        if self._task_index is not None:
            return self._task_index.get(task_id)
        return next((t for t in self.tasks if t.id == task_id), None)

    def remove_task(self, task: Task):
        self.tasks.remove(task)
        if self._task_index is not None and task.id in self._task_index:
            del self._task_index[task.id]
        for t in list(task.tags):
            if t in self._tag_index and task in self._tag_index[t]:
                self._tag_index[t].remove(task)
                if not self._tag_index[t]:
                    del self._tag_index[t]
        self.invalidate_filter_cache()

    def _rebuild_index(self) -> None:
        if self._task_index is not None:
            self._task_index = {task.id: task for task in self.tasks}

    def _rebuild_tag_index(self) -> None:
        self._tag_index = {}
        for task in self.tasks:
            for t in task.tags:
                self._tag_index.setdefault(t, []).append(task)

    def _update_tag_index_for_task(self, task: Task, old_tags: Optional[List[str]] = None) -> None:
        if old_tags:
            for t in old_tags:
                if t in self._tag_index and task in self._tag_index[t]:
                    self._tag_index[t].remove(task)
                    if not self._tag_index[t]:
                        del self._tag_index[t]
        for t in task.tags:
            if task not in self._tag_index.setdefault(t, []):
                self._tag_index[t].append(task)

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        return self._tag_index.get(normalize_tag(tag), [])

    def get_all_tags_with_stats(self) -> Dict[str, Dict[str, int]]:
        stats: Dict[str, Dict[str, int]] = {}
        for t, tasks in self._tag_index.items():
            done = sum(1 for x in tasks if x.done)
            total = len(tasks)
            stats[t] = {"done": done, "total": total, "pending": total - done}
        return stats

    # ------------------------------------------------------------------
    # Filtering / Sorting / Paging
    # ------------------------------------------------------------------
    def get_filter_tasks(self, tasks: List[Task]) -> List[Task]:
        from utils.filter_parser import parse_filter_expression, matches_all_conditions

        filter_value = (self.filter or "").strip()
        if not filter_value or filter_value.lower() == "none":
            return tasks

        conditions = parse_filter_expression(filter_value)
        if not conditions:
            return tasks
        return [t for t in tasks if matches_all_conditions(t, conditions)]

    @property
    def filtered_tasks(self) -> List[Task]:
        filter_changed = self._current_filter != self.filter
        if filter_changed:
            self._current_filter = self.filter
            self._filter_cache_dirty = True

        if not self._filter_cache_dirty and self._filtered_tasks_cache is not None:
            return self._filtered_tasks_cache

        filtered = self.get_filter_tasks(self.tasks)
        self._filtered_tasks_cache = filtered
        self._filter_cache_dirty = False
        return filtered

    def invalidate_filter_cache(self) -> None:
        self._filter_cache_dirty = True

    def get_sorted_tasks(self, tasks: List[Task]) -> List[Task]:
        reverse = (self.sort_order == "desc")

        if self.sort == "priority":
            return sorted(tasks, key=lambda t: t.priority, reverse=reverse)
        if self.sort == "id":
            return sorted(tasks, key=lambda t: t.id, reverse=reverse)
        if self.sort == "name":
            return sorted(tasks, key=lambda t: (t.name or "").casefold(), reverse=reverse)
        if self.sort == "age":
            from utils.time import age_seconds

            def key_age(t: Task):
                a = age_seconds(getattr(t, "created_at", ""))
                return a if a is not None else 10 ** 12

            # asc => youngest first (smaller age seconds first)
            reverse_flag = (self.sort_order == "desc")
            return sorted(tasks, key=key_age, reverse=reverse_flag)
        return tasks

    def get_current_page_tasks(self) -> List[Task]:
        # Page size from config based on view mode
        self.page_size = ui.COMPACT_PAGE_SIZE if self.view_mode == "compact" else ui.DETAIL_PAGE_SIZE
        show_tasks = self.filtered_tasks
        show_tasks = self.get_sorted_tasks(show_tasks)
        start = self.page * self.page_size
        end = start + self.page_size
        return show_tasks[start:end]

    # ------------------------------------------------------------------
    # Persistence (tasks)
    # ------------------------------------------------------------------
    def _console_print(self, console: Any | None, message: str) -> None:
        try:
            if console is None:
                return
            if hasattr(console, "print"):
                console.print(message)
            else:
                # Fallback to stdout
                print(message)
        except Exception:
            pass

    def save_to_file(self, filename: str, console: Any | None = None):
        """Save all tasks with atomic write and backups, including safety guards."""
        if self._file_manager is None:
            self._file_manager = SafeFileManager(
                filename, lock_timeout=5.0, backup_count=3, console=console
            )

        try:
            from debug_logger import debug_log

            # Pre-save logging
            try:
                import threading as _t

                thread_name = _t.current_thread().name
            except Exception:
                thread_name = "unknown"
            debug_log.info(
                f"[STATE] save_to_file() - Saving {len(self.tasks)} tasks to {filename} [thread={thread_name}]"
            )
            if self.tasks:
                task_ids = sorted([t.id for t in self.tasks])
                debug_log.debug(f"[STATE] Task IDs being saved: {task_ids}")
            else:
                debug_log.warning("[STATE] WARNING: Saving empty task list!")
                if self._last_saved_count > 0:
                    warning_mark = "⚠" if USE_UNICODE else "!"
                    self._console_print(
                        console,
                        f"[red]{warning_mark} CRITICAL: Refusing to overwrite existing tasks with empty list (previous: {self._last_saved_count}).",
                    )
                    return

            current_count = len(self.tasks)

            if current_count == 0 and self._last_saved_count > 0:
                debug_log.error(
                    f"[STATE] CRITICAL: Attempting to save 0 tasks (previous: {self._last_saved_count})"
                )
                warning_mark = "⚠" if USE_UNICODE else "!"
                self._console_print(
                    console,
                    f"[red]{warning_mark} CRITICAL: Attempting to delete ALL {self._last_saved_count} tasks! Check backup files.[/red]",
                )
                return
            elif current_count < self._last_saved_count * 0.5 and self._last_saved_count > 5:
                debug_log.warning(
                    f"[STATE] WARNING: Task count dropped {self._last_saved_count} -> {current_count}"
                )
                warning_mark = "⚠" if USE_UNICODE else "!"
                self._console_print(
                    console,
                    f"[yellow]{warning_mark} Warning: Task count dropped from {self._last_saved_count} to {current_count}[/yellow]",
                )

            tasks_data = [asdict(task) for task in self.tasks]
            self._file_manager.save_json_with_lock(tasks_data, indent=performance.JSON_INDENT)

            debug_log.info(f"[STATE] Save successful - {len(self.tasks)} tasks written")
            check_mark = "✓" if USE_UNICODE else "+"
            self._console_print(console, f"[green]{check_mark}[/green] Tasks saved to [bold]{filename}[/bold]")

            self._last_saved_count = current_count
            self._save_preferences()

        except FileLockTimeoutError as e:
            x_mark = "✗" if USE_UNICODE else "X"
            bulb = "💡" if USE_UNICODE else "!"
            self._console_print(console, f"[red]{x_mark}[/red] {e}")
            self._console_print(console, f"[yellow]{bulb} Close other instances and try again[/yellow]")
        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            self._console_print(console, f"[red]{x_mark}[/red] Failed to save tasks: {e}")

    def load_from_file(self, filename: str, console: Console):
        """Load tasks with recovery from backups and rebuild indices/preferences."""
        if self._file_manager is None:
            self._file_manager = SafeFileManager(
                filename, lock_timeout=5.0, backup_count=3, console=console
            )

        try:
            tasks_data = self._file_manager.load_json_with_lock()
            self.tasks = [Task(**t) for t in tasks_data]
            self.next_id = max((t.id for t in self.tasks), default=0) + 1
            self._rebuild_index()
            self._rebuild_tag_index()
            self._load_preferences()

            check_mark = "✓" if USE_UNICODE else "+"
            console.print(f"[green]{check_mark}[/green] Tasks loaded from [bold]{filename}[/bold]")

            # Load notes from filesystem
            try:
                from services.notes import FileNoteRepository
                from config import DEFAULT_NOTES_DIR
                repo = FileNoteRepository(DEFAULT_NOTES_DIR)
                self.notes = repo.list_all()
                self._rebuild_note_indexes()
            except Exception:
                self.notes = []
                self._note_index = {}
                self._notes_by_task = {}

        except FileNotFoundError:
            info_mark = "ℹ" if USE_UNICODE else "i"
            console.print(f"[yellow]{info_mark}[/yellow] No saved tasks found. Starting fresh.")
            self.tasks = []
            self.next_id = 1
            self._load_preferences()
            # Initialize notes directory if missing
            try:
                from services.notes import FileNoteRepository
                from config import DEFAULT_NOTES_DIR
                repo = FileNoteRepository(DEFAULT_NOTES_DIR)
                self.notes = repo.list_all()
                self._rebuild_note_indexes()
            except Exception:
                self.notes = []
        except FileCorruptionError:
            x_mark = "✗" if USE_UNICODE else "X"
            bulb = "💡" if USE_UNICODE else "!"
            console.print(f"[red]{x_mark}[/red] All files corrupted and no valid backups!")
            console.print(f"[yellow]{bulb} Check .backup files manually in the directory[/yellow]")
            self.tasks = []
            self.next_id = 1
            self._load_preferences()
            self.notes = []
            self._note_index = {}
            self._notes_by_task = {}
        except FileLockTimeoutError as e:
            warning = "⚠" if USE_UNICODE else "!"
            bulb = "💡" if USE_UNICODE else "!"
            console.print(f"[yellow]{warning}[/yellow] {e}")
            console.print(f"[yellow]{bulb} Waiting for other instance to finish...[/yellow]")
            self.tasks = []
            self.next_id = 1
            self._load_preferences()
            self.notes = []
            self._note_index = {}
            self._notes_by_task = {}

    # ------------------------------------------------------------------
    # Notes indexing & queries
    # ------------------------------------------------------------------
    def _rebuild_note_indexes(self) -> None:
        self._note_index = {n.id: n for n in self.notes}
        by_task: Dict[int, List[str]] = {}
        for n in self.notes:
            for tid in n.task_ids:
                by_task.setdefault(tid, []).append(n.id)
        self._notes_by_task = by_task

    def get_notes_for_task(self, task_id: int) -> List[Note]:
        ids = self._notes_by_task.get(task_id, [])
        return [self._note_index[i] for i in ids if i in self._note_index]

    def refresh_notes_from_disk(self) -> None:
        try:
            from services.notes import FileNoteRepository
            from config import DEFAULT_NOTES_DIR
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            notes = repo.list_all()
            self.notes = notes
            self._rebuild_note_indexes()
            try:
                from debug_logger import debug_log
                debug_log.info(f"[STATE] Notes refreshed from disk - {len(notes)} notes")
                if notes:
                    sample = ", ".join((n.title or 'Untitled')[:24] for n in notes[:5])
                    debug_log.debug(f"[STATE] Note sample: {sample}")
            except Exception:
                pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def _save_preferences(self) -> None:
        try:
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            # Merge with existing settings to preserve unrelated keys (e.g., theme)
            existing: dict = {}
            try:
                if settings_path.exists():
                    existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            data = {
                "sort": getattr(self, "sort", "priority"),
                "sort_order": getattr(self, "sort_order", "asc"),
                "view_mode": getattr(self, "view_mode", "compact"),
                "filter": getattr(self, "filter", "none"),
            }
            merged = {**existing, **data}
            tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
            tmp.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            try:
                import os as _os

                _os.replace(tmp, settings_path)
            except Exception:
                settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_preferences(self) -> None:
        try:
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                sort = data.get("sort")
                sort_order = data.get("sort_order")
                view_mode = data.get("view_mode")
                filter_value = data.get("filter")
                if sort in ("priority", "id", "name", "age"):
                    self.sort = sort
                if sort_order in ("asc", "desc"):
                    self.sort_order = sort_order
                if view_mode in ("compact", "detail"):
                    self.view_mode = view_mode
                if isinstance(filter_value, str) and filter_value:
                    self.filter = filter_value
        except Exception:
            pass

    # ------------------------------------------------------------------
    # AI Conversation
    # ------------------------------------------------------------------
    def add_ai_message(self, role: str, content: str) -> AIMessage:
        message = AIMessage(role=role, content=content)
        self.ai_conversation.append(message)
        if len(self.ai_conversation) > MAX_CONVERSATION_MESSAGES:
            over = len(self.ai_conversation) - MAX_CONVERSATION_MESSAGES
            self.ai_conversation = self.ai_conversation[over:]
        return message

    def clear_conversation(self) -> None:
        self.ai_conversation = []

    def get_conversation_context(self, max_messages: int = 20) -> List[dict]:
        recent = self.ai_conversation[-max_messages:]
        return [m.get_openai_format() for m in recent]

    def get_total_tokens(self) -> int:
        return sum(m.token_count for m in self.ai_conversation)

    def save_conversation_to_file(self, filename: str, console: Console) -> None:
        if self._ai_file_manager is None:
            self._ai_file_manager = SafeFileManager(
                filename, lock_timeout=5.0, backup_count=3, console=console
            )
        try:
            data = [m.to_dict() for m in self.ai_conversation]
            self._ai_file_manager.save_json_with_lock(data, indent=2)
            check_mark = "✓" if USE_UNICODE else "+"
            console.print(f"[green]{check_mark}[/green] Conversation saved to [bold]{filename}[/bold]")
        except FileLockTimeoutError as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] {e}")
        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] Failed to save conversation: {e}")

    def load_conversation_from_file(self, filename: str, console: Console) -> None:
        if self._ai_file_manager is None:
            self._ai_file_manager = SafeFileManager(
                filename, lock_timeout=5.0, backup_count=3, console=console
            )
        try:
            data = self._ai_file_manager.load_json_with_lock()
            self.ai_conversation = [AIMessage.from_dict(m) for m in data]
            check_mark = "✓" if USE_UNICODE else "+"
            console.print(
                f"[green]{check_mark}[/green] Conversation loaded from [bold]{filename}[/bold] ({len(self.ai_conversation)} messages)"
            )
        except FileNotFoundError:
            info_mark = "ℹ" if USE_UNICODE else "i"
            console.print(f"[yellow]{info_mark}[/yellow] No saved conversation found. Starting fresh.")
            self.ai_conversation = []
        except FileCorruptionError:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] Conversation file corrupted. Starting fresh.")
            self.ai_conversation = []
        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] Error loading conversation: {e}. Starting fresh.")
            self.ai_conversation = []

# --- Runtime overrides for output glyphs and save/load to avoid mojibake ---
# Some environments produced corrupted glyphs in string literals. The following
# overrides replace any problematic implementations with clean, safe versions.

def _appstate_save_to_file_clean(self, filename: str, console: Console | None):
    if self._file_manager is None:
        self._file_manager = SafeFileManager(
            filename, lock_timeout=5.0, backup_count=3, console=console
        )
    try:
        from debug_logger import debug_log as _dl
        try:
            import threading as _t
            thr = _t.current_thread().name
        except Exception:
            thr = "unknown"
        _dl.info(
            f"[STATE] save_to_file() - Saving {len(self.tasks)} tasks to {filename} [thread={thr}]"
        )
        current_count = len(self.tasks)
        if not self.tasks and getattr(self, "_last_saved_count", 0) > 0:
            warn = "⚠" if USE_UNICODE else "!"
            if console:
                console.print(
                    f"[red]{warn} CRITICAL: Refusing to overwrite existing tasks with empty list (previous: {self._last_saved_count})."
                )
            return
        if current_count == 0 and getattr(self, "_last_saved_count", 0) > 0:
            warn = "⚠" if USE_UNICODE else "!"
            if console:
                console.print(
                    f"[red]{warn} CRITICAL: Attempting to delete ALL {self._last_saved_count} tasks! Check backup files.[/red]"
                )
            return
        tasks_data = [asdict(task) for task in self.tasks]
        self._file_manager.save_json_with_lock(tasks_data, indent=performance.JSON_INDENT)
        _dl.info(f"[STATE] Save successful - {len(self.tasks)} tasks written")
        check = "✓" if USE_UNICODE else "+"
        if console:
            console.print(f"[green]{check}[/green] Tasks saved to [bold]{filename}[/bold]")
        self._last_saved_count = current_count
        self._save_preferences()
    except FileLockTimeoutError as e:
        x = "✗" if USE_UNICODE else "X"
        bulb = "💡" if USE_UNICODE else "!"
        if console:
            console.print(f"[red]{x}[/red] {e}")
            console.print(f"[yellow]{bulb} Close other instances and try again[/yellow]")
    except Exception as e:
        x = "✗" if USE_UNICODE else "X"
        if console:
            console.print(f"[red]{x}[/red] Failed to save tasks: {e}")


def _appstate_load_from_file_clean(self, filename: str, console: Console):
    if self._file_manager is None:
        self._file_manager = SafeFileManager(
            filename, lock_timeout=5.0, backup_count=3, console=console
        )
    try:
        tasks_data = self._file_manager.load_json_with_lock()
        self.tasks = [Task(**t) for t in tasks_data]
        self.next_id = max((t.id for t in self.tasks), default=0) + 1
        self._rebuild_index()
        self._rebuild_tag_index()
        self._load_preferences()
        check = "✓" if USE_UNICODE else "+"
        console.print(f"[green]{check}[/green] Tasks loaded from [bold]{filename}[/bold]")
        try:
            from services.notes import FileNoteRepository
            from config import DEFAULT_NOTES_DIR
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            self.notes = repo.list_all()
            self._rebuild_note_indexes()
        except Exception:
            self.notes = []
            self._note_index = {}
    except FileNotFoundError:
        info = "ℹ" if USE_UNICODE else "i"
        console.print(f"[yellow]{info}[/yellow] No saved tasks found. Starting fresh.")
        self.tasks = []
        self.next_id = 1
    except FileCorruptionError:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] All files corrupted and no valid backups!")
        self.tasks = []
        self.next_id = 1
    except Exception as e:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] Error loading tasks: {e}")
        self.tasks = []
        self.next_id = 1


def _appstate_save_conversation_clean(self, filename: str, console: Console) -> None:
    if self._ai_file_manager is None:
        self._ai_file_manager = SafeFileManager(
            filename, lock_timeout=5.0, backup_count=3, console=console
        )
    try:
        data = [m.to_dict() for m in self.ai_conversation]
        self._ai_file_manager.save_json_with_lock(data, indent=2)
        check = "✓" if USE_UNICODE else "+"
        console.print(f"[green]{check}[/green] Conversation saved to [bold]{filename}[/bold]")
    except FileLockTimeoutError as e:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] {e}")
    except Exception as e:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] Failed to save conversation: {e}")


def _appstate_load_conversation_clean(self, filename: str, console: Console) -> None:
    if self._ai_file_manager is None:
        self._ai_file_manager = SafeFileManager(
            filename, lock_timeout=5.0, backup_count=3, console=console
        )
    try:
        data = self._ai_file_manager.load_json_with_lock()
        self.ai_conversation = [AIMessage.from_dict(m) for m in data]
        check = "✓" if USE_UNICODE else "+"
        console.print(
            f"[green]{check}[/green] Conversation loaded from [bold]{filename}[/bold] ({len(self.ai_conversation)} messages)"
        )
    except FileNotFoundError:
        info = "ℹ" if USE_UNICODE else "i"
        console.print(f"[yellow]{info}[/yellow] No saved conversation found. Starting fresh.")
        self.ai_conversation = []
    except FileCorruptionError:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] Conversation file corrupted. Starting fresh.")
        self.ai_conversation = []
    except Exception as e:
        x = "✗" if USE_UNICODE else "X"
        console.print(f"[red]{x}[/red] Error loading conversation: {e}. Starting fresh.")
        self.ai_conversation = []


# Apply overrides (last definition wins)
try:
    AppState.save_to_file = _appstate_save_to_file_clean  # type: ignore[attr-defined]
    AppState.load_from_file = _appstate_load_from_file_clean  # type: ignore[attr-defined]
    AppState.save_conversation_to_file = _appstate_save_conversation_clean  # type: ignore[attr-defined]
    AppState.load_conversation_from_file = _appstate_load_conversation_clean  # type: ignore[attr-defined]
except Exception:
    pass

