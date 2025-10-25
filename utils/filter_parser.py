"""
Filter Expression Parser

Parses advanced filter expressions with operators:
- =  : equals
- != : not equals
- >= : greater than or equal
- <= : less than or equal

Supports:
- Single conditions: priority=1
- Compound filters: status=done tag=psdc (space = AND)
- Multi-value: priority=1,2 (comma = OR)
- Multi-tag: tag=psdc+webasto (+ = AND for tags)

Examples:
    status=done              → Completed tasks
    priority>=2              → Medium or low priority
    status=undone tag=psdc   → Incomplete tasks tagged "psdc"
    tag=psdc,webasto         → Tasks with either tag
    tag=psdc+webasto         → Tasks with both tags
"""

from typing import List, Tuple, Optional
import re
from utils.time import parse_duration


class FilterCondition:
    """Represents a single filter condition"""

    def __init__(self, field: str, operator: str, value: str):
        self.field = field.lower()
        self.operator = operator
        self.value = value.lower()

        # Parse multi-value (comma-separated OR logic)
        if ',' in self.value and field != 'tag':
            self.values = [v.strip() for v in self.value.split(',')]
        else:
            self.values = [self.value]

    def __repr__(self):
        return f"FilterCondition({self.field} {self.operator} {self.value})"


def parse_filter_expression(filter_str: str) -> List[FilterCondition]:
    """
    Parse filter expression into list of conditions.

    Args:
        filter_str: Filter expression like "status=done tag=psdc priority>=2"

    Returns:
        List of FilterCondition objects

    Examples:
        >>> parse_filter_expression("status=done tag=psdc")
        [FilterCondition(status = done), FilterCondition(tag = psdc)]
    """
    if not filter_str or filter_str.strip() == "":
        return []

    filter_str = filter_str.strip().lower()

    # Handle legacy syntax (backward compatibility)
    if filter_str == "none" or filter_str == "all":
        return []

    if filter_str == "done":
        return [FilterCondition("status", "=", "done")]

    if filter_str == "undone":
        return [FilterCondition("status", "=", "undone")]

    if filter_str.startswith("tag:"):
        # Legacy "tag:name" syntax
        tag_name = filter_str.split(":", 1)[1].strip()
        if tag_name and tag_name != "none":
            return [FilterCondition("tag", "=", tag_name)]
        return []

    # Parse new operator-based syntax
    conditions = []

    # Split by spaces, but handle quoted values
    parts = filter_str.split()

    for part in parts:
        condition = parse_condition(part)
        if condition:
            conditions.append(condition)

    return conditions


def parse_condition(condition_str: str) -> Optional[FilterCondition]:
    """
    Parse a single condition like "priority>=2" or "tag=psdc"

    Args:
        condition_str: Single condition string

    Returns:
        FilterCondition object or None if invalid
    """
    # Try to match operators in order of precedence (longest first)
    operators = ['!=', '>=', '<=', '=']

    for op in operators:
        if op in condition_str:
            parts = condition_str.split(op, 1)
            if len(parts) == 2:
                field = parts[0].strip().lower()
                value = parts[1].strip()

                # Normalize field aliases
                field_aliases = {
                    'prio': 'priority', 'pri': 'priority', 'p': 'priority',
                    'stat': 'status', 's': 'status',
                    't': 'tag'
                }
                field = field_aliases.get(field, field)

                # Validate field
                if field not in ('status', 'priority', 'tag', 'age'):
                    continue

                # Validate value
                if not value:
                    continue

                return FilterCondition(field, op, value)

    return None


def matches_condition(task, condition: FilterCondition) -> bool:
    """
    Check if task matches a filter condition.

    Args:
        task: Task object
        condition: FilterCondition to check

    Returns:
        True if task matches condition
    """
    field = condition.field
    operator = condition.operator
    value = condition.value

    if field == 'status':
        return match_status(task, operator, value)
    elif field == 'priority':
        return match_priority(task, operator, value)
    elif field == 'tag':
        return match_tag(task, operator, value)
    elif field == 'age':
        return match_age(task, operator, value)

    return False


def match_status(task, operator: str, value: str) -> bool:
    """Match status condition (done/undone)"""
    is_done = getattr(task, 'done', False)

    if value == 'done':
        if operator == '=':
            return is_done
        elif operator == '!=':
            return not is_done
    elif value == 'undone':
        if operator == '=':
            return not is_done
        elif operator == '!=':
            return is_done

    return False


