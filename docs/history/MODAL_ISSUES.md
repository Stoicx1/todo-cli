# Modal Forms - Known Issues & Fix Plan

**Status:** 🔴 NON-FUNCTIONAL (Temporarily Disabled)
**Date:** 2025-10-20
**Flag:** `USE_MODAL_FORMS = False` in main.py

---

## 🐛 Critical Issues Discovered

### Issue #1: Non-Interactive Fields
**Problem:** Form fields render as static HTML text, not editable input widgets.

**Code Location:** `ui/form_fields.py:81-86`
```python
# Current implementation (BROKEN):
input_html = HTML(f'<ansiwhite>[{input_value}_]</ansiwhite>')
return Window(FormattedTextControl(input_html), height=1)
```

**Why It's Broken:**
- `Window` with `FormattedTextControl` displays static text
- No actual `Buffer` or `TextArea` for input
- Users cannot type, edit, or backspace

**Expected Behavior:**
- Should use `prompt_toolkit.widgets.TextArea` with real Buffer
- Should accept keyboard input
- Should show cursor and allow editing

---

### Issue #2: Keyboard Navigation Doesn't Work
**Problem:** Tab/Shift-Tab registered but fields don't update visually.

**Code Location:** `ui/modal_form.py:194-224`
```python
@kb.add('tab')
def _(event):
    self.controller.next_field()  # Changes internal focus
    # BUT: UI doesn't re-render!
```

**Why It's Broken:**
- Focus changes internally but no `app.invalidate()` called
- Fields render once, never update
- No dynamic re-rendering on focus change

**Expected Behavior:**
- Tab should visually highlight next field
- Previous field should un-highlight
- UI should refresh immediately

---

### Issue #3: Manual Character Input Handler
**Problem:** `<any>` key binding tries to route all input to fields manually.

**Code Location:** `ui/modal_form.py:217-222`
```python
@kb.add('<any>')
def _(event):
    current_field.handle_input(event.data)  # Stores char
    # BUT: No re-render, no visual feedback!
```

**Why It's Broken:**
- Characters stored in field.value
- No cursor management
- No UI update after input
- User sees nothing happen

**Expected Behavior:**
- prompt_toolkit widgets handle input automatically
- Cursor moves after each character
- UI updates in real-time

---

### Issue #4: No Background Dimming
**Problem:** Modal doesn't have visible background or proper centering.

**Code Location:** `ui/modal_form.py:266-277`
```python
FloatContainer(
    content=Window(),  # Empty background!
    floats=[Float(content=frame, left=0, right=0, top=0, bottom=0)]  # Fills screen!
)
```

**Why It's Broken:**
- Background Window has no content or style
- Float positioning (0,0,0,0) makes it fill entire screen
- No centering calculation

**Expected Behavior:**
- Background should be dimmed (gray overlay)
- Modal should be centered (calculate position)
- Visible border around modal

---

## 🔍 Root Cause Analysis

The implementation is a **"fake" modal form**:
1. ✅ Displays form fields (static rendering)
2. ❌ Fields don't accept input (no interactive widgets)
3. ❌ Tab navigation doesn't work (no visual update)
4. ❌ No cursor, no editing, no backspace
5. ❌ No background, no proper centering

**Fundamental Mistake:**
Used `Window` with `FormattedTextControl` for form fields instead of interactive `TextArea` widgets.

---

## ✅ Correct Implementation Pattern

### TextField Should Be:
```python
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import HSplit

class TextField(ModalField):
    def __init__(self, name, label, ...):
        self.textarea = TextArea(
            text=default_value,
            multiline=False,
            max_length=max_length,
            scrollbar=False,
            focus_on_click=True
        )

    def render(self) -> Container:
        # Return the actual TextArea widget!
        return HSplit([
            Window(FormattedTextControl(label_html), height=1),
            self.textarea,  # <-- Interactive widget
            error_window if self.error else Window(height=0)
        ])

    def get_value(self) -> str:
        return self.textarea.text  # Get from widget
```

