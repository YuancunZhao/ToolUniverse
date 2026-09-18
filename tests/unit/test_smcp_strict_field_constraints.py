"""Regression guard for Fix-C-20260918 (schema side): strict-mode parameter
models crashed with ``TypeError: unhashable type: 'list'`` for JSON Schema
parameters whose ``type`` is a LIST (e.g. ``["string", "null"]`` -- the
standard nullable-string spelling), because ``SMCP._strict_field_constraints``
tested list-typed ``param_info["type"]`` for membership in a SET. Set
membership hashes the key, and lists are unhashable. The membership tests
now use tuples (equality-based, list-safe).
"""

import pytest

from tooluniverse.smcp import SMCP

pytestmark = pytest.mark.unit


def test_list_typed_string_null_does_not_raise():
    constraints = SMCP._strict_field_constraints(
        {"type": ["string", "null"], "maxLength": 10, "minLength": 1}
    )
    assert constraints == {"max_length": 10, "min_length": 1}


def test_plain_string_constraints_unchanged():
    constraints = SMCP._strict_field_constraints(
        {"type": "string", "maxLength": 10, "pattern": "^rs\\d+$"}
    )
    assert constraints == {"max_length": 10, "pattern": "^rs\\d+$"}


def test_number_constraints_unchanged():
    constraints = SMCP._strict_field_constraints(
        {"type": "number", "minimum": 0, "maximum": 1}
    )
    assert constraints == {"ge": 0, "le": 1}


def test_integer_type_still_recognized():
    constraints = SMCP._strict_field_constraints(
        {"type": "integer", "exclusiveMinimum": 0}
    )
    assert constraints == {"gt": 0}


def test_list_typed_number_null_does_not_raise():
    # A nullable number must take the numeric branch by equality, not crash
    constraints = SMCP._strict_field_constraints(
        {"type": ["number", "null"], "minimum": 0}
    )
    assert constraints == {"ge": 0}


def test_array_type_constraints_unchanged():
    constraints = SMCP._strict_field_constraints(
        {"type": "array", "minItems": 1, "maxItems": 5}
    )
    assert constraints == {"min_length": 1, "max_length": 5}
