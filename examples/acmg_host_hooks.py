"""Framework-neutral host hooks for the evidence-only ACMG workflow.

The host decides when a request has ACMG final-classification intent. These
helpers only define the required ToolUniverse calls; they do not claim to
intercept text that the host never submits.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


ExecuteTool = Callable[[str, dict[str, Any]], dict[str, Any]]


def collect_before_answer(
    execute_tool: ExecuteTool,
    collector_arguments: dict[str, Any],
) -> dict[str, Any]:
    """Run the required pre-answer evidence collection call."""
    return execute_tool("ACMG_evidence_collector", dict(collector_arguments))


def guard_after_answer(
    execute_tool: ExecuteTool,
    draft_answer: str,
    collector_result: dict[str, Any],
) -> dict[str, Any]:
    """Run the required post-answer guard against the collected result."""
    return execute_tool(
        "ACMG_guard_final_answer",
        {
            "final_answer_text": str(draft_answer),
            "collector_result": collector_result,
        },
    )


__all__ = ["collect_before_answer", "guard_after_answer"]
