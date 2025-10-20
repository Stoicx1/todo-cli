"""
TUI Modal Form Framework
Centered overlay forms with keyboard navigation and validation
"""

from typing import Dict, Any, Optional, List, Tuple, Callable
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, Dimension
from prompt_toolkit.layout.containers import Container, FloatContainer, Float
from prompt_toolkit.widgets import Frame, Box
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
import sys

# Unicode/emoji support detection for Windows compatibility
USE_UNICODE = (
    sys.stdout.encoding and
    sys.stdout.encoding.lower() in ('utf-8', 'utf8')
)


class ModalField:
    """
    Base class for modal form fields.
    Subclasses should implement rendering and validation logic.
    """

    def __init__(
        self,
        name: str,
        label: str,
        required: bool = False,
        validator: Optional[Callable[[Any], Tuple[bool, str]]] = None
    ):
        self.name = name
        self.label = label
        self.required = required
        self.validator = validator
        self.value: Any = None
        self.error: Optional[str] = None
        self.focused: bool = False

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate field value.
        Returns (is_valid, error_message)
        """
        # Check required
        if self.required and not self.value:
            return False, f"{self.label} is required"

        # Run custom validator if provided
        if self.validator and self.value:
            is_valid, error = self.validator(self.value)
            if not is_valid:
                return False, error

        return True, None

    def render(self) -> Container:
        """
        Render the field as a prompt_toolkit Container.
        Subclasses should override this.
        """
        raise NotImplementedError("Subclasses must implement render()")

    def handle_input(self, char: str) -> bool:
        """
        Handle character input for this field.
        Returns True if handled, False otherwise.
        Subclasses should override this.
        """
        return False

    def get_value(self) -> Any:
        """Get the current field value"""
        return self.value

    def set_value(self, value: Any):
        """Set the field value"""
        self.value = value
        self.error = None


class ModalFormController:
    """
    Controller for managing modal form state, navigation, and validation.
    """

    def __init__(self, title: str, width: int = 60, fields: List[ModalField] = None):
        self.title = title
        self.width = width
        self.fields: List[ModalField] = fields or []
        self.current_field_index: int = 0
        self.result: Optional[Dict[str, Any]] = None
        self.cancelled: bool = False

    def add_field(self, field: ModalField):
        """Add a field to the form"""
        self.fields.append(field)

    def get_current_field(self) -> Optional[ModalField]:
        """Get the currently focused field"""
        if 0 <= self.current_field_index < len(self.fields):
            return self.fields[self.current_field_index]
        return None

    def next_field(self):
        """Move to next field (Tab)"""
        if self.current_field_index < len(self.fields) - 1:
            if self.get_current_field():
                self.get_current_field().focused = False
            self.current_field_index += 1
            if self.get_current_field():
                self.get_current_field().focused = True

    def prev_field(self):
        """Move to previous field (Shift-Tab)"""
        if self.current_field_index > 0:
            if self.get_current_field():
                self.get_current_field().focused = False
            self.current_field_index -= 1
            if self.get_current_field():
                self.get_current_field().focused = True

    def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Validate all fields.
        Returns (all_valid, list_of_errors)
        """
        errors = []
        all_valid = True

        for field in self.fields:
            is_valid, error = field.validate()
            if not is_valid:
                all_valid = False
                field.error = error
                errors.append(error)
            else:
                field.error = None

        return all_valid, errors

    def submit(self) -> bool:
        """
        Attempt to submit the form.
        Returns True if validation passes, False otherwise.
        """
        all_valid, errors = self.validate_all()

        if all_valid:
            # Collect field values
            self.result = {field.name: field.get_value() for field in self.fields}
            return True

        return False

    def cancel(self):
        """Cancel the form"""
        self.cancelled = True
        self.result = None


class ModalForm:
    """
    Base class for TUI modal forms.
    Displays a centered overlay box with form fields.
    """

    def __init__(
        self,
        title: str,
        width: int = 60,
        height: int = 20,
        console: Optional[Console] = None
    ):
        self.title = title
        self.width = width
        self.height = height
        self.console = console or Console()
        self.controller = ModalFormController(title, width)
        self.app: Optional[Application] = None

    def add_field(self, field: ModalField):
        """Add a field to the form"""
        self.controller.add_field(field)

    def create_key_bindings(self) -> KeyBindings:
        """Create keyboard bindings for form navigation"""
        kb = KeyBindings()

        @kb.add('tab')
        def _(event):
            """Move to next field"""
            self.controller.next_field()

        @kb.add('s-tab')  # Shift-Tab
        def _(event):
            """Move to previous field"""
            self.controller.prev_field()

        @kb.add('escape')
        def _(event):
            """Cancel form"""
            self.controller.cancel()
            event.app.exit()

        @kb.add('enter')
        def _(event):
            """Submit form (if validation passes)"""
            if self.controller.submit():
                event.app.exit()

        # Allow character input to current field
        @kb.add('<any>')
        def _(event):
            """Handle character input for current field"""
            current_field = self.controller.get_current_field()
            if current_field:
                current_field.handle_input(event.data)

        return kb

    def create_layout(self) -> Layout:
        """
        Create the modal layout.
        Returns a prompt_toolkit Layout with centered modal.
        """
        # Title bar
        title_text = HTML(f'<b><ansibrightcyan>{self.title}</ansibrightcyan></b>')
        title_window = Window(
            FormattedTextControl(title_text),
            height=1,
            align="center"
        )

        # Field containers (will be populated by subclasses)
        field_windows = []
        for field in self.controller.fields:
            field_windows.append(field.render())

        # Help text at bottom
        help_text_str = "Tab: Next  |  Shift-Tab: Prev  |  ESC: Cancel  |  Enter: Save"
        help_text = HTML(f'<ansigray>{help_text_str}</ansigray>')
        help_window = Window(
            FormattedTextControl(help_text),
            height=1,
            align="center"
        )

        # Vertical stack: title + fields + help
        content = HSplit([
            title_window,
            Window(height=1),  # Spacing
            *field_windows,
            Window(height=1),  # Spacing
            help_window
        ])

        # Frame around content
        frame = Frame(content, style="class:modal-frame")

        # Float container for centering
        float_container = FloatContainer(
            content=Window(),  # Background (dimmed)
            floats=[
                Float(
                    content=frame,
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                )
            ]
        )

        return Layout(float_container)

    def show(self) -> Optional[Dict[str, Any]]:
        """
        Show the modal and wait for user input.
        Returns field values dict if submitted, None if cancelled.
        """
        # Set first field as focused
        if self.controller.fields:
            self.controller.fields[0].focused = True

        # Create application
        layout = self.create_layout()
        key_bindings = self.create_key_bindings()

        self.app = Application(
            layout=layout,
            key_bindings=key_bindings,
            full_screen=True,
            mouse_support=True
        )

        # Run application (blocks until exit)
        try:
            self.app.run()
        except KeyboardInterrupt:
            self.controller.cancel()

        # Return result (None if cancelled)
        if self.controller.cancelled:
            return None
        return self.controller.result


def test_modal():
    """Test function to verify modal framework works"""
    from ui.form_fields import TextField  # Will be implemented in Phase 2

    modal = ModalForm("Test Modal", width=50, height=15)

    # Add test field (placeholder - actual TextField will be in Phase 2)
    # modal.add_field(TextField("test", "Test Field", required=True))

    result = modal.show()

    if result:
        print(f"Form submitted with values: {result}")
    else:
        print("Form cancelled")


if __name__ == "__main__":
    # Test the modal framework
    test_modal()
