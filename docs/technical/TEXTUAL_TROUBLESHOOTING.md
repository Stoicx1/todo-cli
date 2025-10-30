# Textual Troubleshooting Guide

This document contains solutions to known issues with the Textual UI implementation.

## Critical Issue: CSS File Caching

### Problem Description

**Symptoms:**
- CSS parsing errors showing content that doesn't exist in the actual CSS file
- Error messages reference old/deleted CSS code
- Changes to CSS files don't take effect
- Error persists even after:
  - Fixing the CSS syntax
  - Deleting Python `__pycache__` directories
  - Clearing Python bytecode files
  - Deleting Textual cache directories
  - Restarting the terminal
  - Renaming CSS files

**Example Error:**
```
Error at D:\MyProjects\todo-cli\styles\app.tcss:40:26
  38 │   Screen.-maximized-view {
  39 │   │   layout: vertical !important;
  40 │   │   hatch: right $panel;
  41 │   │   overflow-y: auto !important;

expected a percentage here; found '#334155'
```

Even when line 40 in the actual file contains completely different content.

### Root Cause

Textual aggressively caches CSS files in multiple locations:
1. **Application-level cache**: `C:\Users\<username>\AppData\Local\Textualize\textual\Cache`
2. **Internal module cache**: Somewhere in Textual's internals
3. **File system cache**: OS-level file caching

The cache persists even after:
- Deleting cache directories
- Renaming files
- Clearing Python cache

### Solution: Use Inline CSS

**Instead of using `CSS_PATH`:**
```python
class TodoTextualApp(App):
    CSS_PATH = "styles/app.tcss"  # ❌ Subject to caching issues
```

**Use inline `CSS` variable:**
```python
class TodoTextualApp(App):
    CSS = """
    /* All your CSS here */
    $primary: #0891b2;

    Screen {
        background: $surface;
    }

    /* ... rest of CSS ... */
    """
```

### Implementation Steps

1. **Copy CSS content** from your `.tcss` file
2. **Edit `textual_app.py`**:
   ```python
   # Comment out CSS_PATH
   # CSS_PATH = "styles/app.tcss"

   # Add inline CSS
   CSS = """
   [paste your CSS content here]
   """
   ```
3. **Test the application** - it should work immediately without caching issues

### Benefits of Inline CSS

| Aspect | CSS_PATH | Inline CSS |
|--------|----------|------------|
| **Caching Issues** | ❌ Frequent | ✅ None |
| **Hot Reload** | ⚠️ Unreliable | ✅ Immediate |
| **Deployment** | ⚠️ Extra file | ✅ Single file |
| **Version Control** | ⚠️ Two files | ✅ One file |
| **Readability** | ✅ Separate file | ⚠️ Longer Python file |

### When to Use Each Approach

**Use Inline CSS (Recommended):**
- Production deployments
- When experiencing caching issues
- For simpler distribution
- When CSS changes frequently during development

**Use CSS_PATH (Optional):**
- Only if you're not experiencing caching issues
- For very large CSS files (>500 lines)
- When multiple developers need to edit CSS separately

### Cache Locations (For Reference)

If you need to manually clear Textual's cache:

**Windows:**
```
C:\Users\<username>\AppData\Local\Textualize\textual\Cache
C:\Users\<username>\AppData\Local\Textualize\textual\
```

**Linux/Mac:**
```
~/.cache/textual/
~/.local/share/textual/
```

**Python cache:**
```bash
# Windows
find . -type d -name __pycache__ -exec rm -rf {} +
del /s /q *.pyc

# Linux/Mac
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
```

**Note:** Even after clearing all these caches, the CSS file caching issue may persist.

## Other Known Issues

### Issue: Import Error for `work` Decorator

**Symptom:**
```
ImportError: cannot import name 'work' from 'textual.worker'
```

**Cause:**
The import path for the `work` decorator changed in Textual 6.3.0+.

**Solution:**
```python
# Old (Textual < 6.3.0)
from textual.worker import work

# New (Textual 6.3.0+)
from textual import work
```

**Fix in `textual_app.py`:**
```python
from textual import work  # ✅ Correct for Textual 6.3.0+
```

### Issue: CSS Variables Not Working with Opacity

