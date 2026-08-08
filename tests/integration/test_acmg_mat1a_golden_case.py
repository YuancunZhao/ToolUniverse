"""Offline MAT1A golden path for broad/strict evidence and literature overlap."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.guard import validate_guard_context


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "acmg" / "mat1a_r249q.json"
)
BASE_ARGUMENTS = {
    "variant": "NM_000429.3:c.746G>A",
    "gene": "MAT1A",
    "transcript": "NM_000429.3",
    "disease": "Hypermethioninemia / MAT1A deficiency",
    "inheritance": "autosomal dominant",
}


class MAT1AProviderFixture:
    """Serve frozen provider and document results without network access."""

    def __init__(self):
        self.responses = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.calls: list[dict[str, Any]] = []

    def _document(self, call: dict[str, Any]) -> Any | None:
        name = str(call.get("name") or "")
        arguments = call.get("arguments") or {}
        identifier = str(
            arguments.get("pmid")
            or arguments.get("article_id")
            or arguments.get("pmcid")
            or ""
        )
        identifier = {
            "PMC5004716": "26933843",
            "PMC5512230": "28748147",
        }.get(identifier, identifier)
        documents = self.responses["documents"]
        if name == "EuropePMC_get_full_text" and identifier == "26933843":
            return {"status": "error", "error": "structured XML unavailable"}
        if name in {"EuropePMC_get_full_text", "EuropePMC_get_fulltext"}:
            return deepcopy(documents.get(identifier))
        return None

    def run_one_function(self, call: dict[str, Any], **_kwargs: Any) -> Any:
        self.calls.append(deepcopy(call))
        document = self._document(call)
        if document is not None:
            return document
        name = str(call.get("name") or "")
        if name in self.responses and name != "documents":
            return deepcopy(self.responses[name])
        return {"status": "unavailable", "reason": "MAT1A fixture has no result"}

    def run_many_functions(
        self,
        calls: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[Any]:
        return [self.run_one_function(call, **kwargs) for call in calls]


def _proposal(
    *,
    fact_id: str,
    fact_type: str,
    pmid: str,
    pmcid: str,
    excerpt: str,
    values: dict[str, Any],
    field_excerpts: dict[str, str],
    criterion: str,
    strength: str,
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "pmid": pmid,
        "pmcid": pmcid,
        "locator": "results",
        "excerpt": excerpt,
        "variant_identity": BASE_ARGUMENTS["variant"],
        "gene": BASE_ARGUMENTS["gene"],
        "values": {
            "variant_identity": BASE_ARGUMENTS["variant"],
            "gene": BASE_ARGUMENTS["gene"],
            "disease": BASE_ARGUMENTS["disease"],
            "inheritance": BASE_ARGUMENTS["inheritance"],
            **values,
        },
        "field_excerpts": field_excerpts,
        "criterion": criterion,
        "suggested_strength": strength,
        "interpretation": f"The source supports a review proposal for {criterion}.",
        "confidence": 0.82,
        "questions": ["Confirm disease-specific strength before final adoption."],
        "extractor": {"name": "mat1a-golden-llm", "version": "1.0"},
        "reading_manifest": {
            "status": "complete",
            "sections_read": ["results"],
            "tables_read": [],
            "figures_read": [],
            "supplements_read": [],
            "variant_match_locations": ["results"],
            "limitations": [],
        },
    }


KIM_EXCERPT = (
    "MAT1A NM_000429.3:c.746G>A p.Arg249Gln was observed in 4 independent "
    "probands."
)
MURIELLO_EXCERPT = (
    "MAT1A NM_000429.3:c.746G>A p.Arg249Gln was reported in 6 patients"
)

PROPOSALS = [
    _proposal(
        fact_id="kim-2016-case-series",
        fact_type="case_series",
        pmid="26933843",
        pmcid="PMC5004716",
        excerpt=KIM_EXCERPT,
        values={
            "case_count": 4,
            "cases_independent": True,
            "phenotype_consistency": "consistent",
            "cohort_id": "mat1a-r249q-published-cases",
        },
        field_excerpts={
            "case_count": "observed in 4 independent probands",
            "cases_independent": "cases_independent true",
            "phenotype_consistency": "phenotype consistency consistent",
            "cohort_id": "cohort mat1a-r249q-published-cases",
        },
        criterion="PS4",
        strength="PS4_Supporting",
    ),
    _proposal(
        fact_id="muriello-2017-overlapping-series",
        fact_type="case_series",
        pmid="28748147",
        pmcid="PMC5512230",
        excerpt=MURIELLO_EXCERPT,
        values={
            "case_count": 6,
            "cases_independent": True,
            "phenotype_consistency": "consistent",
            "cohort_id": "mat1a-r249q-published-cases",
        },
        field_excerpts={
            "case_count": "reported in 6 patients",
            "cases_independent": "cases_independent true",
            "phenotype_consistency": "phenotype consistency consistent",
            "cohort_id": "cohort mat1a-r249q-published-cases",
        },
        criterion="PS4",
        strength="PS4_Supporting",
    ),
    _proposal(
        fact_id="kim-2016-segregation",
        fact_type="segregation",
        pmid="26933843",
        pmcid="PMC5004716",
        excerpt="family mat1a-r249q-two-families. segregation direction segregates",
        values={
            "family_id": "mat1a-r249q-two-families",
            "segregation_direction": "segregates",
            "informative_meioses": 2,
            "phenotype_consistency": "consistent",
            "cohort_id": "mat1a-r249q-published-cases",
        },
        field_excerpts={
            "family_id": "family mat1a-r249q-two-families",
            "segregation_direction": "segregation direction segregates",
            "informative_meioses": "2 informative meioses",
            "phenotype_consistency": "phenotype consistency consistent",
            "cohort_id": "cohort mat1a-r249q-published-cases",
        },
        criterion="PP1",
        strength="PP1_Supporting",
    ),
    _proposal(
        fact_id="kim-2016-dimer-interface",
        fact_type="region_hotspot",
        pmid="26933843",
        pmcid="PMC5004716",
        excerpt="Protein region dimer interface. pathogenic enrichment true",
        values={
            "protein_region": "dimer interface",
            "pathogenic_enrichment": True,
            "benign_variation_depleted": True,
        },
        field_excerpts={
            "protein_region": "Protein region dimer interface",
            "pathogenic_enrichment": "pathogenic enrichment true",
            "benign_variation_depleted": "benign variation depleted true",
        },
        criterion="PM1",
        strength="PM1_Supporting",
    ),
]


def test_mat1a_broad_and_validated_evidence_workflow():
    """The MAT1A fixture emits traceable candidates without false paper inflation."""
    fixture = MAT1AProviderFixture()
    initial = ACMGEvidencePipeline(fixture).run(
        {**BASE_ARGUMENTS, "response_detail": "summary"}
    )

    candidates = initial["literature_candidates"]
    assert {row["pmid"] for row in candidates} == {"26933843", "28748147"}
    assert len(candidates) == 2
    assert all(
        row["match_class"]
        in {
            "exact_variant_match",
            "equivalent_variant_match",
            "provider_linked_variant_match",
        }
        for row in candidates
    )

    reviewed = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": PROPOSALS,
        }
    )
    by_criterion: dict[str, list[dict[str, Any]]] = {}
    for card in reviewed["evidence_cards"]:
        by_criterion.setdefault(str(card["criterion"]), []).append(card)

    assert len(by_criterion["PS4"]) == 2
    pp1 = next(card for card in by_criterion["PP1"] if card["suggested_strength"])
    pm1 = next(card for card in by_criterion["PM1"] if card["suggested_strength"])
    assert pp1["suggested_strength"] == "PP1_Supporting"
    assert pm1["suggested_strength"] == "PM1_Supporting"
    pm2 = by_criterion["PM2"][0]
    assert pm2["strength"] == "indeterminate"
    assert pm2["suggested_strength"] == "PM2_Supporting"
    assert pm2["verification_status"] == "unresolved"
    assert pm2["system_preview_included"] is True
    assert pm2["validated_subset_included"] is False

    overlap_reasons = {
        row["reason"]
        for row in reviewed["compatibility_report"]["excluded_evidence"]
    }
    assert overlap_reasons.intersection(
        {
            "overlapping_cases",
            "overlapping_clinical_case",
            "overlapping_cohort",
            "duplicate_criterion",
        }
    )
    assert reviewed["system_preview_bayesian"]["estimate_policy"] == (
        "source_backed_candidates"
    )
    assert reviewed["validated_subset_bayesian"]["estimate_policy"] == (
        "validated_subset"
    )
    assert set(reviewed["validated_subset_bayesian"]["included_card_ids"]) < set(
        reviewed["system_preview_bayesian"]["included_card_ids"]
    )

    predictors = reviewed["predictor_scores"]
    for field in (
        "revel_score",
        "alphamissense_score",
        "sift_score",
        "metarnn_score",
        "vest4_score",
        "mutationtaster_prediction",
    ):
        assert field in predictors
    splice = predictors["spliceai"]
    assert splice["profile"]["max_delta_score"] == 0.15
    assert {
        "DS_AG",
        "DS_AL",
        "DS_DG",
        "DS_DL",
    } <= set(splice["scores"][0])
    computational = by_criterion["PP3/BP4"]
    assert all(card["proposal_status"] == "not_suggested" for card in computational)
    assert all(card["system_preview_included"] is False for card in computational)

    html_fact = next(
        fact
        for fact in reviewed["source_facts"]
        if fact.get("features", {}).get("submitted_fact_id") == "kim-2016-case-series"
    )
    assert html_fact["features"]["document_source_tool"] == "EuropePMC_get_fulltext"
    assert html_fact["features"]["document_source"] == "NCBI PMC HTML"
    assert reviewed["guard_context"]["cards"]
    assert validate_guard_context(reviewed["guard_context"]) == (True, "")
    assert reviewed["final_classification_allowed"] is False

    summary = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "summary",
            "literature_proposals": PROPOSALS,
        }
    )
    assert len(json.dumps(summary, ensure_ascii=False, separators=(",", ":"))) < 50_000


def test_mat1a_source_backed_pm2_can_be_user_selected_without_reviewer():
    """Optional reviewer metadata cannot block source-backed user selection."""
    fixture = MAT1AProviderFixture()
    proposed = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": PROPOSALS,
        }
    )
    pm2 = next(card for card in proposed["evidence_cards"] if card["criterion"] == "PM2")
    selected = ACMGEvidencePipeline(fixture).run(
        {
            **BASE_ARGUMENTS,
            "response_detail": "full",
            "literature_proposals": PROPOSALS,
            "evidence_decisions": [
                {"card_id": pm2["card_id"], "decision": "accept"}
            ],
        }
    )

    assert selected["decision_report"]["decision_errors"] == []
    assert selected["user_selected_bayesian"]["included_card_ids"] == [
        pm2["card_id"]
    ]
