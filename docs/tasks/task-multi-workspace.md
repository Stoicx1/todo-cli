# Multi-Workspace Todo CLI - Implementation Plan

## 📋 Comprehensive Review

### Current Architecture
- **Single file**: `tasks.json` stores all tasks
- **Data location**: Project root directory
- **State management**: `AppState` class handles single task list
- **Persistence**: Manual load on startup, auto-save on exit

### Proposed Enhancement: Multi-Workspace System

## 🎯 Design Goals
1. **Simple & Intuitive**: Easy workspace switching with minimal commands
2. **Backward Compatible**: Existing `tasks.json` migrates to default workspace
3. **Best Practices**: Follow XDG conventions for data storage
4. **Transparent**: No breaking changes to existing commands

---

## 📁 Folder Structure & Naming Conventions

### Recommended: `.todo-data/` (data directory pattern)
```
D:\MyProjects\todo-cli\
├── .todo-data/              # Data folder (gitignored)
│   ├── default.json         # Default workspace
│   ├── work.json            # Work tasks
│   ├── personal.json        # Personal tasks
│   ├── psdc.json            # Project-specific tasks
│   └── config.json          # Workspace metadata
├── tasks.json               # Legacy (auto-migrated)
├── core/
├── models/
└── ui/
```

**Rationale for `.todo-data/`:**
- ✅ Hidden dot-prefix keeps data organized
- ✅ Clear purpose (`-data` suffix)
- ✅ Follows conventions: `.git/`, `.vscode/`, `.pytest_cache/`
- ✅ Easy to gitignore
- ✅ Separate from code structure

**Alternative Options Considered:**
- `data/` - Too generic, might conflict
- `workspaces/` - Verbose, not a convention
- `.tasks/` - Confusing with `tasks.json`

---

## 🏗️ Implementation Plan (5 Steps)

### **Step 1: Create Workspace Manager**
**File:** `core/workspace.py`
- `WorkspaceManager` class to handle:
  - List available workspaces
  - Switch between workspaces
  - Create/delete workspaces
  - Auto-migrate `tasks.json` → `.todo-data/default.json`
- Config file: `.todo-data/config.json` stores:
  - Last active workspace
  - Workspace metadata (created date, task count)

**Key Methods:**
```python
class WorkspaceManager:
    def __init__(self, data_dir=".todo-data")
    def list_workspaces() -> List[WorkspaceInfo]
    def switch_workspace(name: str) -> bool
    def create_workspace(name: str) -> bool
    def delete_workspace(name: str, confirm: bool) -> bool
    def rename_workspace(old_name: str, new_name: str) -> bool
    def get_current_workspace() -> str
    def get_workspace_path(name: str) -> str
    def migrate_legacy_tasks() -> bool
```

### **Step 2: Update AppState**
**File:** `core/state.py`
- Add `current_workspace: str` property
- Update `load_from_file()` to accept workspace name
- Update `save_to_file()` to use current workspace path
- Auto-detect and migrate legacy `tasks.json` on first run

**Changes:**
```python
class AppState:
    def __init__(self, workspace_manager: WorkspaceManager = None):
        # ... existing init code ...
        self.workspace_manager = workspace_manager
        self.current_workspace = "default"

    def load_workspace(self, workspace_name: str, console: Console):
        """Load tasks from specified workspace"""
        path = self.workspace_manager.get_workspace_path(workspace_name)
        self.load_from_file(path, console)
        self.current_workspace = workspace_name

    def save_current_workspace(self, console: Console):
        """Save tasks to current workspace"""
        path = self.workspace_manager.get_workspace_path(self.current_workspace)
        self.save_to_file(path, console)
```

### **Step 3: Add Workspace Commands**
**File:** `core/commands.py`
- `workspace list` (alias: `ws list`) - Show all workspaces
- `workspace switch <name>` (alias: `ws <name>`) - Switch workspace
- `workspace new <name>` - Create new workspace
- `workspace delete <name>` - Delete workspace (with confirmation)
- `workspace rename <old> <new>` - Rename workspace

