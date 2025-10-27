"""
Tests for utils/filter_parser.py - Advanced filtering system
"""

import pytest
from models.task import Task
from utils.filter_parser import (
    parse_filter_expression,
    parse_condition,
    FilterCondition,
    matches_condition,
    matches_all_conditions,
    match_status,
    match_priority,
    match_tag,
    get_filter_description,
)


class TestFilterCondition:
    """Test FilterCondition class"""

    def test_create_simple_condition(self):
        """Test creating a simple filter condition"""
        cond = FilterCondition("priority", "=", "1")

        assert cond.field == "priority"
        assert cond.operator == "="
        assert cond.value == "1"
        assert cond.values == ["1"]

    def test_create_multi_value_condition(self):
        """Test creating a multi-value condition"""
        cond = FilterCondition("priority", "=", "1,2,3")

        assert cond.value == "1,2,3"
        assert cond.values == ["1", "2", "3"]

    def test_normalizes_to_lowercase(self):
        """Test that field and value are normalized to lowercase"""
        cond = FilterCondition("PRIORITY", "=", "HIGH")

        assert cond.field == "priority"
        assert cond.value == "high"


class TestParseCondition:
    """Test parsing individual conditions"""

    def test_parse_equals_operator(self):
        """Test parsing equals operator"""
        cond = parse_condition("priority=1")

        assert cond.field == "priority"
        assert cond.operator == "="
        assert cond.value == "1"

    def test_parse_not_equals_operator(self):
        """Test parsing not-equals operator"""
        cond = parse_condition("priority!=2")

        assert cond.field == "priority"
        assert cond.operator == "!="
        assert cond.value == "2"

    def test_parse_greater_equals_operator(self):
        """Test parsing greater-or-equal operator"""
        cond = parse_condition("priority>=2")

        assert cond.field == "priority"
        assert cond.operator == ">="
        assert cond.value == "2"

    def test_parse_less_equals_operator(self):
        """Test parsing less-or-equal operator"""
        cond = parse_condition("priority<=2")

        assert cond.field == "priority"
        assert cond.operator == "<="
        assert cond.value == "2"

    def test_parse_tag_condition(self):
        """Test parsing tag condition"""
        cond = parse_condition("tag=work")

        assert cond.field == "tag"
        assert cond.value == "work"

    def test_parse_status_condition(self):
        """Test parsing status condition"""
        cond = parse_condition("status=done")

        assert cond.field == "status"
        assert cond.value == "done"

    def test_parse_field_aliases(self):
        """Test parsing field aliases"""
        assert parse_condition("p=1").field == "priority"
        assert parse_condition("pri=1").field == "priority"
        assert parse_condition("prio=1").field == "priority"
        assert parse_condition("s=done").field == "status"
        assert parse_condition("stat=done").field == "status"
        assert parse_condition("t=work").field == "tag"

    def test_parse_invalid_condition(self):
        """Test parsing invalid condition"""
        assert parse_condition("invalid") is None
        assert parse_condition("=") is None
        assert parse_condition("field=") is None


class TestParseFilterExpression:
    """Test parsing full filter expressions"""

    def test_parse_empty_expression(self):
        """Test parsing empty expression"""
        conditions = parse_filter_expression("")

        assert conditions == []

    def test_parse_none_expression(self):
        """Test parsing 'none' expression"""
        conditions = parse_filter_expression("none")

        assert conditions == []

    def test_parse_single_condition(self):
        """Test parsing single condition"""
        conditions = parse_filter_expression("priority=1")

        assert len(conditions) == 1
        assert conditions[0].field == "priority"
        assert conditions[0].value == "1"

    def test_parse_compound_expression(self):
        """Test parsing compound expression with multiple conditions"""
        conditions = parse_filter_expression("status=done priority=1 tag=work")

        assert len(conditions) == 3
        assert conditions[0].field == "status"
        assert conditions[1].field == "priority"
        assert conditions[2].field == "tag"

    def test_parse_legacy_done_syntax(self):
        """Test parsing legacy 'done' syntax"""
        conditions = parse_filter_expression("done")

        assert len(conditions) == 1
        assert conditions[0].field == "status"
        assert conditions[0].value == "done"

    def test_parse_legacy_undone_syntax(self):
        """Test parsing legacy 'undone' syntax"""
        conditions = parse_filter_expression("undone")

        assert len(conditions) == 1
        assert conditions[0].field == "status"
        assert conditions[0].value == "undone"

    def test_parse_legacy_tag_syntax(self):
        """Test parsing legacy 'tag:name' syntax"""
        conditions = parse_filter_expression("tag:work")

        assert len(conditions) == 1
        assert conditions[0].field == "tag"
        assert conditions[0].value == "work"


