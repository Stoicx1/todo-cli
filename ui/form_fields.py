"""
Form Field Components
Reusable form fields with validation and rendering logic
"""

from typing import Any, Optional, Tuple, Callable, List
from prompt_toolkit.layout import Window, FormattedTextControl, HSplit, VSplit, Dimension
from prompt_toolkit.layout.containers import Container
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea
from ui.modal_form import ModalField
import sys

# Unicode/emoji support detection for Windows compatibility
USE_UNICODE = (
    sys.stdout.encoding and
    sys.stdout.encoding.lower() in ('utf-8', 'utf8')
)


class TextField(ModalField):
    """
    Single-line text input field with character counter and max length.
    """

    def __init__(
        self,
        name: str,
        label: str,
        required: bool = False,
        max_length: int = 100,
        placeholder: str = "",
        default_value: str = "",
        validator: Optional[Callable[[str], Tuple[bool, str]]] = None
    ):
        super().__init__(name, label, required, validator)
        self.max_length = max_length
        self.placeholder = placeholder
        self.value = default_value
        self.buffer = Buffer(
            document=None,
            multiline=False,
            on_text_changed=self._on_text_changed
        )
        if default_value:
            self.buffer.text = default_value

    def _on_text_changed(self, buffer):
        """Update value when buffer changes"""
        text = buffer.text
        # Enforce max length
        if len(text) > self.max_length:
            buffer.text = text[:self.max_length]
        self.value = buffer.text

    def render(self) -> Container:
        """Render the text field"""
        # Label with required indicator
        required_mark = "*" if self.required else ""
        label_text = f"{self.label} {required_mark}"

        # Character counter
        current_length = len(self.value) if self.value else 0
        counter_text = f"{current_length}/{self.max_length}"

        # Focus indicator
        if self.focused:
            label_html = HTML(f'<b><ansibrightcyan>{label_text}</ansibrightcyan></b>')
            counter_html = HTML(f'<ansicyan>{counter_text}</ansicyan>')
        else:
            label_html = HTML(f'<ansigray>{label_text}</ansigray>')
            counter_html = HTML(f'<ansigray>{counter_text}</ansigray>')

        # Error message if validation failed
        error_content = []
        if self.error:
            error_html = HTML(f'<ansired>  ✗ {self.error}</ansired>') if USE_UNICODE else HTML(f'<ansired>  ! {self.error}</ansired>')
            error_content.append(Window(FormattedTextControl(error_html), height=1))

        # Input box (simplified - using Window instead of TextArea for now)
        input_value = self.value if self.value else self.placeholder
        if self.focused:
            input_html = HTML(f'<ansiwhite>[{input_value}_]</ansiwhite>')
        else:
            input_html = HTML(f'<ansigray>[{input_value}]</ansigray>')

        return HSplit([
            VSplit([
                Window(FormattedTextControl(label_html), width=Dimension(min=20)),
                Window(FormattedTextControl(counter_html), width=Dimension(min=10), align="right")
            ], height=1),
            Window(FormattedTextControl(input_html), height=1),
            *error_content
        ])

    def handle_input(self, char: str) -> bool:
        """Handle character input"""
        if not self.focused:
            return False

        # Handle backspace
        if char == '\x7f' or char == '\x08':  # Backspace
            if self.value:
                self.value = self.value[:-1]
            return True

        # Handle printable characters
        if char.isprintable() and len(self.value) < self.max_length:
            self.value = (self.value or "") + char
            return True

        return False


