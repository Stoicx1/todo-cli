# Task Feature: UX Enhancements

**Branch:** `task-feature-ux-enhancements`
**Created:** 2025-10-20
**Status:** In Development (File Safety COMPLETE ✅)

## Overview

This feature adds comprehensive UX improvements to the Todo CLI application, focusing on:
- **Full TUI Modal Forms** - Interactive overlay forms for add/edit operations
- **Comprehensive Validation** - Real-time field validation with inline error messages
- **Visual Feedback System** - Success panels, progress indicators, and confirmation dialogs
- **Smart Autocomplete** - Tag suggestions, priority selectors, field history
- **File Safety & Data Protection** ✅ (NEW - 2025-10-21) - File locking, atomic writes, backup/recovery

## Goals

1. **Improve Task Entry UX** - Replace basic inline forms with rich TUI modals
2. **Prevent Input Errors** - Add comprehensive validation at the form level
3. **Enhance Visual Feedback** - Show clear success/error states for all operations
4. **Maintain Simplicity** - Keep keyboard-driven workflow, avoid mouse dependency
5. **Preserve Performance** - Fast rendering, no blocking operations

## Architecture Changes

### New Files

#### `ui/modal_form.py`
Core TUI modal framework using prompt_toolkit's Application API.

**Key Components:**
- `ModalForm`: Base class for all modal forms
- `ModalField`: Base class for form fields
- `ModalFormController`: Manages form state, validation, and rendering

**Features:**
- Centered overlay box with blurred background
- Tab/Shift-Tab navigation between fields
- ESC to cancel, Enter to submit
- Real-time validation with inline errors
- Responsive layout (adjusts to terminal size)

**Technical Details:**
```python
class ModalForm:
    def __init__(self, title: str, width: int = 60, height: int = 20)
    def add_field(self, field: ModalField)
    def show(self) -> Optional[Dict[str, Any]]
    def validate(self) -> Tuple[bool, List[str]]
```

#### `ui/form_fields.py`
Reusable form field components with validation and rendering logic.

**Field Types:**
- `TextField`: Single-line text input with max length
- `TextAreaField`: Multi-line text input for descriptions
- `PriorityField`: Visual selector (High/Med/Low) with arrow keys
- `TagField`: Multi-select autocomplete field (limit 3 tags)
- `CheckboxField`: Boolean selection (for future features)

**Validation Features:**
- Required field validation
- Min/max length constraints
- Character counters (e.g., "45/100")
- Custom validation functions
- Real-time error messages

**Example:**
```python
name_field = TextField(
    name="task_name",
    label="Task Name",
    required=True,
    max_length=100,
    placeholder="Enter task name..."
)
```

#### `ui/task_forms.py`
Specific implementations for task add/edit modals.

**Forms:**
- `AddTaskModal`: Form for creating new tasks
- `EditTaskModal`: Form for editing existing tasks (pre-filled)

**Features:**
- Smart defaults (remember last priority used)
- Tag autocomplete from existing tasks
- Pre-filled edit forms with current values
- Seamless integration with AppState

**Usage:**
```python
# In main.py
from ui.task_forms import AddTaskModal

result = AddTaskModal.show(state)
if result:
    state.add_task(**result)
```

#### `ui/feedback.py`
Visual feedback utilities for operations and confirmations.

**Components:**
- `SuccessPanel`: Green panel with success icon
- `ErrorPanel`: Red panel with error details
- `ProgressSpinner`: Animated spinner for async operations
- `ConfirmDialog`: Yes/No confirmation prompt
- `FadeTransition`: Smooth fade-in/fade-out animations

**Usage Examples:**
```python
from ui.feedback import SuccessPanel, ConfirmDialog

# Show success message
SuccessPanel("Task added successfully!", duration=2)

# Confirmation dialog
if ConfirmDialog("Delete 10 tasks?", default=False):
    # Delete tasks
    pass
```

### Modified Files

#### `main.py`
- Replace `inline_add_task()` with `AddTaskModal.show()`
- Replace `inline_edit_task()` with `EditTaskModal.show()`
- Keep fallback to inline forms if modal fails (graceful degradation)
- Add keyboard shortcut `Ctrl+N` for quick add modal

