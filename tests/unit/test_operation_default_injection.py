"""Tools registered as a single operation (DNA_find_orfs, Epidemiology_nnt, ...)
still read arguments["operation"], so the natural call implied by the tool's own
name failed parameter validation and gave the caller no signal the tool was
usable. 148 tools across 41 tool classes were affected.

Rather than patch each class, ToolUniverse fills `operation` in from the tool's
own config (fields.operation, else the schema default) before validation, so it
applies whether or not validation runs. An explicit operation always wins.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse

pytestmark = pytest.mark.unit

DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


@pytest.fixture(scope="module")
def tu():
    engine = ToolUniverse()
    engine.load_tools()
    return engine


def test_operation_injected_from_config(tu):
    args = {"sequence": "ATGAAACCCGGGTTTTAA"}
    tu._apply_operation_default("DNA_find_orfs", args)
    assert args["operation"] == "find_orfs"


def test_explicit_operation_is_not_overwritten(tu):
    args = {"sequence": "GCGC", "operation": "calculate_gc_content"}
    tu._apply_operation_default("DNA_find_orfs", args)
    assert args["operation"] == "calculate_gc_content"


def test_unknown_tool_is_left_alone(tu):
    args = {"x": 1}
    tu._apply_operation_default("NoSuchToolName", args)
    assert "operation" not in args


def test_tool_without_configured_operation_is_left_alone(tu):
    """Tools that take no `operation` must not gain a spurious one."""
    args = {}
    tu._apply_operation_default("UniProt_get_entry_by_accession", args)
    assert "operation" not in args


def test_natural_call_succeeds_end_to_end(tu):
    """The documented example must run with `operation` omitted."""
    result = tu.run(
        {"name": "DNA_find_orfs", "arguments": {"sequence": "ATGAAACCCGGGTTTTAA"}}
    )
    assert isinstance(result, dict)
    assert result.get("status") == "success", result


def test_wired_operations_match_documented_examples():
    """A wrong default would silently run the wrong handler -- guard against it."""
    mismatched = []
    for path in DATA_DIR.glob("*.json"):
        try:
            raw = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        tools = raw if isinstance(raw, list) else raw.get("tools")
        if not isinstance(tools, list):
            continue
        for cfg in tools:
            if not isinstance(cfg, dict):
                continue
            operation = (cfg.get("fields") or {}).get("operation")
            if not operation:
                continue
            documented = {
                ex.get("operation")
                for ex in (cfg.get("test_examples") or [])
                if isinstance(ex, dict) and ex.get("operation")
            }
            if documented and operation not in documented:
                mismatched.append((cfg.get("name"), operation, sorted(documented)))
    assert not mismatched, f"fields.operation disagrees with example: {mismatched[:5]}"
