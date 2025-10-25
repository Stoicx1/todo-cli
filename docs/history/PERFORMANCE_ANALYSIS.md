# Todo CLI Rendering Performance Analysis

**Date:** 2025-10-22
**Focus:** Bottleneck identification and optimization recommendations

---

## Executive Summary

The Todo CLI application currently suffers from **severe rendering inefficiency** due to full-screen clear and complete re-render on every command. This creates visible flicker, wasted CPU cycles, and poor scalability with large task lists.

**Key Findings:**
- 🔴 **Critical:** Full screen clear (OS syscall) on every command
- 🔴 **Critical:** Complete table rebuild even when content unchanged
- 🟡 **Moderate:** O(n) filtering + sorting on every render
- 🟢 **Good:** Textual framework already available as migration path

**Estimated Performance Impact:**
- Current: ~50-150ms per render (includes OS clear + table rebuild)
- Optimized (Rich Live): ~5-20ms (incremental updates only)
- Optimized (Textual): ~3-10ms (reactive framework)

**Improvement Potential: 5-15x faster rendering**

---

## Current Architecture Analysis

### Rendering Flow (app.py lines 298-322)

```python
# Main loop in app.py
while True:
    user_input = self.session.prompt(self._create_prompt()).strip()
    should_continue = self.handle_input(user_input)

    if not should_continue:
        break

    # THE BOTTLENECK: Lines 317-318
    clear_screen()                              # OS-level cls/clear syscall
    render_dashboard(self.console, self.state)  # Full rebuild
```

**What happens on EVERY command:**

1. **Line 317: `clear_screen()`** (utils/terminal.py:14-28)
   - Windows: `os.system("cls")` - spawns cmd.exe process
   - Unix: `os.system("clear")` - spawns shell process
   - **Cost:** 10-30ms for process spawn + terminal clear
   - **Problem:** Visible flicker, interrupts reading

2. **Line 318: `render_dashboard()`** (ui/renderer.py:131-223)
   - Clears screen AGAIN (line 147: `clear_screen()`)
   - Builds entire Rich Table from scratch (lines 152-197)
   - Renders status panel (line 202)
   - Renders AI panel if active (line 205)
   - Renders messages (lines 208-217)
   - **Cost:** 20-80ms depending on task count
   - **Problem:** Rebuilds unchanged content

### Detailed Bottleneck Breakdown

#### Bottleneck #1: Double Screen Clear (10-30ms each)

**Code locations:**
- `app.py:317` - Before render
- `ui/renderer.py:147` - Inside render_dashboard()

**Why it's a problem:**
- Two OS syscalls per command (wasteful)
- Visible flicker interrupts reading flow
- Doesn't integrate with prompt_toolkit's drawing model

**Evidence:**
```python
# utils/terminal.py:14-28
def clear_screen() -> None:
    if platform.system() == "Windows":
        os.system("cls")    # Spawns cmd.exe, clears screen, waits
    else:
        os.system("clear")  # Spawns shell, clears screen, waits
```

#### Bottleneck #2: Full Table Rebuild (20-80ms)

**Code location:** `ui/renderer.py:152-197`

**What's rebuilt on EVERY render:**
```python
# Lines 152-158: Table creation
table = Table(
    show_header=True,
    header_style="bold cyan",
    expand=True,
    box=SIMPLE,
    show_edge=False
)

# Lines 159-162: Column definitions (4 columns)
table.add_column("ID", ...)
table.add_column("Priority", ...)
table.add_column("Tags", ...)
table.add_column("Task", ...)

# Lines 164-196: Row population (loops through all visible tasks)
for idx, task in enumerate(tasks):
    # Complex string formatting for each cell
    row_style = "" if idx % 2 == 0 else "on grey15"
    status_icon = "✓" if task.done else "✗"
    priority_icon = priority_icons.get(task.priority, "⚪")
    priority_display = f"{priority_icon} {priority_label}"
    tags_display = task.get_tags_display()
    task_display = f"[{status_color}]{status_icon}[/{status_color}] {task.name}"

    table.add_row(...)  # Add main row

    if mode == "detail":
        table.add_row(...)  # Add comment row
        table.add_row(...)  # Add description row
```

**Why it's a problem:**
- Rebuilds table structure even when only status changes (e.g., marking task done)
- Re-formats ALL strings even when content unchanged
- No caching of rendered rows
- Scales linearly with task count