**Changes:**
```python
# Before
if user_input.strip() == "add":
    filled_input = inline_add_task(console)
    handle_command(filled_input, state, console)

# After
if user_input.strip() == "add":
    result = AddTaskModal.show(state)
    if result:
        state.add_task(**result)
        SuccessPanel(f"Task '{result['name']}' added!")
```

#### `core/commands.py`
- Add confirmation prompts for destructive operations
- Use visual feedback panels for operation results
- Add progress indicators for bulk operations
- Improve error messages with rich formatting

**Enhancements:**
- `handle_done()`: Show "✓ 5 tasks marked as done" panel
- `handle_remove()`: Confirm bulk deletes (>3 tasks)
- `handle_edit()`: Show diff of changed fields
- All commands: Use `SuccessPanel` and `ErrorPanel`

#### `ui/renderer.py`
- Add support for modal overlay rendering
- Blur background when modal is active (dim colors)
- Ensure modals don't interfere with dashboard updates

#### `requirements.txt`
- Add/update prompt-toolkit to >=3.0.43
- Ensure rich compatibility

## Implementation Phases

### Phase 1: Core TUI Modal Framework ✅
**File:** `ui/modal_form.py`

**Tasks:**
- [x] Create `ModalForm` base class
- [x] Implement centered overlay rendering
- [x] Add keyboard navigation (Tab, Shift-Tab, ESC, Enter)
- [x] Implement background blur effect
- [x] Add validation framework

**Testing:**
- Can create empty modal and display it
- Tab navigation cycles through fields
- ESC closes modal without saving
- Enter submits if validation passes

### Phase 2: Form Field Components ✅
**File:** `ui/form_fields.py`

**Tasks:**
- [x] Create `ModalField` base class
- [x] Implement `TextField` with validation
- [x] Implement `PriorityField` with visual selector
- [x] Implement `TagField` with autocomplete
- [x] Implement `TextAreaField` for descriptions
- [x] Add character counters to all text fields
- [x] Add inline error display

**Testing:**
- Each field type renders correctly
- Validation triggers on blur/change
- Character counters update in real-time
- Tab autocomplete works for tags
- Priority selector responds to arrows and numbers

### Phase 3: Task Forms ✅
**File:** `ui/task_forms.py`

**Tasks:**
- [x] Create `AddTaskModal` class
- [x] Create `EditTaskModal` class
- [x] Implement smart defaults (remember last priority)
- [x] Add tag autocomplete from existing tasks
- [x] Pre-fill edit forms with current values
- [x] Handle form cancellation gracefully

**Testing:**
- Add modal creates valid tasks
- Edit modal pre-fills all fields correctly
- Tag autocomplete suggests existing tags
- Form remembers last priority used
- Cancellation doesn't modify state

### Phase 4: Visual Feedback System ✅
**File:** `ui/feedback.py`

**Tasks:**
- [x] Implement `SuccessPanel` with icons
- [x] Implement `ErrorPanel` with details
- [x] Implement `ProgressSpinner` for async ops
- [x] Implement `ConfirmDialog` for destructive operations
- [x] Add fade-in/fade-out transitions
- [x] Ensure Windows CP1252 compatibility (emoji fallback)

**Testing:**
- Success panels appear and auto-dismiss
- Error panels show detailed messages
- Progress spinners animate smoothly
- Confirm dialogs return correct boolean
- Transitions don't block user input

### Phase 5: Enhanced Command Experience ✅
**File:** `core/commands.py`

**Tasks:**
- [x] Add confirmation for bulk delete (>3 tasks)
- [x] Replace text messages with rich panels
- [x] Add progress indicators for bulk operations
- [x] Show operation summaries (e.g., "5 tasks marked done")
- [x] Improve error formatting with examples

**Testing:**
- Bulk delete shows confirmation dialog
- All operations show success/error panels
- Progress indicators appear for long operations
- Operation summaries are accurate
- Error messages are clear and helpful

### Phase 6: Integration & Testing 🔄
**Files:** `main.py`, all new files

**Tasks:**
- [ ] Replace inline forms in main.py
- [ ] Add keyboard shortcuts (Ctrl+N for quick add)
- [ ] Test full user flow (add, edit, delete)
- [ ] Test edge cases (empty fields, max lengths, invalid input)
- [ ] Test on both UTF-8 and CP1252 terminals
- [ ] Update CLAUDE.md with new architecture
- [ ] Create comprehensive testing checklist

