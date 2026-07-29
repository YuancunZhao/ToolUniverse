"""Offline BRCA2 golden path across collector, decisions, guard, and MCP."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.guard import guard_acmg_answer
from tooluniverse.smcp import SMCP


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "acmg"
    / "brca2_5946delt.json"
)
BASE_ARGUMENTS = {
    "variant": "NM_000059.4:c.5946delT",
    "gene": "BRCA2",
    "disease": "MONDO:0011450",
    "inheritance": "autosomal dominant",
}
MECHANISM_PROPOSAL = {
    "fact_id": "brca2-lof-mechanism",
    "fact_type": "mechanism",
    "pmid": "99999998",
    "pmcid": "PMC9999998",
    "locator": "mechanism",
    "excerpt": (
        "BRCA2 NM_000059.4:c.5946delT is evaluated in a "
        "haploinsufficiency loss-of-function disease mechanism for "
        "MONDO:0011450 with autosomal dominant inheritance."
    ),
    "variant_identity": "NM_000059.4:c.5946delT",
    "gene": "BRCA2",
    "values": {
        "variant_identity": "NM_000059.4:c.5946delT",
        "gene": "BRCA2",
        "disease": "MONDO:0011450",
        "inheritance": "autosomal dominant",
        "gene_disease_mechanism": "haploinsufficiency",
    },
    "field_excerpts": {
        "gene_disease_mechanism": (
            "haploinsufficiency loss-of-function disease mechanism"
        ),
        "disease": "MONDO:0011450",
        "inheritance": "autosomal dominant inheritance",
    },
    "criterion": "PVS1",
    "suggested_strength": "PVS1",
    "interpretation": "The anchored passage establishes the LoF mechanism.",
    "confidence": 0.95,
    "questions": ["Confirm exact disease and inheritance context."],
    "extractor": {"name": "golden-fixture-llm", "version": "1.0"},
}


class GoldenProviderFixture:
    def __init__(self):
        self.responses = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.calls: list[dict[str, Any]] = []

    def fixture_response(self, call: dict[str, Any]) -> Any | None:
        name = str(call.get("name") or "")
        if name not in self.responses:
            return None
        self.calls.append(deepcopy(call))
        return deepcopy(self.responses[name])

    def run_one_function(self, call: dict[str, Any], **_kwargs: Any) -> Any:
        fixture = self.fixture_response(call)
        if fixture is not None:
            return fixture
        self.calls.append(deepcopy(call))
        return {"status": "unavailable", "reason": "golden fixture has no result"}


class MCPGoldenToolUniverse(ToolUniverse, GoldenProviderFixture):
    """Real ToolUniverse dispatch with provider calls replaced by frozen data."""

    def __init__(self):
        ToolUniverse.__init__(self)
        GoldenProviderFixture.__init__(self)
        self.load_tools()

    def run_one_function(self, call: dict[str, Any], **kwargs: Any) -> Any:
        fixture = self.fixture_response(call)
        if fixture is not None:
            return fixture
        return super().run_one_function(call, **kwargs)


def _trusted_fact_ids(result: dict[str, Any]) -> set[str]:
    return {
        str(row.get("fact_id") or "")
        for row in result.get("source_facts") or []
        if row.get("fact_id")
    }


def _reviewed_result(
    fixture: GoldenProviderFixture,
    card_id: str,
    *,
    reviewer: str = "",
) -> dict[str, Any]:
    decision = {"card_id": card_id, "decision": "accept"}
    if reviewer:
        decision.update({"reviewer": reviewer, "decided_at": "2026-07-27T00:00:00Z"})
    return ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": [MECHANISM_PROPOSAL],
            "evidence_decisions": [decision],
        }
    )


def test_brca2_golden_three_phase_evidence_workflow():
    fixture = GoldenProviderFixture()
    initial = ACMGEvidencePipeline(fixture).run(
        {**BASE_ARGUMENTS, "response_detail": "summary"}
    )

    expected_top_level = {
        "status",
        "execution_status",
        "coverage_status",
        "variant_identity",
        "consequence_profile",
        "runtime_manifest",
        "source_facts",
        "evidence_cards",
        "compatibility_report",
        "conflict_report",
        "system_preview_bayesian",
        "user_selected_bayesian",
        "decision_report",
        "final_classification_allowed",
    }
    assert expected_top_level <= set(initial)
    assert initial["variant_identity"]["gene"] == "BRCA2"
    assert initial["variant_identity"]["transcript"] == "NM_000059.4"
    assert initial["consequence_profile"]["protein_effect"] == "lof"
    assert initial["final_classification_allowed"] is False
    assert initial["runtime_manifest"]["acmg_runtime_version"] == "evidence-only-1"
    assert len(initial["runtime_manifest"]["ruleset_hash"]) == 64
    assert len(json.dumps(initial, ensure_ascii=False, separators=(",", ":"))) < 50_000

    proposed = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": [MECHANISM_PROPOSAL],
        }
    )
    pvs1 = next(
        row for row in proposed["evidence_cards"] if row["criterion"] == "PVS1"
    )
    assert pvs1["assessment_status"] == "met"
    assert pvs1["strength"] == "PVS1"
    assert pvs1["system_preview_included"] is True
    assert pvs1["card_id"] in proposed["system_preview_bayesian"]["included_card_ids"]
    assert "compatibility_exclusions" in proposed["conflict_report"]
    assert "correlated_source_exclusions" in proposed["conflict_report"]

    reviewed = _reviewed_result(fixture, pvs1["card_id"])
    reviewed_with_attribution = _reviewed_result(
        fixture, pvs1["card_id"], reviewer="golden-reviewer"
    )
    assert reviewed["decision_report"]["status"] == "completed"
    assert reviewed["user_selected_bayesian"]["status"] == "computed"
    assert reviewed["user_selected_bayesian"]["included_card_ids"] == [pvs1["card_id"]]
    assert (
        reviewed["user_selected_bayesian"]["posterior_probability"]
        == reviewed_with_attribution["user_selected_bayesian"]["posterior_probability"]
    )
    assert (
        reviewed["user_selected_bayesian"]["included_card_ids"]
        == reviewed_with_attribution["user_selected_bayesian"]["included_card_ids"]
    )

    trusted = _trusted_fact_ids(reviewed)
    passed = guard_acmg_answer(
        "PVS1 is a system suggestion supported by the collected facts.",
        reviewed["evidence_cards"],
        trusted_source_fact_ids=trusted,
        known_source_fact_ids=trusted,
    )
    blocked = guard_acmg_answer(
        "This variant is likely_pathogenic.",
        reviewed["evidence_cards"],
        trusted_source_fact_ids=trusted,
        known_source_fact_ids=trusted,
    )
    assert passed["status"] == "PASS"
    assert blocked["status"] == "BLOCK"


def _mcp_payload(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if not isinstance(text, str):
            continue
        decoded = json.loads(text)
        if isinstance(decoded, dict):
            return decoded
    raise AssertionError(f"No JSON object in MCP result: {result!r}")


@pytest.mark.asyncio
async def test_compact_mcp_execute_tool_runs_acmg_collector_offline():
    from fastmcp import Client

    runtime = MCPGoldenToolUniverse()
    server = SMCP(
        name="ACMG golden MCP",
        tooluniverse_config=runtime,
        compact_mode=True,
        search_enabled=False,
    )
    async with Client(server) as client:
        response = await client.call_tool(
            "execute_tool",
            {
                "tool_name": "ACMG_evidence_collector",
                "arguments": {**BASE_ARGUMENTS, "response_detail": "summary"},
            },
        )
    payload = _mcp_payload(response)
    assert payload["execution_status"] == "success"
    assert payload["variant_identity"]["gene"] == "BRCA2"
    assert payload["runtime_manifest"]["collector_schema_version"] == "2026-07-27"
    assert payload["final_classification_allowed"] is False
