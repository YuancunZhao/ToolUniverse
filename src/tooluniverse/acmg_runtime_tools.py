"""Registered ToolUniverse adapters for the evidence-only ACMG runtime."""

from __future__ import annotations

from typing import Any

from .acmg.clinical import clinical_evidence
from .acmg.collector import ACMGEvidencePipeline
from .acmg.computational import computational_evidence
from .acmg.functional import functional_evidence
from .acmg.guard import guard_acmg_answer
from .acmg.literature import literature_evidence
from .acmg.models import evidence_cards_to_result
from .acmg.population import population_evidence
from .base_tool import BaseTool
from .tool_registry import register_tool


def _trusted_source_fact_ids(collector_result: Any) -> set[str] | None:
    """Extract only ready facts from a collector result for the internal guard."""
    if not isinstance(collector_result, dict):
        return None
    facts = collector_result.get("source_facts")
    if not isinstance(facts, list):
        return None
    trusted = {
        fact.get("fact_id", "").strip()
        for fact in facts
        if isinstance(fact, dict)
        and isinstance(fact.get("fact_id"), str)
        and fact.get("fact_id", "").strip()
        and fact.get("status") == "success"
        and fact.get("identity_verified") is True
        and fact.get("assessment_ready") is True
    }
    return trusted


def _known_source_fact_ids(collector_result: Any) -> set[str] | None:
    """Extract all serialized collector fact IDs for citation-only card checks."""
    if not isinstance(collector_result, dict):
        return None
    facts = collector_result.get("source_facts")
    if not isinstance(facts, list):
        return None
    return {
        fact.get("fact_id", "").strip()
        for fact in facts
        if isinstance(fact, dict)
        and isinstance(fact.get("fact_id"), str)
        and fact.get("fact_id", "").strip()
    }


@register_tool("ACMG_evidence_collector")
class ACMGEvidenceCollector(BaseTool):
    """Collect sources and apply the shared deterministic evidence rules."""

    def __init__(self, tool_config: dict[str, Any], tooluniverse: Any | None = None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return {
                "status": "error",
                "error": "arguments must be an object",
                "final_classification_allowed": False,
            }
        return ACMGEvidencePipeline(self.tooluniverse).run(arguments)


@register_tool("ACMG_overlay_gate_assess_variant")
class ACMGOverlayGateTool(BaseTool):
    """Backward-compatible thin alias for the evidence collector."""

    def __init__(self, tool_config: dict[str, Any], tooluniverse: Any | None = None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return ACMGEvidencePipeline(self.tooluniverse).run(dict(arguments))


@register_tool("ACMGEvidenceGroupTool")
class ACMGEvidenceGroupTool(BaseTool):
    """Dispatch one public evidence group to its shared pure rule function."""

    _OPERATIONS = {
        "population": population_evidence,
        "computational": computational_evidence,
        "clinical": clinical_evidence,
        "functional": functional_evidence,
        "literature": literature_evidence,
    }

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.operation = str(tool_config.get("fields", {}).get("operation", ""))

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        target = self._OPERATIONS.get(self.operation)
        if target is None:
            return {
                "status": "error",
                "error": f"Unknown evidence group: {self.operation}",
            }
        return evidence_cards_to_result(target(**arguments))


@register_tool("ACMGGuardFinalAnswerTool")
class ACMGGuardFinalAnswerTool(BaseTool):
    """Enforce EvidenceCard support and block final five-tier labels."""

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        answer_text = str(arguments.get("final_answer_text") or "")
        cards = arguments.get("evidence_cards")
        collector_result = arguments.get("collector_result")
        if cards is None and isinstance(collector_result, dict):
            cards = collector_result.get("evidence_cards", [])
        if not isinstance(cards, list):
            cards = []
        return guard_acmg_answer(
            answer_text,
            cards,
            trusted_source_fact_ids=_trusted_source_fact_ids(collector_result),
            known_source_fact_ids=_known_source_fact_ids(collector_result),
        )


__all__ = [
    "ACMGEvidenceCollector",
    "ACMGEvidenceGroupTool",
    "ACMGGuardFinalAnswerTool",
    "ACMGOverlayGateTool",
]
