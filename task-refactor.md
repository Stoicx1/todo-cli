# Task: Code Refactoring & Optimization

**Branch:** `task-refactor-optimization`
**Created:** 2025-10-21
**Status:** Planning
**Priority:** HIGH

---

## 🎯 Overview

Comprehensive refactoring to address code quality issues identified in the code review. This task focuses on structural improvements, performance optimization, and code maintainability without adding new features.

---

## 📋 Scope

### Issues to Address

1. **Memory Inefficiency** - All tasks always in RAM
2. **Large main.py** - 333 lines, too many responsibilities
3. **Duplicate Code** - Tag parsing logic repeated 3 times
4. **Magic Numbers** - Hardcoded values throughout codebase
5. **Security Hardening** - Minor improvements to input validation

### Out of Scope (Deferred)

- ❌ File locking implementation (separate task)
- ❌ Unit testing (separate task)
- ❌ Backup system (separate task)
- ❌ Database migration to SQLite (future enhancement)

---

## 🏗️ Architecture Changes

### Current Architecture
```
todo-cli/
├── main.py (333 lines) ⚠️ TOO LARGE
├── core/
│   ├── state.py (no task index) ⚠️
│   ├── commands.py (duplicate tag parsing) ⚠️
│   └── suggestions.py ✅
├── ui/
│   ├── renderer.py ✅
│   ├── questionary_forms.py ✅
│   └── feedback.py ✅
└── models/
    └── task.py ✅
```

### Target Architecture
```
todo-cli/
├── main.py (150 lines) ✅ REFACTORED
├── app.py (NEW) ✅ TodoApp class
├── config.py (NEW) ✅ Constants
├── core/
│   ├── state.py (with task index) ✅
│   ├── commands.py (uses utils) ✅
│   └── suggestions.py ✅
├── ui/
│   ├── renderer.py ✅
│   ├── questionary_forms.py ✅
│   └── feedback.py ✅
├── models/
│   └── task.py ✅
└── utils/
    ├── __init__.py (NEW)
    ├── tag_parser.py (NEW) ✅ DRY
    ├── validators.py (NEW) ✅ Input validation
    └── constants.py (MOVED) ✅ From config.py
```

---

## 📝 Detailed Implementation Plan

### Phase 1: Extract Constants & Configuration

#### Task 1.1: Create `config.py`
**File:** `config.py`
**Lines:** ~80
**Dependencies:** None

```python
"""
Application Configuration & Constants
All magic numbers and hardcoded values centralized here
"""

from dataclasses import dataclass
from pathlib import Path


# ============================================================================
# FILE PATHS
# ============================================================================

DEFAULT_TASKS_FILE = "tasks.json"
DEFAULT_HISTORY_FILE = Path.home() / ".todo_cli_history"
DEFAULT_AUTH_FILE = Path.home() / ".todo_auth"


# ============================================================================
# UI CONFIGURATION
# ============================================================================

@dataclass
class UIConfig:
    """UI/UX configuration constants"""

    # Pagination
    COMPACT_PAGE_SIZE: int = 20
    DETAIL_PAGE_SIZE: int = 10

    # Command Palette
    MENU_RESERVE_LINES: int = 12
    MENU_MAX_VISIBLE: int = 8

    # Visual Feedback
    SUCCESS_PANEL_DURATION: float = 2.0
    INFO_PANEL_DURATION: float = 1.5
    SPINNER_REFRESH_RATE: int = 10

    # Confirmation Dialogs
    BULK_DELETE_THRESHOLD: int = 3  # Show confirmation if deleting > 3 tasks


# ============================================================================
# DATA VALIDATION
# ============================================================================

@dataclass
class ValidationConfig:
    """Input validation limits"""

    # Text Field Limits
    MAX_TASK_NAME_LENGTH: int = 200
    MIN_TASK_NAME_LENGTH: int = 1
    MAX_COMMENT_LENGTH: int = 500
    MAX_DESCRIPTION_LENGTH: int = 2000

    # Tag Limits
    MAX_TAGS_PER_TASK: int = 3
    MAX_TAG_LENGTH: int = 50
    MIN_TAG_LENGTH: int = 1

    # Priority Range
    MIN_PRIORITY: int = 1
    MAX_PRIORITY: int = 3
    DEFAULT_PRIORITY: int = 2

    # ID Limits
    MAX_TASK_ID: int = 999999  # Sanity check


# ============================================================================
# ANALYSIS & SUGGESTIONS
# ============================================================================

@dataclass
class AnalysisConfig:
    """LocalSuggestions thresholds"""

    HIGH_PRIORITY_WARNING_THRESHOLD: int = 5
    LOW_COMPLETION_RATE_THRESHOLD: float = 20.0
    HIGH_COMPLETION_RATE_THRESHOLD: float = 80.0
    LARGE_TASK_LIST_THRESHOLD: int = 20
    RECOMMENDED_TASKS_COUNT: int = 3


# ============================================================================
# PERFORMANCE
# ============================================================================

@dataclass
class PerformanceConfig:
    """Performance tuning settings"""

    # Task Index
    USE_TASK_INDEX: bool = True  # Enable O(1) task lookups

    # JSON Formatting
    JSON_INDENT: int = 4  # 0 for no indent (faster, smaller files)
    JSON_ENSURE_ASCII: bool = False  # Allow Unicode in JSON

    # Cache Settings
    ENABLE_TAG_CACHE: bool = True
    TAG_CACHE_TTL: int = 60  # seconds


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

ui = UIConfig()
validation = ValidationConfig()
analysis = AnalysisConfig()
performance = PerformanceConfig()


# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

import sys

USE_UNICODE = (
    sys.stdout.encoding and
    sys.stdout.encoding.lower() in ('utf-8', 'utf8')
)

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')
```

