"""Registered ToolUniverse adapters for the evidence-only ACMG runtime."""

from __future__ import annotations

from typing import Any

from .acmg.clinical import clinical_evidence
from .acmg.collector import ACMGEvidencePipeline
from .acmg.computational import computational_evidence
from .acmg.functional import functional_evidence
from .acmg.guard import guard_acmg_answer, validate_guard_context
from .acmg.literature import literature_evidence
from .acmg.models import evidence_cards_to_result
from .acmg.population import population_evidence
from .base_tool import BaseTool
from .tool_registry import register_tool


def _source_fact_ids(
    collector_result: Any,
) -> tuple[set[str] | None, set[str] | None]:
    """Extract known and assessment-ready fact IDs in one pass."""
    if not isinstance(collector_result, dict):
        return None, None
    facts = collector_result.get("source_facts")
    if not isinstance(facts, list):
        return None, None
    known: set[str] = set()
    trusted: set[str] = set()
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("fact_id") or "").strip()
        if not fact_id:
            continue
        known.add(fact_id)
        if (
            fact.get("status") == "success"
            and fact.get("identity_verified") is True
            and fact.get("assessment_ready") is True
        ):
            trusted.add(fact_id)
    return trusted, known


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
        guard_context = arguments.get("guard_context")
        trusted_ids: set[str] | None = None
        known_ids: set[str] | None = None
        if guard_context is not None:
            context_valid, context_error = validate_guard_context(guard_context)
            if not context_valid:
                return {
                    "status": "BLOCK",
                    "blocking_reasons": ["guard_context_invalid"],
                    "guard_context_error": context_error,
                    "cards_used": [],
                    "card_roles": [],
                    "unsupported_codes": [],
                    "message": "BLOCKED: guard_context_invalid",
                }
            assert isinstance(guard_context, dict)
            cards = guard_context.get("cards", [])
            trusted_ids = {
                str(value)
                for value in guard_context.get("trusted_source_fact_ids") or []
                if value
            }
            known_ids = {
                str(value)
                for value in guard_context.get("known_source_fact_ids") or []
                if value
            }
        elif cards is None and isinstance(collector_result, dict):
            cards = collector_result.get("evidence_cards", [])
        if not isinstance(cards, list):
            cards = []
        if guard_context is None:
            trusted_ids, known_ids = _source_fact_ids(collector_result)
        return guard_acmg_answer(
            answer_text,
            cards,
            trusted_source_fact_ids=trusted_ids,
            known_source_fact_ids=known_ids,
        )


__all__ = [
    "ACMGEvidenceCollector",
    "ACMGEvidenceGroupTool",
    "ACMGGuardFinalAnswerTool",
    "ACMGOverlayGateTool",
]
