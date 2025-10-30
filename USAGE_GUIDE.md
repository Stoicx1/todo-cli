# 📖 Todo CLI - Complete Usage Guide

## Command Input with Suggestions

### Version
Show current app version from the CLI:
```bash
python main.py --version
# or
python main.py -v
```
The Textual UI header also appends the version to the title (e.g., `Todo CLI (Textual) • v0.1.0`).

### How It Works

The command input uses Textual's inline suggestion system (Suggester) to offer real-time completions as you type.

### Usage

#### 1. **Typeto see all commands**

When you type `/`, the command input activates and shows suggestions grouped by category:

```
📊 Tasks: 31 | ✅ Done: 15 | ⏳ Todo: 16 | ... (Status Line)
❯ Type / for commands › /
   ┌─────────────────────────────────────────────────────────────┐
   │ ➕ add          📝 Task Management → Add a new task         │
   │ ✏️ edit         📝 Task Management → Edit an existing task  │
   │ ✅ done         📝 Task Management → Mark task as complete   │
   │ 🔄 undone       📝 Task Management → Mark task incomplete    │
   │ 🗑️ remove       📝 Task Management → Delete a task          │
   │ 📋 view compact 👁️ View Controls → Switch to compact view    │
   │ ... (more commands)                                          │
   └─────────────────────────────────────────────────────────────┘
```

**Features:**
- **Icons** show what each command does
- **Category** shows where the command belongs
- **Description** explains the command's purpose
- **Arrow keys** (↑↓) navigate through the list
- **Enter** or **Tab** selects the command

#### 2. **Type+ text to filter commands**

As you continue typing after `/`, the list filters to show only matching commands:

```
❯ Type / for commands › /fil
   ┌─────────────────────────────────────────────────────────────┐
   │ ✓ filter done   🔧 Filters & Sort → Show completed tasks    │
   │ ○ filter undone 🔧 Filters & Sort → Show incomplete tasks   │
   │ 🔓 filter none   🔧 Filters & Sort → Clear all filters       │
   │ 🏷️ filter tag:   🔧 Filters & Sort → Filter by tag          │
   └─────────────────────────────────────────────────────────────┘
```

**Fuzzy matching** - Searches anywhere in the command name!

Examples:
- `/add` → Shows "add" command
- `/fil` → Shows all "filter" commands
- `/done` → Shows "done", "undone", "filter done"
- `/tag` → Shows "filter tag:", "tags"

#### 3. **Type commands directly (without `/`)**

You can also start typing command names directly, and suggestions will appear inline:

