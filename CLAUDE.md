# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based terminal task management CLI application built with `rich` for UI rendering and `prompt_toolkit` for interactive input. The application provides a dashboard-style interface for managing tasks with features like filtering, sorting, pagination, and GPT-powered task assistance.

## Running the Application

```bash
python main.py
```

The application runs in an interactive REPL loop. Tasks are persisted to `tasks.json`.

## Architecture

### Core Structure

The application follows a simple MVC-like pattern:

- **main.py**: Entry point, main loop, inline input forms, keyboard bindings (ESC to clear input)
- **core/state.py**: `AppState` class - central state management (tasks list, pagination, filters, sorting, messages)
- **core/commands.py**: Command parsing and handlers for all CLI commands with error validation
- **core/suggestions.py**: Local AI insights system (no API required)
- **ui/renderer.py**: `render_dashboard()` - renders table + two-line status display using Rich
- **ui/command_palette.py**: Command completion system with dropdown filtering
- **models/task.py**: `Task` dataclass representing individual tasks
- **assistant.py**: GPT integration (OpenAI API) for task analysis and suggestions (optional)

### State Management Flow

1. User input → `handle_command()` in `core/commands.py`
2. Command handlers mutate `AppState` (update tasks, change filters/sort, add messages)
3. `render_dashboard()` calls `state.get_current_page_tasks()` which chains:
   - Filter tasks via `get_filter_tasks()`
   - Sort tasks via `get_sorted_tasks()`
   - Paginate based on current page and page size
4. Dashboard re-renders with updated state

### Key State Properties

- `state.tasks`: Full task list in memory
- `state.page`: Current page index (0-based)
- `state.page_size`: Dynamically set based on view mode (20 for compact, 10 for detail)
- `state.view_mode`: "compact" or "detail"
- `state.filter`: "none", "done", "undone", or "tag:<tagname>"
- `state.sort`: "priority", "id", or "name"
- `state.messages`: Status messages displayed in a panel below the dashboard

### Command System

All commands are parsed via `shlex.split()` to handle quoted strings properly. Command format:

```
add "Task Name" "Comment" "Description" priority "tag"
edit <id> "name" "comment" "description" priority "tag"
done <id>
undone <id>
remove <id>
show <id>
view compact|detail
next/prev
sort id|name|priority
filter none|done|undone|tag:<tagname>
tags
insights (local AI analysis)
suggest (local AI suggestions)
cls|clear|c (clear screen)
? (GPT assistance - requires API key)
help
exit|quit
```

The `add` and `edit` commands support inline interactive forms when called with just the command name or ID.

### Inline Forms

When a user types `add` or `edit <id>`, the application prompts for individual fields interactively (see `inline_add_task()` and `inline_edit_task()` in main.py:8-32), then reconstructs the full command string and passes it to `handle_command()`.

### GPT Integration

The `?` command triggers `assistant.py` which:
- Formats current task list as plain text
- Prompts user for a question/request
- Sends to OpenAI GPT-4o-mini API with system prompt "You are a helpful assistant for managing tasks"
- Displays response in the status panel

Requires `OPENAI_API_KEY` in `.env` file.

### Persistence

Tasks are saved/loaded from `tasks.json`:
- Auto-saved on exit/interrupt
- Loaded on startup via `state.load_from_file()`
- Uses Python's `json` module with task dictionaries

### UI Rendering

Uses `rich.table.Table` with alternating row colors (black/white backgrounds). The status panel at the bottom shows the last message from `state.messages`.

## UI Components

### Command Palette (`ui/command_palette.py`)
- Custom `CommandCompleter` class implementing prompt_toolkit's Completer interface
- 24 commands organized into 7 categories (Task Management, View Controls, Navigation, Filters & Sort, Information, AI Assistant, System)
- Unicode/emoji detection for Windows CP1252 compatibility via `USE_EMOJI` flag
- Three completion modes:
  1. Type `/` - Show all commands with icons and descriptions
  2. Type `/text` - Filter commands by text
  3. Type `text` - Direct command completion without slash

### Status Display (`ui/renderer.py`)
- Two-line status format (reorganized 2025-10-20):
  - **Line 1** (Navigation): page | showing | view | sort
  - **Line 2** (Statistics): tasks | done | todo | filter (if active)
- Unicode fallback for Windows terminals (emojis replaced with text labels)
- Uses `USE_UNICODE` flag to detect encoding support

### Keyboard Bindings (`main.py`)
- **ESC key** clears input buffer via custom KeyBindings
- History navigation with ↑/↓ arrows
- Tab completion integrated with prompt_toolkit
- Transparent dropdown background via custom Style

## Recent Bug Fixes (2025-10-20)

### Crash Prevention
All command handlers now validate input before processing to prevent IndexError and UnboundLocalError crashes:

1. **`done` / `undone` / `remove`** - Check for missing task ID argument
2. **`add`** - Initialize all variables (name, comment, description, priority, tag) with defaults before conditional logic
3. **All commands** - Show helpful error messages with syntax and examples instead of crashing

### Error Message Format
```
[!] Error description
    Usage: command syntax
    Example: concrete example with real values
```

**Example:**
```
❯ done
[!] Usage: done <id>
    Example: done 3
```

### Unicode/Encoding Compatibility
- Detects Windows CP1252 encoding vs UTF-8
- Falls back to ASCII when Unicode not supported:
  - Prompt symbols: `❯ ›` → `> >`
  - Dropdown icons: `➕ ✏️` → `>`
  - Status emojis: `📊 ✅ ⏳` → plain text labels
- Applied to: `main.py`, `ui/command_palette.py`, `ui/renderer.py`

## Development Notes

- All task tags are normalized to lowercase on add/edit
- Priority is an integer (typically 1-3, lower = higher priority)
- The `edit` command uses "-" as a sentinel to skip updating a field
- Page size adjusts automatically when switching view modes (20 for compact, 10 for detail)
- Filter changes reset pagination to page 0
- Commands are crash-proof with validation and helpful error messages
- ESC key clears input buffer instantly
- `cls`, `clear`, or `c` commands refresh the screen
