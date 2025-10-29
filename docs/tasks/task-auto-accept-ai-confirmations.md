# Task: Implement Auto-Accept for AI Tool Confirmations

**Created:** October 29, 2025
**Status:** 🟡 In Progress (Config added, implementation pending)
**Priority:** Medium
**Estimated Effort:** 8-9 hours remaining

---

## 📋 Overview

Implement an auto-accept feature that allows AI tools to execute data-modifying operations (create/edit) without requiring explicit user confirmation for each action, while maintaining safety by always confirming delete operations.

### User Requirements

✅ **Scope:** AI tools that change data should ask for confirmation if auto-accept is disabled
✅ **Control:** Show auto-accept status in status line, provide runtime toggle
✅ **Safety:** Delete operations ALWAYS require confirmation (even with auto-accept enabled)
✅ **UI Feedback:** Confirmation dialog in AI chat area or at bottom of chat panel

---

## 🎯 Feature Specification

### Behavior Matrix

| AI Tool Type | Auto-Accept OFF | Auto-Accept ON |
|-------------|-----------------|----------------|
| **Read-only** (search, get details) | ✅ Execute | ✅ Execute |
| **Create** (create_task, create_note) | ❓ Ask confirmation | ✅ Execute |
| **Modify** (edit_task, complete_task) | ❓ Ask confirmation | ✅ Execute |
| **Delete** (delete_task, delete_note) | ❓ Ask confirmation | ❓ **Ask confirmation** |

### User Flows

#### Flow 1: Auto-Accept Disabled (Default)
```
User: "create a task for code review"
System: [Confirmation dialog appears in AI chat]
        ┌─────────────────────────────────────┐
        │ 🔧 Confirm Tool Execution          │
        │ Tool: create_task                   │
        │ Args: name="code review", ...       │
        │                                     │
        │  [✓ Confirm]  [✗ Cancel]            │
        └─────────────────────────────────────┘
User: Clicks Confirm
AI: ✅ Created task #451: code review
```

#### Flow 2: Auto-Accept Enabled
```
User: "create a task for code review"
AI: ✅ Created task #451: code review
    [dim](auto-accepted)[/dim]
```

#### Flow 3: Delete Always Confirms
```
User: "delete task #420"
System: [Confirmation dialog even with auto-accept ON]
        ┌─────────────────────────────────────┐
        │ ⚠️  Confirm Delete Operation        │
        │ Task #420: "BypassTemperatures..."  │
        │                                     │
        │  [Delete]  [Cancel]                 │
        └─────────────────────────────────────┘
```

---

## ✅ Completed

### 1. Config Infrastructure ✅
**File:** `config.py`
**Status:** ✅ Done
**Changes:**
```python
@dataclass
class AIConfig:
    # ... existing fields ...

    # Auto-Accept Settings (NEW - Oct 2025)
    AUTO_ACCEPT_TOOLS: bool = False  # Auto-execute create/edit without confirmation
                                     # Note: Delete operations ALWAYS require confirmation
```

**Location:** Lines 187-189

---

## 📝 Remaining Tasks

### 2. State Tracking & Persistence
**File:** `core/state.py`
**Priority:** High
**Estimated Time:** 1 hour

**Tasks:**
- [ ] Add `auto_accept_ai_tools: bool = False` field to AppState class
- [ ] Create `load_auto_accept_setting()` method
- [ ] Create `save_auto_accept_setting(enabled: bool)` method
- [ ] Update settings JSON schema to include `"auto_accept_ai": false`

**Implementation:**
```python
class AppState:
    # ... existing fields ...
    auto_accept_ai_tools: bool = False  # Runtime auto-accept flag

    def load_auto_accept_setting(self) -> bool:
        """Load auto-accept setting from ~/.todo_cli_settings.json"""
        try:
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                return data.get("auto_accept_ai", False)
        except Exception:
            pass
        return False

    def save_auto_accept_setting(self, enabled: bool) -> None:
        """Save auto-accept setting to ~/.todo_cli_settings.json"""
        try:
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            existing = {}
            if settings_path.exists():
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            existing["auto_accept_ai"] = enabled

            from core.file_safety import SafeFileManager
            SafeFileManager.save_json_with_lock(str(settings_path), existing)
        except Exception as e:
            debug_log.error(f"Failed to save auto-accept setting: {e}")
```

