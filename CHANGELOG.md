# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

## [0.2.0] - 2025-10-27

### Added
- **Notes Feature** - Complete note-taking system integrated with tasks
  - Create, edit, delete, and search notes with full-text search
  - Link notes to tasks (many-to-many relationship)
  - Tag-based organization separate from task tags
  - External editor support (Notepad, VS Code, Vim)
  - Dual-mode UI: Toggle between tasks view and notes view with `m` key
  - Markdown support for rich note content
  - AI integration: GPT can create, edit, search, and link notes
  - Persistent storage in `notes/` directory (one JSON file per note)

- **New Models & Services**:
  - `models/note.py` - Note dataclass with id, title, body, tags, task_links
  - `services/notes_repo.py` - NotesRepository for CRUD operations and search

- **New UI Widgets** (Textual):
  - `textual_widgets/note_table.py` - Notes list view with search/filter
  - `textual_widgets/note_editor_modal.py` - Note editing with external editor
  - `textual_widgets/note_detail_modal.py` - Note detail view
  - `textual_widgets/link_task_picker.py` - Task linking modal
  - `textual_widgets/title_prompt.py` - Title input modal
  - `textual_widgets/context_footer.py` - Context-aware footer

- **New Utilities**:
  - `utils/version.py` - get_version() reads VERSION file or derives from git
  - `utils/ids.py` - Unique ID generation for notes
  - `utils/editor.py` - External editor integration

- **New AI Tools** (for GPT agent):
  - `create_note()` - Create note with title, body, tags, task links
  - `edit_note()` - Edit existing note (append/replace/prepend modes)
  - `search_notes()` - Full-text search across notes
  - `get_note_details()` - Retrieve note by ID
  - `link_note_to_task()` / `unlink_note_from_task()` - Manage relationships
  - `convert_note_to_task()` - Transform note into task
  - `open_note_in_editor()` - Launch external editor

- **Testing**:
  - `tests/conftest.py` - Shared fixtures (in_memory_state, temp files)
  - `tests/test_mode_aware_routing.py` - 17 tests for dual-mode commands
  - `tests/test_notes_repo.py` - Notes CRUD and search tests
  - `tests/test_ai_note_tools.py` - AI tool integration tests
  - `tests/integration/` - End-to-end integration tests
  - `pytest.ini` - Test configuration with markers

- **Documentation**:
  - `VERSION` - Single source of truth for version (0.2.0)
  - `VERSION.md` - Versioning policy and workflow guide
  - `CHANGELOG.md` - This file (Keep a Changelog format)
  - Updated `CLAUDE.md` - Refactored from 1004 to 413 lines (59% reduction)
  - Updated `readme.md` - Notes feature documentation
  - Updated `USAGE_GUIDE.md` - Notes commands reference
  - Updated `QUICK_REFERENCE.md` - Notes shortcuts

### Fixed
- **Mode-Aware Commands**: `add`/`a` and `edit`/`e` now respect current mode
  - In **tasks mode**: `a` opens task form, `e` edits task
  - In **notes mode**: `a` creates note, `e` edits note
  - Consistent behavior between keyboard shortcuts and commands

- **Note Creation UX**:
  - Modal shows "Create Note" header when adding (was "Edit Note")
  - Pressing Esc during creation properly cancels (no orphaned empty notes)
  - Applied to both `Ctrl+N` (new note) and `Shift+N` (quick note)

- **TaskForm Critical Bug**:
  - Fixed `AttributeError: '_asyncio.Task' object has no attribute 'name'` crash
  - Renamed `self._task` → `self._task_data` (avoid Textual framework collision)
  - Updated CLAUDE.md with widget naming best practices

- **Command Input Focus**: Improved focus management in Textual UI
- **Status Bar**: Enhanced display with mode indicator and context

### Changed
- **Command System**: Mode-aware command routing in `textual_app.py`
  - Commands adapt to current context (tasks vs notes)
  - Command descriptions reflect mode-awareness

- **State Management**: Extended AppState with notes support
  - `state.notes` - List of all notes
  - `state.current_mode` - "tasks" | "notes"
  - Mode-aware filtering and pagination

- **AI Tools**: Expanded core/ai_tools.py with 8 new note-related tools
- **File Safety**: Enhanced SafeFileManager for notes directory
- **Requirements**: Added `pyperclip` for clipboard support

### Removed
- `app.py` - Consolidated into main.py

## [0.1.0] - 2025-10-26
- Initial tracked version
- Basic task management with Textual UI
- AI chat integration
- Filter caching and performance optimizations

