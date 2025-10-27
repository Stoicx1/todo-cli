import pytest

from models.task import Task
from utils.tag_parser import parse_tags, normalize_tag, merge_tags


def test_tags_normalized_to_lowercase():
    tags = parse_tags("Backend, API, Urgent")
    assert tags == ["backend", "api", "urgent"]


def test_max_3_tags_enforced_in_parser():
    tags = parse_tags("a, b, c, d", max_tags=3)
    assert tags == ["a", "b", "c"]


def test_duplicate_tags_removed():
    tags = parse_tags("a, A, a, b")
    assert tags == ["a", "b"]


def test_empty_tags_filtered():
    tags = parse_tags(" , a, , b , ")
    assert tags == ["a", "b"]


def test_tag_whitespace_stripped():
    tags = parse_tags("  spaced  , under_score ")
    assert tags == ["spaced", "under_score"]


def test_tag_special_chars_handled():
    tags = parse_tags("valid, in*valid, also@bad, good-tag")
    assert tags == ["valid", "good-tag"]


def test_task_dataclass_migrates_legacy_tag_and_limits():
    t = Task(id=1, name="n", comment="", description="", priority=2, tag="MAIN", tags=["extra", "MORE", "X", "Y"]) 
    # __post_init__ lowercases and limits to 3
    assert t.tags == ["extra", "more", "x"]
    assert t.tag == "extra"


def test_task_add_tag_respects_limit():
    t = Task(id=1, name="n", comment="", description="", priority=2, tag="a", tags=["a", "b", "c"]) 
    ok = t.add_tag("d")
    assert not ok
    assert t.tags == ["a", "b", "c"]


def test_merge_tags_respects_limit_and_order():
    merged = merge_tags(["a", "b"], ["b", "c", "d"], max_tags=3)
    assert merged == ["a", "b", "c"]


def test_normalize_tag_helper():
    assert normalize_tag("  MixedCase  ") == "mixedcase"

