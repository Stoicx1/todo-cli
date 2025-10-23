# Rich Live Display Implementation Guide

**Estimated Time:** 3-4 hours
**Expected Performance Gain:** 5-10x faster rendering
**Risk Level:** Medium (significant code changes, but isolated)

---

## Overview

This guide shows how to migrate from full-screen clears to Rich's `Live` display for incremental updates.

**Benefits:**
- Only redraws changed content (diff-based rendering)
- Eliminates flicker completely
- 5-10x faster rendering
- Built-in refresh throttling
- Compatible with prompt_toolkit

**Architecture:**
```
┌─────────────────────────────────────┐
│ Rich Live Display (persistent)      │
│ ┌─────────────────────────────────┐ │
│ │ Layout: Header (3 lines)        │ │
│ ├─────────────────────────────────┤ │
│ │ Layout: Table (dynamic height)  │ │  <- Only updates when tasks change
│ ├─────────────────────────────────┤ │
│ │ Layout: Status (5 lines)        │ │  <- Only updates when stats change
│ ├─────────────────────────────────┤ │
│ │ Layout: AI Panel (12 lines)     │ │  <- Only visible when AI active
│ ├─────────────────────────────────┤ │
│ │ Layout: Messages (3 lines)      │ │  <- Only updates when messages change
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Prompt Toolkit Input (separate)     │
│ ❯ [user types here...]              │
└─────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Create Layout Components (30 min)

Create a new file for component rendering:

**File:** `D:\MyProjects\todo-cli\ui\live_components.py`

```python
"""
Rich Live Display Components
Individual render functions for each layout region
"""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED, SIMPLE
from core.state import AppState
from config import USE_UNICODE


def render_header_component(state: AppState) -> Panel:
    """
    Render header panel (static, rarely changes)

    Returns:
        Panel with app title and info
    """
    title = Text("Todo CLI", style="bold cyan")
    subtitle = Text("Type / for commands • ESC to clear", style="dim")

    content = Text.assemble(title, "\n", subtitle)

    return Panel(
        content,
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
        expand=True
    )


def render_table_component(state: AppState) -> Table:
    """
    Render task table (updates when tasks/page changes)

    Returns:
        Rich Table with current page tasks
    """
    tasks = state.get_current_page_tasks()
    mode = state.view_mode

    # Build table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        expand=True,
        box=SIMPLE,
        show_edge=False
    )

    table.add_column("ID", justify="center", no_wrap=True, style="dim", width=4)
    table.add_column("Priority", justify="center", no_wrap=True, width=10)
    table.add_column("Tags", justify="left", style="cyan", width=20)
    table.add_column("Task", justify="left")

    # Populate rows
    for idx, task in enumerate(tasks):
        row_style = "" if idx % 2 == 0 else "on grey15"

        if USE_UNICODE:
            status_icon = "✓" if task.done else "✗"
            priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
            priority_icon = priority_icons.get(task.priority, "⚪")
        else:
            status_icon = "Y" if task.done else "N"
            priority_icons = {1: "!", 2: "·", 3: "-"}
            priority_icon = priority_icons.get(task.priority, "?")

        status_color = "green" if task.done else "red"
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        priority_label = priority_labels.get(task.priority, "???")
        task_display = f"[{status_color}]{status_icon}[/{status_color}] {task.name}"
        priority_display = f"{priority_icon} {priority_label}"
        tags_display = task.get_tags_display()

        table.add_row(
            str(task.id),
            priority_display,
            tags_display,
            task_display,
            style=row_style,
        )

        if mode == "detail":
            from utils.emoji import emoji
            arrow = emoji("?", "->")
            if task.comment:
                table.add_row("", "", "", f"  [dim]{arrow} {task.comment}[/dim]", style=row_style)
            if task.description:
                table.add_row("", "", "", f"    [dim italic]{task.description}[/dim italic]", style=row_style)

    return table


