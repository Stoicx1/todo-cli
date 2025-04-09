from prompt_toolkit import PromptSession
from rich.console import Console
from core.commands import handle_command
from core.state import AppState
from ui.renderer import render_dashboard


def main():
    console = Console()
    session = PromptSession()
    state = AppState()

    # Load tasks from file (if available)
    state.load_from_file("tasks.json", console)
    console.clear()
    render_dashboard(console, state)

    while True:
        try:
            user_input = session.prompt("[>]: ")
            if user_input.strip().lower() in ("exit", "quit"):
                # Save tasks before exiting
                state.save_to_file("tasks.json", console)
                console.print("\n[yellow]Exiting...[/yellow]")
                break

            handle_command(user_input, state, console)
            render_dashboard(console, state)

        except (KeyboardInterrupt, EOFError):
            # Save tasks on exit
            state.save_to_file("tasks.json", console)  # Pass console here
            console.print("\n[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    main()