class TextAreaField(ModalField):
    """
    Multi-line text input field for descriptions.
    """

    def __init__(
        self,
        name: str,
        label: str,
        required: bool = False,
        max_length: int = 500,
        height: int = 3,
        default_value: str = "",
        validator: Optional[Callable[[str], Tuple[bool, str]]] = None
    ):
        super().__init__(name, label, required, validator)
        self.max_length = max_length
        self.height = height
        self.value = default_value

    def render(self) -> Container:
        """Render the text area field"""
        # Label with required indicator
        required_mark = "*" if self.required else ""
        label_text = f"{self.label} {required_mark}"

        # Character counter
        current_length = len(self.value) if self.value else 0
        counter_text = f"{current_length}/{self.max_length}"

        # Focus indicator
        if self.focused:
            label_html = HTML(f'<b><ansibrightcyan>{label_text}</ansibrightcyan></b>')
            counter_html = HTML(f'<ansicyan>{counter_text}</ansicyan>')
        else:
            label_html = HTML(f'<ansigray>{label_text}</ansigray>')
            counter_html = HTML(f'<ansigray>{counter_text}</ansigray>')

        # Error message if validation failed
        error_content = []
        if self.error:
            error_html = HTML(f'<ansired>  ✗ {self.error}</ansired>') if USE_UNICODE else HTML(f'<ansired>  ! {self.error}</ansired>')
            error_content.append(Window(FormattedTextControl(error_html), height=1))

        # Display value (simplified rendering)
        display_lines = []
        if self.value:
            # Split into lines and truncate if needed
            lines = self.value.split('\n')[:self.height]
            for line in lines:
                if len(line) > 50:  # Truncate long lines
                    line = line[:47] + "..."
                display_lines.append(line)

        # Pad with empty lines
        while len(display_lines) < self.height:
            display_lines.append("")

        if self.focused:
            text_windows = [
                Window(FormattedTextControl(HTML(f'<ansiwhite>[{line}_]</ansiwhite>')), height=1)
                for line in display_lines
            ]
        else:
            text_windows = [
                Window(FormattedTextControl(HTML(f'<ansigray>[{line}]</ansigray>')), height=1)
                for line in display_lines
            ]

        return HSplit([
            VSplit([
                Window(FormattedTextControl(label_html), width=Dimension(min=20)),
                Window(FormattedTextControl(counter_html), width=Dimension(min=10), align="right")
            ], height=1),
            *text_windows,
            *error_content
        ])

    def handle_input(self, char: str) -> bool:
        """Handle character input"""
        if not self.focused:
            return False

        # Handle backspace
        if char == '\x7f' or char == '\x08':
            if self.value:
                self.value = self.value[:-1]
            return True

        # Handle enter (newline)
        if char == '\r' or char == '\n':
            if len(self.value) < self.max_length:
                self.value = (self.value or "") + '\n'
            return True

        # Handle printable characters
        if char.isprintable() and len(self.value) < self.max_length:
            self.value = (self.value or "") + char
            return True

        return False


class PriorityField(ModalField):
    """
    Visual priority selector field (High/Med/Low).
    Responds to arrow keys and number keys (1, 2, 3).
    """

    PRIORITY_LABELS = {
        1: "High",
        2: "Med",
        3: "Low"
    }

    def __init__(
        self,
        name: str,
        label: str,
        default_value: int = 2,
        validator: Optional[Callable[[int], Tuple[bool, str]]] = None
    ):
        super().__init__(name, label, False, validator)
        self.value = default_value

    def render(self) -> Container:
        """Render the priority selector"""
        label_text = self.label

        # Focus indicator
        if self.focused:
            label_html = HTML(f'<b><ansibrightcyan>{label_text}</ansibrightcyan></b>')
        else:
            label_html = HTML(f'<ansigray>{label_text}</ansigray>')

        # Priority options with visual indicators
        options = []
        for priority_val in [1, 2, 3]:
            label = self.PRIORITY_LABELS[priority_val]
            if priority_val == self.value:
                # Selected (filled circle)
                if USE_UNICODE:
                    indicator = "●"
                else:
                    indicator = "*"
                if self.focused:
                    option_html = HTML(f'<ansibrightcyan>{indicator} {label}</ansibrightcyan>')
                else:
                    option_html = HTML(f'<ansicyan>{indicator} {label}</ansicyan>')
            else:
                # Not selected (empty circle)
                if USE_UNICODE:
                    indicator = "○"
                else:
                    indicator = "o"
                option_html = HTML(f'<ansigray>{indicator} {label}</ansigray>')

            options.append(Window(FormattedTextControl(option_html), width=Dimension(min=10)))

        # Error message if validation failed
        error_content = []
        if self.error:
            error_html = HTML(f'<ansired>  ✗ {self.error}</ansired>') if USE_UNICODE else HTML(f'<ansired>  ! {self.error}</ansired>')
            error_content.append(Window(FormattedTextControl(error_html), height=1))

        return HSplit([
            Window(FormattedTextControl(label_html), height=1),
            VSplit(options, height=1),
            *error_content
        ])

    def handle_input(self, char: str) -> bool:
        """Handle character input (arrow keys, numbers 1-3)"""
        if not self.focused:
            return False

        # Handle number keys (1, 2, 3)
        if char in ['1', '2', '3']:
            self.value = int(char)
            return True

        # Handle left/right arrow keys (would need special key handling)
        # For now, just handle number input

        return False


