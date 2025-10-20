from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, ThreadedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import os
import sys
from core.commands import handle_command
from core.state import AppState
from core.suggestions import LocalSuggestions
from ui.renderer import render_dashboard
from ui.command_palette import create_command_completer, get_available_tags
from ui.task_forms import AddTaskModal, EditTaskModal
from ui.feedback import show_success, show_error
from ui.questionary_forms import questionary_add_task, questionary_edit_task

# Unicode/emoji support detection for Windows compatibility
USE_UNICODE = (
    sys.stdout.encoding and
    sys.stdout.encoding.lower() in ('utf-8', 'utf8')
)

# Form system selection
USE_MODAL_FORMS = False  # Disabled: modal forms non-functional (fields don't accept input)
USE_QUESTIONARY_FORMS = True  # Enabled: questionary forms work great!


def inline_add_task(console):
    console.print("\n[bold green]Add New Task[/bold green]")
    console.print("[dim]Type 'cancel' to abort[/dim]\n")

    task = input("Task Name: ").strip()

    # Check for cancellation
    if task.lower() in ('cancel', 'c', 'q', 'quit'):
        console.print("[yellow]❌ Cancelled[/yellow]")
        return None

    comment = input("Comment: ")
    description = input("Description: ")
    priority = input("Priority (1-3): ") or "2"
    tag = input("Tag(s) [comma-separated, up to 3]: ")

    command = f'add "{task}" "{comment}" "{description}" {priority} "{tag}"'
    return command


def inline_edit_task(console, task):
    console.print("\n[bold yellow]Edit Task[/bold yellow]")
    console.print(f"ID: {task.id}")
    console.print("[dim]Type 'cancel' to abort, or press Enter to keep current values[/dim]\n")

    task_name = input(f"Task Name [{task.name}]: ").strip()

    # Check for cancellation
    if task_name.lower() in ('cancel', 'c', 'q', 'quit'):
        console.print("[yellow]❌ Cancelled[/yellow]")
        return None

    # Use current value if empty
    task_name = task_name or task.name

    comment = input(f"Comment [{task.comment}]: ") or task.comment
    description = input(f"Description [{task.description}]: ") or task.description
    priority = input(f"Priority [{task.priority}]: ") or str(task.priority)

    # Show current tags comma-separated
    current_tags = task.get_tags_display()
    tag = input(f"Tag(s) [{current_tags}]: ") or current_tags

    command = (
        f'edit {task.id} "{task_name}" "{comment}" "{description}" {priority} "{tag}"'
    )
    return command


def create_simple_prompt() -> HTML:
    """
    Create simple prompt line (status info is shown separately)
    Uses ASCII fallback when Unicode is not supported to prevent invisible characters
    """
    # Use Unicode or ASCII based on encoding support
    if USE_UNICODE:
        # Unicode prompt with special characters
        prompt_text = '<violet>❯</violet> <dim>Type / for commands</dim> <violet>›</violet> '
    else:
        # ASCII fallback for Windows CP1252 encoding
        prompt_text = '<violet>></violet> <dim>Type / for commands</dim> <violet>></violet> '
    return HTML(prompt_text)