**Command Handlers:**
```python
def handle_workspace(command_arguments: list, state: AppState, console: Console):
    """
    Handle workspace subcommands:
    - workspace list / ws list
    - workspace switch <name> / ws <name>
    - workspace new <name>
    - workspace delete <name>
    - workspace rename <old> <new>
    """
    if len(command_arguments) < 2:
        state.messages.append('[!] Usage: workspace list|switch|new|delete|rename')
        return

    subcommand = command_arguments[1].lower()

    if subcommand == "list":
        # List all workspaces with task counts
        workspaces = state.workspace_manager.list_workspaces()
        # Display formatted list

    elif subcommand == "switch":
        # Switch to specified workspace
        # Save current workspace first
        # Load new workspace

    elif subcommand == "new":
        # Create new workspace
        # Validate name

    elif subcommand == "delete":
        # Delete workspace with confirmation
        # Cannot delete current workspace

    elif subcommand == "rename":
        # Rename workspace
```

### **Step 4: Update Command Palette**
**File:** `ui/command_palette.py`
- Add "Workspace Management" category
- New commands with icons:
  - 📂 `workspace list` - List all workspaces
  - 🔄 `workspace switch` - Switch workspace
  - ➕ `workspace new` - Create workspace
  - 🗑️ `workspace delete` - Delete workspace

**Update Command Categories:**
```python
# Add to COMMAND_CATEGORIES
WORKSPACE_COMMANDS = [
    ("workspace list", "📂", "List all workspaces"),
    ("workspace switch", "🔄", "Switch to another workspace"),
    ("workspace new", "➕", "Create new workspace"),
    ("workspace delete", "🗑️", "Delete workspace"),
    ("workspace rename", "✏️", "Rename workspace"),
]
```

### **Step 5: Update UI Display**
**File:** `ui/renderer.py`
- Show current workspace name in status line
- Format: `📂 workspace: default | page: 1 | showing: 1-20 | ...`
- Color-code workspace name (cyan/magenta for visual distinction)

**Status Line Update:**
```python
def render_dashboard(console: Console, state: AppState):
    # ... existing code ...

    # Line 1: Navigation + Workspace
    workspace_info = f"📂 [cyan]{state.current_workspace}[/cyan]"
    page_info = f"page: {state.page + 1}"
    # ... rest of status line ...
```

---

## 🔧 Technical Details

### Migration Strategy
```python
# On first run, check for legacy tasks.json
if os.path.exists("tasks.json") and not os.path.exists(".todo-data/"):
    # Create .todo-data/ directory
    os.makedirs(".todo-data", exist_ok=True)

    # Move tasks.json → .todo-data/default.json
    shutil.move("tasks.json", ".todo-data/default.json")

    # Create config.json with default workspace
    config = {
        "version": "1.0",
        "current_workspace": "default",
        "workspaces": {
            "default": {
                "created_at": datetime.now().isoformat(),
                "task_count": len(tasks),
                "last_accessed": datetime.now().isoformat()
            }
        }
    }
    with open(".todo-data/config.json", "w") as f:
        json.dump(config, f, indent=4)

    console.print("[yellow]✓ Migrated tasks.json to workspace 'default'[/yellow]")
```

### Config Schema (`.todo-data/config.json`)
```json
{
    "version": "1.0",
    "current_workspace": "default",
    "workspaces": {
        "default": {
            "created_at": "2025-10-20T18:00:00",
            "task_count": 29,
            "last_accessed": "2025-10-20T19:30:00"
        },
        "work": {
            "created_at": "2025-10-20T18:15:00",
            "task_count": 12,
            "last_accessed": "2025-10-20T19:25:00"
        }
    }
}
```

### Workspace Validation
```python
import re

def validate_workspace_name(name: str) -> bool:
    """
    Validate workspace name:
    - Alphanumeric + hyphens/underscores only
    - Max 50 characters
    - Not reserved names
    """
    RESERVED_NAMES = ["none", "all", "config", ".", ".."]

    if not name or name in RESERVED_NAMES:
        return False

    if len(name) > 50:
        return False

    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False

    return True
```

### Command Examples
```bash
# List workspaces
❯ workspace list
📂 Available Workspaces:
  • default (29 tasks) ← current
  • work (12 tasks)
  • personal (5 tasks)

# Switch workspace
❯ workspace switch work
[💾] Saving workspace: default
[✓] Switched to workspace: work
[📂] Loaded 12 tasks

# Short alias
❯ ws work
[✓] Switched to workspace: work

# Create new workspace
❯ workspace new psdc
[+] Created workspace: psdc
[✓] Switched to workspace: psdc

# Delete workspace (with confirmation)
❯ workspace delete personal
[!] Delete workspace 'personal' with 5 tasks? (yes/no): yes
[-] Deleted workspace: personal

# Rename workspace
❯ workspace rename work office
[✓] Renamed workspace: work → office
```