**Changes Required:**
- Update all files to import from config
- Replace hardcoded values with config references

---

### Phase 2: Extract Utility Functions

#### Task 2.1: Create `utils/tag_parser.py`
**File:** `utils/tag_parser.py`
**Lines:** ~60
**Purpose:** DRY - Eliminate duplicate tag parsing logic

```python
"""
Tag Parsing Utilities
Centralized tag parsing, validation, and normalization
"""

import re
from typing import List
from config import validation


def validate_tag_format(tag: str) -> bool:
    """
    Validate tag format.
    Tags must be alphanumeric with hyphens/underscores only.

    Args:
        tag: Tag string to validate

    Returns:
        True if valid, False otherwise
    """
    if not tag:
        return False

    if len(tag) < validation.MIN_TAG_LENGTH or len(tag) > validation.MAX_TAG_LENGTH:
        return False

    # Only allow: letters, numbers, hyphens, underscores
    return bool(re.match(r'^[a-z0-9_-]+$', tag))


def normalize_tag(tag: str) -> str:
    """
    Normalize tag: lowercase, strip whitespace.

    Args:
        tag: Tag string to normalize

    Returns:
        Normalized tag string
    """
    return tag.strip().lower()


def parse_tags(tag_str: str, max_tags: int = None) -> List[str]:
    """
    Parse comma-separated tags and normalize them.

    Args:
        tag_str: Comma-separated tag string (e.g., "tag1, tag2, tag3")
        max_tags: Maximum number of tags to return (default: from config)

    Returns:
        List of unique, normalized, validated tags

    Example:
        >>> parse_tags("Backend, API, Urgent")
        ['backend', 'api', 'urgent']

        >>> parse_tags("tag1, tag1, tag2, tag3, tag4", max_tags=3)
        ['tag1', 'tag2', 'tag3']
    """
    if max_tags is None:
        max_tags = validation.MAX_TAGS_PER_TASK

    if not tag_str:
        return []

    # Split by comma if present
    if ',' in tag_str:
        raw_tags = tag_str.split(',')
    else:
        # Single tag
        raw_tags = [tag_str]

    # Normalize and validate
    normalized = []
    seen = set()

    for tag in raw_tags:
        tag = normalize_tag(tag)

        if not tag:
            continue

        # Skip duplicates
        if tag in seen:
            continue

        # Validate format
        if not validate_tag_format(tag):
            # Skip invalid tags silently (or log warning)
            continue

        # Add to result
        seen.add(tag)
        normalized.append(tag)

        # Respect max limit
        if len(normalized) >= max_tags:
            break

    return normalized


def tags_to_string(tags: List[str]) -> str:
    """
    Convert tag list to comma-separated string.

    Args:
        tags: List of tag strings

    Returns:
        Comma-separated string

    Example:
        >>> tags_to_string(['backend', 'api', 'urgent'])
        'backend, api, urgent'
    """
    return ', '.join(tags) if tags else ''


def merge_tags(existing: List[str], new: List[str], max_tags: int = None) -> List[str]:
    """
    Merge two tag lists, removing duplicates and respecting max limit.

    Args:
        existing: Current tags
        new: Tags to add
        max_tags: Maximum total tags (default: from config)

    Returns:
        Merged list of unique tags
    """
    if max_tags is None:
        max_tags = validation.MAX_TAGS_PER_TASK

    # Use dict to preserve order while removing duplicates
    merged = {}
    for tag in existing + new:
        if tag not in merged and len(merged) < max_tags:
            merged[tag] = True

    return list(merged.keys())
```

