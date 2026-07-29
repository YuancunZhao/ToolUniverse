"""Public literature evidence tool contract."""

from __future__ import annotations

from tooluniverse.tools.ACMG_literature_evidence import ACMG_literature_evidence


def test_literature_group_tool_returns_review_only_card_for_structured_inputs():
    result = ACMG_literature_evidence(
        case_control_facts=[
            {
                "fact_id": "review-only-1",
                "section_locator": "table-1",
                "variant_identity": "NM_000142.5:c.1075+95C>G",
                "gene": "FGFR3",
                "case_count": 5,
                "control_count": 100,
                "odds_ratio": 2.0,
                "ci_lower": 0.8,
                "phenotype_consistent": True,
                "cases_independent": True,
                }
        ],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )

    by_criterion = {row["criterion"]: row for row in result["evidence_cards"]}
    assert {"PS4"}.issubset(by_criterion)
    assert by_criterion["PS4"]["system_preview_included"] is False
