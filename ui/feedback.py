"""
Visual Feedback System
Success panels, error panels, progress indicators, and confirmation dialogs
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import yes_no_dialog
import time
from config import ui
from utils.emoji import emoji


class SuccessPanel:
    """
    Display a success message in a green panel.
    Auto-dismisses after specified duration.
    """

    def __init__(
        self,
        message: str,
        duration: float = None,
        console: Optional[Console] = None
    ):
        self.message = message
        self.duration = duration if duration is not None else ui.SUCCESS_PANEL_DURATION
        self.console = console or Console()

    def show(self):
        """Display the success panel"""
        # Icon selection based on Unicode support
        icon = emoji("✓", "OK")

        # Create success text
        success_text = Text()
        success_text.append(f"{icon} {self.message}", style="bold green")

        # Create panel
        panel = Panel(
            success_text,
            border_style="green",
            padding=(0, 1)
        )

        # Display panel
        self.console.print(panel)

        # Auto-dismiss after duration
        if self.duration > 0:
            time.sleep(self.duration)

    @staticmethod
    def show_message(
        message: str,
        duration: float = 2.0,
        console: Optional[Console] = None
    ):
        """Convenience static method to show success message"""
        panel = SuccessPanel(message, duration, console)
        panel.show()


class ErrorPanel:
    """
    Display an error message in a red panel with details.
    """

    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        console: Optional[Console] = None
    ):
        self.message = message
        self.details = details
        self.console = console or Console()

    def show(self):
        """Display the error panel"""
        # Icon selection based on Unicode support
        icon = emoji("✗", "ERROR")

        # Create error text
        error_text = Text()
        error_text.append(f"{icon} {self.message}", style="bold red")

        # Add details if provided
        if self.details:
            error_text.append("\n\n", style="dim")
            error_text.append(self.details, style="dim red")

        # Create panel
        panel = Panel(
            error_text,
            border_style="red",
            padding=(0, 1)
        )

        # Display panel
        self.console.print(panel)

    @staticmethod
    def show_message(
        message: str,
        details: Optional[str] = None,
        console: Optional[Console] = None
    ):
        """Convenience static method to show error message"""
        panel = ErrorPanel(message, details, console)
        panel.show()


class InfoPanel:
    """
    Display an informational message in a blue panel.
    """

    def __init__(
        self,
        message: str,
        console: Optional[Console] = None
    ):
        self.message = message
        self.console = console or Console()

    def show(self):
        """Display the info panel"""
        # Icon selection based on Unicode support
        icon = emoji("ℹ", "INFO")

        # Create info text
        info_text = Text()
        info_text.append(f"{icon} {self.message}", style="bold cyan")

        # Create panel
        panel = Panel(
            info_text,
            border_style="cyan",
            padding=(0, 1)
        )

        # Display panel
        self.console.print(panel)

    @staticmethod
    def show_message(
        message: str,
        console: Optional[Console] = None
    ):
        """Convenience static method to show info message"""
        panel = InfoPanel(message, console)
        panel.show()


class ProgressSpinner:
    """
    Display an animated progress spinner for async operations.
    """

    def __init__(
        self,
        message: str = "Processing...",
        spinner_type: str = "dots",
        console: Optional[Console] = None
    ):
        self.message = message
        self.spinner_type = spinner_type
        self.console = console or Console()
        self.live: Optional[Live] = None

    def __enter__(self):
        """Start the spinner (context manager)"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the spinner (context manager)"""
        self.stop()

    def start(self):
        """Start displaying the spinner"""
        spinner = Spinner(self.spinner_type, text=self.message)
        self.live = Live(spinner, console=self.console, refresh_per_second=10)
        self.live.start()

    def stop(self, final_message: Optional[str] = None):
        """Stop displaying the spinner"""
        if self.live:
            self.live.stop()

        # Show final message if provided
        if final_message:
            self.console.print(final_message)

    def update(self, message: str):
        """Update the spinner message"""
        if self.live:
            spinner = Spinner(self.spinner_type, text=message)
            self.live.update(spinner)


class ConfirmDialog:
    """
    Display a Yes/No confirmation dialog.
    Returns True if user confirms, False otherwise.
    """

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        default: bool = False
    ):
        self.message = message
        self.title = title
        self.default = default

    def show(self) -> bool:
        """
        Show the confirmation dialog and return user's choice.
        Returns True for Yes, False for No.
        """
        # Simple prompt-based confirmation (no GUI dialog)
        # Format: "Are you sure? (y/N): "
        default_indicator = "Y/n" if self.default else "y/N"
        prompt_text = f"\n{self.title}: {self.message} ({default_indicator}): "

        try:
            response = input(prompt_text).strip().lower()

            if not response:
                return self.default

            return response in ['y', 'yes']

        except (KeyboardInterrupt, EOFError):
            return False

    @staticmethod
    def confirm(
        message: str,
        title: str = "Confirm",
        default: bool = False
    ) -> bool:
        """Convenience static method to show confirmation dialog"""
        dialog = ConfirmDialog(message, title, default)
        return dialog.show()