**Symptom:**
```
expected a percentage here; found '#334155'
```

**Cause:**
Textual doesn't support CSS variables with opacity percentages.

**Invalid Syntax:**
```css
background: $secondary 10%;  /* ❌ CSS variable + opacity */
hatch: right $panel 30%;     /* ❌ CSS variable + opacity */
```

**Valid Syntax:**
```css
background: cyan 10%;        /* ✅ Named color + opacity */
background: #06b6d4 10%;     /* ✅ Hex color + opacity */
background: $secondary;      /* ✅ CSS variable without opacity */
```

### Issue: CSS Functions Not Supported

**Symptom:**
```
Invalid CSS function
```

**Cause:**
Textual CSS doesn't support CSS functions like `rgba()`, `rgb()`, `hsl()`.

**Invalid Syntax:**
```css
background: rgba(0, 0, 0, 0.7);  /* ❌ CSS function */
background: rgb(14, 116, 144);   /* ❌ CSS function */
```

**Valid Syntax:**
```css
background: #000000 70%;         /* ✅ Hex color + opacity */
background: cyan 50%;            /* ✅ Named color + opacity */
```

### Issue: WorkerError - Double-Wrapping @work Decorated Methods

**Symptom:**
```
WorkerError: Unsupported attempt to run an async worker
  File "textual_widgets/panels/task_edit_panel.py", line 247
    self.run_worker(self.action_cancel(), exclusive=True)
```

**Cause:**
Attempting to wrap an already `@work` decorated method with `run_worker()` creates nested workers, which Textual doesn't support.

**Invalid Code:**
```python
# ❌ WRONG - Double wrapping
@work(exclusive=True)
async def action_cancel(self) -> None:
    # ... cancel logic ...

def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "cancel_btn":
        self.run_worker(self.action_cancel(), exclusive=True)  # ❌ CRASH!
```

**Valid Code:**
```python
# ✅ CORRECT - Let @work handle worker creation
@work(exclusive=True)
async def action_cancel(self) -> None:
    # ... cancel logic ...

def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "cancel_btn":
        self.action_cancel()  # ✅ Method already decorated with @work
        event.stop()
```

**Key Rule:** If a method is decorated with `@work`, call it directly. Don't wrap it with `run_worker()`.

**Affected Files:** TaskEditPanel, NoteEditPanel (cancel button handlers)

### Issue: Button Event Bubbling - Actions Trigger Multiple Times

**Symptom:**
- Single button click triggers action 7+ times
- Log shows same action called repeatedly with ~200ms delays
- Example from debug logs:
```
18:42:43.330 - action_back_to_list() called  ← Original
18:42:43.827 - action_back_to_list() called  ← 0.5s later
18:42:44.054 - action_back_to_list() called  ← 0.2s later
...
```

**Cause:**
Missing `event.stop()` allows events to bubble up through parent containers, causing repeated action execution.

**Invalid Code:**
```python
# ❌ WRONG - Missing event.stop()
def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "save_btn":
        self.action_save()
        # Event bubbles up to parent containers!
```

**Valid Code:**
```python
# ✅ CORRECT - Prevent bubbling with event.stop()
def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "save_btn":
        self.action_save()
        event.stop()  # ✅ Prevents event bubbling
    elif event.button.id == "cancel_btn":
        self.action_cancel()
        event.stop()  # ✅ Prevents event bubbling
```

**Key Rule:** ALWAYS call `event.stop()` after handling button presses to prevent event bubbling.

**Affected Widgets:** TaskDetailPanel, NoteDetailPanel, TaskEditPanel, NoteEditPanel (all 12 buttons)

### Issue: Dual Mode System Desynchronization

**Symptom:**
- Switching to notes mode (via `m` key or `mode notes` command)
- Status bar shows "5 notes" but panel displays empty task list
- Panel title shows "Tasks" instead of "Notes"
- Notes never load despite correct entity mode

**Cause:**
Two separate mode properties exist and must be synchronized:
- `state.entity_mode` (str: "tasks" | "notes") - Data layer
- `state.left_panel_mode` (LeftPanelMode enum) - UI layer

Updating only `entity_mode` leaves `left_panel_mode` at LIST_TASKS, so TaskTable stays visible.

