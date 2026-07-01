#!/usr/bin/env python3
"""Direct tests for mandatory ACMG final-answer post-guard."""

from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.finalizer import issue_finalization_token
from tooluniverse.acmg_gate.session import add_overlay_validated_evidence, create_acmg_session
from tooluniverse.acmg_overlay_gate_tool import ACMGOverlayGateTool


def _finalized_session(classification: str) -> dict:
    session = create_acmg_session(variant="NM_000142.5:c.1075+95C>G", gene="FGFR3")
    session = add_overlay_validated_evidence(session, {"criterion": "PM2", "strength": "supporting"})
    session.validator_status = "PASS"
    session.semantic_combiner_status = "PASS"
    session.final_classification_allowed = True
    session.literature_status = "reviewed"
    session.classification = classification
    issued = issue_finalization_token(session)
    assert issued["status"] == "PASS", issued
    return issued


def _blocked(text: str) -> None:
    result = guard_acmg_final_answer(
        answer_text=text,
        session={"state": "DRAFT_ONLY", "validator_status": "DRAFT_ONLY", "semantic_combiner_status": "NOT_RUN", "final_classification_allowed": False},
        finalization_token=None,
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "BLOCK", result


def test_final_answer_post_guard() -> None:
    for text in (
        "ACMG分类：Likely Pathogenic",
        "草稿分类：Likely Pathogenic",
        "倾向可能致病",
        "PM2 + PP3，因此可能致病",
        "Likely benign draft",
    ):
        _blocked(text)

    for text in ("P value", "B cell", "LP score", "致病机制", "良性肿瘤", "pathogenic bacteria"):
        result = guard_acmg_final_answer(text, None, None, None)
        assert result["status"] == "PASS", result

    issued = _finalized_session("VUS")
    result = guard_acmg_final_answer(
        "ACMG classification: VUS",
        issued["acmg_session"],
        issued["acmg_finalization_token"],
        "ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "PASS", result


def _guard_with_token(answer: str, classification: str) -> dict:
    issued = _finalized_session(classification)
    return guard_acmg_final_answer(
        answer,
        issued["acmg_session"],
        issued["acmg_finalization_token"],
        "ACMG_FINAL_CLASSIFICATION",
    )


def test_final_answer_classification_binding_cases() -> None:
    cases = (
        ("Likely Pathogenic", "ACMG classification: Likely Pathogenic", "PASS"),
        ("Likely Pathogenic", "ACMG classification: Pathogenic", "BLOCK"),
        ("Likely Pathogenic", "ACMG分类：可能致病", "PASS"),
        ("Likely Pathogenic", "ACMG分类：致病", "BLOCK"),
        ("VUS", "ACMG分类：临床意义不明", "PASS"),
        ("Likely Benign", "ACMG分类：可能良性", "PASS"),
        ("Likely Benign", "ACMG分类：良性", "BLOCK"),
        ("Likely Pathogenic", "ACMG classification: Likely Pathogenic, but could be Pathogenic", "BLOCK"),
    )
    for token_classification, answer, expected_status in cases:
        result = _guard_with_token(answer, token_classification)
        assert result["status"] == expected_status, result
        assert result["detected_final_labels"], result
        assert result["session_classification"] == token_classification, result
        if expected_status == "PASS":
            assert result["classification_binding_ok"] is True, result
        else:
            assert result["classification_binding_ok"] is False, result


def test_final_answer_false_positives_remain_allowed() -> None:
    for text in ("P value", "B cell", "LP score", "致病机制", "良性肿瘤", "pathogenic bacteria"):
        result = guard_acmg_final_answer(text, None, None, None)
        assert result["status"] == "PASS", result
        assert result["detected_final_labels"] == [], result


def test_guard_final_answer_tool_callsite_enforces_binding() -> None:
    issued = _finalized_session("Likely Pathogenic")
    tool = ACMGOverlayGateTool(
        {"name": "ACMG_guard_final_answer", "type": "ACMGOverlayGateTool", "fields": {"operation": "guard_final_answer"}}
    )
    result = tool.run(
        {
            "answer": "ACMG classification: Pathogenic",
            "harness_result": issued["acmg_session"],
            "finalization_token": issued["acmg_finalization_token"],
            "intent": "ACMG_FINAL_CLASSIFICATION",
        }
    )
    assert result["status"] == "FAIL", result
    assert result["final_answer_guard"]["status"] == "BLOCK", result
    assert result["final_answer_guard"]["classification_binding_ok"] is False, result


if __name__ == "__main__":
    test_final_answer_post_guard()
    test_final_answer_classification_binding_cases()
    test_final_answer_false_positives_remain_allowed()
    test_guard_final_answer_tool_callsite_enforces_binding()
    print("PASS test_acmg_final_answer_post_guard")