**Location:** Around line 50 (after entity_mode field)

---

### 3. Tool Classification System
**File:** `core/ai_tools.py`
**Priority:** High
**Estimated Time:** 1 hour

**Tasks:**
- [ ] Create `TOOL_SAFETY_LEVELS` dictionary classifying all 22 tools
- [ ] Create `requires_confirmation(tool_name, auto_accept_enabled)` function
- [ ] Document each tool's safety level

**Implementation:**
```python
# Add after line 50 (after imports)

# Tool classification by data modification level
TOOL_SAFETY_LEVELS = {
    "read_only": [
        "search_tasks", "get_task_details", "get_task_statistics",
        "search_notes", "get_note_details", "get_linked_notes_for_task",
        "get_current_edit_context", "get_note_body"
    ],
    "create": [
        "create_task", "create_note"
    ],
    "modify": [
        "edit_task", "edit_note", "complete_task", "uncomplete_task",
        "link_note", "unlink_note", "append_note_to_task",
        "convert_note_to_task"
    ],
    "delete": [
        "delete_task", "delete_note"
    ],
    "external": [
        "open_note_in_editor", "save_all_changes"
    ]
}


def requires_confirmation(tool_name: str, auto_accept_enabled: bool) -> bool:
    """
    Check if tool requires user confirmation before execution.

    Args:
        tool_name: Name of the tool being executed
        auto_accept_enabled: Whether auto-accept is currently enabled

    Returns:
        True if confirmation needed, False if can proceed

    Rules:
        - Read-only tools: Never need confirmation
        - Delete tools: ALWAYS need confirmation (safety)
        - Create/Modify: Need confirmation only if auto-accept disabled
        - External tools: ALWAYS need confirmation (side effects)
    """
    # Read-only tools never need confirmation
    if tool_name in TOOL_SAFETY_LEVELS["read_only"]:
        return False

    # Delete and external tools ALWAYS need confirmation (safety)
    if tool_name in TOOL_SAFETY_LEVELS["delete"]:
        return True
    if tool_name in TOOL_SAFETY_LEVELS.get("external", []):
        return True

    # Create/Modify tools: need confirmation if auto-accept disabled
    if tool_name in TOOL_SAFETY_LEVELS["create"] or tool_name in TOOL_SAFETY_LEVELS["modify"]:
        return not auto_accept_enabled

    # Unknown tool: err on side of caution
    debug_log.warning(f"[AI_TOOLS] Unknown tool '{tool_name}' - requiring confirmation")
    return True


def get_tool_safety_level(tool_name: str) -> str:
    """Get the safety level of a tool for display purposes."""
    for level, tools in TOOL_SAFETY_LEVELS.items():
        if tool_name in tools:
            return level
    return "unknown"
```

**Location:** After imports, before first tool definition

---

### 4. Confirmation Dialog Widget
**File:** `textual_widgets/tool_confirm_dialog.py` (NEW)
**Priority:** High
**Estimated Time:** 2 hours

**Tasks:**
- [ ] Create new file `textual_widgets/tool_confirm_dialog.py`
- [ ] Implement `ToolConfirmDialog` class extending `ModalScreen[bool]`
- [ ] Add styling for normal vs delete operations
- [ ] Add keyboard shortcuts (Y=confirm, N/Esc=cancel)
- [ ] Show tool name, arguments preview, safety level