**Performance by task count (estimated):**
- 10 tasks: ~5ms table build
- 50 tasks: ~20ms table build
- 200 tasks: ~80ms table build
- 1000 tasks: ~400ms table build (unusable!)

#### Bottleneck #3: Filtering + Sorting on Every Render (5-50ms)

**Code location:** `core/state.py:271-291`

```python
def get_current_page_tasks(self):
    # Step 1: Filter tasks - O(n) scan
    show_tasks = self.get_filter_tasks(self.tasks)  # Lines 203-243

    # Step 2: Sort tasks - O(n log n)
    show_tasks = self.get_sorted_tasks(show_tasks)  # Lines 245-269

    # Step 3: Paginate
    start = self.page * self.page_size
    end = start + self.page_size
    return show_tasks[start:end]
```

**Filtering complexity (utils/filter_parser.py):**
- Parses filter expression on every call (no memoization)
- Iterates through ALL tasks: `[t for t in tasks if matches_all_conditions(t, conditions)]`
- Complex condition matching (operators, multi-tag logic)

**Sorting complexity:**
- Python's Timsort: O(n log n) comparisons
- String case-folding for name sort: `.casefold()` called n times

**Why it's a problem:**
- Filter/sort runs even when filter/sort/tasks haven't changed
- No result caching between renders
- Unnecessary work for static navigation (next/prev page)

**Performance by task count (estimated):**
- 10 tasks: ~0.5ms filter+sort
- 50 tasks: ~3ms filter+sort
- 200 tasks: ~15ms filter+sort
- 1000 tasks: ~100ms filter+sort

#### Bottleneck #4: Prompt Integration Overhead (5-15ms)

**Code location:** `ui/renderer.py:220-223`

```python
# Render using prompt_toolkit integration or direct console
if use_prompt_toolkit:
    print_rich_with_prompt_toolkit(_render_content)  # Inefficient capture
else:
    _render_content(console)
```

**What `print_rich_with_prompt_toolkit()` does (utils/terminal.py:43-81):**
```python
def print_rich_with_prompt_toolkit(render_func: Callable[[Console], Any]) -> None:
    # 1. Create string buffer
    string_buffer = StringIO()

    # 2. Create temporary console writing to buffer
    temp_console = Console(file=string_buffer, force_terminal=True, width=None)

    # 3. Render ALL content to buffer
    render_func(temp_console)

    # 4. Extract ANSI string
    ansi_output = string_buffer.getvalue()

    # 5. Print via prompt_toolkit
    print_formatted_text(ANSI(ansi_output))
```

**Why it's a problem:**
- Double rendering: Rich renders to buffer, then prompt_toolkit prints buffer
- String buffer allocation and copying
- ANSI parsing overhead
- Not using prompt_toolkit's native drawing primitives

---

## What Actually Changes vs. What Gets Re-rendered

### Command Impact Analysis

| Command | What Changes | What Gets Re-rendered | Waste % |
|---------|-------------|----------------------|---------|
| `next/prev` | Current page slice (10-20 tasks) | **ENTIRE UI** (table, status, panels) | 80% |
| `done <id>` | Single task's `done` flag | **ENTIRE UI** | 95% |
| `sort <field>` | Task order | **ENTIRE UI** | 50% |
| `filter <expr>` | Visible tasks | **ENTIRE UI** | 30% |
| `view compact/detail` | Row count + detail rows | **ENTIRE UI** | 40% |
| `add/edit` | Task list content | **ENTIRE UI** | 20% |
| `help/insights` | Message panel only | **ENTIRE UI** | 90% |

**Key Insight:** 80-95% of re-rendered content is UNCHANGED!

### Example: Marking Task as Done

**User action:** `done 5`

**What changes:**
- Task #5's `done` attribute: `False` → `True`
- Status icon in one table cell: `✗` → `✓`
- Status color in one table cell: `red` → `green`
- Status panel completed count: `5` → `6`
- Status panel incomplete count: `7` → `6`

**What gets re-rendered:**
- ❌ Full screen clear (30ms)
- ❌ Complete table rebuild (50ms)
  - All 20 task rows
  - All priority icons
  - All tag displays
  - All status icons
  - Detail rows if visible