---

## 🛡️ Safety Features

### 1. Prevent Data Loss
- **Confirm before deleting workspace with tasks**:
  ```python
  if task_count > 0:
      confirm = Prompt.ask(f"Delete workspace '{name}' with {task_count} tasks?",
                          choices=["yes", "no"], default="no")
      if confirm != "yes":
          return False
  ```

- **Cannot delete current workspace**:
  ```python
  if name == self.get_current_workspace():
      console.print("[red][!] Cannot delete current workspace. Switch first.[/red]")
      return False
  ```

- **Auto-save before switching**:
  ```python
  def switch_workspace(self, name: str):
      # Save current workspace first
      self.save_current_workspace()
      # Then switch and load new workspace
      self.load_workspace(name)
  ```

### 2. Validation
- **Workspace names**: Alphanumeric + hyphens/underscores only
- **Max length**: 50 characters
- **Reserved names**: "none", "all", "config", ".", ".."
- **No special characters**: Prevent path traversal attacks

### 3. Error Handling
```python
def load_workspace(self, name: str, console: Console):
    try:
        path = self.get_workspace_path(name)
        self.load_from_file(path, console)
    except FileNotFoundError:
        console.print(f"[yellow][!] Workspace '{name}' not found. Creating new.[/yellow]")
        self.create_workspace(name)
    except json.JSONDecodeError:
        console.print(f"[red][!] Corrupted workspace '{name}'. Creating backup.[/red]")
        # Create backup file
        backup_path = f"{path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(path, backup_path)
        # Initialize empty workspace
        self.tasks = []
        self.next_id = 1
```

---