```
❯ Type / for commands › add
   ┌─────────────────────────────────────────────────────────────┐
   │ ➕ add          Add a new task                              │
   └─────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
|| Activate command input |
| `Tab` | Accept suggestion |\r\n| `Up`/`Down` | Command history |
| `Enter` | Execute selected command |
| `Esc` | Clear input buffer (clears what you typed) |
| `Ctrl+C` | Exit application |

---

## 📊 Two-Line Status Display

### Reorganized Interface (Updated 2025-10-20)

The UI has **two status lines** + one prompt line:

#### Line 1: **Navigation & View Context**
```
📄 Page 1/2 | 👁️ 20/29 showing | 🎨 compact | ⬆️ priority (asc)
```

**What it shows:**
- 📄 **Page**: Current page / total pages
- 👁️ **Showing**: Tasks visible / total tasks
- 🎨 **View**: View mode (compact=20/page, detail=10/page)
- ↕️ **Sort**: Current sort method and order (e.g., priority (ASC|DESC))

#### Line 2: **Task Statistics**
```
📊 29 tasks | ✅ 15 done | ⏳ 14 todo
```

**What it shows:**
- 📊 **Tasks**: Total number of tasks
- ✅ **Done**: Completed tasks count
- ⏳ **Todo**: Incomplete tasks count
- 🔍 **Filter** (if active): Shows current filter (e.g., "tag:psdc")

#### Line 3: **Prompt Line** (Input)
Where you type commands - INTERACTIVE

```
❯ Type / for commands ›
```

**Features:**
- Clean, minimal design
- Helpful hint text
- Press ESC to clear input

---

## 🎨 Complete Command Reference

### 📝 Task Management

| Command | Usage | Description |
|---------|-------|-------------|
| `add` | `add` | Opens inline form to add a new task |
| `edit <id>` | `edit 5` | Opens inline form to edit task #5 |
| `done <id>` | `done 5` | Marks task #5 as complete |
| `undone <id>` | `undone 5` | Marks task #5 as incomplete |
| `remove <id>` | `remove 5` | Deletes task #5 |
| `show <id>` | `show 5` | Shows full details of task #5 |

### 👁️ View Controls

| Command | Usage | Description |
|---------|-------|-------------|
| `view compact` | `view compact` | Show 20 tasks per page (no details) |
| `view detail` | `view detail` | Show 10 tasks per page with comments/descriptions |

### 🧭 Navigation

| Command | Usage | Description |
|---------|-------|-------------|
| `next` | `next` | Go to next page |
| `prev` | `prev` | Go to previous page |

### 🔧 Filters & Sorting

| Command | Usage | Description |
|---------|-------|-------------|
| `filter done` | `filter done` | Show only completed tasks |
| `filter undone` | `filter undone` | Show only incomplete tasks |
| `filter none` | `filter none` | Clear all filters (show all) |
| `filter tag:<name>` | `filter tag:psdc` | Show only tasks with tag "psdc" |
| `sort priority [asc|desc]` | `sort priority desc` | Sort by priority (1→3 asc, 3→1 desc) |
| `sort id [asc|desc]` | `sort id asc` | Sort by task ID (asc = oldest first) |
| `sort name [asc|desc]` | `sort name desc` | Sort alphabetically (asc = A→Z) |
| `sort order [asc|desc]` | `sort order asc` | Set sort order without changing field |
| `tags` | `tags` | List all tags with completion stats |

### ℹ️ Information & Analytics

| Command | Usage | Description |
|---------|-------|-------------|
| `insights` | `insights` | Show comprehensive task analysis (local AI) |
| `suggest` | `suggest` | Get smart recommendations (local AI) |
| `help` | `help` | Show full command reference |

### 🤖 AI Assistant (Requires API Key)

| Command | Usage | Description |
|---------|-------|-------------|
| `?` | `?` | Ask GPT for task advice |

### ⚙️ System

| Command | Usage | Description |
|---------|-------|-------------|
| `cls` | `cls` | Clear screen and refresh dashboard |
| `clear` | `clear` | Same as cls |
| `c` | `c` | Shortcut for cls |
| `exit` or `quit` | `exit` | Save and exit the application |

---

## 🤖 Local AI Features (No API Required!)

### Insights Command

Get comprehensive task analysis:

```bash
❯ insights
```

**Shows:**
- Total tasks, completion rate
- Priority distribution with ASCII chart
- Tag summary with completion rates
- Smart suggestions based on your workload
- Recommended next tasks to work on

**Example Output:**
```
📊 Task Insights
────────────────────────────────────────
Total Tasks:     31
Completed:       15 (48.4%)
Incomplete:      16

Priority Distribution (Incomplete Tasks):
  🔴 High   [ 3]: ███
  🟡 Medium [ 8]: ████████
  🟢 Low    [ 5]: █████

Tag Summary:
  🏷️ psdc            → 10/16 (62%)
  🏷️ work            → 5/8 (62%)
  🏷️ personal        → 0/7 (0%)

💡 Smart Suggestions:
  ⚠️ You have 3 high-priority tasks. Consider focusing on these first.
  📊 Most active tag: 'psdc' (16 tasks)

⚡ Recommended Next Tasks:
  1. 🔴 [6] PSDC PAA1 – Merge Local HMIs
  2. 🔴 [7] PSDC – Complete HMI Translations
  3. 🟡 [9] PSDC FA040 – Conditional Unload
```

### Suggest Command

Get quick, actionable suggestions:

```bash
❯ suggest
```

**Shows:**
- Workload assessment
- Priority-based recommendations
- Tag utilization insights
- Productivity tips

---

## 💡 Pro Tips & Workflows

### 1. **Quick Task Completion Workflow**

```bash
# Show only incomplete tasks
/filter undone

# Type / and arrow down to "done" commands
/done

# Or just start typing the task ID
done 5
```

### 2. **Focus on High Priority**

```bash
# Filter to incomplete tasks
filter undone

# Sort by priority
sort priority

# Work through top tasks
done 6
done 7
done 9
```

### 3. **Work by Project Tag**

```bash
# See all tags
tags

# Filter to specific project
filter tag:psdc

# Get insights for this project
insights
```

### 4. **Daily Planning Routine**

```bash
# 1. Check insights
insights

# 2. Filter to incomplete
filter undone

# 3. Sort by priority (descending)
sort priority desc

# 4. Review suggested tasks
suggest

# 5. Start working!
```

### 5. **Bulk Task Entry**

```bash
# Type / to open command palette
/

# Arrow to "add"
# Press Enter

