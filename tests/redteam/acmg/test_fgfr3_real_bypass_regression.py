#!/usr/bin/env python3
"""Red-team regression for the observed FGFR3 ACMG runtime bypass."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.final_label_detector import manual_acmg_counting_matches
from tooluniverse.acmg_gate.runtime_integration import (
    after_tool_call,
    before_final_answer,
    before_tool_call,
    route_user_message_before_agent,
)
from tooluniverse.acmg_gate.session import evaluate_finalization_gate, is_acmg_finalization_blocked
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output


FIXTURE = Path(__file__).with_name("fixtures") / "fgfr3_real_bypass_transcript.md"


def _fgfr3_draft_session() -> dict:
    return {
        "session_id": "fgfr3-real-bypass",
        "intent": "ACMG_FINAL_CLASSIFICATION",
        "state": "DRAFT_ONLY",
        "variant": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "effect_type": "deep_intronic",
        "classification_status": "draft classification",
        "validator_status": "DRAFT_ONLY",
        "semantic_combiner_status": "NOT_RUN",
        "final_classification_allowed": False,
        "literature_status": "not_reviewed",
        "required_next_actions": [
            "pm2_absence_rarity",
            "pp3_bp4_splicing_prediction",
            "pvs1_splicing_refinement",
            "literature_review",
        ],
        "completed_actions": [],
        "source_lead_sandbox": [
            sandbox_source_output(
                tool_name="GeneBe_classify_variant",
                raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3", "PP5"]},
                intent="ACMG_FINAL_CLASSIFICATION",
            ),
            sandbox_source_output(
                tool_name="SpliceAI_get_max_delta",
                raw_output={"max_delta": 0.97, "interpretation": "damaging splice donor gain"},
                intent="ACMG_FINAL_CLASSIFICATION",
            ),
            sandbox_source_output(
                tool_name="PubMed_search_articles",
                raw_output={"pmid": "34162030", "abstract": "functional and case report evidence"},
                intent="ACMG_FINAL_CLASSIFICATION",
            ),
        ],
        "counted_evidence": [
            {
                "criterion": "PS3",
                "source_name": "PubMed",
                "source_type": "literature",
                "access_level": "abstract",
                "overlay_validated": False,
            },
            {
                "criterion": "PP3",
                "tool_name": "SpliceAI_get_max_delta",
                "source_lead_only": True,
                "acmg_countable_evidence": False,
            },
        ],
    }


def test_fgfr3_real_bypass_transcript_is_workflow_failure() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    session = _fgfr3_draft_session()

    gate = evaluate_finalization_gate(session)
    blocked = is_acmg_finalization_blocked(session)
    guard = guard_acmg_final_answer(text, session, None, "ACMG_FINAL_CLASSIFICATION")

    assert gate.can_finalize is False
    assert blocked["status"] == "BLOCK"
    assert guard["status"] == "BLOCK"
    assert guard["has_final_label"] is True
    assert guard["has_manual_acmg_counting"] is True
    assert manual_acmg_counting_matches(text)
    assert "required overlay actions are incomplete" in gate.blocking_reasons
    assert "classification status is draft/provisional" in gate.blocking_reasons
    assert "counted evidence is not overlay-validated" in gate.blocking_reasons
    assert any(row.get("required_action") == "literature_review" for row in gate.blocking_route_requirements)
    assert any(row.get("diagnostics", {}).get("code") == "literature_deep_review_missing" for row in gate.blocking_route_requirements)
    assert any(row.get("diagnostics", {}).get("code") == "spliceai_max_delta_shortcut_blocked" for row in gate.blocking_route_requirements)


def test_runtime_blocks_no_tool_and_genebe_first_paths() -> None:
    routed = route_user_message_before_agent("根据ACMG规则评估FGFR3 NM_000142.5:c.1075+95C>G 是否致病")
    state = routed["runtime_state"]
    assert routed["allow_direct_answer"] is False
    assert routed["guard_required"] is True

    direct = before_final_answer("ACMG分类：Likely Pathogenic", state)
    assert direct["action"] == "block"

    genebe_first = before_tool_call("GeneBe_classify_variant", {"variant": "FGFR3 c.1075+95C>G"}, state)
    assert genebe_first["action"] == "reroute"
    assert genebe_first["reroute_to"] == "ACMG_overlay_gate_assess_variant"

    state = after_tool_call("ACMG_overlay_gate_assess_variant", {"acmg_session": _fgfr3_draft_session()}, state)["runtime_state"]
    final_like_draft = before_final_answer("草稿分类：Likely Pathogenic，PM2 + PP3 支持。", state)
    assert final_like_draft["action"] == "block"
    assert final_like_draft["answer_text"]["status"] == "DRAFT_ONLY"


if __name__ == "__main__":
    test_fgfr3_real_bypass_transcript_is_workflow_failure()
    test_runtime_blocks_no_tool_and_genebe_first_paths()
    print("PASS test_fgfr3_real_bypass_regression")