def match_priority(task, operator: str, value: str) -> bool:
    """Match priority condition with operators"""
    task_priority = getattr(task, 'priority', 2)

    # Helper: convert textual priority to numeric
    def to_pri(v: str) -> Optional[int]:
        v = v.strip().lower()
        mapping = {
            '1': 1, 'high': 1, 'h': 1,
            '2': 2, 'medium': 2, 'med': 2, 'm': 2,
            '3': 3, 'low': 3, 'l': 3,
        }
        return mapping.get(v)

    # Handle multi-value (comma-separated OR)
    if ',' in value:
        values = [to_pri(v) for v in value.split(',')]
        values = [v for v in values if v is not None]
        # For multi-value, only = and != make sense
        if operator == '=':
            return task_priority in values
        elif operator == '!=':
            return task_priority not in values
        return False

    # Single value comparison
    target_priority = to_pri(value)
    if target_priority is None:
        return False

    if operator == '=':
        return task_priority == target_priority
    elif operator == '!=':
        return task_priority != target_priority
    elif operator == '>=':
        return task_priority >= target_priority
    elif operator == '<=':
        return task_priority <= target_priority

    return False


def match_age(task, operator: str, value: str) -> bool:
    """Match age condition using created_at timestamp.

    Value accepts duration strings like '30m', '2h', '3d', '1y'.
    """
    from utils.time import age_seconds

    task_age = age_seconds(getattr(task, 'created_at', ''))
    if task_age is None:
        return False

    target = parse_duration(value)
    if target is None:
        return False

    if operator == '=':
        return task_age == target
    if operator == '!=':
        return task_age != target
    if operator == '>=':
        return task_age >= target
    if operator == '<=':
        return task_age <= target
    return False


def match_tag(task, operator: str, value: str) -> bool:
    """
    Match tag condition with special multi-tag logic.

    Syntax:
        tag=psdc          → Has tag "psdc"
        tag!=psdc         → Doesn't have tag "psdc"
        tag=psdc,webasto  → Has tag "psdc" OR "webasto" (comma = OR)
        tag=psdc+webasto  → Has tag "psdc" AND "webasto" (plus = AND)
    """
    task_tags = [t.lower() for t in getattr(task, 'tags', [])]

    # Handle multi-tag AND logic (plus sign)
    if '+' in value:
        required_tags = [t.strip() for t in value.split('+')]
        if operator == '=':
            # Must have ALL tags
            return all(tag in task_tags for tag in required_tags)
        elif operator == '!=':
            # Must NOT have ALL tags (i.e., missing at least one)
            return not all(tag in task_tags for tag in required_tags)
        return False

    # Handle multi-tag OR logic (comma)
    if ',' in value:
        possible_tags = [t.strip() for t in value.split(',')]
        if operator == '=':
            # Has ANY of the tags
            return any(tag in task_tags for tag in possible_tags)
        elif operator == '!=':
            # Doesn't have ANY of the tags
            return not any(tag in task_tags for tag in possible_tags)
        return False

    # Single tag
    target_tag = value.strip()

    if operator == '=':
        return target_tag in task_tags
    elif operator == '!=':
        return target_tag not in task_tags

    return False


def matches_all_conditions(task, conditions: List[FilterCondition]) -> bool:
    """
    Check if task matches ALL conditions (AND logic).

    Args:
        task: Task object
        conditions: List of FilterCondition objects

    Returns:
        True if task matches all conditions
    """
    if not conditions:
        return True

    for condition in conditions:
        if not matches_condition(task, condition):
            return False

    return True


def get_filter_description(conditions: List[FilterCondition]) -> str:
    """
    Get human-readable description of filter.

    Args:
        conditions: List of FilterCondition objects

    Returns:
        Description string like "done, tagged psdc, high priority"
    """
    if not conditions:
        return "none"

    parts = []
    for condition in conditions:
        field = condition.field
        op = condition.operator
        value = condition.value

        if field == 'status':
            if op == '=' and value == 'done':
                parts.append("completed")
            elif op == '=' and value == 'undone':
                parts.append("incomplete")
            elif op == '!=' and value == 'done':
                parts.append("not completed")
            elif op == '!=' and value == 'undone':
                parts.append("not incomplete")

        elif field == 'priority':
            if op == '=':
                if ',' in value:
                    # Map textual values to human words if possible
                    names_map = {
                        '1': 'high', 'high': 'high', 'h': 'high',
                        '2': 'medium', 'medium': 'medium', 'med': 'medium', 'm': 'medium',
                        '3': 'low', 'low': 'low', 'l': 'low',
                    }
                    pretty = ','.join(names_map.get(v.strip().lower(), v.strip()) for v in value.split(','))
                    parts.append(f"priority {pretty}")
                else:
                    priority_names = {1: "high", 2: "medium", 3: "low"}
                    try:
                        num = int(value)
                        parts.append(f"{priority_names.get(num, value)} priority")
                    except ValueError:
                        parts.append(f"{value} priority")
            elif op == '!=':
                parts.append(f"not priority {value}")
            elif op == '>=':
                parts.append(f"priority >= {value}")
            elif op == '<=':
                parts.append(f"priority <= {value}")

        elif field == 'tag':
            if '+' in value:
                parts.append(f"tags {value.replace('+', ' AND ')}")
            elif ',' in value:
                parts.append(f"tags {value.replace(',', ' OR ')}")
            elif op == '=':
                parts.append(f"tagged {value}")
            elif op == '!=':
                parts.append(f"not tagged {value}")

    return ", ".join(parts)
