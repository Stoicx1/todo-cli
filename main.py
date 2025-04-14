from prompt_toolkit import PromptSession
from rich.console import Console
from core.commands import handle_command
from core.state import AppState
from ui.renderer import render_dashboard


def inline_add_task(console):
    console.print("\n[bold green]Add New Task[/bold green]")
    task = input("Task Name: ")
    comment = input("Comment: ")
    description = input("Description: ")
    priority = input("Priority (1-3): ") or "2"
    tag = input("Tag: ")

    command = f'add "{task}" "{comment}" "{description}" {priority} "{tag}"'
    return command


def inline_edit_task(console, task):
    console.print("\n[bold yellow]Edit Task[/bold yellow]")
    console.print(f"ID: {task.id}")
    task_name = input(f"Task Name [{task.name}]: ") or task.name
    comment = input(f"Comment [{task.comment}]: ") or task.comment
    description = input(f"Description [{task.description}]: ") or task.description
    priority = input(f"Priority [{task.priority}]: ") or str(task.priority)
    tag = input(f"Tag [{task.tag}]: ") or task.tag

    command = (
        f'edit {task.id} "{task_name}" "{comment}" "{description}" {priority} "{tag}"'
    )
    return command


def main():
    console = Console()
    session = PromptSession()
    state = AppState()

    state.load_from_file("tasks.json", console)
    console.clear()
    render_dashboard(console, state)

    while True:
        try:
            user_input = session.prompt("[>]: ").strip()

            if user_input.lower() in ("exit", "quit"):
                state.save_to_file("tasks.json", console)
                console.print("\n[yellow]Exiting...[/yellow]")
                break

            if user_input.startswith("edit "):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    task_id = int(parts[1])
                    task = next((t for t in state.tasks if t.id == task_id), None)

                    if task:
                        filled_input = inline_edit_task(console, task)
                        handle_command(filled_input, state, console)
                        render_dashboard(console, state)
                        continue
                    else:
                        console.print(f"[red]Task with ID {task_id} not found.[/red]")
                        continue

            if user_input.strip() == "add":
                filled_input = inline_add_task(console)
                handle_command(filled_input, state, console)
                render_dashboard(console, state)
                continue

            handle_command(user_input, state, console)
            render_dashboard(console, state)

        except (KeyboardInterrupt, EOFError):
            state.save_to_file("tasks.json", console)
            console.print("\n[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    main()