## 📝 Updated `.gitignore`
```gitignore
# Data files
.todo-data/
tasks.json
*.json
!requirements.txt

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 🎨 UI Enhancements

### Status Line (Before)
```
Page: 1 | Showing: 1-20 | View: compact | Sort: priority
Tasks: 29 | Done: 15 | Todo: 14
```

### Status Line (After)
```
📂 workspace: default | Page: 1 | Showing: 1-20 | View: compact | Sort: priority
Tasks: 29 | Done: 15 | Todo: 14
```

### Command Palette Addition
```
┌─────────────────────────────────────────────────┐
│ 🗂️  Workspace Management                        │
├─────────────────────────────────────────────────┤
│ 📂 workspace list       List all workspaces     │
│ 🔄 workspace switch     Switch to workspace     │
│ ➕ workspace new        Create new workspace    │
│ 🗑️ workspace delete     Delete workspace        │
│ ✏️  workspace rename     Rename workspace        │
└─────────────────────────────────────────────────┘
```

---

## ✅ Testing Checklist

### Functionality Tests
- [ ] Legacy `tasks.json` auto-migrates to `.todo-data/default.json`
- [ ] Can create workspaces with valid names
- [ ] Can switch between workspaces
- [ ] Can delete empty workspaces
- [ ] Can delete workspaces with confirmation
- [ ] Cannot delete current workspace
- [ ] Can rename workspaces
- [ ] Tasks save to correct workspace file
- [ ] Config persists current workspace between sessions

### Validation Tests
- [ ] Invalid workspace names rejected (special chars)
- [ ] Reserved names rejected ("none", "all", "config")
- [ ] Names over 50 chars rejected
- [ ] Empty names rejected

### UI Tests
- [ ] Workspace list shows correct task counts
- [ ] Status line displays current workspace
- [ ] Command shortcuts work (`ws` alias)
- [ ] Command palette shows workspace commands
- [ ] Unicode fallback for Windows terminals

### Edge Cases
- [ ] Corrupted workspace file creates backup
- [ ] Missing workspace file creates new
- [ ] Concurrent access handled gracefully
- [ ] Very long workspace names truncated in UI
- [ ] Empty workspaces display correctly

---

## 📦 Deliverables

### New Files
1. **`core/workspace.py`** (~250 lines)
   - `WorkspaceManager` class
   - Migration logic
   - Validation functions

2. **`.todo-data/config.json`** (auto-generated)
   - Workspace metadata
   - Current workspace tracking

### Modified Files
3. **`core/state.py`** (~20 lines added)
   - Add `current_workspace` property
   - Add workspace-aware load/save methods

4. **`core/commands.py`** (~100 lines added)
   - Add `handle_workspace()` function
   - Add workspace command handlers
   - Update command shortcuts

5. **`ui/command_palette.py`** (~15 lines added)
   - Add workspace commands to palette
   - New category: "Workspace Management"

6. **`ui/renderer.py`** (~5 lines modified)
   - Show workspace in status line

7. **`main.py`** (~10 lines modified)
   - Initialize `WorkspaceManager`
   - Pass to `AppState`
   - Update save/load calls

8. **`.gitignore`** (~2 lines added)
   - Exclude `.todo-data/`
   - Keep excluding `tasks.json`

9. **`CLAUDE.md`** (~50 lines added)
   - Document workspace feature
   - Command examples
   - Architecture notes

### Documentation
10. **`task-multi-workspace.md`** (this file)
    - Complete implementation plan
    - Architecture decisions
    - Testing checklist

---

## 🚀 Implementation Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Create `core/workspace.py` | 45 min |
| 2 | Update `core/state.py` | 15 min |
| 3 | Add commands in `core/commands.py` | 30 min |
| 4 | Update `ui/command_palette.py` | 10 min |
| 5 | Update `ui/renderer.py` | 10 min |
| 6 | Update `main.py` | 10 min |
| 7 | Testing & bug fixes | 30 min |
| 8 | Documentation updates | 20 min |
| **Total** | | **~2.5 hours** |

---

## 💡 Future Enhancements (Optional)

### Phase 2 Features
1. **Workspace Templates**
   - Create workspace from template
   - Built-in templates: "project", "sprint", "daily"
   - Custom template creation

2. **Import/Export**
   - Export workspace as JSON
   - Import workspace from file
   - Merge workspaces

3. **Cloud Sync** (Advanced)
   - Dropbox/Google Drive integration
   - Auto-sync on switch
   - Conflict resolution

4. **Statistics Dashboard**
   - Workspace analytics
   - Task velocity per workspace
   - Completion rates

5. **Auto-Archive**
   - Archive old workspaces automatically
   - Move to `.todo-data/archive/`
   - Restore from archive

6. **Workspace Tags**
   - Tag workspaces (e.g., "active", "archived", "project:X")
   - Filter workspaces by tag
   - Bulk operations on tagged workspaces

---

## 🎓 Design Decisions & Rationale

### Why `.todo-data/` over other options?
1. **Hidden by default** - Dot-prefix hides from casual `ls` listings
2. **Clear semantics** - Name clearly indicates purpose
3. **Convention alignment** - Follows `.git/`, `.vscode/` patterns
4. **Separation of concerns** - Data separate from code
5. **Gitignore friendly** - Easy to exclude from version control

### Why `config.json` over database?
1. **Simplicity** - JSON is human-readable and editable
2. **No dependencies** - Built-in Python `json` module
3. **Portability** - Easy to backup/transfer
4. **Performance** - Sufficient for expected scale (<100 workspaces)
5. **Debugging** - Easy to inspect and fix manually

### Why workspace-per-file over single DB?
1. **Isolation** - Each workspace completely independent
2. **Safety** - Corruption affects only one workspace
3. **Performance** - Only load active workspace data
4. **Backup** - Easy to backup individual workspaces
5. **Simplicity** - No complex query logic needed

### Command Design Philosophy
- **Short aliases**: `ws` for `workspace` (save typing)
- **Intuitive names**: `list`, `switch`, `new`, `delete` (standard CRUD)
- **Safety first**: Confirmations for destructive actions
- **Consistent patterns**: Follow existing command structure

---

## 📚 References

### Python Conventions
- [PEP 8](https://pep8.org/) - Style guide
- [XDG Base Directory](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) - Data storage

### Similar Tools
- `git worktree` - Multiple working trees
- `conda env` - Environment management
- `tmux sessions` - Session switching
- `vim buffers` - Buffer management

### Libraries Used
- `os`, `shutil` - File operations
- `json` - Config persistence
- `dataclasses` - Data structures
- `rich` - Terminal UI

---

## ✨ Summary

This implementation provides a **production-ready multi-workspace system** that:

✅ **Simple** - Intuitive commands, minimal learning curve
✅ **Safe** - Confirmations, validations, backups
✅ **Fast** - Load only active workspace
✅ **Backward Compatible** - Auto-migrates existing data
✅ **Maintainable** - Clean architecture, well-documented
✅ **Extensible** - Easy to add future features

**Total Impact**: ~450 lines of code across 7 files, ~2.5 hours implementation time.
