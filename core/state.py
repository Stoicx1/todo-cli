from typing import Optional, List
from dataclasses import asdict
from models.task import Task
from models.ai_message import AIMessage
from rich.console import Console
from config import ui, performance, USE_UNICODE, DEFAULT_SETTINGS_FILE
from pathlib import Path
import json
from utils.tag_parser import parse_tags
from core.file_safety import SafeFileManager, FileLockTimeoutError, FileCorruptionError

# AI Conversation limits
MAX_CONVERSATION_MESSAGES = 100  # Maximum messages to keep in conversation history


class AppState:
    def __init__(self):
        """
        Initialize the application state for the task manager.
        """
        self.tasks: list[Task] = []  # All tasks in memory
        self.next_id: int = 1  # Auto-incrementing task ID
        self.page: int = 0  # Current page number
        self.page_size: int = 5  # Number of tasks per page
        self.view_mode: str = "compact"  # View mode: 'compact' or 'detailed'
        self.messages: list[str] = []  # Messages to display to the user
        self.filter: str = "none"  # Active task filter
        self.sort: str = "priority"  # Active sort method
        self.sort_order: str = "asc"  # Sort order: 'asc' or 'desc'

        # AI panel state (for live, scrollable assistant output)
        self.ai_text: str = ""          # Full streamed AI content
        self.ai_scroll: int = 0          # Lines scrolled back from bottom
        self.ai_streaming: bool = False  # Whether AI is currently streaming

        # AI conversation history (NEW! - Phase 2.1)
        self.ai_conversation: List[AIMessage] = []  # Full conversation history
        self._ai_file_manager: Optional[SafeFileManager] = None  # For conversation persistence

        # Task index for O(1) lookups (performance optimization)
        self._task_index: dict[int, Task] = {} if performance.USE_TASK_INDEX else None

        # Tag index for O(1) tag lookups (NEW! - Phase 2.1)
        self._tag_index: dict[str, list[Task]] = {}

        # File safety manager (initialized on first save/load)
        self._file_manager: Optional[SafeFileManager] = None

        # Filtered task cache (performance optimization with dirty flag)
        # Dirty flag approach: O(1) check instead of O(n) tuple generation
        self._filtered_tasks_cache: Optional[list[Task]] = None
        self._filter_cache_dirty: bool = True  # True = needs recalculation
        self._current_filter: str = "none"  # Track filter changes

        # Data integrity tracking (for detecting catastrophic data loss)
        self._last_saved_count: int = 0  # Track task count for validation

    def add_task(
        self, name: str, comment: str, description: str, priority: int, tag: str
    ):
        """
        Add a new task to the task list.

        Args:
            name (str): The title or name of the task.
            comment (str): A short comment or note.
            description (str): A more detailed task description.
            priority (int): Task priority (lower = higher priority).
            tag (str): A label/tag to categorize the task.
                      Can be comma-separated for multiple tags (up to 3).
                      Example: "backend, api, urgent"
        """
        # Parse tags using centralized utility (DRY)
        # Note: No console here, so warnings go to stdout
        tag_list = parse_tags(
            tag,
            warn_callback=lambda msg: print(f"Warning: {msg}")
        )

        task = Task(
            id=self.next_id,
            name=name.strip(),
            comment=comment.strip(),
            description=description.strip(),
            priority=priority,
            tag=tag_list[0] if tag_list else "",  # Legacy field (first tag)
            tags=tag_list  # New field (list of tags)
        )
        self.tasks.append(task)

        # Update task index for O(1) lookups
        if self._task_index is not None:
            self._task_index[task.id] = task

        # Update tag index for O(1) tag lookups (NEW! - Phase 2.1)
        for tag in task.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(task)

        self.next_id += 1

        # Invalidate filter cache after adding task (CRITICAL FIX)
        self.invalidate_filter_cache()

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """
        Get task by ID with O(1) lookup (if index enabled).

        Args:
            task_id: Task ID to find

        Returns:
            Task object if found, None otherwise
        """
        if self._task_index is not None:
            # O(1) dictionary lookup - fast even for 10,000+ tasks
            return self._task_index.get(task_id)
        else:
            # O(n) fallback (for compatibility if index disabled)
            return next((t for t in self.tasks if t.id == task_id), None)

    def remove_task(self, task: Task):
        """
        Remove task from list and update indices.

        Args:
            task: Task object to remove
        """
        self.tasks.remove(task)

        # Update task index
        if self._task_index is not None and task.id in self._task_index:
            del self._task_index[task.id]

        # Update tag index (NEW! - Phase 2.1)
        for tag in task.tags:
            if tag in self._tag_index:
                self._tag_index[tag].remove(task)
                # Clean up empty tag lists
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

    def _rebuild_index(self):
        """
        Rebuild task index from task list.
        Called after loading tasks from file.
        """
        if self._task_index is not None:
            self._task_index = {task.id: task for task in self.tasks}

    def _rebuild_tag_index(self):
        """
        Rebuild tag index from task list.
        Called after loading tasks or when tags change.

        Creates mapping: {tag: [task1, task2, ...]}
        Allows O(1) lookup of all tasks with a given tag.
        """
        self._tag_index = {}
        for task in self.tasks:
            for tag in task.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(task)

    def get_tasks_by_tag(self, tag: str) -> list[Task]:
        """
        Get all tasks with a specific tag - O(1) lookup.

        Args:
            tag: Tag to search for (will be normalized)

        Returns:
            List of tasks with that tag
        """
        from utils.tag_parser import normalize_tag
        tag = normalize_tag(tag)
        return self._tag_index.get(tag, [])

    def get_all_tags_with_stats(self) -> dict[str, dict[str, int]]:
        """
        Get all tags with statistics - single O(1) operation.

        Returns:
            Dictionary: {tag: {'done': 5, 'total': 10, 'pending': 5}}
        """
        stats = {}
        for tag, tasks in self._tag_index.items():
            done = sum(1 for t in tasks if t.done)
            total = len(tasks)
            stats[tag] = {
                'done': done,
                'total': total,
                'pending': total - done
            }
        return stats

    def _update_tag_index_for_task(self, task: Task, old_tags: list[str] = None):
        """
        Update tag index when task tags change.

        Args:
            task: Task with updated tags
            old_tags: Previous tags (if task was edited)
        """
        # Remove from old tags
        if old_tags:
            for tag in old_tags:
                if tag in self._tag_index and task in self._tag_index[tag]:
                    self._tag_index[tag].remove(task)
                    # Clean up empty tag lists
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]

        # Add to new tags
        for tag in task.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if task not in self._tag_index[tag]:
                self._tag_index[tag].append(task)

    def get_filter_tasks(self, tasks):
        """
        Filters the task list based on the current filter value.

        Supports advanced filtering with operators:
            - Single conditions: status=done, priority=1, tag=psdc
            - Operators: =, !=, >=, <=
            - Compound filters: status=done tag=psdc (space = AND)
            - Multi-value: priority=1,2 (comma = OR)
            - Multi-tag logic: tag=psdc+webasto (+ = AND), tag=psdc,webasto (, = OR)

        Legacy syntax still supported:
            - "done", "undone", "tag:name"

        Args:
            tasks (list): The list of Task objects to filter.

        Returns:
            list: A filtered list of tasks based on the current filter.

        Examples:
            status=done              → Completed tasks
            priority>=2              → Medium or low priority
            status=undone tag=psdc   → Incomplete tasks tagged "psdc"
            tag=psdc+webasto         → Tasks with both tags
        """
        from utils.filter_parser import parse_filter_expression, matches_all_conditions

        filter_value = self.filter.strip()

        if not filter_value or filter_value.lower() == "none":
            return tasks

        # Parse filter expression into conditions
        conditions = parse_filter_expression(filter_value)

        if not conditions:
            return tasks

        # Apply all conditions (AND logic)
        return [t for t in tasks if matches_all_conditions(t, conditions)]

    @property
    def filtered_tasks(self) -> list[Task]:
        """
        Get filtered tasks with caching for performance.

        Cache is invalidated when:
        - Task list changes (add/remove/edit)
        - Filter changes
        - Task done status changes

        Returns:
            Filtered list of tasks based on current filter

        Performance: O(1) dirty flag check vs O(n) tuple generation
        """
        # Check if filter setting changed (requires recalculation)
        filter_changed = self._current_filter != self.filter
        if filter_changed:
            self._current_filter = self.filter
            self._filter_cache_dirty = True

        # Return cached result if still valid (dirty flag = False)
        if not self._filter_cache_dirty and self._filtered_tasks_cache is not None:
            return self._filtered_tasks_cache

        # Cache miss or dirty - recalculate
        filtered = self.get_filter_tasks(self.tasks)

        # Update cache and mark as clean
        self._filtered_tasks_cache = filtered
        self._filter_cache_dirty = False

        return filtered

    def invalidate_filter_cache(self) -> None:
        """
        Mark filter cache as dirty for recalculation.
        Called when tasks are modified (add/remove/edit/done/undone).

        Performance: O(1) flag set vs O(n) tuple comparison
        """
        self._filter_cache_dirty = True

    def get_sorted_tasks(self, tasks):
        """
        Sorts the task list based on the current sort setting.

        Supported sort options:
            - "priority": Sort by task priority (ascending).
            - "id":       Sort by task ID (ascending).
            - "name":     Sort alphabetically by task name.

        Args:
            tasks (list): The list of Task objects to sort.

        Returns:
            list: A sorted list of tasks.
        """
        reverse = (self.sort_order == "desc")

        if self.sort == "priority":
            return sorted(tasks, key=lambda t: t.priority, reverse=reverse)
        if self.sort == "id":
            return sorted(tasks, key=lambda t: t.id, reverse=reverse)
        if self.sort == "name":
            # Case-insensitive sort for better UX
            return sorted(tasks, key=lambda t: (t.name or "").casefold(), reverse=reverse)
        return tasks  # Fallback: return unsorted if sort option is unknown

    def get_current_page_tasks(self):
        """
        Applies filtering, sorting, and pagination to the task list
        and returns only the tasks for the current page.

        Returns:
            list: A list of tasks to be displayed on the current page.
        """
        # Set page size dynamically based on view mode (from config)
        self.page_size = ui.COMPACT_PAGE_SIZE if self.view_mode == "compact" else ui.DETAIL_PAGE_SIZE

        # Step 1: Filter tasks (uses cache for performance)
        show_tasks = self.filtered_tasks

        # Step 2: Sort tasks
        show_tasks = self.get_sorted_tasks(show_tasks)

        # Step 3: Paginate tasks
        start = self.page * self.page_size
        end = start + self.page_size
        return show_tasks[start:end]

    def save_to_file(self, filename: str, console: Console):
        """
        Save all tasks to a JSON file with file safety protection.

        Features:
        - File locking (prevents concurrent writes)
        - Atomic writes (prevents partial write corruption)
        - Automatic backups (creates backup before saving)

        Args:
            filename (str): The name of the file to save tasks to.
            console (Console): Rich console for output messages.
        """
        # Initialize file manager on first use
        if self._file_manager is None:
            self._file_manager = SafeFileManager(
                filename,
                lock_timeout=5.0,
                backup_count=3,
                console=console
            )

        try:
            # Debug logging BEFORE save (critical for detecting data loss)
            from debug_logger import debug_log
            debug_log.info(f"[STATE] save_to_file() - Saving {len(self.tasks)} tasks to {filename}")
            if self.tasks:
                task_ids = sorted([t.id for t in self.tasks])
                debug_log.debug(f"[STATE] Task IDs being saved: {task_ids}")
            else:
                debug_log.warning("[STATE] WARNING: Saving empty task list!")

            # Data integrity validation (safety net against data loss)
            # Compare to last known state instead of arbitrary threshold
            current_count = len(self.tasks)

            # CRITICAL: Attempting to save empty list when tasks existed
            if current_count == 0 and self._last_saved_count > 0:
                debug_log.error(
                    f"[STATE] CRITICAL: Attempting to save 0 tasks (previous: {self._last_saved_count})"
                )
                warning_mark = "⚠" if USE_UNICODE else "!"
                console.print(
                    f"[red]{warning_mark} CRITICAL: Attempting to delete ALL {self._last_saved_count} tasks! "
                    f"Check backup files.[/red]"
                )

            # MAJOR: Task count dropped by >50%
            elif current_count < self._last_saved_count * 0.5 and self._last_saved_count > 5:
                debug_log.warning(
                    f"[STATE] WARNING: Task count dropped {self._last_saved_count} → {current_count}"
                )
                warning_mark = "⚠" if USE_UNICODE else "!"
                console.print(
                    f"[yellow]{warning_mark} Warning: Task count dropped from {self._last_saved_count} to {current_count}[/yellow]"
                )

            # Serialize tasks to dictionary format using asdict() (more efficient than __dict__)
            tasks_data = [asdict(task) for task in self.tasks]

            # Save with file locking, atomic writes, and backup
            # Uses configurable indent from config (None for production = 66% smaller files)
            self._file_manager.save_json_with_lock(
                tasks_data,
                indent=performance.JSON_INDENT
            )

            debug_log.info(f"[STATE] Save successful - {len(self.tasks)} tasks written")
            check_mark = "✓" if USE_UNICODE else "+"
            console.print(f"[green]{check_mark}[/green] Tasks saved to [bold]{filename}[/bold]")

            # Update last saved count for next validation
            self._last_saved_count = current_count

            # Persist preferences (best-effort)
            self._save_preferences()

        except FileLockTimeoutError as e:
            x_mark = "✗" if USE_UNICODE else "X"
            bulb = "💡" if USE_UNICODE else "!"
            console.print(f"[red]{x_mark}[/red] {e}")
            console.print(
                f"[yellow]{bulb} Close other instances and try again[/yellow]"
            )

        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] Failed to save tasks: {e}")

    def load_from_file(self, filename: str, console: Console):
        """
        Load tasks from a JSON file with automatic backup recovery.

        Features:
        - File locking (prevents reading during write)
        - Automatic recovery from corruption (tries backups)
        - Graceful handling of missing files

        Args:
            filename (str): The path to the file to load from.
            console (Console): Rich console for displaying status messages.
        """
        # Initialize file manager on first use
        if self._file_manager is None:
            self._file_manager = SafeFileManager(
                filename,
                lock_timeout=5.0,
                backup_count=3,
                console=console
            )

        try:
            # Load with file locking and backup recovery
            tasks_data = self._file_manager.load_json_with_lock()

            # Deserialize tasks
            self.tasks = [Task(**task) for task in tasks_data]
            self.next_id = (
                max(task.id for task in self.tasks) + 1 if self.tasks else 1
            )

            # Rebuild task index after loading
            self._rebuild_index()

            # Rebuild tag index after loading (NEW! - Phase 2.1)
            self._rebuild_tag_index()

            # Load preferences (sort, order, view, filter)
            self._load_preferences()

            # Use safe symbols for Windows compatibility
            check_mark = "✓" if USE_UNICODE else "+"
            console.print(
                f"[green]{check_mark}[/green] Tasks loaded from [bold]{filename}[/bold]"
            )

        except FileNotFoundError:
            info_mark = "ℹ" if USE_UNICODE else "i"
            console.print(
                f"[yellow]{info_mark}[/yellow] No saved tasks found. Starting fresh."
            )
            self.tasks = []
            self.next_id = 1
            # Still try to load preferences so UI retains sort choices
            self._load_preferences()

        except FileCorruptionError:
            x_mark = "✗" if USE_UNICODE else "X"
            bulb = "💡" if USE_UNICODE else "!"
            console.print(
                f"[red]{x_mark}[/red] All files corrupted and no valid backups!"
            )
            console.print(
                f"[yellow]{bulb} Check .backup files manually in the directory[/yellow]"
            )
            self.tasks = []
            self.next_id = 1
            # Load preferences to not regress UI state
            self._load_preferences()

        except FileLockTimeoutError as e:
            warning = "⚠️" if USE_UNICODE else "!"
            bulb = "💡" if USE_UNICODE else "!"
            console.print(f"[yellow]{warning}[/yellow] {e}")
            console.print(
                f"[yellow]{bulb} Waiting for other instance to finish...[/yellow]"
            )
            # Start fresh but warn user
            self.tasks = []
            self.next_id = 1
            self._load_preferences()

    # ------------------------------------------------------------------
    # Preferences (simple JSON settings stored separately)
    # ------------------------------------------------------------------
    def _save_preferences(self) -> None:
        try:
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            data = {
                "sort": getattr(self, "sort", "priority"),
                "sort_order": getattr(self, "sort_order", "asc"),
                "view_mode": getattr(self, "view_mode", "compact"),
                "filter": getattr(self, "filter", "none"),
            }
            settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            # Best-effort; ignore errors to not impact main flow
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
                if sort in ("priority", "id", "name"):
                    self.sort = sort
                if sort_order in ("asc", "desc"):
                    self.sort_order = sort_order
                if view_mode in ("compact", "detail"):
                    self.view_mode = view_mode
                if isinstance(filter_value, str) and filter_value:
                    self.filter = filter_value
        except Exception:
            # Ignore malformed settings without crashing
            pass

    # =========================================================================
    # AI CONVERSATION MANAGEMENT (Phase 2.1)
    # =========================================================================

    def add_ai_message(self, role: str, content: str) -> AIMessage:
        """
        Add a message to the AI conversation history with automatic pruning

        Maintains a maximum of MAX_CONVERSATION_MESSAGES messages in memory
        by removing oldest messages when the limit is exceeded.

        Args:
            role: "user" or "assistant"
            content: Message content

        Returns:
            The created AIMessage object
        """
        message = AIMessage(role=role, content=content)
        self.ai_conversation.append(message)

        # Prune old messages if we exceed the limit
        if len(self.ai_conversation) > MAX_CONVERSATION_MESSAGES:
            # Remove oldest messages to stay within limit
            messages_to_remove = len(self.ai_conversation) - MAX_CONVERSATION_MESSAGES
            self.ai_conversation = self.ai_conversation[messages_to_remove:]

        return message

    def clear_conversation(self) -> None:
        """Clear all conversation history"""
        self.ai_conversation = []

    def get_conversation_context(self, max_messages: int = 20) -> List[dict]:
        """
        Get conversation history in OpenAI API format

        Args:
            max_messages: Maximum number of recent messages to include

        Returns:
            List of {"role": "user"|"assistant", "content": "..."} dicts
        """
        # Get last N messages
        recent_messages = self.ai_conversation[-max_messages:]
        return [msg.get_openai_format() for msg in recent_messages]

    def get_total_tokens(self) -> int:
        """Get total estimated tokens used in conversation"""
        return sum(msg.token_count for msg in self.ai_conversation)

    def save_conversation_to_file(self, filename: str, console: Console) -> None:
        """
        Save conversation history to file

        Args:
            filename: Path to conversation file
            console: Rich console for status messages
        """
        # Initialize AI file manager if needed
        if self._ai_file_manager is None:
            self._ai_file_manager = SafeFileManager(
                filename,
                lock_timeout=5.0,
                backup_count=3,
                console=console
            )

        try:
            # Serialize conversation to dict format
            conversation_data = [msg.to_dict() for msg in self.ai_conversation]

            # Save with file locking and atomic writes
            self._ai_file_manager.save_json_with_lock(
                conversation_data,
                indent=2  # Human-readable for conversation history
            )

            check_mark = "✓" if USE_UNICODE else "+"
            console.print(
                f"[green]{check_mark}[/green] Conversation saved to [bold]{filename}[/bold]"
            )

        except FileLockTimeoutError as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] {e}")

        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(f"[red]{x_mark}[/red] Failed to save conversation: {e}")

    def load_conversation_from_file(self, filename: str, console: Console) -> None:
        """
        Load conversation history from file

        Args:
            filename: Path to conversation file
            console: Rich console for status messages
        """
        # Initialize AI file manager if needed
        if self._ai_file_manager is None:
            self._ai_file_manager = SafeFileManager(
                filename,
                lock_timeout=5.0,
                backup_count=3,
                console=console
            )

        try:
            # Load with file locking and backup recovery
            conversation_data = self._ai_file_manager.load_json_with_lock()

            # Deserialize messages
            self.ai_conversation = [
                AIMessage.from_dict(msg) for msg in conversation_data
            ]

            check_mark = "✓" if USE_UNICODE else "+"
            console.print(
                f"[green]{check_mark}[/green] Conversation loaded from [bold]{filename}[/bold] "
                f"({len(self.ai_conversation)} messages)"
            )

        except FileNotFoundError:
            # No saved conversation - start fresh
            info_mark = "ℹ" if USE_UNICODE else "i"
            console.print(
                f"[yellow]{info_mark}[/yellow] No saved conversation found. Starting fresh."
            )
            self.ai_conversation = []

        except FileCorruptionError:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(
                f"[red]{x_mark}[/red] Conversation file corrupted. Starting fresh."
            )
            self.ai_conversation = []

        except Exception as e:
            x_mark = "✗" if USE_UNICODE else "X"
            console.print(
                f"[red]{x_mark}[/red] Error loading conversation: {e}. Starting fresh."
            )
            self.ai_conversation = []