def main():
    console = Console()
    state = AppState()

    # Load tasks from file
    state.load_from_file("tasks.json", console)
    console.clear()
    render_dashboard(console, state)

    # Create command completer with current state
    completer = create_command_completer(state)

    # Setup history file
    history_file = os.path.join(os.path.expanduser("~"), ".todo_cli_history")
    history = FileHistory(history_file)

    # Create custom style for completion menu
    # Makes background transparent and improves visual alignment
    completion_style = Style.from_dict({
        'completion-menu': 'bg:default',  # Transparent background
        'completion-menu.completion': 'bg:default',  # Transparent item background
        'completion-menu.completion.current': 'bg:#444444 #ffffff',  # Highlight current selection
        'completion-menu.meta.current': 'bg:#444444 #ffffff',  # Highlight meta text
        'completion-menu.multi-column-meta': 'bg:default',  # Transparent meta column
    })

    # Create custom key bindings
    kb = KeyBindings()

    @kb.add('escape')
    def clear_input(event):
        """Clear the input buffer when ESC is pressed"""
        event.current_buffer.reset()

    # Create prompt session with completer
    # Wrap completer in ThreadedCompleter for better performance
    threaded_completer = ThreadedCompleter(completer)

    session = PromptSession(
        completer=threaded_completer,
        complete_while_typing=True,  # Show completions as user types
        history=history,
        enable_history_search=False,  # CRITICAL: Must be False to avoid conflict with complete_while_typing
        mouse_support=True,  # Enable mouse for menu navigation
        reserve_space_for_menu=12,  # Reserve space for completion menu (increased for 23 commands)
        complete_style=CompleteStyle.MULTI_COLUMN,  # Multi-column layout for better display
        style=completion_style,  # Apply transparent background style
        key_bindings=kb  # Add ESC key binding to clear input
    )

    while True:
        try:
            # Show simple prompt (info is shown under table by renderer)
            prompt_html = create_simple_prompt()
            user_input = session.prompt(prompt_html).strip()

            # Handle empty input
            if not user_input:
                console.clear()
                render_dashboard(console, state)
                continue

            # Clear screen command - truly clear everything
            if user_input.lower() in ("cls", "clear", "c"):
                state.messages = []  # Clear all messages/output
                console.clear()      # Clear terminal
                render_dashboard(console, state)
                continue

            # Insights command (local AI suggestions)
            if user_input.lower() == "insights":
                console.clear()
                render_dashboard(console, state)
                insights = LocalSuggestions.get_insights_summary(state)
                console.print(Panel(insights, title="[bold cyan]📊 Task Insights[/bold cyan]", border_style="cyan"))
                continue

            # Suggest command (quick suggestions)
            if user_input.lower() == "suggest":
                suggestions = LocalSuggestions.get_smart_suggestions(state)
                console.print("\n[bold cyan]💡 Smart Suggestions:[/bold cyan]\n")
                for suggestion in suggestions:
                    console.print(f"  {suggestion}")
                    console.print()  # Add blank line after each suggestion for better readability
                continue

            # Tags with autocomplete
            if user_input.lower() == "tags":
                tags = get_available_tags(state)
                if tags:
                    console.print("\n[bold cyan]🏷️ Available Tags:[/bold cyan]")
                    for tag in tags:
                        tag_tasks = [t for t in state.tasks if t.tag == tag]
                        done = sum(1 for t in tag_tasks if t.done)
                        total = len(tag_tasks)
                        console.print(f"  • {tag}: {done}/{total} completed")
                else:
                    console.print("[yellow]No tags found[/yellow]")
                console.print()
                continue

            # Exit command (including 'x' shortcut)
            if user_input.lower() in ("exit", "quit", "x"):
                state.save_to_file("tasks.json", console)
                console.print("\n[yellow]Exiting...[/yellow]")
                break

            # Edit command with questionary form (or fallback to inline)
            if user_input.startswith("edit "):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    task_id = int(parts[1])
                    task = next((t for t in state.tasks if t.id == task_id), None)

                    if task:
                        if USE_QUESTIONARY_FORMS:
                            try:
                                # Use questionary interactive form
                                result = questionary_edit_task(task, state)

                                if result:
                                    # Update task using result from form
                                    task.name = result['name']
                                    task.comment = result.get('comment', '')
                                    task.description = result.get('description', '')
                                    task.priority = result.get('priority', 2)

                                    # Handle tags
                                    if 'tag' in result:
                                        tag_str = result['tag']
                                        if ',' in tag_str:
                                            tag_list = [t.strip().lower() for t in tag_str.split(',') if t.strip()]
                                            tag_list = tag_list[:3]
                                        else:
                                            tag_list = [tag_str.strip().lower()] if tag_str.strip() else []

                                        task.tag = tag_list[0] if tag_list else ""
                                        task.tags = tag_list

                                    console.clear()
                                    render_dashboard(console, state)
                                    show_success(f"Task #{task_id} updated successfully!", console)
                                else:
                                    # User cancelled (Ctrl+C or ESC)
                                    console.clear()
                                    render_dashboard(console, state)
                                    console.print("[yellow]Cancelled[/yellow]")
                            except Exception as e:
                                # Fallback to inline form if questionary fails
                                console.print(f"[yellow]Questionary form error: {e}. Using inline form...[/yellow]")
                                filled_input = inline_edit_task(console, task)
                                if filled_input is None:
                                    console.clear()
                                    render_dashboard(console, state)
                                    continue
                                handle_command(filled_input, state, console)
                                console.clear()
                                render_dashboard(console, state)
                        else:
                            # Use inline form (questionary disabled)
                            filled_input = inline_edit_task(console, task)
                            if filled_input is None:
                                console.clear()
                                render_dashboard(console, state)
                                continue
                            handle_command(filled_input, state, console)
                            console.clear()
                            render_dashboard(console, state)
                        continue
                    else:
                        console.print(f"[red]Task with ID {task_id} not found.[/red]")
                        continue

            # Add command with questionary form (or fallback to inline)
            if user_input.strip() == "add":
                if USE_QUESTIONARY_FORMS:
                    try:
                        # Use questionary interactive form
                        result = questionary_add_task(state)

                        if result:
                            # Add task using result from form
                            state.add_task(
                                name=result['name'],
                                comment=result.get('comment', ''),
                                description=result.get('description', ''),
                                priority=result.get('priority', 2),
                                tag=result.get('tag', '')
                            )
                            console.clear()
                            render_dashboard(console, state)
                            show_success(f"Task '{result['name']}' added successfully!", console)
                        else:
                            # User cancelled (Ctrl+C or ESC)
                            console.clear()
                            render_dashboard(console, state)
                            console.print("[yellow]Cancelled[/yellow]")
                    except Exception as e:
                        # Fallback to inline form if questionary fails
                        console.print(f"[yellow]Questionary form error: {e}. Using inline form...[/yellow]")
                        filled_input = inline_add_task(console)
                        if filled_input is None:
                            console.clear()
                            render_dashboard(console, state)
                            continue
                        handle_command(filled_input, state, console)
                        console.clear()
                        render_dashboard(console, state)
                else:
                    # Use inline form (questionary disabled)
                    filled_input = inline_add_task(console)
                    if filled_input is None:
                        console.clear()
                        render_dashboard(console, state)
                        continue
                    handle_command(filled_input, state, console)
                    console.clear()
                    render_dashboard(console, state)
                continue

            # Handle all other commands
            handle_command(user_input, state, console)
            console.clear()
            render_dashboard(console, state)

        except (KeyboardInterrupt, EOFError):
            state.save_to_file("tasks.json", console)
            console.print("\n[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    main()
