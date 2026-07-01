#!/usr/bin/env python3
"""Receipt and provenance tests for ACMG route completion."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.provenance import complete_step, make_evidence_provenance, make_tool_call_receipt


def test_complete_step_accepts_inner_tool_receipts() -> None:
    session = {
        "session_id": "s1",
        "route_requirements": [{"route": "variant_normalization", "status": "pending", "finalization_blocker": True}],
        "completed_actions": [],
    }
    receipt = make_tool_call_receipt(
        call_id="call-1",
        outer_tool="mcp__tooluniverse__execute_tool",
        inner_tool="VariantValidator_validate_variant",
        route="variant_normalization",
        status="success",
        inputs={"variant": "NM_000142.5:c.1075+95C>G"},
        output={"normalized": True},
    )
    result = complete_step(session, route="variant_normalization", inner_tool="VariantValidator_validate_variant", receipt=receipt)
    assert result["status"] == "PASS", result
    completed = result["acmg_session"]["completed_actions"]
    assert "variant_normalization" in completed
    route = result["acmg_session"]["route_requirements"][0]
    assert route["status"] == "completed"
    assert route["finalization_blocker"] is False


def test_literature_access_levels_are_distinct() -> None:
    abstract = make_evidence_provenance(
        evidence_id="pmid-1",
        source_type="pubmed",
        source_name="PubMed",
        pmid="34162030",
        route="literature_discovery",
        access_level="abstract_only",
        review_status="screened",
    )
    full_text = make_evidence_provenance(
        evidence_id="pmc-1",
        source_type="pmc_full_text_xml",
        source_name="PMC",
        pmid="34162030",
        route="literature_deep_review",
        access_level="full_text_xml",
        review_status="reviewed",
    )
    blocked = make_evidence_provenance(
        evidence_id="publisher-1",
        source_type="publisher_html",
        source_name="Publisher",
        url="https://example.test/article",
        route="literature_deep_review",
        access_level="blocked",
        review_status="blocked",
    )
    assert abstract["access_level"] == "abstract_only"
    assert full_text["access_level"] == "full_text_xml"
    assert blocked["access_level"] == "blocked"
    assert abstract["counted"] is False


if __name__ == "__main__":
    test_complete_step_accepts_inner_tool_receipts()
    test_literature_access_levels_are_distinct()
    print("PASS test_acmg_provenance")