class OperationSummary:
    """
    Display a summary of bulk operations.
    Example: "5 tasks marked as done, 2 failed"
    """

    def __init__(
        self,
        operation: str,
        success_count: int,
        failure_count: int = 0,
        console: Optional[Console] = None
    ):
        self.operation = operation
        self.success_count = success_count
        self.failure_count = failure_count
        self.console = console or Console()

    def show(self):
        """Display the operation summary"""
        # Build summary message
        summary_parts = []

        if self.success_count > 0:
            summary_parts.append(
                emoji(f"✓ {self.success_count} {self.operation}", f"OK: {self.success_count} {self.operation}")
            )

        if self.failure_count > 0:
            summary_parts.append(
                emoji(f"✗ {self.failure_count} failed", f"ERROR: {self.failure_count} failed")
            )

        summary_text = ", ".join(summary_parts)

        # Choose panel style based on success/failure
        if self.failure_count == 0:
            # All success - green panel
            SuccessPanel.show_message(summary_text, duration=2.0, console=self.console)
        elif self.success_count == 0:
            # All failed - red panel
            ErrorPanel.show_message(summary_text, console=self.console)
        else:
            # Mixed - yellow/info panel
            InfoPanel.show_message(summary_text, console=self.console)

    @staticmethod
    def show_summary(
        operation: str,
        success_count: int,
        failure_count: int = 0,
        console: Optional[Console] = None
    ):
        """Convenience static method to show operation summary"""
        summary = OperationSummary(operation, success_count, failure_count, console)
        summary.show()


class FadeTransition:
    """
    Smooth fade-in/fade-out animation for messages.
    Note: Terminal animations are limited, this is a simple delay-based implementation.
    """

    @staticmethod
    def fade_in(
        content: str,
        duration: float = 0.5,
        console: Optional[Console] = None
    ):
        """
        Fade in content (simple implementation with delay).
        In terminals, true fade is not possible, so this just adds a smooth delay.
        """
        console = console or Console()

        # Simple fade: just print with a slight delay
        # Real fade would require more complex terminal control
        time.sleep(duration / 2)
        console.print(content)
        time.sleep(duration / 2)

    @staticmethod
    def fade_out(
        duration: float = 0.5,
        console: Optional[Console] = None
    ):
        """
        Fade out (simple implementation with delay).
        In terminals, just adds a delay before clearing.
        """
        console = console or Console()
        time.sleep(duration)
        # Optionally clear the last line (implementation depends on use case)


# Helper functions for common feedback patterns

def show_success(message: str, console: Optional[Console] = None):
    """Quick helper to show success message"""
    SuccessPanel.show_message(message, duration=2.0, console=console)


def show_error(message: str, details: Optional[str] = None, console: Optional[Console] = None):
    """Quick helper to show error message"""
    ErrorPanel.show_message(message, details, console=console)


def show_info(message: str, console: Optional[Console] = None):
    """Quick helper to show info message"""
    InfoPanel.show_message(message, console=console)


def confirm(message: str, default: bool = False) -> bool:
    """Quick helper to show confirmation dialog"""
    return ConfirmDialog.confirm(message, default=default)


def with_progress(message: str, operation, console: Optional[Console] = None):
    """
    Execute an operation with a progress spinner.

    Usage:
        result = with_progress("Saving tasks...", lambda: state.save_to_file("tasks.json"))
    """
    with ProgressSpinner(message, console=console) as spinner:
        result = operation()
        return result


# Example usage and testing
if __name__ == "__main__":
    console = Console()

    # Test success panel
    console.print("\n[bold]Testing Success Panel:[/bold]")
    show_success("Task added successfully!")

    # Test error panel
    console.print("\n[bold]Testing Error Panel:[/bold]")
    show_error("Failed to save task", details="File is read-only")

    # Test info panel
    console.print("\n[bold]Testing Info Panel:[/bold]")
    show_info("5 tasks found matching filter")

    # Test operation summary
    console.print("\n[bold]Testing Operation Summary:[/bold]")
    OperationSummary.show_summary("tasks marked as done", success_count=5, failure_count=2)

    # Test confirmation dialog
    console.print("\n[bold]Testing Confirmation Dialog:[/bold]")
    if confirm("Delete 10 tasks?", default=False):
        console.print("[green]User confirmed![/green]")
    else:
        console.print("[yellow]User cancelled.[/yellow]")

    # Test progress spinner
    console.print("\n[bold]Testing Progress Spinner:[/bold]")
    with ProgressSpinner("Processing tasks...", console=console) as spinner:
        time.sleep(2)  # Simulate work
        spinner.update("Almost done...")
        time.sleep(1)
    console.print("[green]Done![/green]")
