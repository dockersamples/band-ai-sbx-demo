"""The required behaviour of slugify().

These tests are the specification. Repo Doctor is instructed never to modify them,
and its write_source tool is scoped to src/ so that it cannot.
"""

from slugify import slugify


def test_lowercases_input() -> None:
    assert slugify("Hello") == "hello"


def test_trims_surrounding_whitespace() -> None:
    assert slugify("  hello  ") == "hello"


def test_leaves_a_simple_slug_unchanged() -> None:
    assert slugify("hello-world") == "hello-world"


def test_collapses_runs_of_whitespace_to_one_hyphen() -> None:
    assert slugify("hello   world") == "hello-world"
    assert slugify("a\tb") == "a-b"