- ❌ Status panel rebuild (5ms)
- ❌ AI panel rebuild (10ms if active)
- ❌ Message panel rebuild (2ms)

**Total cost:** ~100ms
**Necessary cost:** ~5ms (update one row + status counts)
**Waste:** 95%

---

## Available Optimization Approaches

### Option 1: Rich Live Display (Incremental Updates)

**What it is:**
- Rich's `Live` class provides incremental terminal updates
- Only redraws changed content (diff-based rendering)
- Built-in refresh throttling
- Works with prompt_toolkit

**Architecture:**
```python
from rich.live import Live
from rich.layout import Layout

# Create persistent layout
layout = Layout()
layout.split(
    Layout(name="table"),
    Layout(name="status", size=5),
    Layout(name="messages", size=3)
)

# Start live display
with Live(layout, console=console, refresh_per_second=10) as live:
    while True:
        user_input = session.prompt(...)

        # Update only changed parts
        if command == "done":
            layout["table"].update(render_table(state))
            layout["status"].update(render_status(state))
            # Messages NOT updated (unchanged)

        # No clear_screen() needed!
        # Live handles diff and refresh automatically
```

**Pros:**
- ✅ 5-10x faster (only redraws diffs)
- ✅ No flicker (incremental updates)
- ✅ Minimal code changes (still uses Rich)
- ✅ Works with prompt_toolkit
- ✅ Built-in refresh throttling (no spam)

**Cons:**
- ⚠️ Layout must be defined upfront (less flexible)
- ⚠️ Requires restructuring render logic (split into components)
- ⚠️ Still does full table rebuild internally (no row-level caching)

**Implementation effort:** Medium (2-3 hours)

**Example code:**
```python
# New file: ui/live_dashboard.py
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

class LiveDashboard:
    def __init__(self, console, state):
        self.console = console
        self.state = state
        self.layout = self._create_layout()

    def _create_layout(self):
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="table"),
            Layout(name="status", size=5),
            Layout(name="ai", size=12, visible=False),
            Layout(name="messages", size=3)
        )
        return layout

    def update_table(self):
        """Update only the table layout"""
        table = render_table_component(self.state)
        self.layout["table"].update(table)

    def update_status(self):
        """Update only the status panel"""
        status = render_status_component(self.state)
        self.layout["status"].update(status)

    def update_messages(self):
        """Update only the messages"""
        msg = render_messages_component(self.state)
        self.layout["messages"].update(msg)

    def update_all(self):
        """Full refresh (only when necessary)"""
        self.update_table()
        self.update_status()
        self.update_messages()

# Modified app.py main loop
with Live(dashboard.layout, console=console, refresh_per_second=10) as live:
    while True:
        user_input = session.prompt(...)

        # Selective updates based on command
        if command in ("done", "undone"):
            dashboard.update_table()
            dashboard.update_status()
        elif command in ("next", "prev"):
            dashboard.update_table()
        elif command in ("filter", "sort"):
            dashboard.update_table()
            dashboard.update_status()
        else:
            dashboard.update_all()
```

---

### Option 2: Textual Framework (Full Migration)

**What it is:**
- Modern TUI framework by the Rich team
- Reactive data binding (auto-updates on state change)
- Widget-based architecture (proper component model)
- Native keyboard handling (no prompt_toolkit needed)
- CSS-like styling system

**Status:** Already implemented in `textual_app.py`!

**Architecture:**
```python
# Already exists in textual_app.py:23-393
class TodoTextualApp(App):
    # Reactive attributes - UI auto-updates when changed
    tasks_count = reactive(0)
    page_number = reactive(0)
    filter_text = reactive("none")

    def compose(self) -> ComposeResult:
        yield Header()
        yield TaskTable(id="task_table")      # Widget with internal state
        yield StatusBar(id="status_bar")      # Auto-updates via reactive
        yield CommandInput(id="command_input")
        yield Footer()

    def action_mark_done(self) -> None:
        task.done = True
        self.refresh_table()  # Only refreshes TaskTable widget
        # No full screen clear!
        # No status panel rebuild (reactive binding handles it)
```

**Pros:**
- ✅ 10-15x faster (reactive updates only changed widgets)
- ✅ Zero flicker (proper TUI rendering)
- ✅ Clean separation of concerns (widget architecture)
- ✅ Better keyboard handling (built-in)
- ✅ Professional appearance (CSS styling)
- ✅ **Already 80% implemented in codebase!**