**Testing:**
- Full add/edit workflow works end-to-end
- All validation rules are enforced
- Visual feedback appears correctly
- No regressions in existing features
- Performance is acceptable (no lag)

### Phase 7: File Safety & Data Protection ✅ (COMPLETE - 2025-10-21)
**Files:** `core/file_safety.py`, `core/state.py`, `requirements.txt`

**Tasks:**
- [x] Add portalocker dependency to requirements.txt
- [x] Create SafeFileManager class with file locking
- [x] Implement atomic writes using tempfile + os.replace()
- [x] Implement backup rotation system (keep last 3)
- [x] Implement automatic recovery from corruption
- [x] Update AppState to use SafeFileManager
- [x] Update CLAUDE.md with file safety documentation
- [x] Create FILE_SAFETY_COMPLETE.md documentation

**Features Implemented:**
- ✅ File locking (prevents concurrent writes)
- ✅ Atomic writes (prevents partial write corruption)
- ✅ Backup rotation (keeps last 3 backups)
- ✅ Automatic recovery (tries backups on corruption)
- ✅ Lock timeout handling (5 seconds default)
- ✅ Cross-platform support (Windows, Linux, Mac)
- ✅ Graceful error messages
- ✅ Performance overhead <20ms

**Protection Against:**
- ✅ Concurrent write race conditions → File locking prevents
- ✅ Power failure data loss → Atomic writes + backups
- ✅ File corruption → Automatic backup recovery
- ✅ Network drive issues → fsync() + timeout handling

**Documentation:**
- ✅ FILE_SAFETY_COMPLETE.md - Full technical documentation
- ✅ CLAUDE.md - Updated with file safety section
- ✅ task-file-safety.md - Implementation plan (marked complete)

## Validation Rules

### Required Fields
- **Task Name**: Minimum 1 character, cannot be whitespace only

### Field Lengths
- **Task Name**: 1-100 characters
- **Comment**: 0-200 characters
- **Description**: 0-500 characters

### Priority
- Must be integer 1, 2, or 3
- Default: 2 (Medium)
- Visual labels: 1=High, 2=Med, 3=Low

### Tags
- Maximum 3 tags per task
- Lowercase normalization
- Comma-separated input
- Autocomplete from existing tags
- Empty string allowed (no tags)

## User Experience Flow

### Adding a Task (Before)
```
❯ add
Task Name: Fix login bug
Comment: Urgent
Description: Users can't log in after password reset
Priority (1-3): 1
Tag(s): backend,urgent
[+] Added task: Fix login bug
```

### Adding a Task (After)
```
❯ add

┌─ Add New Task ─────────────────────────────────────┐
│                                                     │
│  Task Name *                                        │
│  [Fix login bug________________________] 14/100     │
│                                                     │
│  Priority                                           │
│  ● High  ○ Med  ○ Low                               │
│                                                     │
│  Tags (max 3)                                       │
│  [backend, urgent___________] ↓ Suggestions         │
│  • backend  • urgent  • api                         │
│                                                     │
│  Comment                                            │
│  [Urgent_______________________________] 6/200      │
│                                                     │
│  Description                                        │
│  [Users can't log in after password___] 35/500     │
│  [reset___________________________________]         │
│                                                     │
│  Tab: Next Field  |  ESC: Cancel  |  Enter: Save   │
└─────────────────────────────────────────────────────┘

✓ Task "Fix login bug" added successfully!
```

## Technical Considerations

### Performance
- Modal rendering should be <50ms
- Autocomplete suggestions should be <100ms
- Validation should not block user input
- Background blur should not slow down rendering

### Compatibility
- UTF-8 terminals: Use Unicode emojis and box-drawing characters
- CP1252 terminals: Fall back to ASCII characters
- Windows CMD: Test thoroughly (known prompt_toolkit issues)
- Terminal size: Responsive layout (min 80x24)

### Error Handling
- Graceful degradation if modal fails (fall back to inline forms)
- Handle terminal resize during modal display
- Prevent modal stacking (only one modal at a time)
- Validate all input before processing

### State Management
- Forms should not mutate state until submission
- Cancelled forms should not affect state
- Remember last-used values (priority, tags) across sessions
- Persist form history to `.todo_form_history` file

## Future Enhancements

