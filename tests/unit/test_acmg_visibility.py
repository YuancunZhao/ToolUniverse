"""Visibility does not promote incomplete, negated, or invalid evidence."""

from copy import deepcopy

import pytest

from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    _compact_result,
    _literature_review_state,
    _literature_values,
)
from tooluniverse.acmg.literature_extractor import extract_literature_facts
from tooluniverse.acmg.models import (
    EvidenceCard,
    evidence_cards_to_result,
    fact_is_strictly_verified,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "operation", ["population", "computational", "clinical", "functional", "literature"]
)
def test_public_groups_return_shared_invalid_card_diagnostics(monkeypatch, operation):
    """Every public evidence group uses the shared serialization boundary."""
    from tooluniverse.acmg_runtime_tools import ACMGEvidenceGroupTool

    card = EvidenceCard(
        criterion="PS3",
        strength="PS3_Unsupported",
        source_label="fixture",
        observed_facts={},
        rule_basis="fixture",
        source_fact_ids=["source-1"],
    )
    monkeypatch.setitem(
        ACMGEvidenceGroupTool._OPERATIONS, operation, lambda **_: [card]
    )
    result = ACMGEvidenceGroupTool({"fields": {"operation": operation}}).run({})
    assert result["evidence_cards"] == []
    assert (
        result["serialization_diagnostics"][0]["reason_code"] == "unsupported_strength"
    )


def test_summary_preserves_values_titles_and_explicit_review_states():
    """Compact output keeps clinical scalars and resolves shared observations."""
    full = {
        "consequence_profile": {"hgvs_p": "p.Arg1Gly"},
        "evidence_cards": [
            {
                "criterion": "PS4",
                "strength": "PS4",
                "card_id": "card-1",
                "observed_facts": {
                    "af": 0,
                    "controls_affected": False,
                    "unknown": None,
                    "odds_ratio": 9.2,
                    "ci": [2.1, 12.2],
                    "case_count": 4,
                    "consequence_profile": {"hgvs_p": "p.Arg1Gly"},
                    "full_text": "bulky article body",
                    "raw_payload": {"raw": "provider response"},
                    "exons": [1, 2],
                },
            }
        ],
        "literature_candidates": [
            {"pmid": "1", "title": "Variant study", "abstract": "text"}
        ],
        "criterion_reviews": [
            {
                "criterion": "PS4",
                "route_status": "insufficient_information",
                "evidence_status": "source_backed_candidate",
                "missing_requirements": ["independent controls"],
            }
        ],
    }
    original = deepcopy(full)
    compact = _compact_result(full)
    facts = compact["evidence_cards"][0]["observed_facts"]
    assert facts["af"] == 0 and facts["controls_affected"] is False
    assert facts["unknown"] is None
    assert facts["ci"] == [2.1, 12.2] and facts["case_count"] == 4
    assert facts["consequence_profile_in"] == "consequence_profile"
    assert "full_text" not in facts and "exons" not in facts
    assert "raw_payload" not in facts
    assert compact["literature_candidates"][0]["title"] == "Variant study"
    assert compact["literature_candidates"][0]["abstract_available"] is True
    assert compact["criterion_reviews"][0]["route_status"] == "insufficient_information"
    assert compact["criterion_reviews"][0]["missing_requirements"] == [
        "independent controls"
    ]
    assert "criterion_review_defaults" not in compact
    assert _compact_result(full) == compact and full == original


@pytest.mark.parametrize(
    "text,reason",
    [
        ("NM_000001.1:c.1A>G was not de novo in patient P1.", "negated_observation"),
        ("NM_000001.1:c.1A>G was de novo.", "minimum_facts_incomplete"),
    ],
)
def test_review_only_literature_is_visible_without_cards(text, reason):
    """Negative and incomplete atoms stay out of every scoring route."""
    identity = {"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"}
    candidates = [
        {
            "publication_id": "pmid:1",
            "pmid": "1",
            "match_class": "exact_variant_match",
            "abstract": text,
        }
    ]
    facts = extract_literature_facts(candidates, {}, identity=identity)
    assert facts
    assert all(f.features.get("extraction_review_only") for f in facts.values())
    assert not any(fact_is_strictly_verified(f) for f in facts.values())
    assert not _literature_values(facts, "de_novo")
    assert not ACMGEvidencePipeline._literature_proposal_cards(facts, {})
    review = _literature_review_state(
        candidates, facts, identity=identity, arguments={}
    )
    assert any(reason in row["reason_codes"] for row in review["fact_reviews"])
    full = {
        "literature_review": review,
        "source_facts": [f.to_dict() for f in facts.values()],
    }
    summary = _compact_result(full)
    assert summary["literature_review"]["fact_reviews"]
    assert {f.fact_id for f in facts.values()} <= {
        f["fact_id"] for f in summary["source_facts"]
    }


def test_methodology_skip_is_diagnostic_not_a_fact():
    """Technical uses of de novo must not generate PM6."""
    diagnostics = []
    facts = extract_literature_facts(
        [
            {
                "publication_id": "pmid:1",
                "pmid": "1",
                "match_class": "exact_variant_match",
                "abstract": "NM_000001.1:c.1A>G was identified by de novo transcript assembly.",
            }
        ],
        {},
        identity={"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"},
        diagnostics=diagnostics,
    )
    assert not facts
    assert any(
        row["reason_code"] == "methodological_false_positive" for row in diagnostics
    )


@pytest.mark.parametrize(
    "criterion,status,strength,reason",
    [
        ("PS3", "source_backed_candidate", "PS3_Unsupported", "unsupported_strength"),
        ("PS3", "excluded", "PS3_Unsupported", "unsupported_strength"),
        ("PS3", "invented", "PS3", "invalid_evidence_status"),
        ("PS3", "invented", "not_assessed", "invalid_evidence_status"),
        ("PS99", "excluded", "not_assessed", "invalid_criterion"),
    ],
)
def test_invalid_card_has_diagnostic_without_a_claim_id(
    criterion, status, strength, reason
):
    """Invalid strength never vanishes or becomes a selectable card."""
    result = evidence_cards_to_result(
        [
            EvidenceCard(
                criterion=criterion,
                strength=strength,
                source_fact_ids=["source-1"],
                evidence_status=status,
                source_label="fixture",
                observed_facts={},
                rule_basis="fixture",
            )
        ],
        known_source_fact_ids={"source-1"},
    )
    assert not result["evidence_cards"]
    assert result["serialization_diagnostics"] == [
        {
            "criterion": criterion,
            "strength": strength,
            "source_fact_ids": ["source-1"],
            "reason_code": reason,
            **(
                {"evidence_status": status}
                if reason == "invalid_evidence_status"
                else {}
            ),
        }
    ]
