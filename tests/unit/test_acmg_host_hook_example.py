"""The framework-neutral ACMG host hook example remains executable."""

from __future__ import annotations

import importlib.util
from pathlib import Path


EXAMPLE_PATH = Path("examples/acmg_host_hooks.py")
SPEC = importlib.util.spec_from_file_location("acmg_host_hooks_example", EXAMPLE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
collect_before_answer = MODULE.collect_before_answer
guard_after_answer = MODULE.guard_after_answer


class _Executor:
    def __init__(self):
        self.calls = []

    def __call__(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "ACMG_evidence_collector":
            return {
                "evidence_cards": [],
                "source_facts": [],
                "final_classification_allowed": False,
            }
        return {"status": "BLOCK"}


def test_reference_host_hooks_preserve_collector_result_binding():
    execute = _Executor()
    collected = collect_before_answer(
        execute,
        {"variant": "NM_000059.4:c.5946delT", "gene": "BRCA2"},
    )
    guarded = guard_after_answer(execute, "Pathogenic", collected)

    assert guarded["status"] == "BLOCK"
    assert execute.calls == [
        (
            "ACMG_evidence_collector",
            {"variant": "NM_000059.4:c.5946delT", "gene": "BRCA2"},
        ),
        (
            "ACMG_guard_final_answer",
            {
                "final_answer_text": "Pathogenic",
                "collector_result": collected,
            },
        ),
    ]