**Usage Examples:**
```python
# Before (duplicated 3 times):
if ',' in tag:
    tag_list = [t.strip().lower() for t in tag.split(',') if t.strip()]
    tag_list = tag_list[:3]

# After (single import):
from utils.tag_parser import parse_tags
tag_list = parse_tags(tag)
```

#### Task 2.2: Create `utils/validators.py`
**File:** `utils/validators.py`
**Lines:** ~100
**Purpose:** Input validation and sanitization

```python
"""
Input Validation Utilities
Validate and sanitize user input to prevent errors and security issues
"""

from typing import Optional, Tuple
from config import validation


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


def validate_task_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate task name.

    Args:
        name: Task name to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_task_name("Valid Task")
        (True, None)

        >>> validate_task_name("")
        (False, "Task name cannot be empty")
    """
    name = name.strip()

    if not name:
        return False, "Task name cannot be empty"

    if len(name) < validation.MIN_TASK_NAME_LENGTH:
        return False, f"Task name must be at least {validation.MIN_TASK_NAME_LENGTH} character(s)"

    if len(name) > validation.MAX_TASK_NAME_LENGTH:
        return False, f"Task name too long (max {validation.MAX_TASK_NAME_LENGTH} characters)"

    return True, None


def validate_priority(priority: any) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate and normalize priority.

    Args:
        priority: Priority value (int or str)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)

    Example:
        >>> validate_priority("2")
        (True, None, 2)

        >>> validate_priority(999)
        (False, "Priority must be between 1 and 3", None)
    """
    # Try to convert to int
    try:
        p = int(priority)
    except (ValueError, TypeError):
        return False, "Priority must be a number", None

    # Validate range
    if p < validation.MIN_PRIORITY or p > validation.MAX_PRIORITY:
        return False, f"Priority must be between {validation.MIN_PRIORITY} and {validation.MAX_PRIORITY}", None

    return True, None, p


def validate_task_id(task_id: any) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate task ID.

    Args:
        task_id: Task ID value (int or str)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return False, "Task ID must be a number", None

    if tid < 1:
        return False, "Task ID must be positive", None

    if tid > validation.MAX_TASK_ID:
        return False, f"Task ID too large (max {validation.MAX_TASK_ID})", None

    return True, None, tid


def sanitize_text(text: str, max_length: int, allow_empty: bool = True) -> str:
    """
    Sanitize text input: strip whitespace, enforce length limit.

    Args:
        text: Text to sanitize
        max_length: Maximum length to allow
        allow_empty: Whether empty string is allowed

    Returns:
        Sanitized text (truncated if too long)
    """
    text = text.strip()

    if not allow_empty and not text:
        raise ValidationError("Text cannot be empty")

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]

    return text


def sanitize_comment(comment: str) -> str:
    """Sanitize comment field"""
    return sanitize_text(comment, validation.MAX_COMMENT_LENGTH, allow_empty=True)


def sanitize_description(description: str) -> str:
    """Sanitize description field"""
    return sanitize_text(description, validation.MAX_DESCRIPTION_LENGTH, allow_empty=True)


def clamp_priority(priority: int) -> int:
    """
    Clamp priority to valid range [1, 3].
    Use this when you want to auto-correct instead of error.

    Args:
        priority: Priority value (may be out of range)

    Returns:
        Clamped priority within valid range

    Example:
        >>> clamp_priority(999)
        3
        >>> clamp_priority(-5)
        1
    """
    return max(validation.MIN_PRIORITY, min(validation.MAX_PRIORITY, priority))
```

---

### Phase 3: Add Task Index (O(1) Lookups)

