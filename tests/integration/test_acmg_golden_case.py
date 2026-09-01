"""Offline BRCA2 golden path across collector, decisions, guard, and MCP."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.guard import guard_acmg_answer, validate_guard_context
from tooluniverse.smcp import SMCP


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "acmg" / "brca2_5946delt.json"
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

    def run_many_functions(
        self,
        calls: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[Any]:
        """Keep the golden path fully offline while exercising batch orchestration."""
        return [self.run_one_function(call, **kwargs) for call in calls]


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
        if call.get("name") != "execute_tool" and not str(
            call.get("name") or ""
        ).startswith("ACMG_"):
            self.calls.append(deepcopy(call))
            return {"status": "unavailable", "reason": "golden fixture has no result"}
        return super().run_one_function(call, **kwargs)

    def run_many_functions(
        self,
        calls: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[Any]:
        results = []
        for call in calls:
            fixture = self.fixture_response(call)
            if fixture is None:
                self.calls.append(deepcopy(call))
                fixture = {
                    "status": "unavailable",
                    "reason": "golden fixture has no result",
                }
            results.append(fixture)
        return results


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


def test_brca2_golden_three_phase_evidence_workflow(check_acmg_summary):
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
        "automatic_bayesian",
        "verified_bayesian",
        "user_selected_bayesian",
        "guard_context",
        "decision_report",
        "final_classification_allowed",
    }
    assert expected_top_level <= set(initial)
    assert initial["variant_identity"]["gene"] == "BRCA2"
    assert initial["variant_identity"]["transcript"] == "NM_000059.4"
    assert initial["consequence_profile"]["protein_effect"] == "lof"
    assert initial["review_readiness"]["status"] == "ready_for_evidence_review"
    assert not initial["review_readiness"].get("pending_request_ids")
    assert initial["final_classification_allowed"] is False
    assert initial["runtime_manifest"]["acmg_runtime_version"] == (
        "evidence-automation-4.3"
    )
    assert len(initial["runtime_manifest"]["ruleset_hash"]) == 64
    assert validate_guard_context(initial["guard_context"]) == (True, "")
    assert (
        initial["guard_context"]["ruleset_hash"]
        == initial["runtime_manifest"]["ruleset_hash"]
    )
    check_acmg_summary(initial)
    assert (
        len(
            json.dumps(
                initial["guard_context"],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        < 5_000
    )
    forbidden_card_fields = {
        "assessment_status",
        "suggested_criterion",
        "suggested_strength",
        "effective_strength",
    }
    assert all(
        forbidden_card_fields.isdisjoint(card) for card in initial["evidence_cards"]
    )
    assert initial["scenario_estimates"]
    assert all(
        "rule_execution_trace" not in scenario
        and scenario["rule_execution_trace_in"] == "full response scenario_estimates"
        for scenario in initial["scenario_estimates"]
    )

    proposed = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": [MECHANISM_PROPOSAL],
        }
    )
    assert all(
        "rule_execution_trace" in scenario
        for scenario in proposed["scenario_estimates"]
    )
    pvs1 = next(
        row
        for row in proposed["evidence_cards"]
        if row["criterion"] == "PVS1"
        and row["card_id"] in proposed["automatic_bayesian"]["included_card_ids"]
    )
    assert pvs1["strength"] == "PVS1"
    assert pvs1["calculation_roles"]["automatic"] is True
    assert pvs1["calculation_roles"]["verified"] is False
    assert pvs1["card_id"] in proposed["automatic_bayesian"]["included_card_ids"]
    assert pvs1["card_id"] not in proposed["verified_bayesian"]["included_card_ids"]
    assert proposed["review_readiness"]["status"] == "ready_for_evidence_review"
    assert not proposed["review_readiness"].get("pending_request_ids")
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
        verified_source_fact_ids=trusted,
        known_source_fact_ids=trusted,
    )
    blocked = guard_acmg_answer(
        "This variant is likely_pathogenic.",
        reviewed["evidence_cards"],
        verified_source_fact_ids=trusted,
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
@pytest.mark.parametrize("extra_literature", [0, 400])
async def test_compact_mcp_execute_tool_runs_acmg_collector_offline(
    extra_literature, check_acmg_summary
):
    from fastmcp import Client

    runtime = MCPGoldenToolUniverse()
    runtime.responses["PubMed_search_articles"]["data"] = [
        *runtime.responses["PubMed_search_articles"]["data"]["articles"],
    ]
    runtime.responses["PubMed_search_articles"]["data"].extend(
        [
            {
                "pmid": str(80000000 + i),
                "doi": f"10.0000/mcp-size-fixture-{i}",
                "title": "BRCA2 background fixture",
                "abstract": "General gene background only.",
            }
            for i in range(extra_literature)
        ]
    )
    server = SMCP(
        name="ACMG golden MCP",
        tooluniverse_config=runtime,
        compact_mode=True,
        search_enabled=False,
    )
    async with Client(server) as client:
        calls = ["ACMG_evidence_collector"]
        response = await client.call_tool(
            "execute_tool",
            {
                "tool_name": "ACMG_evidence_collector",
                "arguments": {**BASE_ARGUMENTS, "response_detail": "summary"},
            },
        )
        payload = _mcp_payload(response)
        size = check_acmg_summary(payload)
        if extra_literature:
            assert size > 40_000
            assert {str(80000000 + i) for i in range(extra_literature)} <= {
                row.get("pmid") for row in payload["literature_candidates"]
            }
        assert (
            len(json.dumps(payload["guard_context"], separators=(",", ":")).encode())
            < 5_000
        )
        calls.append("ACMG_guard_final_answer")
        guarded = await client.call_tool(
            "execute_tool",
            {
                "tool_name": "ACMG_guard_final_answer",
                "arguments": {
                    "final_answer_text": "BRCA2 evidence review; no final classification is issued.",
                    "guard_context": payload["guard_context"],
                },
            },
        )
        assert _mcp_payload(guarded)["status"] == "PASS"
        assert calls == ["ACMG_evidence_collector", "ACMG_guard_final_answer"]
    assert payload["execution_status"] == "success"
    assert payload["variant_identity"]["gene"] == "BRCA2"
    assert payload["runtime_manifest"]["collector_schema_version"] == (
        "2026-08-31-v4.3"
    )
    assert payload["final_classification_allowed"] is False