# Fill in the inline form
# Repeat as needed
```

---

## 🎯 Advanced Features

### Command History

The app remembers your recent commands. Use:
- `↑` arrow to go back through history
- `↓` arrow to go forward

History is saved in `~/.todo_cli_history`

### Preferences Persistence

Your view and sorting preferences persist between runs.

- Stored at: `~/.todo_cli_settings.json`
- Includes: `sort`, `sort_order`, `view_mode`, and `filter`
- Loaded on startup, saved on save/exit
- Safe to delete if you want to reset preferences

### Fuzzy Search

Suggestions support fuzzy matching:
- `/ed` matches "edit"
- `/rmv` matches "remove"
- `/ftag` matches "filter tag:"

### Auto-completion Everywhere

Start typing any command and suggestions appear:
- `add` → shows "add" command
- `fil` → shows all filter commands
- `sort` → shows all sort options

### Inline Forms

Commands `add` and `edit <id>` open interactive forms:
- Pre-filled with defaults or current values
- Press Enter to skip fields
- All fields validated before saving

---

## 🛡️ Error Handling & Help Messages

All commands now provide helpful error messages when used incorrectly:

### Example: Missing Argument
```bash
❯ done
[!] Usage: done <id>
    Example: done 3
```

### Example: Invalid Argument
```bash
❯ done abc
[!] Invalid task ID: "abc"
    Usage: done <id>
    Example: done 3
```

### Example: Wrong Command Format
```bash
❯ add
[!] Usage: add "name" ["comment"] ["description"] [priority] ["tag"]
    Example: add "Fix bug" "urgent" "Fix the login issue" 1 "work"
```

### Commands with Improved Error Messages:
- ✅ `done <id>` - Shows usage when ID missing or invalid
- ✅ `undone <id>` - Shows usage when ID missing or invalid
- ✅ `remove <id>` - Shows usage when ID missing or invalid
- ✅ `add` - Shows full syntax with example
- ✅ `edit <id>` - Shows usage when ID missing
- ✅ `show <id>` - Shows usage when ID missing
- ✅ All other commands validate input properly

**No more crashes!** Every command handles errors gracefully.

---

## 🐛 Troubleshooting

### Command input not focusing?\r\n\r\nPressto focus the command input\r\n\r\n### Commands not filtering?

**Cause**: Not typingfirst

**Solution**: Pressto focus the command input

### Status line not showing?

**Cause**: Console clearing issue

**Solution**: Run `exit` and restart the app

### Suggestions showing wrong commands?

**Cause**: Suggestions cache is stale

**Solution**: Restart the app (suggestions refresh on startup)

---

## 📚 Additional Resources

- **README.md** - Installation and quick start
- **CLAUDE.md** - Developer documentation
- **requirements.txt** - Required dependencies

---

**Need help?** Type `help` in the app orto browse all available commands!

## Age Support (Oct 2025)
- Column layout: `ID | Age | Prio | Tags | Task`
- Sort: `sort age [asc|desc]` (asc = youngest first)
- Filter: `filter age>=3d`, `filter age<=2h`, `filter age>=30m`
- Age is derived from `created_at` and cannot be set directly
- Filter: ilter age>=3d, ilter age<=2h, ilter age>=30m`n- Age is derived from created_at and cannot be set directly
 
---
 
## 🔄 Mode-Aware Commands (Textual UI)

The Textual UI supports **dual-mode operation** for tasks and notes. The `add` and `edit` commands automatically adapt based on your current mode:

### Switching Modes
```bash
mode tasks                   # Switch to tasks view
mode notes                   # Switch to notes view
m                           # Keyboard shortcut: toggle mode
```

### Add Command (Mode-Aware)
```bash
# In TASKS mode:
add                         # Opens task form (⌨️ shortcut: a)

# In NOTES mode:
add                         # Opens note editor with "Create Note" header (⌨️ shortcut: a)
```

### Edit Command (Mode-Aware)
```bash
# In TASKS mode:
edit 5                      # Edits task #5 (⌨️ shortcut: e)

# In NOTES mode:
edit abc12345               # Edits note by ID prefix (⌨️ shortcut: e)
```

**Note:** The `remove`, `open` (Enter), and `delete` (d) commands are also mode-aware.

---

## 📝 Notes (Offline)
- Files live in `notes/` as Markdown with YAML front matter (id, title, tags, task_ids, timestamps).
- Link notes to tasks via `task_ids` in the front matter (managed by commands).

Commands
```bash
mode notes                     # Switch to notes list
notes [task_id|query]          # List/search notes (or for a task); sets Notes mode with paging (use next/prev)
notes clear                    # Clear notes filters and show all
note new --title "..." [--task 12] [--tag x]
note edit <note_id_prefix>     # Open in $EDITOR
note link <note_id> <task_id>  # Link/unlink
note unlink <note_id> <task_id>
note delete <note_id_prefix>   # Delete notes by id prefix
note duplicate <note_id_prefix> [--title '...'] [--task 12]
```

 