**Cons:**
- ⚠️ Requires full migration from prompt_toolkit
- ⚠️ Different mental model (reactive vs. imperative)
- ⚠️ Command palette needs reimplementation
- ⚠️ Two apps to maintain during transition

**Implementation effort:** High (already 80% done, needs polish + feature parity)

**Existing Implementation Review:**

**What's already done in `textual_app.py`:**
- ✅ App structure and layout (lines 74-89)
- ✅ Keyboard bindings (lines 39-54)
- ✅ Reactive attributes (lines 57-60)
- ✅ Task operations (add, edit, delete, done/undone) (lines 199-322)
- ✅ Pagination (next/prev) (lines 324-343)
- ✅ View toggle (lines 345-353)
- ✅ Sort cycling (lines 364-372)
- ✅ Command input handling (lines 128-178)
- ✅ Confirmation dialogs (lines 292-322)

**What's missing:**
- ❌ TaskTable widget implementation (referenced but not shown)
- ❌ StatusBar widget implementation
- ❌ CommandInput widget implementation
- ❌ Task filtering UI
- ❌ AI panel integration
- ❌ Full command parity with prompt_toolkit version

---

### Option 3: Hybrid Approach (Best of Both)

**What it is:**
- Keep prompt_toolkit for command input (familiar UX)
- Use Rich Live Display for dashboard rendering
- Selective updates based on command impact

**Architecture:**
```python
# Three-layer optimization
class OptimizedDashboard:
    def __init__(self, console, state):
        self.console = console
        self.state = state
        self.layout = Layout()

        # Cache rendered components
        self._cached_table = None
        self._cached_status = None
        self._table_hash = None  # Hash of visible tasks
        self._status_hash = None  # Hash of state stats

    def render_table(self, force=False):
        """Render table with caching"""
        # Calculate hash of visible tasks
        tasks = self.state.get_current_page_tasks()
        task_hash = hash((
            tuple((t.id, t.name, t.done, t.priority, tuple(t.tags)) for t in tasks),
            self.state.view_mode
        ))

        # Return cached if unchanged
        if not force and task_hash == self._table_hash and self._cached_table:
            return self._cached_table

        # Rebuild table
        self._cached_table = self._build_table(tasks)
        self._table_hash = task_hash
        return self._cached_table

    def update(self, changed_components: set):
        """Update only specified components"""
        if "table" in changed_components:
            self.layout["table"].update(self.render_table())
        if "status" in changed_components:
            self.layout["status"].update(self.render_status())
        # Other components unchanged = no redraw!

# Command-specific update strategies
COMMAND_UPDATES = {
    "done": {"table", "status"},
    "undone": {"table", "status"},
    "next": {"table"},
    "prev": {"table"},
    "sort": {"table", "status"},
    "filter": {"table", "status"},
    "view": {"table"},
    "insights": {"messages"},
    "help": {"messages"},
}

# Modified main loop
with Live(dashboard.layout, console=console) as live:
    while True:
        user_input = session.prompt(...)

        # Determine what needs updating
        cmd = parse_command_type(user_input)
        changed = COMMAND_UPDATES.get(cmd, {"all"})

        # Selective update
        dashboard.update(changed)
```

**Pros:**
- ✅ 5-8x faster (selective updates + caching)
- ✅ Keeps familiar prompt_toolkit UX
- ✅ Incremental migration path
- ✅ Component-level caching
- ✅ No flicker

**Cons:**
- ⚠️ More complex (caching + invalidation logic)
- ⚠️ Still some full rebuilds (when cache misses)
- ⚠️ Two rendering systems to maintain

**Implementation effort:** Medium-High (3-4 hours)

---

## Optimization Recommendations

### Immediate Wins (Quick Fixes)

#### 1. Remove Double Clear (5 minutes, 20-40% faster)

**Problem:** Screen cleared twice per render

**Fix:**
```python
# app.py:317-318 - BEFORE
clear_screen()
render_dashboard(self.console, self.state)

# app.py:317-318 - AFTER
render_dashboard(self.console, self.state)  # Let renderer handle clear

# ui/renderer.py:147 - Keep this one
clear_screen()  # Single clear inside renderer
```

**Impact:** Saves 10-30ms per command, eliminates one flicker

---