class TagField(ModalField):
    """
    Tag input field with autocomplete from existing tags.
    Supports comma-separated input, max 3 tags.
    """

    def __init__(
        self,
        name: str,
        label: str,
        existing_tags: List[str] = None,
        max_tags: int = 3,
        default_value: str = "",
        validator: Optional[Callable[[str], Tuple[bool, str]]] = None
    ):
        super().__init__(name, label, False, validator)
        self.existing_tags = existing_tags or []
        self.max_tags = max_tags
        self.value = default_value

    def get_tag_list(self) -> List[str]:
        """Parse current value into list of tags"""
        if not self.value:
            return []
        return [tag.strip().lower() for tag in self.value.split(',') if tag.strip()]

    def get_suggestions(self) -> List[str]:
        """Get autocomplete suggestions based on current input"""
        current_tags = self.get_tag_list()
        if len(current_tags) >= self.max_tags:
            return []

        # Get last partial tag being typed
        last_part = self.value.split(',')[-1].strip().lower()

        # Filter existing tags
        suggestions = [
            tag for tag in self.existing_tags
            if tag not in current_tags and last_part in tag
        ]

        return suggestions[:5]  # Limit to 5 suggestions

    def render(self) -> Container:
        """Render the tag field"""
        # Label with tag count
        current_tags = self.get_tag_list()
        tag_count_text = f"{len(current_tags)}/{self.max_tags}"
        label_text = f"{self.label} ({tag_count_text})"

        # Focus indicator
        if self.focused:
            label_html = HTML(f'<b><ansibrightcyan>{label_text}</ansibrightcyan></b>')
        else:
            label_html = HTML(f'<ansigray>{label_text}</ansigray>')

        # Input display
        input_value = self.value if self.value else "comma-separated"
        if self.focused:
            input_html = HTML(f'<ansiwhite>[{input_value}_]</ansiwhite>')
        else:
            input_html = HTML(f'<ansigray>[{input_value}]</ansigray>')

        # Suggestions
        suggestions = self.get_suggestions()
        suggestion_content = []
        if self.focused and suggestions:
            if USE_UNICODE:
                suggestion_text = "↓ Suggestions: " + ", ".join(suggestions)
            else:
                suggestion_text = "  Suggestions: " + ", ".join(suggestions)
            suggestion_html = HTML(f'<ansigray>{suggestion_text}</ansigray>')
            suggestion_content.append(Window(FormattedTextControl(suggestion_html), height=1))

        # Current tags display
        tag_display_content = []
        if current_tags:
            if USE_UNICODE:
                tag_display_text = "  • " + "  • ".join(current_tags)
            else:
                tag_display_text = "  - " + "  - ".join(current_tags)
            tag_html = HTML(f'<ansicyan>{tag_display_text}</ansicyan>')
            tag_display_content.append(Window(FormattedTextControl(tag_html), height=1))

        # Error message if validation failed
        error_content = []
        if self.error:
            error_html = HTML(f'<ansired>  ✗ {self.error}</ansired>') if USE_UNICODE else HTML(f'<ansired>  ! {self.error}</ansired>')
            error_content.append(Window(FormattedTextControl(error_html), height=1))

        return HSplit([
            Window(FormattedTextControl(label_html), height=1),
            Window(FormattedTextControl(input_html), height=1),
            *suggestion_content,
            *tag_display_content,
            *error_content
        ])

    def handle_input(self, char: str) -> bool:
        """Handle character input"""
        if not self.focused:
            return False

        # Handle backspace
        if char == '\x7f' or char == '\x08':
            if self.value:
                self.value = self.value[:-1]
            return True

        # Handle comma (tag separator)
        if char == ',':
            current_tags = self.get_tag_list()
            if len(current_tags) < self.max_tags:
                self.value = (self.value or "") + char
            return True

        # Handle printable characters
        if char.isprintable():
            self.value = (self.value or "") + char
            return True

        return False

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate tag field"""
        # Check max tags
        current_tags = self.get_tag_list()
        if len(current_tags) > self.max_tags:
            return False, f"Maximum {self.max_tags} tags allowed"

        # Run parent validation
        return super().validate()

    def get_value(self) -> List[str]:
        """Get tag list as value"""
        return self.get_tag_list()


class CheckboxField(ModalField):
    """
    Boolean checkbox field (for future features).
    """

    def __init__(
        self,
        name: str,
        label: str,
        default_value: bool = False,
        validator: Optional[Callable[[bool], Tuple[bool, str]]] = None
    ):
        super().__init__(name, label, False, validator)
        self.value = default_value

    def render(self) -> Container:
        """Render the checkbox"""
        # Focus indicator
        if self.focused:
            label_html = HTML(f'<b><ansibrightcyan>{self.label}</ansibrightcyan></b>')
        else:
            label_html = HTML(f'<ansigray>{self.label}</ansigray>')

        # Checkbox indicator
        if self.value:
            if USE_UNICODE:
                checkbox = "[✓]"
            else:
                checkbox = "[X]"
            checkbox_html = HTML(f'<ansibrightgreen>{checkbox}</ansibrightgreen>')
        else:
            checkbox = "[ ]"
            checkbox_html = HTML(f'<ansigray>{checkbox}</ansigray>')

        return HSplit([
            VSplit([
                Window(FormattedTextControl(checkbox_html), width=Dimension(min=5)),
                Window(FormattedTextControl(label_html))
            ], height=1)
        ])

    def handle_input(self, char: str) -> bool:
        """Handle character input (spacebar toggles)"""
        if not self.focused:
            return False

        # Toggle on spacebar or Enter
        if char == ' ' or char == '\r' or char == '\n':
            self.value = not self.value
            return True

        return False


# Validation helper functions
def validate_not_empty(value: str) -> Tuple[bool, str]:
    """Validator: ensure string is not empty"""
    if not value or not value.strip():
        return False, "This field cannot be empty"
    return True, ""


def validate_priority(value: int) -> Tuple[bool, str]:
    """Validator: ensure priority is 1-3"""
    if value not in [1, 2, 3]:
        return False, "Priority must be 1 (High), 2 (Med), or 3 (Low)"
    return True, ""


def validate_max_length(max_len: int):
    """Validator factory: ensure string doesn't exceed max length"""
    def validator(value: str) -> Tuple[bool, str]:
        if len(value) > max_len:
            return False, f"Maximum {max_len} characters allowed"
        return True, ""
    return validator


def validate_tag_count(max_tags: int):
    """Validator factory: ensure tag count doesn't exceed max"""
    def validator(value: List[str]) -> Tuple[bool, str]:
        if len(value) > max_tags:
            return False, f"Maximum {max_tags} tags allowed"
        return True, ""
    return validator