class TestMatchStatus:
    """Test status matching"""

    def test_match_status_done_equals(self):
        """Test matching done status with equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="", done=True)

        assert match_status(task, "=", "done") is True
        assert match_status(task, "=", "undone") is False

    def test_match_status_undone_equals(self):
        """Test matching undone status with equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="", done=False)

        assert match_status(task, "=", "undone") is True
        assert match_status(task, "=", "done") is False

    def test_match_status_not_equals(self):
        """Test matching status with not-equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="", done=True)

        assert match_status(task, "!=", "done") is False
        assert match_status(task, "!=", "undone") is True


class TestMatchPriority:
    """Test priority matching"""

    def test_match_priority_equals(self):
        """Test matching priority with equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="")

        assert match_priority(task, "=", "1") is True
        assert match_priority(task, "=", "2") is False

    def test_match_priority_not_equals(self):
        """Test matching priority with not-equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="")

        assert match_priority(task, "!=", "1") is False
        assert match_priority(task, "!=", "2") is True

    def test_match_priority_greater_equals(self):
        """Test matching priority with greater-or-equal"""
        task = Task(id=1, name="Task", comment="", description="", priority=2, tag="")

        assert match_priority(task, ">=", "1") is True
        assert match_priority(task, ">=", "2") is True
        assert match_priority(task, ">=", "3") is False

    def test_match_priority_less_equals(self):
        """Test matching priority with less-or-equal"""
        task = Task(id=1, name="Task", comment="", description="", priority=2, tag="")

        assert match_priority(task, "<=", "3") is True
        assert match_priority(task, "<=", "2") is True
        assert match_priority(task, "<=", "1") is False

    def test_match_priority_text_values(self):
        """Test matching priority with text values (high/medium/low)"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="")

        assert match_priority(task, "=", "high") is True
        assert match_priority(task, "=", "h") is True
        assert match_priority(task, "=", "medium") is False

    def test_match_priority_multi_value(self):
        """Test matching priority with multiple values (OR logic)"""
        task = Task(id=1, name="Task", comment="", description="", priority=2, tag="")

        assert match_priority(task, "=", "1,2") is True
        assert match_priority(task, "=", "1,3") is False
        assert match_priority(task, "!=", "1,2") is False


class TestMatchTag:
    """Test tag matching"""

    def test_match_tag_single_equals(self):
        """Test matching single tag with equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"])

        assert match_tag(task, "=", "work") is True
        assert match_tag(task, "=", "personal") is False

    def test_match_tag_not_equals(self):
        """Test matching tag with not-equals"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"])

        assert match_tag(task, "!=", "work") is False
        assert match_tag(task, "!=", "personal") is True

    def test_match_tag_multi_tag_or(self):
        """Test matching multiple tags with OR logic (comma)"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work", "urgent"])

        # Has work OR personal (has work)
        assert match_tag(task, "=", "work,personal") is True
        # Has personal OR hobby (has neither)
        assert match_tag(task, "=", "personal,hobby") is False

    def test_match_tag_multi_tag_and(self):
        """Test matching multiple tags with AND logic (plus)"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work", "urgent"])

        # Has work AND urgent (has both)
        assert match_tag(task, "=", "work+urgent") is True
        # Has work AND personal (missing personal)
        assert match_tag(task, "=", "work+personal") is False

    def test_match_tag_case_insensitive(self):
        """Test that tag matching is case insensitive"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"])

        # FilterCondition normalizes values to lowercase
        cond = FilterCondition("tag", "=", "WORK")
        assert cond.value == "work"  # Normalized
        assert match_tag(task, "=", "work") is True


class TestMatchesCondition:
    """Test matching tasks against conditions"""

    def test_matches_status_condition(self):
        """Test matching status condition"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="", done=True)
        cond = FilterCondition("status", "=", "done")

        assert matches_condition(task, cond) is True

    def test_matches_priority_condition(self):
        """Test matching priority condition"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="")
        cond = FilterCondition("priority", "=", "1")

        assert matches_condition(task, cond) is True

    def test_matches_tag_condition(self):
        """Test matching tag condition"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"])
        cond = FilterCondition("tag", "=", "work")

        assert matches_condition(task, cond) is True


class TestMatchesAllConditions:
    """Test matching tasks against multiple conditions (AND logic)"""

    def test_matches_all_empty_conditions(self):
        """Test matching with no conditions"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="")

        assert matches_all_conditions(task, []) is True

    def test_matches_all_single_condition(self):
        """Test matching with single condition"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="", done=True)
        conditions = [FilterCondition("status", "=", "done")]

        assert matches_all_conditions(task, conditions) is True

    def test_matches_all_multiple_conditions_match(self):
        """Test matching with multiple conditions that all match"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"], done=True)
        conditions = [
            FilterCondition("status", "=", "done"),
            FilterCondition("priority", "=", "1"),
            FilterCondition("tag", "=", "work"),
        ]

        assert matches_all_conditions(task, conditions) is True

    def test_matches_all_multiple_conditions_partial_match(self):
        """Test matching with multiple conditions where one doesn't match"""
        task = Task(id=1, name="Task", comment="", description="", priority=1, tag="work", tags=["work"], done=True)
        conditions = [
            FilterCondition("status", "=", "done"),
            FilterCondition("priority", "=", "2"),  # Doesn't match
            FilterCondition("tag", "=", "work"),
        ]

        assert matches_all_conditions(task, conditions) is False


