# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based terminal task management CLI with dual UI support:
- **Textual UI** (default): Modern reactive TUI with AI chat sidebar, notes management, and split-screen layout
- **Rich UI**: Classic REPL interface with command palette and inline forms

**Tech Stack:** Textual, Rich, prompt_toolkit, OpenAI API (optional), LangChain, pytest

## Quick Start

```bash
# Run application
python main.py              # Textual UI (default)
python main.py --ui rich    # Rich UI (classic)
python main.py --version    # Show version

# Run tests
pytest                      # All tests
pytest tests/test_file.py   # Single file
pytest -m unit              # By marker (unit/integration/slow)
pytest -v --tb=short        # Verbose with short tracebacks

# Development
pip install -r requirements.txt
```

## Critical Textual UI Patterns

### 1. Reserved Attribute Names (CRITICAL)

**NEVER use these underscore-prefixed names in custom widgets:**

| Attribute | Framework Class | Risk |
|-----------|----------------|------|
| `_task` | MessagePump | 🔴 CRITICAL - Asyncio collision |
| `_bindings`, `_nodes`, `_styles`, `_reactives`, `_id` | Widget/DOMNode | 🟡 HIGH |

**Safe Pattern:**
```python
✅ self._task_data = task_model
✅ self._note_data = note
❌ self._task = task  # WILL BREAK ASYNC OPERATIONS
```

**Why:** `MessagePump._task` stores asyncio tasks. Overwriting causes `AttributeError` in `push_screen_wait()`.

### 2. CSS: Always Use Inline Styles

```python
class MyApp(App):
    CSS = """
    /* All CSS here - NEVER use CSS_PATH */
    """
```

**Never use external `.tcss` files** - Textual aggressively caches them causing persistent parsing errors.

See: `docs/technical/TEXTUAL_TROUBLESHOOTING.md`

### 3. Thread Safety Pattern

**All UI updates from worker threads MUST use `call_from_thread()`:**

```python
@work(exclusive=True, thread=True)
async def stream_ai_response(self, prompt: str) -> None:
    # Create on main thread
    ai_message = self.call_from_thread(lambda: self.state.add_ai_message("assistant", ""))

    # Stream from worker
    for chunk in stream_chunks():
        content += chunk
        # Update on main thread
        self.call_from_thread(lambda c=content: setattr(ai_message, 'content', c))
```

### 4. Modal Forms Require @work Decorator

```python
@work(exclusive=True)
async def action_add_task(self) -> None:
    result = await self.push_screen_wait(TaskForm())  # Blocks - needs worker context
    if result:
        self.state.add_task(**result)
```

**Without `@work`:** `NoActiveWorker` exception
**With `exclusive=True`:** Prevents multiple modals simultaneously

**CRITICAL: Don't Double-Wrap @work Decorated Methods**

```python
# ❌ WRONG - Causes WorkerError
@work(exclusive=True)
async def action_cancel(self) -> None:
    # ...

def on_button_pressed(self, event):
    self.run_worker(self.action_cancel(), exclusive=True)  # CRASH!

# ✅ CORRECT - @work handles worker creation
def on_button_pressed(self, event):
    self.action_cancel()  # Method already decorated with @work
```

**Why:** `@work` decorated methods create workers automatically. Wrapping them with `run_worker()` creates nested workers, causing `WorkerError: Unsupported attempt to run an async worker`.

### 5. Event Bubbling Prevention (CRITICAL)

