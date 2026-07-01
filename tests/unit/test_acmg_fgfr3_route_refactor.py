#!/usr/bin/env python3
"""FGFR3 transcript-derived route/refactor regression tests."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.finalizer import issue_finalization_token
from tooluniverse.acmg_gate.provenance import complete_step, make_tool_call_receipt
from tooluniverse.acmg_gate.route_policy import determine_required_routes
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output


VARIANT_CONTEXT = {
    "gene": "FGFR3",
    "variant": "NM_000142.5:c.1075+95C>G",
    "effect_type": "intronic",
    "transcript": "NM_000142.5",
}

USER_CONTEXT = {
    "phenotype": ["short stature", "prenatal long bone shortening"],
    "family_history": "mother and maternal grandmother have similar symptoms",
    "confirmed_relative_genotypes": False,
}


def test_fgfr3_full_transcript_no_final_without_token() -> None:
    result = guard_acmg_final_answer(
        answer_text="最终分类：ACMG分类：Likely Pathogenic（可能致病）",
        session={"state": "DRAFT_ONLY", "validator_status": "DRAFT_ONLY", "semantic_combiner_status": "NOT_RUN", "final_classification_allowed": False},
        finalization_token=None,
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "BLOCK", result


def test_fgfr3_genebe_criteria_quarantined() -> None:
    genebe = sandbox_source_output(
        tool_name="GeneBe_classify_variant",
        raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3_Moderate", "PP5"]},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert genebe["quarantined_conclusions"]["acmg_classification"] == "Likely_pathogenic"
    assert all(row["counted"] is False for row in genebe["candidate_routes"])


def test_fgfr3_pp1_not_counted_without_relative_genotypes() -> None:
    routes = determine_required_routes(
        session={},
        user_context=USER_CONTEXT,
        variant_context=VARIANT_CONTEXT,
    )
    segregation = next(row for row in routes if row["route"] == "segregation_de_novo_review")
    assert segregation["diagnostics"]["confirmed_relative_genotypes"] is False
    assert segregation["route_candidates"][0]["suggested_criterion"] == "PP1"
    assert segregation["route_candidates"][0]["counted"] is False
    assert segregation["route_candidates"][0]["required_action"] == "test_relatives_for_variant"


def test_fgfr3_pp4_can_count_only_through_phenotype_review() -> None:
    routes = determine_required_routes(session={}, user_context=USER_CONTEXT, variant_context=VARIANT_CONTEXT)
    phenotype = next(row for row in routes if row["route"] == "phenotype_specificity_review")
    assert phenotype["route_candidates"][0]["suggested_criterion"] == "PP4"
    assert phenotype["route_candidates"][0]["counted"] is False
    assert phenotype["route_candidates"][0]["requires_overlay_validation"] is True


def test_complete_step_accepts_inner_tool_receipts() -> None:
    session = {"session_id": "fgfr3", "route_requirements": [{"route": "variant_normalization", "status": "pending", "finalization_blocker": True}]}
    receipt = make_tool_call_receipt(
        call_id="call-vv",
        outer_tool="mcp__tooluniverse__execute_tool",
        inner_tool="VariantValidator_validate_variant",
        route="variant_normalization",
        status="success",
    )
    result = complete_step(session, route="variant_normalization", receipt=receipt, inner_tool="VariantValidator_validate_variant")
    assert result["status"] == "PASS", result


def test_spliceai_conflicting_outputs_require_review() -> None:
    routes = determine_required_routes(
        session={},
        source_leads=[
            {"tool_name": "SpliceAI_get_max_delta", "score": 0.0},
            {"tool_name": "SpliceAI_predict_splice", "DS_DG": 0.97, "predicted_splice_event_type": "donor gain"},
        ],
        variant_context=VARIANT_CONTEXT,
    )
    computational = next(row for row in routes if row["route"] == "computational_prediction")
    assert computational["status"] == "pending"
    assert computational["finalization_blocker"] is True


def test_finalizer_blocks_if_required_routes_pending() -> None:
    session = {
        "session_id": "fgfr3-finalizer",
        "intent": "ACMG_FINAL_CLASSIFICATION",
        "state": "READY_FOR_FINALIZER",
        "variant": VARIANT_CONTEXT["variant"],
        "gene": "FGFR3",
        "classification": "VUS",
        "validator_status": "PASS",
        "semantic_combiner_status": "PASS",
        "final_classification_allowed": True,
        "literature_status": "ready",
        "counted_evidence": [{"criterion": "PM2", "strength": "supporting", "overlay_validated": True}],
        "required_next_actions": [],
        "completed_actions": [],
        "route_requirements": [
            {"route": "population_frequency", "status": "pending", "finalization_blocker": True},
            {"route": "computational_prediction", "status": "pending", "finalization_blocker": True},
        ],
    }
    result = issue_finalization_token(session)
    assert result["status"] == "BLOCK", result
    assert "required ACMG routes are incomplete" in result["blocking_reasons"]


if __name__ == "__main__":
    test_fgfr3_full_transcript_no_final_without_token()
    test_fgfr3_genebe_criteria_quarantined()
    test_fgfr3_pp1_not_counted_without_relative_genotypes()
    test_fgfr3_pp4_can_count_only_through_phenotype_review()
    test_complete_step_accepts_inner_tool_receipts()
    test_spliceai_conflicting_outputs_require_review()
    test_finalizer_blocks_if_required_routes_pending()
    print("PASS test_acmg_fgfr3_route_refactor")