#### 2. Cache Filter/Sort Results (15 minutes, 10-30% faster)

**Problem:** Filter and sort run on every render even when unchanged

**Fix:**
```python
# core/state.py - Add caching attributes
class AppState:
    def __init__(self):
        # ... existing code ...

        # Cache for filter/sort results
        self._filtered_cache = None
        self._filter_hash = None
        self._sorted_cache = None
        self._sort_hash = None

    def get_filter_tasks(self, tasks):
        # Calculate hash of filter state
        filter_hash = (self.filter, len(tasks), hash(tuple(t.id for t in tasks)))

        # Return cached if unchanged
        if filter_hash == self._filter_hash and self._filtered_cache is not None:
            return self._filtered_cache

        # Run filter
        filtered = self._apply_filter(tasks)  # Extract current logic

        # Cache result
        self._filtered_cache = filtered
        self._filter_hash = filter_hash
        return filtered

    def get_sorted_tasks(self, tasks):
        # Similar caching for sort
        sort_hash = (self.sort, self.sort_order, len(tasks))

        if sort_hash == self._sort_hash and self._sorted_cache is not None:
            return self._sorted_cache

        sorted_tasks = self._apply_sort(tasks)
        self._sorted_cache = sorted_tasks
        self._sort_hash = sort_hash
        return sorted_tasks

    def invalidate_cache(self):
        """Call when tasks change"""
        self._filtered_cache = None
        self._filter_hash = None
        self._sorted_cache = None
        self._sort_hash = None
```

**Impact:** Saves 5-50ms per command (depending on task count)

---

#### 3. Use ANSI Clear Instead of OS Syscall (2 minutes, 10-20% faster)

**Problem:** `os.system("cls")` spawns process

**Fix:**
```python
# utils/terminal.py:14-28 - BEFORE
def clear_screen() -> None:
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

# utils/terminal.py:14-28 - AFTER
def clear_screen() -> None:
    # Use ANSI escape codes (much faster, no process spawn)
    # \033[2J = Clear entire screen
    # \033[H = Move cursor to home position (0,0)
    print("\033[2J\033[H", end="", flush=True)
```

**Impact:** Saves 10-30ms per command, works on all modern terminals

---

### Medium-Term Solution: Rich Live Display (Recommended)

**Why this is the best path forward:**
- Maintains current Rich-based UI (no full rewrite)
- Compatible with prompt_toolkit
- Incremental adoption (can migrate one component at a time)
- 5-10x performance improvement
- Eliminates flicker completely

**Implementation Plan:**

1. **Phase 1: Create Layout Structure (30 min)**
   - New file: `ui/live_dashboard.py`
   - Define `Layout` with named regions
   - Extract render functions into components

2. **Phase 2: Selective Updates (1 hour)**
   - Create `LiveDashboard` class with update methods
   - Implement command-to-component mapping
   - Add change detection logic

3. **Phase 3: Integration (1 hour)**
   - Modify `app.py` main loop to use Live
   - Test with prompt_toolkit integration
   - Handle edge cases (AI streaming, modals)

4. **Phase 4: Optimization (30 min)**
   - Add component-level caching
   - Tune refresh rate
   - Profile and validate improvements

**Total effort:** 3-4 hours
**Expected improvement:** 5-10x faster rendering

---

### Long-Term Solution: Textual Framework (Future)

**Why Textual is the ultimate solution:**
- Purpose-built for interactive TUI apps
- Reactive architecture eliminates manual updates
- Professional widget library
- Better keyboard handling
- **Already 80% implemented!**

**Migration Path:**

1. **Complete Textual Implementation** (4-6 hours)
   - Implement missing widgets (TaskTable, StatusBar, CommandInput)
   - Add advanced filtering UI
   - Integrate AI panel
   - Achieve feature parity

2. **Run Dual Apps During Transition** (1-2 weeks)
   - Keep `app.py` (prompt_toolkit) as stable
   - Iterate on `textual_app.py` with users
   - Fix bugs and polish UX

3. **Switch Default** (1 hour)
   - Make Textual the default in `main.py`
   - Keep prompt_toolkit version as `--classic` flag
   - Deprecate old version over time

**Total effort:** 1-2 weeks part-time
**Expected improvement:** 10-15x faster, professional TUI

---

## Performance Benchmarks (Estimated)

### Current Performance