**Implementation:**
```python
"""
Tool Confirmation Dialog for AI Execution

Shows confirmation dialog when AI wants to execute a tool that modifies data.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical
from textual.widgets import Static, Button
from textual.binding import Binding


class ToolConfirmDialog(ModalScreen[bool]):
    """
    Modal confirmation dialog for AI tool execution.

    Returns True if user confirms, False if cancelled.
    """

    BINDINGS = [
        Binding("y", "confirm", "Confirm", show=True),
        Binding("n", "cancel", "Cancel", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ToolConfirmDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #dialog-container.delete {
        border: thick $error;
    }

    .dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .dialog-content {
        margin-bottom: 1;
    }

    .tool-name {
        text-style: bold;
        color: $accent;
    }

    .tool-args {
        color: $text-muted;
    }

    .button-container {
        layout: horizontal;
        align: center middle;
        height: 3;
    }

    .confirm-button {
        margin: 0 1;
    }

    .delete-button {
        background: $error;
    }
    """

    def __init__(
        self,
        tool_name: str,
        tool_args: dict,
        safety_level: str = "modify"
    ):
        super().__init__()
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.safety_level = safety_level
        self.is_delete = safety_level == "delete"

    def compose(self) -> ComposeResult:
        """Build the confirmation dialog."""
        container_classes = "delete" if self.is_delete else ""

        with Container(id="dialog-container", classes=container_classes):
            # Title
            if self.is_delete:
                yield Static("⚠️  Confirm Delete Operation", classes="dialog-title")
            else:
                yield Static("🔧 Confirm Tool Execution", classes="dialog-title")

            # Tool details
            with Vertical(classes="dialog-content"):
                yield Static(f"Tool: [bold]{self.tool_name}[/bold]", classes="tool-name")

                # Show abbreviated args
                args_preview = self._format_args(self.tool_args)
                yield Static(f"Args: {args_preview}", classes="tool-args")

            # Buttons
            with Container(classes="button-container"):
                if self.is_delete:
                    yield Button("Delete", variant="error", id="confirm", classes="delete-button")
                else:
                    yield Button("✓ Confirm", variant="primary", id="confirm", classes="confirm-button")
                yield Button("✗ Cancel", variant="default", id="cancel", classes="confirm-button")

    def _format_args(self, args: dict) -> str:
        """Format tool arguments for display (abbreviated)."""
        if not args:
            return "(none)"

        # Show first 2-3 args, truncate long values
        parts = []
        for i, (key, value) in enumerate(args.items()):
            if i >= 3:
                parts.append("...")
                break

            value_str = str(value)
            if len(value_str) > 40:
                value_str = value_str[:37] + "..."
            parts.append(f"{key}={value_str}")

        return ", ".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Keyboard shortcut: Y key."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Keyboard shortcut: N or Escape."""
        self.dismiss(False)
```

---

### 5. Integrate Confirmation in AI Agent
**File:** `core/ai_agent.py`
**Priority:** High
**Estimated Time:** 2 hours

**Tasks:**
- [ ] Modify `ask()` method to intercept tool calls
- [ ] Check if confirmation needed using `requires_confirmation()`
- [ ] Show confirmation dialog if needed
- [ ] Cancel tool execution if user declines
- [ ] Handle async confirmation flow

**Implementation Approach:**

This is complex because LangChain agent execution is synchronous, but Textual confirmation is async. Need to:

1. Use a callback/queue system
2. Pause agent execution
3. Show confirmation
4. Resume based on result

**Pseudo-code:**
```python
# In TaskAssistantAgent class

async def ask_with_confirmation(
    self,
    question: str,
    streaming_callback: Optional[Callable] = None,
    confirmation_callback: Optional[Callable] = None
) -> str:
    """
    Ask with optional tool confirmation.

    Args:
        confirmation_callback: Async function(tool_name, tool_args) -> bool
                              Returns True if user confirms, False if cancelled
    """
    # Build context...
    # Execute agent with tool interception...
    # For each tool call:
    #   if requires_confirmation(tool_name, state.auto_accept_ai_tools):
    #       confirmed = await confirmation_callback(tool_name, tool_args)
    #       if not confirmed:
    #           return "❌ Tool execution cancelled by user"
    # Continue execution...
```

**Note:** This is the most complex part. May need to wrap LangChain agent or modify execution flow.

---

### 6. Status Bar Indicator
**File:** `textual_widgets/status_bar.py`
**Priority:** Medium
**Estimated Time:** 30 minutes

**Tasks:**
- [ ] Add auto-accept indicator to status bar render
- [ ] Show "🤖 Auto" when enabled (cyan color)
- [ ] Show "🤖 Manual" when disabled (dim color)
- [ ] Update on toggle

**Implementation:**
```python
# In StatusBar.render() method or compose()
# Add after existing status parts

# Auto-accept indicator
if self.app.state.auto_accept_ai_tools:
    status_parts.append("[cyan]🤖 Auto[/cyan]")
else:
    status_parts.append("[dim]🤖 Manual[/dim]")
```

**Location:** In status bar rendering logic

---

### 7. Toggle Command & Key Binding
**File:** `textual_app.py`
**Priority:** Medium
**Estimated Time:** 1 hour