### PriorityField Should Be:
```python
from prompt_toolkit.widgets import RadioList

class PriorityField(ModalField):
    def __init__(self, name, label, default_value=2):
        self.radio_list = RadioList(
            values=[
                (1, "High"),
                (2, "Med"),
                (3, "Low")
            ],
            default=default_value
        )

    def render(self) -> Container:
        return HSplit([
            Window(FormattedTextControl(label_html), height=1),
            self.radio_list  # <-- Interactive radio buttons
        ])

    def get_value(self) -> int:
        return self.radio_list.current_value
```

### Focus Management Should Be:
```python
from prompt_toolkit.layout import Layout

def create_layout(self) -> Layout:
    # Create container with all field widgets
    all_fields = HSplit([field.render() for field in self.fields])

    # Return layout with focus chain
    return Layout(
        all_fields,
        focused_element=self.fields[0].textarea  # Start focus on first field
    )

# Tab navigation handled automatically by prompt_toolkit!
```

---

## 🎯 Fix Plan

### Phase 1: Quick Fix (COMPLETED ✅)
- [x] Add `USE_MODAL_FORMS = False` flag in main.py
- [x] Disable modal form calls
- [x] Revert to inline forms (functional)
- [x] Document issues in MODAL_ISSUES.md

### Phase 2: Enhance Inline Forms (IN PROGRESS)
- [ ] Replace `input()` with `prompt_toolkit.prompt()`
- [ ] Add tag autocomplete with `WordCompleter`
- [ ] Add validation with `Validator`
- [ ] Add field history
- [ ] Test thoroughly

### Phase 3: Rewrite Modal Forms (FUTURE)
- [ ] Rewrite `TextField` with real `TextArea`
- [ ] Rewrite `PriorityField` with `RadioList`
- [ ] Rewrite `TagField` with autocomplete
- [ ] Fix modal layout (background, centering)
- [ ] Fix focus management
- [ ] Re-enable with `USE_MODAL_FORMS = True`

**Time Estimate:**
- Phase 2: 1-2 hours
- Phase 3: 4-6 hours

---

## 📚 References

### prompt_toolkit Documentation
- **Widgets:** https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#widgets
- **TextArea:** https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#prompt_toolkit.widgets.TextArea
- **RadioList:** https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#prompt_toolkit.widgets.RadioList
- **Layout:** https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#prompt_toolkit.layout.Layout
- **Application:** https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#prompt_toolkit.application.Application

### Similar Projects (for reference)
- **Textual:** https://github.com/Textualize/textual (full TUI framework)
- **PyInquirer:** https://github.com/CITGuru/PyInquirer (interactive prompts)
- **Questionary:** https://github.com/tmbo/questionary (simple forms)

---

## 🎓 Lessons Learned

1. **Test Early, Test Often**
   - Modal forms were implemented without testing
   - Issues only discovered when user tried to use them
   - Should have tested each field type individually

2. **Use Real Widgets, Not Static Rendering**
   - Don't try to manually handle keyboard input
   - Use prompt_toolkit's built-in widgets
   - They handle focus, input, cursor automatically

3. **Read Documentation First**
   - prompt_toolkit has powerful widgets (TextArea, RadioList, etc.)
   - No need to reinvent the wheel
   - Follow existing patterns

4. **Simplicity Wins**
   - Inline forms with `prompt_toolkit.prompt()` work great
   - Don't need fancy modals for simple task entry
   - User experience > visual appeal

---

## 🚀 Current Status

**Working:** Inline forms (simple but functional)
**Broken:** Modal forms (disabled)
**Next:** Enhance inline forms with prompt_toolkit features

**User Impact:** None - inline forms work fine!

---

**Last Updated:** 2025-10-20
**Author:** Claude Code
**Status:** Modal forms disabled, inline forms active
