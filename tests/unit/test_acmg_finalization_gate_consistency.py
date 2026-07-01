#!/usr/bin/env python3
"""Consistency tests for the canonical ACMG finalization gate."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate import evaluate_finalization_gate
from tooluniverse.acmg_gate.draft_policy import explain_why_final_blocked
from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.finalizer import issue_finalization_token
from tooluniverse.acmg_gate.session import session_can_finalize


def _valid_session() -> dict:
    return {
        "session_id": "s-valid",
        "state": "FINALIZED",
        "variant": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "classification": "Likely Pathogenic",
        "validator_status": "PASS",
        "semantic_combiner_status": "PASS",
        "final_classification_allowed": True,
        "counted_evidence": [{"criterion": "PS3", "strength": "Strong", "overlay_validated": True}],
        "required_next_actions": [],
        "completed_actions": ["literature_review"],
        "literature_status": "ready",
        "route_requirements": [],
    }


def _blocking_reasons_from_surfaces(session: dict) -> tuple[list[str], list[str], list[str]]:
    gate = evaluate_finalization_gate(session)
    assert session_can_finalize(session) is gate.can_finalize
    issued = issue_finalization_token(session)
    guarded = guard_acmg_final_answer(
        answer_text="ACMG分类：可能致病",
        session=session,
        finalization_token=None,
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    return (
        gate.blocking_reasons,
        issued["finalization_gate"]["blocking_reasons"],
        guarded["finalization_gate"]["blocking_reasons"],
    )


def test_invalid_session_has_consistent_gate_reasons() -> None:
    invalid_session = {
        "session_id": "s-invalid",
        "state": "DRAFT_ONLY",
        "validator_status": "DRAFT_ONLY",
        "semantic_combiner_status": "FAIL",
        "final_classification_allowed": False,
        "counted_evidence": [],
        "required_next_actions": ["literature_review"],
        "completed_actions": [],
        "literature_status": "not_reviewed",
    }

    gate_reasons, token_reasons, guard_reasons = _blocking_reasons_from_surfaces(invalid_session)
    assert gate_reasons == token_reasons == guard_reasons
    assert explain_why_final_blocked(invalid_session) == gate_reasons


def test_route_requirement_block_is_consistent() -> None:
    session = _valid_session()
    session["route_requirements"] = [
        {"route": "population_frequency", "status": "pending", "finalization_blocker": True}
    ]

    gate_reasons, token_reasons, guard_reasons = _blocking_reasons_from_surfaces(session)
    assert gate_reasons == token_reasons == guard_reasons
    assert "required ACMG routes are incomplete" in gate_reasons


def test_missing_counted_evidence_block_is_consistent() -> None:
    session = _valid_session()
    session["counted_evidence"] = []

    gate_reasons, token_reasons, guard_reasons = _blocking_reasons_from_surfaces(session)
    assert gate_reasons == token_reasons == guard_reasons
    assert "counted evidence is empty" in gate_reasons


def test_literature_status_block_is_consistent() -> None:
    session = _valid_session()
    session["literature_status"] = "not_reviewed"

    gate_reasons, token_reasons, guard_reasons = _blocking_reasons_from_surfaces(session)
    assert gate_reasons == token_reasons == guard_reasons
    assert "literature is not ready" in gate_reasons


def test_valid_session_token_and_matching_answer_pass_guard() -> None:
    session = _valid_session()
    issued = issue_finalization_token(session)
    assert issued["status"] == "PASS", issued

    result = guard_acmg_final_answer(
        answer_text="ACMG分类：可能致病",
        session=issued["acmg_session"],
        finalization_token=issued["acmg_finalization_token"],
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "PASS", result


def test_valid_token_mismatched_answer_label_blocks() -> None:
    session = _valid_session()
    issued = issue_finalization_token(session)
    assert issued["status"] == "PASS", issued

    result = guard_acmg_final_answer(
        answer_text="ACMG分类：致病",
        session=issued["acmg_session"],
        finalization_token=issued["acmg_finalization_token"],
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "BLOCK", result
    assert result["classification_binding_ok"] is False


if __name__ == "__main__":
    test_invalid_session_has_consistent_gate_reasons()
    test_route_requirement_block_is_consistent()
    test_missing_counted_evidence_block_is_consistent()
    test_literature_status_block_is_consistent()
    test_valid_session_token_and_matching_answer_pass_guard()
    test_valid_token_mismatched_answer_label_blocks()
    print("PASS test_acmg_finalization_gate_consistency")