**Tasks:**
- [ ] Add `action_toggle_auto_accept()` method
- [ ] Add key binding `Ctrl+Shift+A`
- [ ] Update status bar after toggle
- [ ] Show notification on toggle
- [ ] Persist setting to file

**Implementation:**
```python
# In TodoTextualApp class

def action_toggle_auto_accept(self) -> None:
    """Toggle AI auto-accept mode (Ctrl+Shift+A)."""
    current = self.state.auto_accept_ai_tools
    new_value = not current

    # Update state
    self.state.auto_accept_ai_tools = new_value

    # Persist to file
    self.state.save_auto_accept_setting(new_value)

    # Notify user
    if new_value:
        message = "AI auto-accept enabled. Delete operations still require confirmation."
        severity = "information"
    else:
        message = "AI auto-accept disabled. All data modifications will require confirmation."
        severity = "warning"

    self.notify(message, severity=severity, timeout=5)

    # Refresh status bar
    try:
        status_bar = self.query_one(StatusBar)
        status_bar.refresh()
    except Exception:
        pass

# Add to BINDINGS list
BINDINGS = [
    # ... existing bindings ...
    Binding("ctrl+shift+a", "toggle_auto_accept", "Toggle AI Auto-Accept", show=False),
]
```

**Location:** With other action methods (around line 800-1000)

---

### 8. Comprehensive Testing
**File:** `tests/test_auto_accept.py` (NEW)
**Priority:** High
**Estimated Time:** 2 hours

**Tasks:**
- [ ] Test config loading/saving
- [ ] Test tool classification (all 22 tools)
- [ ] Test confirmation logic
- [ ] Test toggle command
- [ ] Test status bar indicator
- [ ] Test persistence across sessions

**Test Plan:**
```python
"""Tests for auto-accept feature."""

class TestToolClassification:
    def test_read_only_tools_never_confirm(self):
        # search_tasks, get_task_details, etc.
        pass

    def test_delete_tools_always_confirm(self):
        # delete_task, delete_note
        pass

    def test_create_needs_confirm_when_disabled(self):
        # auto_accept=False
        pass

    def test_create_skips_confirm_when_enabled(self):
        # auto_accept=True
        pass

class TestStatePersistence:
    def test_save_auto_accept_setting(self):
        pass

    def test_load_auto_accept_setting(self):
        pass

    def test_default_is_false(self):
        pass

class TestToggleCommand:
    def test_toggle_updates_state(self):
        pass

    def test_toggle_persists_to_file(self):
        pass

    def test_toggle_shows_notification(self):
        pass

class TestConfirmationDialog:
    def test_dialog_shows_tool_info(self):
        pass

    def test_confirm_returns_true(self):
        pass

    def test_cancel_returns_false(self):
        pass

    def test_delete_dialog_has_warning_style(self):
        pass
```

---

## 🎨 UI/UX Details

### Status Bar Display
```
┌─ Status Bar ────────────────────────────────────────┐
│ Tasks | 450 total | 120 done | 🤖 Auto | Page 1/23 │
└─────────────────────────────────────────────────────┘
```

### Confirmation Dialog (Normal)
```
┌───────────────────────────────────┐
│  🔧 Confirm Tool Execution        │
│                                   │
│  Tool: create_task                │
│  Args: name=code review, ...      │
│                                   │
│   [✓ Confirm]  [✗ Cancel]         │
│                                   │
│  Shortcuts: Y=Confirm, N=Cancel   │
└───────────────────────────────────┘
```

### Confirmation Dialog (Delete)
```
┌───────────────────────────────────┐
│  ⚠️  Confirm Delete Operation     │
│                                   │
│  Task #420: "BypassTemperatures"  │
│  This action cannot be undone.    │
│                                   │
│   [Delete]  [Cancel]              │
│                                   │
│  Shortcuts: Y=Delete, N=Cancel    │
└───────────────────────────────────┘
```

---

## 🔒 Safety Considerations

### Delete Protection
- Delete tools ALWAYS require confirmation
- Even with auto-accept enabled
- Clear warning in dialog
- Red/error styling

### Unknown Tools
- Tools not in classification: require confirmation
- Log warning for unclassified tools
- Fail-safe behavior

### State Validation
- Auto-accept flag validated on load
- Invalid values default to False (safe)
- Settings file corruption handled gracefully