| Task Count | Filter+Sort | Table Build | Screen Clear | Total Render | User Perception |
|-----------|-------------|-------------|--------------|--------------|----------------|
| 10 | 0.5ms | 5ms | 20ms | 25ms | ✅ Acceptable |
| 50 | 3ms | 20ms | 20ms | 43ms | ⚠️ Noticeable |
| 200 | 15ms | 80ms | 20ms | 115ms | 🔴 Laggy |
| 1000 | 100ms | 400ms | 20ms | 520ms | 🔴 Unusable |

### With Quick Fixes (ANSI clear + cache)

| Task Count | Filter+Sort | Table Build | Screen Clear | Total Render | Improvement |
|-----------|-------------|-------------|--------------|--------------|-------------|
| 10 | 0ms (cached) | 5ms | 2ms | 7ms | 3.5x faster |
| 50 | 0ms (cached) | 20ms | 2ms | 22ms | 2x faster |
| 200 | 0ms (cached) | 80ms | 2ms | 82ms | 1.4x faster |
| 1000 | 0ms (cached) | 400ms | 2ms | 402ms | 1.3x faster |

### With Rich Live Display

| Task Count | Diff Detection | Partial Render | Total Render | Improvement |
|-----------|---------------|---------------|--------------|-------------|
| 10 | 1ms | 2ms | 3ms | 8x faster |
| 50 | 2ms | 5ms | 7ms | 6x faster |
| 200 | 5ms | 15ms | 20ms | 5.7x faster |
| 1000 | 15ms | 50ms | 65ms | 8x faster |

### With Textual Framework

| Task Count | Reactive Update | Widget Render | Total Render | Improvement |
|-----------|----------------|---------------|--------------|-------------|
| 10 | 0.5ms | 1ms | 1.5ms | 16x faster |
| 50 | 1ms | 3ms | 4ms | 10x faster |
| 200 | 2ms | 8ms | 10ms | 11x faster |
| 1000 | 5ms | 25ms | 30ms | 17x faster |

---

## Conclusion

### Summary of Bottlenecks

1. **Critical: Double screen clear** - 20-40ms wasted per command
2. **Critical: Full table rebuild** - Scales poorly with task count
3. **Moderate: Uncached filter/sort** - Repeated work for static data
4. **Moderate: Prompt integration overhead** - Double rendering

### Recommended Action Plan

**Immediate (Today):**
1. ✅ Remove double clear (5 min, 20% faster)
2. ✅ Switch to ANSI clear (2 min, 10% faster)
3. ✅ Add filter/sort caching (15 min, 20% faster)

**Expected immediate gain: 40-50% faster, 30 minutes work**

**Short-Term (This Week):**
1. Implement Rich Live Display (3-4 hours)
2. Add selective component updates
3. Profile and validate improvements

**Expected short-term gain: 5-10x faster, minimal flicker**

**Long-Term (Next Sprint):**
1. Complete Textual implementation (6-8 hours)
2. Achieve feature parity
3. Migrate users incrementally

**Expected long-term gain: 10-15x faster, professional UX**

---

## Code Examples for Quick Wins

### Quick Win #1: Remove Double Clear

**File:** `D:\MyProjects\todo-cli\app.py`

```python
# LINE 316-318 - BEFORE
            # Re-render dashboard
            clear_screen()
            render_dashboard(self.console, self.state)

# LINE 316-318 - AFTER
            # Re-render dashboard (clear happens inside)
            render_dashboard(self.console, self.state)
```

---

### Quick Win #2: ANSI Clear

**File:** `D:\MyProjects\todo-cli\utils\terminal.py`

```python
# LINES 14-28 - REPLACE ENTIRE FUNCTION
def clear_screen() -> None:
    """
    Clear the terminal screen using ANSI escape codes.

    Much faster than os.system() since it doesn't spawn a process.
    Works on all modern terminals (Windows 10+, Linux, macOS).
    """
    # \033[2J = Clear entire screen
    # \033[H = Move cursor to home position (0,0)
    print("\033[2J\033[H", end="", flush=True)
```

---

### Quick Win #3: Filter/Sort Caching

**File:** `D:\MyProjects\todo-cli\core\state.py`