#### Task 3.1: Update `core/state.py`
**Changes:**
- Add `_task_index: dict[int, Task]` to `AppState.__init__`
- Update `add_task()` to maintain index
- Add `get_task_by_id()` method for O(1) lookup
- Update `load_from_file()` to rebuild index

```python
# core/state.py additions

from typing import List, Optional
from config import performance

class AppState:
    def __init__(self):
        self.tasks: list[Task] = []
        self.next_id: int = 1

        # NEW: Task index for O(1) lookups
        if performance.USE_TASK_INDEX:
            self._task_index: dict[int, Task] = {}

        # ... rest of init

    def add_task(self, name: str, comment: str, description: str, priority: int, tag: str):
        """Add task and maintain index"""
        # Existing logic...
        task = Task(id=self.next_id, ...)
        self.tasks.append(task)

        # NEW: Update index
        if performance.USE_TASK_INDEX:
            self._task_index[task.id] = task

        self.next_id += 1

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """
        Get task by ID with O(1) lookup.

        Args:
            task_id: Task ID to find

        Returns:
            Task object if found, None otherwise
        """
        if performance.USE_TASK_INDEX:
            # O(1) dictionary lookup
            return self._task_index.get(task_id)
        else:
            # O(n) fallback (for compatibility)
            return next((t for t in self.tasks if t.id == task_id), None)

    def remove_task(self, task: Task):
        """Remove task and update index"""
        self.tasks.remove(task)

        # NEW: Update index
        if performance.USE_TASK_INDEX and task.id in self._task_index:
            del self._task_index[task.id]

    def load_from_file(self, filename: str, console: Console):
        """Load tasks and rebuild index"""
        # Existing load logic...
        self.tasks = [Task(**task) for task in tasks_data]

        # NEW: Rebuild index after load
        if performance.USE_TASK_INDEX:
            self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild task index from task list"""
        self._task_index = {task.id: task for task in self.tasks}
```

#### Task 3.2: Update all task lookups in `core/commands.py`

```python
# Before (O(n) linear search):
task = next((t for t in state.tasks if t.id == task_id), None)

# After (O(1) index lookup):
task = state.get_task_by_id(task_id)
```

**Files to update:**
- `core/commands.py` (15 occurrences)
- `main.py` (2 occurrences)

**Performance Impact:**
- 100 tasks: 0.01ms → 0.001ms (10x faster)
- 1,000 tasks: 0.1ms → 0.001ms (100x faster)
- 10,000 tasks: 1ms → 0.001ms (1000x faster)

---

### Phase 4: Refactor main.py into TodoApp Class

#### Task 4.1: Create `app.py`
**File:** `app.py`
**Lines:** ~250
**Purpose:** Extract application logic from main.py