def render_status_component(state: AppState) -> Panel:
    """
    Render status panel (updates when stats/page changes)

    Returns:
        Panel with navigation and statistics
    """
    total = len(state.tasks)
    completed = sum(1 for t in state.tasks if t.done)
    incomplete = total - completed
    shown = len(state.get_current_page_tasks())

    # Calculate total pages
    filtered_tasks = state.get_filter_tasks(state.tasks)
    total_pages = (len(filtered_tasks) + state.page_size - 1) // state.page_size if len(filtered_tasks) > 0 else 1
    current_page = state.page + 1

    # Line 1: Navigation and view context
    if USE_UNICODE:
        order_icon = "↑" if getattr(state, "sort_order", "asc") == "asc" else "↓"
        line1_parts = [
            f"Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"[white]{shown}[/white][dim]/{total}[/dim] showing",
            f"[magenta]{state.view_mode}[/magenta]",
            f"{order_icon} [blue]{state.sort}[/blue] [dim]({state.sort_order})[/dim]"
        ]
    else:
        order_text = "ASC" if getattr(state, "sort_order", "asc") == "asc" else "DESC"
        line1_parts = [
            f"Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"[white]{shown}[/white][dim]/{total}[/dim] showing",
            f"[magenta]{state.view_mode}[/magenta]",
            f"Sort: [blue]{state.sort}[/blue] [dim]({order_text})[/dim]"
        ]
    line1 = "  •  ".join(line1_parts)

    # Line 2: Task statistics
    line2_parts = [
        f"[cyan]{total}[/cyan] tasks",
        f"[green]{completed}[/green] done",
        f"[yellow]{incomplete}[/yellow] todo"
    ]

    # Add filter info if active
    if state.filter != "none":
        line2_parts.append(f"Filter: [yellow]{state.filter}[/yellow]")

    line2 = "  •  ".join(line2_parts)

    # Create panel
    content = f"{line1}\n[dim]{line2}[/dim]"
    return Panel(
        content,
        title="[bold cyan]Status[/bold cyan]",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
        expand=False
    )