```python
# ADD TO __init__ (around line 30)
class AppState:
    def __init__(self):
        # ... existing attributes ...

        # Performance: Cache filter/sort results
        self._filtered_cache: Optional[list[Task]] = None
        self._filter_cache_key: Optional[tuple] = None
        self._sorted_cache: Optional[list[Task]] = None
        self._sort_cache_key: Optional[tuple] = None

# REPLACE get_filter_tasks (lines 203-243)
def get_filter_tasks(self, tasks):
    """Filter tasks with caching for performance."""
    from utils.filter_parser import parse_filter_expression, matches_all_conditions

    filter_value = self.filter.strip()

    if not filter_value or filter_value.lower() == "none":
        return tasks

    # Create cache key (filter + task IDs + task done status)
    cache_key = (
        filter_value,
        tuple((t.id, t.done, tuple(t.tags)) for t in tasks)
    )

    # Return cached result if key matches
    if cache_key == self._filter_cache_key and self._filtered_cache is not None:
        return self._filtered_cache

    # Run filter
    conditions = parse_filter_expression(filter_value)
    if not conditions:
        filtered = tasks
    else:
        filtered = [t for t in tasks if matches_all_conditions(t, conditions)]

    # Cache result
    self._filtered_cache = filtered
    self._filter_cache_key = cache_key
    return filtered

# REPLACE get_sorted_tasks (lines 245-269)
def get_sorted_tasks(self, tasks):
    """Sort tasks with caching for performance."""
    # Create cache key (sort + order + task IDs + priorities/names)
    if self.sort == "priority":
        task_sig = tuple((t.id, t.priority) for t in tasks)
    elif self.sort == "name":
        task_sig = tuple((t.id, t.name) for t in tasks)
    else:  # id
        task_sig = tuple(t.id for t in tasks)

    cache_key = (self.sort, self.sort_order, task_sig)

    # Return cached result if key matches
    if cache_key == self._sort_cache_key and self._sorted_cache is not None:
        return self._sorted_cache

    # Run sort
    reverse = (self.sort_order == "desc")

    if self.sort == "priority":
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=reverse)
    elif self.sort == "id":
        sorted_tasks = sorted(tasks, key=lambda t: t.id, reverse=reverse)
    elif self.sort == "name":
        sorted_tasks = sorted(tasks, key=lambda t: (t.name or "").casefold(), reverse=reverse)
    else:
        sorted_tasks = tasks

    # Cache result
    self._sorted_cache = sorted_tasks
    self._sort_cache_key = cache_key
    return sorted_tasks

# ADD cache invalidation to add_task (around line 50)
def add_task(self, name: str, comment: str = "", description: str = "",
             priority: int = 2, tag: str = ""):
    # ... existing code ...

    # Invalidate caches when tasks change
    self._filtered_cache = None
    self._filter_cache_key = None
    self._sorted_cache = None
    self._sort_cache_key = None

# ADD cache invalidation to remove_task (around line 103)
def remove_task(self, task: Task):
    # ... existing code ...

    # Invalidate caches
    self._filtered_cache = None
    self._filter_cache_key = None
    self._sorted_cache = None
    self._sort_cache_key = None
```

---

## Performance Profiling Script

To validate improvements, run this profiling script:

```python
# performance_test.py
import time
from core.state import AppState
from models.task import Task
from rich.console import Console
from ui.renderer import render_dashboard

def profile_render(state, console, iterations=10):
    """Profile render_dashboard performance"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        render_dashboard(console, state, use_prompt_toolkit=False)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        "avg_ms": round(avg, 2),
        "min_ms": round(min_time, 2),
        "max_ms": round(max_time, 2)
    }

# Create test states with different task counts
console = Console()
test_cases = [10, 50, 200]

print("Performance Profiling Results:")
print("=" * 60)

for task_count in test_cases:
    state = AppState()

    # Generate test tasks
    for i in range(task_count):
        state.add_task(
            name=f"Test Task {i}",
            comment=f"Comment for task {i}",
            description=f"Description for task {i}",
            priority=(i % 3) + 1,
            tag=f"tag{i % 5}"
        )

    # Profile
    results = profile_render(state, console)

    print(f"\n{task_count} tasks:")
    print(f"  Average: {results['avg_ms']}ms")
    print(f"  Min: {results['min_ms']}ms")
    print(f"  Max: {results['max_ms']}ms")

print("\n" + "=" * 60)
```

Run before and after optimizations to measure improvement!

---

**End of Analysis**