### Not in This Phase (Consider Later)
- [ ] Undo/Redo system (single-level undo)
- [ ] Interactive table row selection mode
- [ ] Drag-and-drop priority reordering
- [ ] Split-pane view (tasks | details)
- [ ] Custom keybindings configuration
- [ ] Theme customization (colors, icons)
- [ ] Export to Markdown/CSV
- [ ] Recurring tasks support

### Dependencies
- Keep dependencies minimal
- Avoid heavy libraries (questionary, textual)
- Use only prompt_toolkit + rich (already in use)

## Testing Checklist

### Modal Form Framework
- [ ] Modal appears centered on screen
- [ ] Background is dimmed/blurred
- [ ] ESC key closes modal without saving
- [ ] Enter key submits if validation passes
- [ ] Tab key cycles forward through fields
- [ ] Shift-Tab cycles backward through fields
- [ ] Modal handles terminal resize gracefully

### Form Fields
- [ ] TextField accepts text input
- [ ] TextField shows character counter
- [ ] TextField enforces max length
- [ ] TextField shows required field error
- [ ] PriorityField responds to arrow keys
- [ ] PriorityField responds to number keys (1, 2, 3)
- [ ] TagField shows autocomplete suggestions
- [ ] TagField limits to 3 tags
- [ ] TagField normalizes to lowercase
- [ ] TextAreaField allows multi-line input

### Task Forms
- [ ] Add modal creates task on submit
- [ ] Add modal cancels without creating task (ESC)
- [ ] Edit modal pre-fills all fields correctly
- [ ] Edit modal updates task on submit
- [ ] Edit modal cancels without updating (ESC)
- [ ] Tag autocomplete suggests existing tags
- [ ] Priority selector defaults to last used value

### Visual Feedback
- [ ] Success panels appear after operations
- [ ] Success panels auto-dismiss after 2 seconds
- [ ] Error panels show detailed error messages
- [ ] Progress spinners animate during async operations
- [ ] Confirm dialogs return correct boolean (Yes/No)
- [ ] Transitions are smooth and non-blocking

### Command Enhancements
- [ ] Bulk delete (>3 tasks) shows confirmation
- [ ] Confirmation can be cancelled
- [ ] Success panels show operation summaries
- [ ] Error panels show helpful error messages
- [ ] Progress indicators appear for bulk operations

### Edge Cases
- [ ] Empty task name shows validation error
- [ ] Max length fields prevent additional input
- [ ] Invalid priority (0, 4+) shows error
- [ ] More than 3 tags shows error or truncates
- [ ] Terminal too small shows graceful error
- [ ] Rapid ESC/Enter presses don't crash

### Compatibility
- [ ] Works on UTF-8 terminal (emojis visible)
- [ ] Works on CP1252 terminal (ASCII fallback)
- [ ] Works on Windows CMD
- [ ] Works on Linux/Mac terminals
- [ ] Responsive to different terminal sizes (80x24 to 200x50)

### Integration
- [ ] Add modal integrates with main loop
- [ ] Edit modal integrates with main loop
- [ ] Dashboard updates after form submission
- [ ] State persistence works correctly
- [ ] No regressions in existing commands
- [ ] Command history still works (↑/↓ arrows)
- [ ] Keyboard shortcuts don't conflict (ESC, Tab)

## Success Criteria

This feature is complete when:
1. ✅ All modal forms render correctly and accept input
2. ✅ All validation rules are enforced
3. ✅ Visual feedback appears for all operations
4. ✅ Integration with main.py is seamless
5. ✅ All tests pass (see Testing Checklist)
6. ✅ No regressions in existing features
7. ✅ Documentation is complete (CLAUDE.md updated)
8. ✅ Performance is acceptable (<50ms modal render)

## Notes

- Focus on keyboard-driven workflow (avoid mouse dependency)
- Keep forms simple and fast (no fancy animations that slow down UX)
- Ensure graceful degradation if modal fails
- Test thoroughly on Windows (prompt_toolkit edge cases)
- Document all new keyboard shortcuts in help command
- Update CLAUDE.md with new architecture details

## References

- prompt_toolkit docs: https://python-prompt-toolkit.readthedocs.io/
- rich docs: https://rich.readthedocs.io/
- Similar TUI apps: lazygit, tig, htop (for UX inspiration)
