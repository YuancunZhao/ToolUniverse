#!/usr/bin/env python3
"""Direct tests for the ACMG assessment session state machine."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.finalizer import issue_finalization_token
from tooluniverse.acmg_gate.session import (
    add_overlay_validated_evidence,
    add_route_candidate,
    add_source_lead,
    create_acmg_session,
    mark_completed_action,
    mark_required_action,
    session_can_emit_final_label,
    session_can_finalize,
)


def test_session_state_machine() -> None:
    session = create_acmg_session(variant="NM_000142.5:c.1075+95C>G", gene="FGFR3")
    assert session.state == "DRAFT_ONLY"

    session = add_source_lead(session, {"tool_name": "GeneBe", "classification": "Likely_pathogenic"})
    assert session.source_lead_sandbox[0]["counted"] is False
    assert session.counted_evidence == []

    session = add_route_candidate(session, {"route": "pm2_absence_rarity", "suggested_criterion": "PM2"})
    assert session.route_candidates[0]["counted"] is False

    session = mark_required_action(session, "pm2_absence_rarity")
    assert session_can_finalize(session) is False

    session = mark_completed_action(session, "pm2_absence_rarity")
    session = add_overlay_validated_evidence(session, {"criterion": "PM2", "strength": "supporting"})
    session.validator_status = "PASS"
    session.semantic_combiner_status = "PASS"
    session.final_classification_allowed = True
    session.literature_status = "reviewed"
    session.classification = "VUS"
    assert session_can_finalize(session) is True

    token = issue_finalization_token(session)
    assert token["status"] == "PASS"
    finalized = token["acmg_session"]
    assert session_can_emit_final_label(finalized) is True


if __name__ == "__main__":
    test_session_state_machine()
    print("PASS test_acmg_session_state_machine")