```python
"""
TodoApp - Main Application Class
Encapsulates session management, input handling, and main loop
"""

from typing import Optional
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import ThreadedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.formatted_text import HTML

from core.state import AppState
from core.commands import handle_command
from core.suggestions import LocalSuggestions
from ui.renderer import render_dashboard
from ui.command_palette import create_command_completer, get_available_tags
from ui.questionary_forms import questionary_add_task, questionary_edit_task
from ui.feedback import show_success, show_error
from config import UIConfig, DEFAULT_TASKS_FILE, DEFAULT_HISTORY_FILE, USE_UNICODE


class TodoApp:
    """
    Main Todo CLI Application

    Responsibilities:
    - Session management (prompt_toolkit)
    - Main REPL loop
    - Command routing
    - Dashboard rendering
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        state: Optional[AppState] = None,
        tasks_file: str = DEFAULT_TASKS_FILE,
        use_questionary_forms: bool = True
    ):
        """
        Initialize TodoApp

        Args:
            console: Rich console instance (created if None)
            state: AppState instance (created if None)
            tasks_file: Path to tasks JSON file
            use_questionary_forms: Whether to use questionary forms (fallback to inline)
        """
        self.console = console or Console()
        self.state = state or AppState()
        self.tasks_file = tasks_file
        self.use_questionary_forms = use_questionary_forms

        # Will be initialized in setup()
        self.session: Optional[PromptSession] = None

    def setup(self):
        """Initialize application (load data, create session)"""
        # Load tasks from file
        self.state.load_from_file(self.tasks_file, self.console)

        # Create prompt session
        self.session = self._create_session()

        # Initial render
        self.console.clear()
        render_dashboard(self.console, self.state)

    def _create_session(self) -> PromptSession:
        """
        Create configured prompt_toolkit session

        Returns:
            Configured PromptSession instance
        """
        # Create command completer
        completer = create_command_completer(self.state)
        threaded_completer = ThreadedCompleter(completer)

        # Setup history
        history = FileHistory(str(DEFAULT_HISTORY_FILE))

        # Create custom style for completion menu
        completion_style = Style.from_dict({
            'completion-menu': 'bg:default',
            'completion-menu.completion': 'bg:default',
            'completion-menu.completion.current': 'bg:#444444 #ffffff',
            'completion-menu.meta.current': 'bg:#444444 #ffffff',
            'completion-menu.multi-column-meta': 'bg:default',
        })

        # Create key bindings
        kb = self._create_key_bindings()

        # Create session
        return PromptSession(
            completer=threaded_completer,
            complete_while_typing=True,
            history=history,
            enable_history_search=False,  # Critical: avoid conflict
            mouse_support=True,
            reserve_space_for_menu=UIConfig.MENU_RESERVE_LINES,
            complete_style=CompleteStyle.MULTI_COLUMN,
            style=completion_style,
            key_bindings=kb
        )

    def _create_key_bindings(self) -> KeyBindings:
        """
        Create custom key bindings

        Returns:
            KeyBindings instance with ESC handler
        """
        kb = KeyBindings()

        @kb.add('escape')
        def clear_input(event):
            """Clear input buffer on ESC key"""
            event.current_buffer.reset()

        return kb

    def _create_prompt(self) -> HTML:
        """
        Create prompt HTML

        Returns:
            Formatted HTML prompt
        """
        if USE_UNICODE:
            prompt_text = '<violet>❯</violet> <dim>Type / for commands</dim> <violet>›</violet> '
        else:
            prompt_text = '<violet>></violet> <dim>Type / for commands</dim> <violet>></violet> '

        return HTML(prompt_text)

    def run(self):
        """
        Main application loop

        Runs until user exits (exit/quit/x command or Ctrl+C)
        """
        try:
            while True:
                # Get user input
                user_input = self.session.prompt(self._create_prompt()).strip()

                # Handle input
                should_continue = self.handle_input(user_input)

                if not should_continue:
                    break

                # Re-render dashboard
                self.console.clear()
                render_dashboard(self.console, self.state)

        except (KeyboardInterrupt, EOFError):
            # User pressed Ctrl+C or Ctrl+D
            self.shutdown()

    def handle_input(self, user_input: str) -> bool:
        """
        Handle user input

        Args:
            user_input: Raw user input string

        Returns:
            True to continue loop, False to exit
        """
        # Empty input - just refresh
        if not user_input:
            return True

        # Clear screen command
        if user_input.lower() in ("cls", "clear", "c"):
            self.state.messages = []
            return True

        # Insights command (local AI)
        if user_input.lower() == "insights":
            self._handle_insights()
            return True

        # Suggest command (local AI)
        if user_input.lower() == "suggest":
            self._handle_suggest()
            return True

        # Tags command
        if user_input.lower() == "tags":
            self._handle_tags()
            return True

        # Exit commands
        if user_input.lower() in ("exit", "quit", "x"):
            self.shutdown()
            return False

        # Add command with form
        if user_input.strip() == "add":
            self._handle_add_form()
            return True

        # Edit command with form
        if user_input.startswith("edit "):
            self._handle_edit_form(user_input)
            return True

        # All other commands
        handle_command(user_input, self.state, self.console)
        return True

    def _handle_insights(self):
        """Handle insights command"""
        from rich.panel import Panel
        insights = LocalSuggestions.get_insights_summary(self.state)
        self.console.clear()
        render_dashboard(self.console, self.state)
        self.console.print(Panel(
            insights,
            title="[bold cyan]📊 Task Insights[/bold cyan]",
            border_style="cyan"
        ))

    def _handle_suggest(self):
        """Handle suggest command"""
        suggestions = LocalSuggestions.get_smart_suggestions(self.state)
        self.console.print("\n[bold cyan]💡 Smart Suggestions:[/bold cyan]\n")
        for suggestion in suggestions:
            self.console.print(f"  {suggestion}")
            self.console.print()

    def _handle_tags(self):
        """Handle tags command"""
        tags = get_available_tags(self.state)
        if tags:
            self.console.print("\n[bold cyan]🏷️ Available Tags:[/bold cyan]")
            for tag in tags:
                tag_tasks = [t for t in self.state.tasks if t.tag == tag]
                done = sum(1 for t in tag_tasks if t.done)
                total = len(tag_tasks)
                self.console.print(f"  • {tag}: {done}/{total} completed")
        else:
            self.console.print("[yellow]No tags found[/yellow]")
        self.console.print()

    def _handle_add_form(self):
        """Handle add command with questionary form"""
        if self.use_questionary_forms:
            try:
                result = questionary_add_task(self.state)
                if result:
                    self.state.add_task(
                        name=result['name'],
                        comment=result.get('comment', ''),
                        description=result.get('description', ''),
                        priority=result.get('priority', 2),
                        tag=result.get('tag', '')
                    )
                    self.console.clear()
                    render_dashboard(self.console, self.state)
                    show_success(f"Task '{result['name']}' added successfully!", self.console)
                else:
                    self.console.clear()
                    render_dashboard(self.console, self.state)
                    self.console.print("[yellow]Cancelled[/yellow]")
            except Exception as e:
                self.console.print(f"[yellow]Form error: {e}. Using inline form...[/yellow]")
                self._handle_add_inline()
        else:
            self._handle_add_inline()

    def _handle_add_inline(self):
        """Fallback: inline add form"""
        from ui.inline_forms import inline_add_task
        filled_input = inline_add_task(self.console)
        if filled_input:
            handle_command(filled_input, self.state, self.console)

    def _handle_edit_form(self, user_input: str):
        """Handle edit command with questionary form"""
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            task_id = int(parts[1])
            task = self.state.get_task_by_id(task_id)

            if task and self.use_questionary_forms:
                try:
                    result = questionary_edit_task(task, self.state)
                    if result:
                        # Update task fields
                        task.name = result['name']
                        task.comment = result.get('comment', '')
                        task.description = result.get('description', '')
                        task.priority = result.get('priority', 2)

                        # Handle tags
                        if 'tag' in result:
                            from utils.tag_parser import parse_tags
                            tag_list = parse_tags(result['tag'])
                            task.tag = tag_list[0] if tag_list else ""
                            task.tags = tag_list

                        self.console.clear()
                        render_dashboard(self.console, self.state)
                        show_success(f"Task #{task_id} updated successfully!", self.console)
                    else:
                        self.console.clear()
                        render_dashboard(self.console, self.state)
                        self.console.print("[yellow]Cancelled[/yellow]")
                except Exception as e:
                    self.console.print(f"[yellow]Form error: {e}[/yellow]")
                    # Could add inline form fallback here
            elif not task:
                self.console.print(f"[red]Task #{task_id} not found[/red]")
        else:
            # Invalid edit syntax - let command handler show error
            handle_command(user_input, self.state, self.console)

    def shutdown(self):
        """Shutdown application (save and exit)"""
        self.state.save_to_file(self.tasks_file, self.console)
        self.console.print("\n[yellow]Goodbye![/yellow]")
```

