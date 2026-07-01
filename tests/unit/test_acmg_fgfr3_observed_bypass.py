#!/usr/bin/env python3
"""Regression for observed FGFR3 agent-level manual ACMG bypass."""

from tooluniverse.acmg_gate.draft_policy import build_draft_only_response
from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.session import create_acmg_session
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output
from tooluniverse.acmg_gate.transaction import add_required_actions_from_plan


def test_fgfr3_observed_bypass() -> None:
    session = create_acmg_session(variant="NM_000142.5:c.1075+95C>G", gene="FGFR3", transcript="NM_000142.5")
    for tool_name, raw in (
        ("GeneBe_classify_variant", {"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3_Moderate", "PP5"]}),
        ("SpliceAI_predict_splice", {"DS_DG": 0.97, "predicted_splice_event_type": "donor gain"}),
        ("EnsemblVEP_annotate_hgvs", {"consequence": "intron_variant"}),
        ("ClinGen_search_gene_validity", {"gene": "FGFR3", "validity": "definitive"}),
        ("literature_search", {"hit_count": 8, "literature_status": "not_reviewed"}),
    ):
        session.source_lead_sandbox.append(sandbox_source_output(tool_name=tool_name, raw_output=raw, intent="ACMG_FINAL_CLASSIFICATION"))
    session = create_acmg_session(**{k: getattr(session, k) for k in ("variant", "gene", "transcript")})
    session.source_lead_sandbox = [
        sandbox_source_output(tool_name="GeneBe_classify_variant", raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3_Moderate", "PP5"]}, intent="ACMG_FINAL_CLASSIFICATION"),
        sandbox_source_output(tool_name="SpliceAI_predict_splice", raw_output={"DS_DG": 0.97, "predicted_splice_event_type": "donor gain"}, intent="ACMG_FINAL_CLASSIFICATION"),
        sandbox_source_output(tool_name="literature_search", raw_output={"hit_count": 8, "literature_status": "not_reviewed"}, intent="ACMG_FINAL_CLASSIFICATION"),
    ]
    session = type(session)(**add_required_actions_from_plan(session, {"required_next_actions": ["pm2_absence_rarity", "pp3_bp4_splicing_prediction", "literature_review"]}))
    session.validator_status = "DRAFT_ONLY"
    session.final_classification_allowed = False
    session.counted_evidence = []
    session.literature_status = "not_reviewed"

    bad = "ACMG分类：Likely Pathogenic。证据：PM2 Moderate + PP3 Supporting，PS3 来自 GeneBe。"
    result = guard_acmg_final_answer(bad, session.__dict__, None, "ACMG_FINAL_CLASSIFICATION")
    assert result["status"] == "BLOCK", result

    draft = build_draft_only_response(session)
    assert draft["status"] == "DRAFT_ONLY"
    assert draft["final_classification_allowed"] is False
    assert "Likely Pathogenic" not in str(draft["allowed_sections"])


if __name__ == "__main__":
    test_fgfr3_observed_bypass()
    print("PASS test_acmg_fgfr3_observed_bypass")