class TestGetFilterDescription:
    """Test generating human-readable filter descriptions"""

    def test_description_empty(self):
        """Test description for empty conditions"""
        desc = get_filter_description([])

        assert desc == "none"

    def test_description_status_done(self):
        """Test description for done status"""
        conditions = [FilterCondition("status", "=", "done")]
        desc = get_filter_description(conditions)

        assert desc == "completed"

    def test_description_status_undone(self):
        """Test description for undone status"""
        conditions = [FilterCondition("status", "=", "undone")]
        desc = get_filter_description(conditions)

        assert desc == "incomplete"

    def test_description_priority_single(self):
        """Test description for single priority"""
        conditions = [FilterCondition("priority", "=", "1")]
        desc = get_filter_description(conditions)

        assert "high priority" in desc

    def test_description_priority_multi(self):
        """Test description for multiple priorities"""
        conditions = [FilterCondition("priority", "=", "1,2")]
        desc = get_filter_description(conditions)

        assert "priority" in desc

    def test_description_tag_single(self):
        """Test description for single tag"""
        conditions = [FilterCondition("tag", "=", "work")]
        desc = get_filter_description(conditions)

        assert desc == "tagged work"

    def test_description_tag_or(self):
        """Test description for OR tags"""
        conditions = [FilterCondition("tag", "=", "work,personal")]
        desc = get_filter_description(conditions)

        assert "work OR personal" in desc

    def test_description_tag_and(self):
        """Test description for AND tags"""
        conditions = [FilterCondition("tag", "=", "work+urgent")]
        desc = get_filter_description(conditions)

        assert "work AND urgent" in desc

    def test_description_compound(self):
        """Test description for compound conditions"""
        conditions = [
            FilterCondition("status", "=", "done"),
            FilterCondition("priority", "=", "1"),
            FilterCondition("tag", "=", "work"),
        ]
        desc = get_filter_description(conditions)

        assert "completed" in desc
        assert "high priority" in desc
        assert "tagged work" in desc


class TestComplexFilterScenarios:
    """Test complex real-world filtering scenarios"""

    def test_filter_high_priority_undone_tasks(self):
        """Test filtering for high priority undone tasks"""
        tasks = [
            Task(id=1, name="Task 1", comment="", description="", priority=1, tag="", done=False),
            Task(id=2, name="Task 2", comment="", description="", priority=1, tag="", done=True),
            Task(id=3, name="Task 3", comment="", description="", priority=2, tag="", done=False),
        ]

        conditions = parse_filter_expression("priority=1 status=undone")
        filtered = [t for t in tasks if matches_all_conditions(t, conditions)]

        assert len(filtered) == 1
        assert filtered[0].id == 1

    def test_filter_work_or_personal_tags(self):
        """Test filtering for work OR personal tags"""
        tasks = [
            Task(id=1, name="Task 1", comment="", description="", priority=1, tag="work", tags=["work"]),
            Task(id=2, name="Task 2", comment="", description="", priority=1, tag="personal", tags=["personal"]),
            Task(id=3, name="Task 3", comment="", description="", priority=1, tag="hobby", tags=["hobby"]),
        ]

        conditions = parse_filter_expression("tag=work,personal")
        filtered = [t for t in tasks if matches_all_conditions(t, conditions)]

        assert len(filtered) == 2
        assert filtered[0].id == 1
        assert filtered[1].id == 2

    def test_filter_multiple_tags_required(self):
        """Test filtering for tasks with multiple required tags"""
        tasks = [
            Task(id=1, name="Task 1", comment="", description="", priority=1, tag="work", tags=["work", "urgent"]),
            Task(id=2, name="Task 2", comment="", description="", priority=1, tag="work", tags=["work"]),
            Task(id=3, name="Task 3", comment="", description="", priority=1, tag="urgent", tags=["urgent"]),
        ]

        conditions = parse_filter_expression("tag=work+urgent")
        filtered = [t for t in tasks if matches_all_conditions(t, conditions)]

        assert len(filtered) == 1
        assert filtered[0].id == 1

    def test_filter_medium_or_low_priority(self):
        """Test filtering for medium or low priority"""
        tasks = [
            Task(id=1, name="Task 1", comment="", description="", priority=1, tag=""),
            Task(id=2, name="Task 2", comment="", description="", priority=2, tag=""),
            Task(id=3, name="Task 3", comment="", description="", priority=3, tag=""),
        ]

        conditions = parse_filter_expression("priority=2,3")
        filtered = [t for t in tasks if matches_all_conditions(t, conditions)]

        assert len(filtered) == 2
        assert filtered[0].id == 2
        assert filtered[1].id == 3