---

## 📚 Documentation Updates

### Files to Update:
1. **CLAUDE.md** - Add auto-accept section
2. **readme.md** - Mention feature
3. **USAGE_GUIDE.md** - Document Ctrl+Shift+A
4. **QUICK_REFERENCE.md** - Add key binding

### Documentation Template:
```markdown
## Auto-Accept AI Tools

**Keyboard Shortcut:** Ctrl+Shift+A

Enable auto-accept to allow AI to execute create/edit operations without confirmation.

**Default:** Disabled (safer)
**Status:** Shown in status bar (🤖 Auto / 🤖 Manual)

**Safety:** Delete operations ALWAYS require confirmation, even when auto-accept is enabled.

**Usage:**
1. Press Ctrl+Shift+A to toggle
2. Status bar shows current state
3. Notification confirms change
4. Setting persists across sessions
```

---

## 📊 Implementation Checklist

- [x] 1. Config infrastructure (config.py)
- [ ] 2. State tracking & persistence (core/state.py)
- [ ] 3. Tool classification system (core/ai_tools.py)
- [ ] 4. Confirmation dialog widget (textual_widgets/tool_confirm_dialog.py)
- [ ] 5. Integrate confirmation in AI agent (core/ai_agent.py)
- [ ] 6. Status bar indicator (textual_widgets/status_bar.py)
- [ ] 7. Toggle command & key binding (textual_app.py)
- [ ] 8. Comprehensive testing (tests/test_auto_accept.py)
- [ ] 9. Documentation updates (CLAUDE.md, readme.md, etc.)

---

## ⏱️ Time Tracking

| Task | Estimated | Actual | Status |
|------|-----------|--------|--------|
| 1. Config | 15 min | 15 min | ✅ Done |
| 2. State | 1 hour | - | ⏳ Pending |
| 3. Classification | 1 hour | - | ⏳ Pending |
| 4. Dialog Widget | 2 hours | - | ⏳ Pending |
| 5. Agent Integration | 2 hours | - | ⏳ Pending |
| 6. Status Bar | 30 min | - | ⏳ Pending |
| 7. Toggle Command | 1 hour | - | ⏳ Pending |
| 8. Testing | 2 hours | - | ⏳ Pending |
| 9. Documentation | 30 min | - | ⏳ Pending |
| **Total** | **10.25 hours** | **0.25 hours** | **2% Complete** |

---

## 🚧 Known Challenges

### Challenge 1: Async Confirmation in Sync Agent
**Issue:** LangChain agent execution is synchronous, Textual confirmation is async
**Solution:** Need callback mechanism or agent execution wrapper
**Complexity:** High
**Risk:** May require significant refactoring

### Challenge 2: Tool Call Interception
**Issue:** Need to intercept tool calls before execution
**Solution:** Wrap LangChain agent or modify tool execution
**Complexity:** Medium
**Risk:** May break existing agent behavior

### Challenge 3: State Synchronization
**Issue:** Auto-accept flag needs to be accessible in multiple places
**Solution:** Pass state through agent initialization
**Complexity:** Low
**Risk:** Minimal

---

## 🎯 Success Criteria

Feature is complete when:
- ✅ Auto-accept can be toggled with Ctrl+Shift+A
- ✅ Status bar shows current auto-accept state
- ✅ Create/edit tools skip confirmation when enabled
- ✅ Delete tools ALWAYS show confirmation
- ✅ Setting persists across app restarts
- ✅ All tests pass (target: 15+ new tests)
- ✅ Documentation updated
- ✅ No breaking changes to existing functionality

---

## 📝 Notes

### Design Decisions
- **Default OFF:** Safer for new users
- **Delete always confirms:** Prevent accidental data loss
- **Status bar indicator:** Always visible, no modal clutter
- **Ctrl+Shift+A:** Accessible but not accidental

### Future Enhancements (Not in Scope)
- Per-tool auto-accept settings
- Auto-accept for bulk operations
- Confirmation history/audit log
- Undo support for auto-accepted operations

---

## 🔗 Related Files

- **Bug Fix Document:** `docs/history/BUGFIX_AI_CONTEXT_WRONG_TASK_EDIT.md`
- **Context Awareness:** `docs/technical/AI_CONTEXT_AWARENESS.md`
- **Project Guide:** `CLAUDE.md`