#### Task 4.2: Update `main.py` (Simplified)
**File:** `main.py`
**Lines:** ~30 (down from 333!)

```python
"""
Todo CLI - Main Entry Point
Minimal entry point that creates and runs TodoApp
"""

from app import TodoApp
from config import DEFAULT_TASKS_FILE


def main():
    """
    Main entry point
    Creates TodoApp instance and runs it
    """
    # Create app
    app = TodoApp(
        tasks_file=DEFAULT_TASKS_FILE,
        use_questionary_forms=True
    )

    # Setup (load data, create session)
    app.setup()

    # Run main loop
    app.run()


if __name__ == "__main__":
    main()
```

---

### Phase 5: Apply DRY Principle

#### Task 5.1: Update `core/state.py` to use `utils.tag_parser`

```python
# Before:
if ',' in tag:
    tag_list = [t.strip().lower() for t in tag.split(',') if t.strip()]
    tag_list = tag_list[:3]
else:
    tag_list = [tag.strip().lower()] if tag.strip() else []

# After:
from utils.tag_parser import parse_tags
tag_list = parse_tags(tag)
```

#### Task 5.2: Update `core/commands.py` to use utils

```python
from utils.tag_parser import parse_tags
from utils.validators import validate_priority, validate_task_id, clamp_priority
from config import validation, ui

# Update all tag parsing to use parse_tags()
# Update all priority validation to use validate_priority()
# Update all task ID lookups to use state.get_task_by_id()
```