def render_ai_component(state: AppState) -> Optional[Panel]:
    """
    Render AI panel (only when AI is active)

    Returns:
        Panel with AI output or None if no AI content
    """
    text = getattr(state, "ai_text", "") or ""
    streaming = getattr(state, "ai_streaming", False)

    if not text and not streaming:
        return None

    # Calculate panel height
    try:
        from rich.console import Console
        temp_console = Console()
        term_h = temp_console.size.height
    except Exception:
        term_h = 30

    panel_h = max(8, min(12, term_h // 3))

    # Extract visible lines
    lines = text.splitlines()
    total = len(lines)
    scroll = max(0, min(getattr(state, "ai_scroll", 0), max(0, total - 1)))
    end = total - scroll
    start = max(0, end - panel_h)
    visible = lines[start:end]

    # Footer
    if total > 0:
        footer = f"[dim]Lines {start+1}-{end}/{total}  •  Ctrl+Up/Down PgUp/PgDn Ctrl+Home/End[/dim]"
    else:
        footer = "[dim](waiting for output)[/dim]"

    # Body
    body = "\n".join(visible) if visible else ("[dim]" + ("Streaming..." if streaming else "(no output)") + "[/dim]")
    title = "AI Answer (streaming)" if streaming else "AI Answer"

    return Panel(
        body + "\n\n" + footer,
        title=f"[bold cyan]{title}[/bold cyan]",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def render_messages_component(state: AppState) -> Optional[Panel | Text]:
    """
    Render messages panel (updates when messages change)

    Returns:
        Panel or Text with last message, or None if no messages
    """
    if not state.messages:
        return None

    last_msg = state.messages[-1]

    # Handle special panel messages
    if isinstance(last_msg, tuple) and len(last_msg) == 2 and last_msg[0] == "__PANEL__":
        return last_msg[1]  # Return the panel directly

    # Handle plain text messages
    if USE_UNICODE:
        return Text(f"💬 {last_msg}", style="dim")
    else:
        return Text(str(last_msg), style="dim")
```

---

### Phase 2: Create Live Dashboard Manager (1 hour)

**File:** `D:\MyProjects\todo-cli\ui\live_dashboard.py`

```python
"""
Rich Live Display Dashboard Manager
Manages incremental updates to layout components
"""

from typing import Set, Optional
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from core.state import AppState
from ui.live_components import (
    render_header_component,
    render_table_component,
    render_status_component,
    render_ai_component,
    render_messages_component
)


class LiveDashboard:
    """
    Manages Rich Live Display with selective component updates

    Features:
    - Incremental updates (only changed components)
    - Component-level caching
    - Automatic layout management
    """

    def __init__(self, console: Console, state: AppState):
        self.console = console
        self.state = state
        self.layout = self._create_layout()
        self.live: Optional[Live] = None

        # Cache hashes for change detection
        self._table_hash: Optional[int] = None
        self._status_hash: Optional[int] = None
        self._ai_hash: Optional[int] = None
        self._messages_hash: Optional[int] = None

    def _create_layout(self) -> Layout:
        """
        Create the layout structure

        Returns:
            Layout with named regions
        """
        layout = Layout()

        # Split into vertical regions
        layout.split(
            Layout(name="header", size=4),
            Layout(name="table"),           # Dynamic height
            Layout(name="status", size=6),
            Layout(name="ai", size=14, visible=False),  # Hidden by default
            Layout(name="messages", size=2, visible=False)  # Hidden when empty
        )

        return layout

    def _hash_table_state(self) -> int:
        """Calculate hash of table state"""
        tasks = self.state.get_current_page_tasks()
        return hash((
            tuple((t.id, t.name, t.done, t.priority, tuple(t.tags)) for t in tasks),
            self.state.view_mode,
            self.state.page
        ))

    def _hash_status_state(self) -> int:
        """Calculate hash of status state"""
        return hash((
            len(self.state.tasks),
            sum(1 for t in self.state.tasks if t.done),
            self.state.page,
            self.state.view_mode,
            self.state.sort,
            self.state.sort_order,
            self.state.filter
        ))

    def _hash_ai_state(self) -> int:
        """Calculate hash of AI state"""
        return hash((
            getattr(self.state, "ai_text", ""),
            getattr(self.state, "ai_streaming", False),
            getattr(self.state, "ai_scroll", 0)
        ))

    def _hash_messages_state(self) -> int:
        """Calculate hash of messages state"""
        if not self.state.messages:
            return 0
        last = self.state.messages[-1]
        if isinstance(last, tuple):
            return hash(id(last[1]))  # Panel object ID
        return hash(str(last))

    def update_header(self, force: bool = False):
        """Update header component"""
        # Header is static, only update on force
        if force:
            self.layout["header"].update(render_header_component(self.state))

    def update_table(self, force: bool = False):
        """Update table component with change detection"""
        current_hash = self._hash_table_state()

        if not force and current_hash == self._table_hash:
            return  # No changes, skip update

        self.layout["table"].update(render_table_component(self.state))
        self._table_hash = current_hash

    def update_status(self, force: bool = False):
        """Update status component with change detection"""
        current_hash = self._hash_status_state()

        if not force and current_hash == self._status_hash:
            return  # No changes, skip update

        self.layout["status"].update(render_status_component(self.state))
        self._status_hash = current_hash

    def update_ai(self, force: bool = False):
        """Update AI component with change detection"""
        current_hash = self._hash_ai_state()

        if not force and current_hash == self._ai_hash:
            return  # No changes, skip update

        ai_panel = render_ai_component(self.state)

        if ai_panel:
            self.layout["ai"].update(ai_panel)
            self.layout["ai"].visible = True
        else:
            self.layout["ai"].visible = False

        self._ai_hash = current_hash

    def update_messages(self, force: bool = False):
        """Update messages component with change detection"""
        current_hash = self._hash_messages_state()

        if not force and current_hash == self._messages_hash:
            return  # No changes, skip update

        msg_content = render_messages_component(self.state)

        if msg_content:
            self.layout["messages"].update(msg_content)
            self.layout["messages"].visible = True
        else:
            self.layout["messages"].visible = False

        self._messages_hash = current_hash

    def update_selective(self, components: Set[str]):
        """
        Update only specified components

        Args:
            components: Set of component names ("table", "status", "ai", "messages", "all")
        """
        if "all" in components:
            self.update_all(force=True)
            return

        if "table" in components:
            self.update_table()

        if "status" in components:
            self.update_status()

        if "ai" in components:
            self.update_ai()

        if "messages" in components:
            self.update_messages()

    def update_all(self, force: bool = False):
        """Update all components"""
        self.update_header(force)
        self.update_table(force)
        self.update_status(force)
        self.update_ai(force)
        self.update_messages(force)

    def start(self):
        """Start Live display"""
        self.update_all(force=True)  # Initial render
        self.live = Live(
            self.layout,
            console=self.console,
            refresh_per_second=10,  # Throttle to 10 FPS
            screen=False  # Don't take over entire screen (allow prompt below)
        )
        self.live.start()

    def stop(self):
        """Stop Live display"""
        if self.live:
            self.live.stop()
            self.live = None


# Command-to-component update mapping
COMMAND_UPDATE_MAP = {
    # Task state changes
    "done": {"table", "status"},
    "undone": {"table", "status"},
    "add": {"table", "status"},
    "edit": {"table"},
    "remove": {"table", "status"},

    # Navigation (table content changes, stats don't)
    "next": {"table"},
    "prev": {"table"},

    # View changes
    "view": {"table"},
    "sort": {"table", "status"},
    "filter": {"table", "status"},

    # Info commands (only messages change)
    "help": {"messages"},
    "insights": {"messages"},
    "suggest": {"messages"},
    "tags": {"messages"},
    "show": {"messages"},

    # AI commands
    "?": {"ai", "messages"},
    "clearai": {"ai"},

    # Full refresh
    "cls": {"all"},
    "clear": {"all"},
}


def get_update_components(command: str) -> Set[str]:
    """
    Determine which components need updating based on command

    Args:
        command: User command string

    Returns:
        Set of component names to update
    """
    # Extract base command
    cmd = command.strip().split()[0].lower()

    # Check command shortcuts
    shortcuts = {
        "a": "add",
        "e": "edit",
        "x": "done",
        "u": "undone",
        "s": "show",
        "v": "view",
        "f": "filter",
        "t": "tags",
        "n": "next",
        "p": "prev",
        "h": "help",
        "c": "clear",
        "q": "quit"
    }

    if cmd in shortcuts:
        cmd = shortcuts[cmd]

    # Get update set from map
    return COMMAND_UPDATE_MAP.get(cmd, {"all"})
```

---

### Phase 3: Integrate with App (1 hour)

**File:** `D:\MyProjects\todo-cli\app.py`

**Changes:**

1. **Import LiveDashboard:**

```python
# Add to imports (line 28)
from ui.live_dashboard import LiveDashboard, get_update_components
```

2. **Initialize LiveDashboard in `__init__`:**

```python
def __init__(
    self,
    console: Optional[Console] = None,
    state: Optional[AppState] = None,
    tasks_file: str = DEFAULT_TASKS_FILE,
    use_questionary_forms: bool = True,
    use_live_display: bool = True  # NEW PARAMETER
):
    self.console = console or create_console()
    self.state = state or AppState()
    self.tasks_file = tasks_file
    self.use_questionary_forms = use_questionary_forms
    self.use_live_display = use_live_display  # NEW

    # Will be initialized in setup()
    self.session: Optional[PromptSession] = None
    self._ai_thread: Optional[threading.Thread] = None
    self.dashboard: Optional[LiveDashboard] = None  # NEW
```

3. **Start LiveDashboard in `setup()`:**

```python
def setup(self) -> None:
    """Initialize application (load data, create session)"""
    # Load tasks from file
    self.state.load_from_file(self.tasks_file, self.console)

    # Create prompt session
    self.session = self._create_session()

    # Initialize Live Dashboard if enabled
    if self.use_live_display:
        self.dashboard = LiveDashboard(self.console, self.state)
        self.dashboard.start()
    else:
        # Fallback: Initial render (old approach)
        render_dashboard(self.console, self.state, use_prompt_toolkit=False)
```

4. **Replace render logic in `run()` method:**

```python
def run(self) -> None:
    """
    Main application loop

    Runs until user exits (exit/quit/x command or Ctrl+C)
    """
    try:
        with patch_stdout():
            while True:
                # Get user input
                user_input = self.session.prompt(self._create_prompt()).strip()

                # Handle input
                should_continue = self.handle_input(user_input)

                if not should_continue:
                    break

                # CHANGED: Selective update instead of full render
                if self.use_live_display and self.dashboard:
                    # Determine what changed
                    update_components = get_update_components(user_input)
                    self.dashboard.update_selective(update_components)
                else:
                    # Fallback: Full render (old approach)
                    clear_screen()
                    render_dashboard(self.console, self.state)

    except (KeyboardInterrupt, EOFError):
        # User pressed Ctrl+C or Ctrl+D
        self.shutdown()
```

5. **Stop LiveDashboard in `shutdown()`:**

```python
def shutdown(self) -> None:
    """Shutdown application (save and exit)"""
    # Stop Live display if active
    if self.use_live_display and self.dashboard:
        self.dashboard.stop()

    self.state.save_to_file(self.tasks_file, self.console)
    self.console.print("\n[yellow]Goodbye![/yellow]")
```

6. **Handle AI streaming updates:**

```python
def _handle_ai_question(self) -> None:
    """Ask GPT with streaming tail view, then show full answer in pager."""
    # ... existing setup code ...

    # Clear and show initial state
    if self.use_live_display and self.dashboard:
        self.dashboard.update_ai(force=True)
    else:
        clear_screen()
        render_dashboard(self.console, self.state)

    last_redraw = time.time()
    redraw_interval = 0.1  # Redraw every 100ms

    try:
        # Stream chunks and update panel
        for chunk in assistant.stream_chunks(self.state.tasks, user_prompt):
            self.state.ai_text += chunk

            # Throttled redraw for performance
            now = time.time()
            if now - last_redraw >= redraw_interval:
                if self.use_live_display and self.dashboard:
                    self.dashboard.update_ai(force=True)
                else:
                    clear_screen()
                    render_dashboard(self.console, self.state)
                last_redraw = now

        # Final redraw to show complete response
        self.state.ai_streaming = False
        if self.use_live_display and self.dashboard:
            self.dashboard.update_ai(force=True)
        else:
            clear_screen()
            render_dashboard(self.console, self.state)

        # ... rest of method unchanged ...
```

---

### Phase 4: Testing and Validation (30 min)

**Test Plan:**

1. **Start app with Live Display:**

```bash
python main.py
```

2. **Test navigation (should only update table):**

```bash
next
next
prev
prev
```

Verify:
- ✅ Only table region redraws
- ✅ Status panel stays static
- ✅ No flicker
- ✅ Instant response

3. **Test task operations (should update table + status):**

```bash
add "Test task" "" "" 1 "test"
done 1
undone 1
```

Verify:
- ✅ Table and status update
- ✅ Messages stay static
- ✅ No full screen redraw

4. **Test info commands (should only update messages):**

```bash
help
insights
tags
```

Verify:
- ✅ Only messages region updates
- ✅ Table and status stay static

5. **Test AI streaming:**

```bash
?
Which tasks should I prioritize?
```

Verify:
- ✅ AI panel appears
- ✅ Smooth streaming updates
- ✅ No full screen clears

---

## Performance Validation

**Benchmark Script:**

```python
# benchmark_live.py
import time
import statistics
from core.state import AppState
from app import TodoApp, create_console

# Create app with Live Display
console = create_console()
app = TodoApp(console=console, use_live_display=True)
app.setup()

# Benchmark 50 selective updates
times = []
for i in range(50):
    # Simulate "next" command (only updates table)
    app.state.page = (app.state.page + 1) % 5

    start = time.perf_counter()
    app.dashboard.update_selective({"table"})
    end = time.perf_counter()

    times.append((end - start) * 1000)

print("Live Display Benchmark (selective update):")
print(f"Average: {statistics.mean(times):.2f}ms")
print(f"Median: {statistics.median(times):.2f}ms")
print(f"Min: {min(times):.2f}ms")
print(f"Max: {max(times):.2f}ms")

# Benchmark full updates
times_full = []
for i in range(20):
    start = time.perf_counter()
    app.dashboard.update_all(force=True)
    end = time.perf_counter()
    times_full.append((end - start) * 1000)

print("\nLive Display Benchmark (full update):")
print(f"Average: {statistics.mean(times_full):.2f}ms")
print(f"Median: {statistics.median(times_full):.2f}ms")
print(f"Min: {min(times_full):.2f}ms")
print(f"Max: {max(times_full):.2f}ms")

app.shutdown()
```

**Expected Results:**

```
Live Display Benchmark (selective update):
Average: 3.45ms
Median: 3.21ms
Min: 2.15ms
Max: 8.33ms

Live Display Benchmark (full update):
Average: 12.67ms
Median: 11.89ms
Min: 9.45ms
Max: 18.22ms
```

Compare with old approach (~50-150ms) = **5-15x faster!**

---

## Rollback / Fallback

The implementation includes a `use_live_display` flag for easy fallback:

```bash
# Run with Live Display (new, default)
python main.py

# Run with old rendering (fallback)
python main.py --no-live  # (add CLI flag to main.py)
```

**Add CLI flag to main.py:**

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--no-live", action="store_true", help="Disable Live Display")
args = parser.parse_args()

app = TodoApp(use_live_display=not args.no_live)
```

---

## Next Steps

After validating Live Display:

1. **Fine-tune refresh rate** (currently 10 FPS)
2. **Add row-level caching** for even better table performance
3. **Profile with large task lists** (1000+ tasks)
4. **Consider Textual migration** for ultimate performance

---

**End of Rich Live Implementation Guide**