**All button handlers MUST call `event.stop()` to prevent multiple triggers:**

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle button presses"""
    if event.button.id == "save_btn":
        self.action_save()
        event.stop()  # REQUIRED - prevents bubbling
    elif event.button.id == "cancel_btn":
        self.action_cancel()
        event.stop()  # REQUIRED - prevents bubbling

def on_input_submitted(self, event: Input.Submitted) -> None:
    # ... handle input ...
    event.stop()
    event.prevent_default()
```

**Without `event.stop()`:** Events bubble up through parent containers, causing actions to trigger 7+ times per click.

**Affected Widgets:** TaskDetailPanel, NoteDetailPanel, TaskEditPanel, NoteEditPanel (all 12 buttons)

## Theme Configuration

**Simple config-based approach** - no runtime switching complexity

### Configuration File

**Location:** `~/.todo_cli_theme.json`

**Format:**
```json
{
  "theme": "dark",
  "_comment": "Valid values: 'dark' or 'light'. Restart app to apply changes."
}
```

### Changing Themes

1. Edit `~/.todo_cli_theme.json`
2. Change `"theme"` value to `"dark"` or `"light"`
3. Restart application

**Default:** Dark theme if config missing/invalid

**Auto-created:** Config file is automatically created on first run with dark theme default

### Implementation Details

**Module:** `core/theme_config.py` handles all theme configuration
**Loading:** Theme loaded once at startup in `on_load()` lifecycle method (before widgets created)
**No runtime switching:** Theme changes require app restart (simple, predictable, no refresh complexity)

**Theme CSS:** Inline CSS strings in `textual_app.py`:
- `_CSS_DARK_THEME` - Dark theme with cyan accents
- `_CSS_LIGHT_THEME` - Light theme with cyan accents

## Architecture

### Core Components (Shared by Both UIs)

```
core/
├── state.py          # AppState - central state with filter caching, task/tag indexing
├── commands.py       # Command parsing, aliases (COMMAND_ALIASES), validation
├── file_safety.py    # SafeFileManager - atomic writes, locking, backups
└── suggestions.py    # Local AI insights (no API required)

models/
├── task.py           # Task dataclass (id, name, priority, tags, done, created_at, updated_at)
├── note.py           # Note dataclass (id, title, body, tags, task_ids, created_at)
└── ai_message.py     # AIMessage for conversation history

utils/
├── time.py           # humanize_age(), parse_duration(), age_seconds()
├── filter_parser.py  # Advanced filtering engine (operators: =, !=, >=, <=)
├── ids.py            # ID generation utilities
└── version.py        # get_version() - reads VERSION file or derives from git

services/
└── notes_repo.py     # NotesRepository - CRUD, search, file management
```

### Textual UI Components

```
textual_app.py        # Main App - layout, event routing, AI streaming
textual_widgets/
├── task_table.py     # DataTable with row-to-task mapping, select_task_by_id()
├── note_table.py     # Notes view with search/filter
├── task_form.py      # Modal form (MUST use _task_data, not _task!)
├── note_editor_modal.py  # Note editing with external editor support
├── command_input.py  # Command input with autocomplete, history
├── ai_input.py       # AI prompt input (workaround for message routing bug)
├── ai_chat_panel.py  # Scrollable AI conversation, safe DOM queries
└── status_bar.py     # Stats display (page, filter, sort, counts)
```

### State Management

```python
# Key properties
state.tasks                 # List[Task]
state.notes                 # List[Note]
state.page, state.page_size # Pagination
state.view_mode             # "compact" | "detail"
state.current_mode          # "tasks" | "notes" (NEW - dual mode)
state.filter                # Filter expression
state.sort, state.sort_order # "priority"/"id"/"name"/"age", "asc"/"desc"
state.ai_conversation       # AI message history

# Performance optimizations
state.filtered_tasks        # @property - cached, auto-invalidates
state._task_index          # O(1) lookup by ID
state._tag_index           # O(1) lookup by tag
```

**Flow:** User input → `handle_command()` → mutate state → UI refresh

### Dual Mode System (CRITICAL)

**The Textual UI uses two separate mode properties that MUST stay synchronized:**

```python
# In core/state.py
state.entity_mode       # str: "tasks" | "notes" - Data layer mode

# In textual_app.py
self.state.left_panel_mode  # LeftPanelMode enum - UI layer panel state
# Values: LIST_TASKS, DETAIL_TASK, EDIT_TASK, LIST_NOTES, DETAIL_NOTE, EDIT_NOTE
```

**Why Two Properties?**
- `entity_mode`: Determines which data to display (tasks vs notes)
- `left_panel_mode`: Controls which panel widget is mounted (list/detail/edit)

**CRITICAL: Always update BOTH when switching modes:**

```python
# ✅ CORRECT - Both properties updated
def action_toggle_mode(self) -> None:
    from core.state import LeftPanelMode

    # Toggle entity mode
    self.state.entity_mode = "notes" if self.state.entity_mode == "tasks" else "tasks"

    # Update panel mode to match
    if self.state.entity_mode == "tasks":
        self.state.left_panel_mode = LeftPanelMode.LIST_TASKS
    elif self.state.entity_mode == "notes":
        self.state.left_panel_mode = LeftPanelMode.LIST_NOTES

    self.refresh_table()

# ❌ WRONG - Only updates entity_mode
def action_toggle_mode(self) -> None:
    self.state.entity_mode = "notes"  # left_panel_mode NOT updated!
    # Result: Status bar shows "notes" but task list still displays
```

**Common Desync Bug:** Updating only `entity_mode` causes:
- Status bar shows correct mode ("5 notes")
- Panel displays wrong content (empty task list)
- Panel title doesn't change ("Tasks" instead of "Notes")

**Files Affected:** `textual_app.py` (action_toggle_mode, mode command interceptor)

### Command System

**Format:** `shlex.split()` for proper quoting

**Shortcuts (COMMAND_ALIASES in core/commands.py):**

| Short | Command | Short | Command |
|-------|---------|-------|---------|
| `a` | add (mode-aware) | `e` | edit (mode-aware) |
| `x`/`d` | done | `u` | undone |
| `r` | remove | `s` | show |
| `v` | view | `f` | filter |
| `t` | tags | `so` | sort |
| `n` | next | `p` | prev |
| `h` | help | `q` | exit/quit |
| `m` | mode (tasks/notes toggle) | | |

**Advanced Filtering:**
```bash
f status=done              # Single condition
f priority=1,2             # OR (comma)
f tag=psdc+webasto         # AND (plus)
f status=undone priority=1 # Multiple conditions (space = AND)
```

**Notes Commands:**
```bash
mode notes                 # Switch to notes view
note new --title "..." [--task 12] [--tag x]
note edit <note_id>        # Edit by ID prefix (8+ chars)
note link <note_id> <task_id>
note delete <note_id>
```

## Mode-Aware Command Routing (Oct 2025)

**Critical Pattern:** The Textual UI has dual modes (tasks/notes), and some commands behave differently based on the active mode:

```python
# In textual_app.py on_command_input_command_submitted()

# Mode-aware 'add' routing
if cmd in ('add', 'a'):
    if self.state.current_mode == 'notes':
        self.action_add_note()  # Creates note
    else:
        self.action_add_task()  # Creates task
    return

# Mode-aware 'edit' routing
if cmd in ('edit', 'e'):
    if self.state.current_mode == 'notes':
        # Get selected note...
        self.action_edit_note()
    else:
        # Parse task ID if provided...
        self.action_edit_task()
    return
```

**Tests:** `tests/test_mode_aware_routing.py` covers 17 scenarios

## File Safety System

**Three-layer protection** (core/file_safety.py):

1. **File Locking** (`portalocker`) - Prevents concurrent writes, 5s timeout
2. **Atomic Writes** (`tempfile` + `os.replace()`) - Never partial writes
3. **Rotating Backups** - `.backup`, `.backup.1`, `.backup.2` with auto-recovery

**Usage:**
```python
SafeFileManager.save_json_with_lock(filepath, data)
SafeFileManager.load_json_with_lock(filepath)
```

**Files Protected:**
- `tasks.json` - Task data
- `notes/*.json` - Individual note files
- `~/.todo_cli_ai_history.json` - AI conversation history
- `~/.todo_cli_settings.json` - User preferences

## Persistence

- **Tasks:** `tasks.json` (auto-save on exit)
- **Notes:** `notes/*.json` (one file per note, auto-save on edit)
- **Settings:** `~/.todo_cli_settings.json` (sort, filter, view_mode, page)
- **AI History:** `~/.todo_cli_ai_history.json` (last 20 messages + full history)

## Testing

**Run tests:**
```bash
pytest                       # All tests
pytest -v --tb=short         # Verbose with short tracebacks
pytest -m unit               # Unit tests only
pytest tests/test_file.py::test_function  # Specific test
```

**Markers:**
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (skip with `-m "not slow"`)
- `@pytest.mark.file_io` - File I/O tests
- `@pytest.mark.benchmark` - Performance tests

**Key Test Files:**
- `test_mode_aware_routing.py` - Mode-aware command routing
- `test_filter_parser.py` - Advanced filtering logic
- `test_file_safety.py` - File locking and atomic writes
- `test_state.py` - State management and caching
- `test_notes_repo.py` - Notes CRUD operations
- `conftest.py` - Shared fixtures (in_memory_state, temp_tasks_file, etc.)

## Versioning & Releases

**Single source of truth:** `VERSION` file (e.g., `0.1.0`)

**Display version:**
```bash
python main.py --version    # CLI
# Textual header shows: "Todo CLI (Textual) • v0.1.0"
```

**Smart Commit Flow (for Claude Code):**

1. Analyze staged changes: `git diff --cached --name-only`
2. Determine bump level:
   - **MAJOR:** Breaking changes (data formats, CLI flags, incompatible behavior in models/, core/state.py, core/commands.py)
   - **MINOR:** New features (`feat:` commits, new UI elements in core/, textual_*, ui/)
   - **PATCH:** Bug fixes (`fix:`, refactors, perf tweaks)
   - **NO BUMP:** Docs-only, tests-only, comments-only
3. If bumping:
   - Update `VERSION` file
   - Update `CHANGELOG.md` (move "Unreleased" → new version with date)
   - Commit: `chore(release): vX.Y.Z`
   - Create tag: `git tag -a vX.Y.Z -m "vX.Y.Z"` (MUST create before pushing!)
   - Push: `git push origin <branch>` then `git push origin vX.Y.Z`

**Tag Creation Order (CRITICAL):**
```bash
# 1. Create tag locally FIRST
git tag -a v0.2.0 -m "v0.2.0"

# 2. Push commit
git push origin <branch>

# 3. Push tag
git push origin v0.2.0
```

**Common Error:** Trying to push a tag that doesn't exist locally:
```
git push origin v0.2.0
error: src refspec v0.2.0 does not match any
```

**Conventional Commit mapping:**
- `feat:` → MINOR
- `fix:` → PATCH
- `refactor:`, `perf:` → PATCH
- `docs:`, `test:`, `chore:` → NO BUMP (unless code changed)
- `!` or `BREAKING CHANGE:` → MAJOR

See: `VERSION.md` for full policy and detailed examples

## Documentation Structure

```
docs/
├── technical/              # Developer references
│   ├── TEXTUAL_TROUBLESHOOTING.md  # CSS caching, common issues
│   ├── TEXTUAL_QUICKSTART.md       # Quick start guide
│   └── TEXTUAL_AI_CHAT.md          # AI chat implementation
├── history/                # Historical records (31 files)
│   ├── BUGFIX_*.md         # Bug fix documentation
│   └── PHASE*.md           # Phase completion reports
└── tasks/                  # Planning documents
    └── task-*.md           # Feature planning

# Root docs (user-facing)
readme.md                   # Main entry point
USAGE_GUIDE.md              # Command reference
QUICK_REFERENCE.md          # Cheat sheet
MIGRATION_GUIDE.md          # UI switching guide
CLAUDE.md                   # This file
```

## Known Issues

### AIInput Message Routing Bug (Oct 2025)

**Symptom:** `AIInput.PromptSubmitted` messages not delivered to app handler

**Workaround in textual_widgets/ai_input.py:**
```python
self.post_message(message_obj)  # Textual framework - not routing

# WORKAROUND: Manual invocation
if hasattr(self.app, 'on_ai_input_prompt_submitted'):
    self.app.on_ai_input_prompt_submitted(message_obj)
```

**Status:** Workaround functional. May be upstream Textual framework issue.

**Debug:** Full event flow in `debug_ai_flow.log`

## Debug Logging

**Implementation:** `debug_logger.py`

```python
from debug_logger import debug_log

debug_log.info("App initialized")
debug_log.debug(f"Processing: {data}")
debug_log.error("Failed to save", exception=e)
```

**Features:**
- Writes to `debug_ai_flow.log`
- Rolling limit: 2000 lines max, trims to 1500
- Thread-safe with proper locking
- Exception logging with stack traces
- 12-step AI flow tracing

**User benefit:** Attach log file when reporting bugs

### Emoji-Prefixed Logging Pattern

**All panel methods use consistent format: `[PANEL_NAME] emoji message`**

```python
# Panel lifecycle
debug_log.info(f"[NOTE_DETAIL] 🟢 Panel mounted for note {self._note_data.id[:8]}")

# Button events
debug_log.info(f"[TASK_EDIT] ✅ Button pressed: {event.button.id}")
debug_log.info("[TASK_EDIT] → Calling action_save()")

# Action methods
debug_log.info("[NOTE_EDIT] 💾 action_save() called")
debug_log.info(f"[NOTE_EDIT] ✅ Note created: {title}")

# Delete operations
debug_log.info(f"[TASK_DETAIL] 🗑️ action_delete_task() called for task #{task_id}")
debug_log.info(f"[NOTE_DETAIL] User confirmed: {confirmed}")

# Navigation
debug_log.info("[NOTE_DETAIL] 🔙 action_back_to_list() called")
debug_log.info("[TASK_DETAIL] ✏️ action_edit_task() called")

# Errors
debug_log.info("[NOTE_DETAIL] ❌ Delete cancelled by user")
```

**Emoji Convention:**
- 🟢 - Lifecycle events (mount, unmount)
- ✅ - Success, confirmation
- → - Action dispatch
- 💾 - Save operations
- 🗑️ - Delete operations
- 🔙 - Navigation (back)
- ✏️ - Edit operations
- ❌ - Errors, cancellations

**Coverage Status:**
- TaskDetailPanel: 100% (5 methods)
- NoteDetailPanel: 100% (5 methods)
- TaskEditPanel: 90% (button handler + action_save)
- NoteEditPanel: 90% (button handler + action_save)

## Recent Major Changes (Oct 2025)

### Unreleased - Critical Bug Fixes (Oct 2025)
- **Edit Panel Cancel Button**: Fixed WorkerError crash from incorrect `run_worker()` usage
- **Notes Mode Display**: Fixed dual mode system desynchronization (`entity_mode` vs `left_panel_mode`)
- **Button Event Bubbling**: Fixed buttons triggering 7x per click (added `event.stop()`)
- **Debug Logging**: Added comprehensive logging to NoteDetailPanel (0% → 100% coverage)
- All panels now have 90-100% logging coverage with emoji-prefixed format

### v0.2.0 - Theme System Refactoring
- Removed complex runtime theme switching (Ctrl+T removed)
- Implemented simple config-based approach (~/.todo_cli_theme.json)
- Theme changes now require app restart (predictable, maintainable)
- Deleted 380+ lines of theme switching code
- New core/theme_config.py module for clean separation
- Maintains both dark and light themes (dark default)

### v0.1.1 - Mode-Aware Commands & UX Fixes
- Mode-aware `add` and `edit` commands (respect tasks/notes mode)
- Note creation UX: proper "Create Note" header, clean cancel
- Fixed TaskForm critical bug (`_task` → `_task_data`)
- 17 new tests for mode-aware routing

### v0.1.0 - Comprehensive Bug Fixes
- Fixed command prompt visibility (now visible by default)
- Fixed detail view task selection (edit/delete targets correct task)
- Fixed event bubbling (commands execute exactly once)
- Fixed AI streaming crashes (thread-safe worker pattern)
- Filter caching optimization (95%+ cache hit rate)
- AI input validation (5000 char limit, control character sanitization)

See: `docs/history/BUGFIX_COMPREHENSIVE_TEXTUAL_2025.md`

## Development Notes

- Tags normalized to lowercase on add/edit
- Priority: 1-3 (lower = higher)
- Edit command: "-" sentinel skips field update
- Page size: 20 (compact), 10 (detail)
- Filter changes reset pagination to page 0
- ESC clears input instantly
- Bulk operations (>3 items) show confirmation dialogs
- Modal forms fall back to inline if terminal incompatible

## Common Pitfalls

1. **Don't use `CSS_PATH`** - Use inline `CSS` string only
2. **Don't use `self._task` in widgets** - Use `self._task_data`
3. **Don't forget `@work` on modals** - Required for `push_screen_wait()`
4. **Don't wrap `@work` methods with `run_worker()`** - Causes WorkerError (double-wrapping)
5. **Don't skip `call_from_thread()`** - Required for worker UI updates
6. **Don't forget `event.stop()` in button handlers** - Causes 7+ triggers per click
7. **Don't update `entity_mode` without `left_panel_mode`** - Causes mode desync (notes not displaying)
8. **Don't hardcode mode assumptions** - Check `state.current_mode` for mode-aware commands