#### Task 5.3: Update `main.py` and `app.py`

```python
# Use tag_parser in questionary form handlers
from utils.tag_parser import parse_tags
```

**Total Reduction:** ~100 lines of duplicate code removed

---

### Phase 6: Security Hardening

#### Task 6.1: Add input validation to all commands

```python
# core/commands.py updates

from utils.validators import (
    validate_task_name,
    validate_priority,
    validate_task_id,
    sanitize_comment,
    sanitize_description
)

def handle_add(command_arguments: list, state: AppState, console: Console):
    """Add task with validation"""

    if len(command_arguments) < 2:
        state.messages.append('[!] Usage: add "name" ...')
        return

    # Validate task name
    is_valid, error = validate_task_name(command_arguments[1])
    if not is_valid:
        state.messages.append(f'[!] {error}')
        return

    name = command_arguments[1]

    # ... parse other arguments

    # Validate priority
    if priority_arg:
        is_valid, error, priority = validate_priority(priority_arg)
        if not is_valid:
            state.messages.append(f'[!] {error}')
            return

    # Sanitize text fields
    comment = sanitize_comment(comment)
    description = sanitize_description(description)

    # Add task (now validated)
    state.add_task(name, comment, description, priority, tag)
```

---

## 📊 Impact Assessment

### Code Metrics (Before → After)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| main.py lines | 333 | ~30 | **91% reduction** |
| Duplicate code blocks | 3 | 0 | **100% removed** |
| Magic numbers | 15+ | 0 | **100% removed** |
| Task lookup time (1000 tasks) | 0.1ms | 0.001ms | **100x faster** |
| Task lookup time (10000 tasks) | 1ms | 0.001ms | **1000x faster** |
| Files created | 0 | 5 | New utilities |

### File Count Changes

**Before:**
```
7 Python files (main + core + ui + models)
```

**After:**
```
13 Python files:
  - main.py (simplified)
  - app.py (NEW)
  - config.py (NEW)
  - utils/tag_parser.py (NEW)
  - utils/validators.py (NEW)
  - utils/__init__.py (NEW)
  + existing files (updated)
```

---

## ✅ Testing Strategy

### Unit Tests to Add

```python
# tests/unit/test_tag_parser.py
def test_parse_tags_with_commas():
    assert parse_tags("tag1, tag2, tag3") == ['tag1', 'tag2', 'tag3']

def test_parse_tags_max_limit():
    assert len(parse_tags("a,b,c,d,e", max_tags=3)) == 3

def test_parse_tags_removes_duplicates():
    assert parse_tags("tag1, tag1, tag2") == ['tag1', 'tag2']


# tests/unit/test_validators.py
def test_validate_priority_valid():
    is_valid, error, value = validate_priority(2)
    assert is_valid == True
    assert value == 2

def test_validate_priority_out_of_range():
    is_valid, error, value = validate_priority(999)
    assert is_valid == False
    assert "between 1 and 3" in error


# tests/unit/test_task_index.py
def test_task_index_o1_lookup():
    state = AppState()
    state.add_task("Task 1", "", "", 1, "")

    import time
    start = time.perf_counter()
    task = state.get_task_by_id(1)
    duration = time.perf_counter() - start

    assert task is not None
    assert duration < 0.001  # Should be < 1ms


# tests/integration/test_app.py
def test_app_initialization():
    app = TodoApp()
    app.setup()

    assert app.state is not None
    assert app.session is not None
    assert app.console is not None
```

---

## 🚀 Rollout Plan

### Step 1: Create Branch
```bash
git checkout -b task-refactor-optimization
```

### Step 2: Phase 1 - Constants (1-2 hours)
- Create `config.py`
- Update imports in all files
- Test: All existing functionality works

### Step 3: Phase 2 - Utilities (2-3 hours)
- Create `utils/` package
- Create `tag_parser.py`
- Create `validators.py`
- Write unit tests for utils
- Test: Tag parsing works correctly

### Step 4: Phase 3 - Task Index (1-2 hours)
- Update `core/state.py`
- Add `_task_index` dict
- Add `get_task_by_id()` method
- Update all lookups to use index
- Write performance tests
- Test: Lookups are faster