**Invalid Code:**
```python
# ❌ WRONG - Only updates entity_mode
def action_toggle_mode(self) -> None:
    self.state.entity_mode = "notes"  # left_panel_mode NOT updated!
    self.refresh_table()
    # Result: Status bar shows "notes" but task list still displays
```

**Valid Code:**
```python
# ✅ CORRECT - Update both mode properties
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
```

**Key Rule:** When changing `entity_mode`, ALWAYS update `left_panel_mode` to match.

**Affected Files:** `textual_app.py` (action_toggle_mode, mode command interceptor)

## Textual Version Compatibility

### Tested Versions

| Version | Status | Notes |
|---------|--------|-------|
| 6.3.0 | ⚠️ Issues | CSS caching problems, `work` import changed |
| 6.4.0 | ✅ Works | With inline CSS workaround |

### Recommended Setup

```bash
# Install Textual 6.4.0+
pip install textual>=6.4.0

# Verify installation
python -c "import textual; print(textual.__version__)"
```

## CSS Best Practices for Textual

### 1. Define Variables First

```css
/* ✅ Variables at the top */
$primary: #0891b2;
$surface: #1e293b;

Screen {
    background: $surface;
}
```

### 2. Use Named Colors for Opacity

```css
/* ✅ Recommended */
background: cyan 10%;
border: solid cyan;

/* ⚠️ Avoid */
background: $secondary 10%;  /* May cause issues */
```

### 3. Avoid CSS Functions

```css
/* ❌ Don't use */
background: rgba(0, 0, 0, 0.7);

/* ✅ Use instead */
background: #000000 70%;
```

### 4. Test CSS Changes Immediately

If using `CSS_PATH` and changes don't appear:
1. Switch to inline CSS immediately
2. Don't waste time clearing caches
3. Inline CSS always works

## Development Workflow

### Recommended Approach

1. **Start with inline CSS** in `textual_app.py`
2. **Develop and test** your styles inline
3. **Keep it inline** for production (avoids caching issues)
4. **(Optional)** Extract to `.tcss` file only if:
   - CSS exceeds 500 lines
   - No caching issues observed
   - Team prefers separate files

### If You Must Use CSS_PATH

**Workaround for development:**
```python
import time

class TodoTextualApp(App):
    # Add timestamp to force cache bust
    CSS_PATH = f"styles/app.tcss?v={int(time.time())}"
```

**Note:** This may not work reliably. Inline CSS is still recommended.

## Emergency Recovery

If the app won't start due to CSS errors:

1. **Immediate fix** - Use minimal inline CSS:
   ```python
   CSS = """
   Screen { background: #1e293b; }
   """
   ```

2. **Gradually add styles** back one section at a time

3. **Test after each addition** to identify problematic CSS

## Future Considerations

### Potential Long-term Solutions

1. **Feature request to Textual**: Disable CSS caching or provide cache-busting API
2. **Custom CSS loader**: Implement file hash-based cache invalidation
3. **Stay with inline CSS**: Most reliable approach

### Monitoring for Updates

Check Textual's changelog for CSS caching improvements:
- GitHub: https://github.com/Textualize/textual
- PyPI: https://pypi.org/project/textual/

## Summary

**TL;DR:**
- **Problem**: Textual aggressively caches CSS files
- **Solution**: Use inline CSS in Python file (`CSS = """..."""`)
- **Benefit**: Zero caching issues, immediate updates, simpler deployment

---

**Last Updated:** 2025-10-23
**Textual Version:** 6.4.0
**Status:** Active workaround in production

---

## Resolved Issues (October 2025)

The following issues were fixed in a comprehensive debugging session. See `docs/history/BUGFIX_COMPREHENSIVE_TEXTUAL_2025.md` for complete technical details.

### ✅ Command Prompt Not Working

**Symptom:**
- Type command, press Enter → nothing happens
- No error messages, no feedback
- Appeared completely broken

**Root Cause:**
CommandInput widget was hidden by default (`display = False`). Users were typing into AIInput widget by mistake.

**Fix:**
```python
# textual_app.py:343
self.query_one(CommandInput).display = True
self.command_mode = True
```

**Status:** ✅ Fixed Oct 2025

---

