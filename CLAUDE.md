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

### 5. Event Bubbling Prevention

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    # ... handle input ...

    # REQUIRED to prevent duplicate execution
    event.stop()
    event.prevent_default()
```

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
├── note.py           # Note dataclass (id, title, body, tags, task_links, created_at)
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
   - Suggest tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`

**Conventional Commit mapping:**
- `feat:` → MINOR
- `fix:` → PATCH
- `refactor:`, `perf:` → PATCH
- `docs:`, `test:`, `chore:` → NO BUMP (unless code changed)
- `!` or `BREAKING CHANGE:` → MAJOR

See: `VERSION.md` for full policy

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

## Recent Major Changes (Oct 2025)

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
4. **Don't skip `call_from_thread()`** - Required for worker UI updates
5. **Don't forget event.stop()** - Required to prevent bubbling
6. **Don't hardcode mode assumptions** - Check `state.current_mode` for mode-aware commands
