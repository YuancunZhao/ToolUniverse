#!/usr/bin/env python3
"""Integration-level protocol checks preventing manual source-lead assignment."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.finalizer import issue_finalization_token
from tooluniverse.acmg_gate.session import create_acmg_session
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output
from tooluniverse.acmg_gate.transaction import add_required_actions_from_plan


def test_no_manual_assignment_pipeline() -> None:
    session = create_acmg_session(variant="NM_000142.5:c.1075+95C>G", gene="FGFR3")
    session.source_lead_sandbox.append(
        sandbox_source_output(
            tool_name="GeneBe_classify_variant",
            raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PM2", "PP3", "PS3"]},
            intent="ACMG_FINAL_CLASSIFICATION",
        )
    )
    session.source_lead_sandbox.append(
        sandbox_source_output(tool_name="gnomad_get_variant", raw_output={"AF": 0.0, "suggestion": "PM2"}, intent="ACMG_FINAL_CLASSIFICATION")
    )
    session.source_lead_sandbox.append(
        sandbox_source_output(tool_name="SpliceAI_predict_splice", raw_output={"DS_DG": 0.97, "interpretation": "pathogenic"}, intent="ACMG_FINAL_CLASSIFICATION")
    )
    session = create_acmg_session(variant=session.variant, gene=session.gene)
    session.source_lead_sandbox = [
        sandbox_source_output(tool_name="GeneBe_classify_variant", raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PM2", "PP3", "PS3"]}, intent="ACMG_FINAL_CLASSIFICATION"),
        sandbox_source_output(tool_name="gnomad_get_variant", raw_output={"AF": 0.0, "suggestion": "PM2"}, intent="ACMG_FINAL_CLASSIFICATION"),
        sandbox_source_output(tool_name="SpliceAI_predict_splice", raw_output={"DS_DG": 0.97, "interpretation": "pathogenic"}, intent="ACMG_FINAL_CLASSIFICATION"),
    ]
    session = type(session)(**add_required_actions_from_plan(session, {}))
    session.validator_status = "DRAFT_ONLY"
    session.semantic_combiner_status = "NOT_RUN"
    session.final_classification_allowed = False
    session.literature_status = "not_reviewed"

    assert all(row["acmg_countable_evidence"] is False for row in session.source_lead_sandbox)
    assert issue_finalization_token(session, classification="Likely Pathogenic")["status"] == "BLOCK"

    for text in (
        "ACMG分类：Likely Pathogenic",
        "PM2 from gnomAD absence, therefore likely pathogenic",
        "SpliceAI assigns PP3, therefore possibly pathogenic",
    ):
        result = guard_acmg_final_answer(text, session.__dict__, None, "ACMG_FINAL_CLASSIFICATION")
        assert result["status"] == "BLOCK", result


if __name__ == "__main__":
    test_no_manual_assignment_pipeline()
    print("PASS test_acmg_no_manual_assignment_pipeline")