### ✅ Edit/Delete Targets Wrong Task in Detail View

**Symptom:**
- In detail view: clicking task #3 edits/deletes task #1 or #2
- Especially broken when tasks have comments or descriptions
- Operations target incorrect task

**Root Cause:**
Row-to-task mapping used enumeration index instead of actual row count. In detail view, each task creates multiple rows (main + comment + description), causing mapping to break.

**Fix:**
```python
# textual_widgets/task_table.py:97-119
# Use len(self.rows) instead of idx parameter
current_row = len(self.rows)
self._row_to_task_id[current_row] = task.id

# Map detail rows to same task ID
if view_mode == "detail":
    if task.comment:
        current_row = len(self.rows)
        self._row_to_task_id[current_row] = task.id
        # ... add comment row
```

**Status:** ✅ Fixed Oct 2025

---

### ✅ AI Streaming Crashes

**Symptom:**
- Random crashes during AI message streaming
- Race conditions updating conversation
- Data corruption in message history

**Root Cause:**
Worker threads directly mutating shared state without synchronization, violating Textual's threading model.

**Fix:**
```python
# textual_app.py:727-755
# All UI updates from worker threads must use call_from_thread()

def update_content(content=response_content, text_chunk=chunk):
    """Update message content safely"""
    ai_message.content = content
    ai_panel.append_to_last_message(text_chunk)

self.call_from_thread(update_content)
```

**Status:** ✅ Fixed Oct 2025

---

### ✅ Duplicate Command Execution

**Symptom:**
- Commands execute multiple times
- Race conditions in command handling
- Unexpected state mutations

**Root Cause:**
Input.Submitted events bubbling up widget tree, allowing multiple handlers to process same event.

**Fix:**
```python
# textual_widgets/command_input.py:193-194
# textual_widgets/ai_input.py:77-78
event.stop()
event.prevent_default()
```

**Status:** ✅ Fixed Oct 2025

---

### ✅ AI Chat Panel Crashes on Second Message

**Symptom:**
```
NoMatches: No nodes match query '#empty_message'
```
- First AI message works fine
- Second message crashes app

**Root Cause:**
`query_one("#empty_message")` raises exception when element doesn't exist, instead of returning None.

**Fix:**
```python
# textual_widgets/ai_chat_panel.py:106-112
try:
    empty = self.query_one("#empty_message", Label)
    empty.remove()
except Exception:
    # Empty state already removed
    pass
```

**Status:** ✅ Fixed Oct 2025

---

### ✅ Performance Issues with Large Task Lists

**Symptom:**
- Slow filtering with 1000+ tasks
- Lag on every keystroke/navigation
- 50-100ms delays

**Root Cause:**
Filtering recalculated on every render, even when tasks/filter unchanged.

**Fix:**
```python
# core/state.py:254-295
@property
def filtered_tasks(self) -> list[Task]:
    """Cached filtered tasks with automatic invalidation"""
    current_key = (
        self.filter,
        len(self.tasks),
        tuple(t.id for t in self.tasks),
        tuple(t.done for t in self.tasks)
    )

    if self._filter_cache_key == current_key:
        return self._filtered_tasks_cache  # Cache hit - O(1)

    # Cache miss - recalculate
    filtered = self.get_filter_tasks(self.tasks)
    self._filter_cache_key = current_key
    self._filtered_tasks_cache = filtered
    return filtered
```

**Impact:** 95%+ cache hit rate, 50-100ms → <1ms

**Status:** ✅ Fixed Oct 2025

---

## Prevention Patterns

### Event Bubbling Prevention
**Always** add to input submission handlers:
```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    # ... process input ...

    # REQUIRED:
    event.stop()
    event.prevent_default()
```

### Thread Safety for Workers
**All UI updates from worker threads:**
```python
@work(exclusive=True, thread=True)
async def background_task(self) -> None:
    # Compute in worker thread
    result = expensive_computation()

    # Update UI on main thread
    def update_ui():
        self.some_widget.content = result

    self.call_from_thread(update_ui)
```

### Safe DOM Queries
**Wrap query_one() when element might not exist:**
```python
try:
    element = self.query_one("#optional_element")
    element.remove()
except Exception:
    pass  # Element doesn't exist, that's fine
```

---