### Step 5: Phase 4 - Refactor main.py (3-4 hours)
- Create `app.py` with `TodoApp` class
- Move logic from main.py to app.py
- Simplify main.py to 30 lines
- Test: All commands still work

### Step 6: Phase 5 - Apply DRY (1-2 hours)
- Replace all duplicate tag parsing
- Replace all duplicate validation
- Test: No regressions

### Step 7: Phase 6 - Security (1-2 hours)
- Add validation to all commands
- Add sanitization to text inputs
- Test: Invalid inputs rejected

### Step 8: Integration Testing (2-3 hours)
- Test all commands end-to-end
- Test with 100, 1000, 10000 tasks
- Performance benchmarks
- Compatibility testing (Windows, Linux, Mac)

### Step 9: Documentation (1 hour)
- Update CLAUDE.md
- Update README.md
- Add docstrings to new files

### Step 10: Merge (1 hour)
- Code review
- Final testing
- Merge to main branch
- Tag release

---

## ⏱️ Time Estimates

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Constants | config.py, update imports | 1-2 hours |
| Phase 2: Utilities | tag_parser.py, validators.py | 2-3 hours |
| Phase 3: Task Index | state.py updates, lookups | 1-2 hours |
| Phase 4: Refactor main | app.py, main.py | 3-4 hours |
| Phase 5: DRY | Replace duplicates | 1-2 hours |
| Phase 6: Security | Validation, sanitization | 1-2 hours |
| Phase 7: Testing | Unit + integration tests | 2-3 hours |
| Phase 8: Documentation | Update docs | 1 hour |
| **TOTAL** | | **12-19 hours** |

**Conservative estimate:** 2-3 full work days

---

## 📝 Acceptance Criteria

### Phase 1: Constants
- ✅ All magic numbers extracted to config.py
- ✅ All files import from config
- ✅ No hardcoded values in code

### Phase 2: Utilities
- ✅ Tag parsing centralized in utils/tag_parser.py
- ✅ Validation centralized in utils/validators.py
- ✅ Unit tests pass for all utility functions

### Phase 3: Task Index
- ✅ Task lookups use index (O(1) instead of O(n))
- ✅ Performance tests show 100x+ speedup for 1000+ tasks
- ✅ Index automatically maintained on add/remove/load

### Phase 4: Refactor main.py
- ✅ main.py reduced to ~30 lines
- ✅ All logic moved to TodoApp class
- ✅ App is testable (can mock console, session)
- ✅ All existing functionality works

### Phase 5: DRY
- ✅ Zero duplicate tag parsing code
- ✅ Zero duplicate validation code
- ✅ Code coverage same or better

### Phase 6: Security
- ✅ All commands validate input
- ✅ All text fields sanitized
- ✅ Invalid input rejected with helpful errors

### Overall
- ✅ All existing tests pass (when added)
- ✅ No regressions in functionality
- ✅ Performance improved (benchmarks)
- ✅ Code quality improved (metrics)
- ✅ Documentation updated

---

## 🐛 Risks & Mitigations

### Risk 1: Breaking Existing Functionality
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Test after each phase
- Keep old code commented out initially
- Comprehensive integration testing

### Risk 2: Performance Regression
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Benchmark before and after
- Profile code with cProfile
- Task index should improve performance, not degrade it

### Risk 3: Import Cycles
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Careful dependency management
- utils/ should have no dependencies on core/ui/
- config.py should have no dependencies (pure data)

### Risk 4: Time Overrun
**Probability:** Medium
**Impact:** Low
**Mitigation:**
- Phased approach allows stopping at any point
- Each phase delivers value independently
- Can defer Phase 6 (security) if needed

---

## 📚 References

### Code Review Findings
- `COMPREHENSIVE_CODE_REVIEW.md` - Full analysis
- Section 5: Code Smells & Anti-patterns
- Section 2: Performance Analysis

### Best Practices
- PEP 8: Python Style Guide
- Clean Code by Robert C. Martin
- Refactoring by Martin Fowler

### Similar Projects
- Click (CLI framework) - For app structure inspiration
- Rich CLI examples - For TodoApp pattern

---

**Status:** Ready for implementation
**Next Step:** Create branch and begin Phase 1 (config.py)
