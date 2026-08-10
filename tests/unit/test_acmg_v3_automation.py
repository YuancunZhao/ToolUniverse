from __future__ import annotations

from copy import deepcopy

from tooluniverse.acmg.collector import (
    _apply_evidence_decisions,
    _clinical_observation_facts,
    _normalize_clinical_observations,
)
from tooluniverse.acmg.clinical import clinical_evidence
from tooluniverse.acmg.cspec import _deterministic_text_contract
from tooluniverse.acmg.literature_extractor import extract_literature_facts
from tooluniverse.acmg.models import (
    SourceFact,
    fact_is_strictly_verified,
    is_automatic_evidence,
    is_verified_evidence,
)
from tooluniverse.acmg.vcep import parse_vcep_assertions
from tooluniverse.acmg.rule_catalog import ACMG_CRITERIA, criterion_use_matrix
from tooluniverse.acmg.scenario_engine import (
    build_scenario_results,
    evaluate_cspec_criterion,
)


def _fact(
    fact_id: str,
    *,
    tool_name: str,
    features: dict,
    request_arguments: dict | None = None,
) -> SourceFact:
    return SourceFact(
        fact_id=fact_id,
        tool_name=tool_name,
        status="success",
        query_identity={"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"},
        result_identity={"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"},
        features=features,
        raw_result_hash=f"hash-{fact_id}",
        provider_version="2026-08-08",
        request_arguments=request_arguments or {},
        provenance=(fact_id,),
        identity_status="matched",
        source_status="available",
        extraction_status="structured",
        version_status="versioned",
        disease_match_status="matched",
        independence_status="independent",
    )


def _vcep_row(*, version: str, assertion: str, disease: str = "MONDO:0000001"):
    return {
        "Variation": "NM_000001.1:c.1A>G",
        "ClinVar Variation Id": "123",
        "CAID": "CA123",
        "HGVS": ["NM_000001.1:c.1A>G"],
        "Assertion": assertion,
        "Expert Panel": "TEST VCEP",
        "Disease": "Test disease",
        "Mondo Id": disease,
        "MOI": "autosomal dominant",
        "Version": version,
        "Release Date": f"2026-0{version}.01",
        "Status": "Released",
        "Applied Criteria": [
            {
                "criterion": "PM2",
                "strength": "Supporting",
                "status": "Met",
                "evidenceSummary": "Absent from the matched population dataset.",
                "pmids": ["12345678"],
            }
        ],
    }


def test_vcep_exact_match_uses_latest_release_and_expands_applied_criteria():
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={
            "variant_classifications": [
                _vcep_row(version="1", assertion="VUS"),
                _vcep_row(version="2", assertion="Likely Pathogenic"),
            ]
        },
    )
    context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={
            "gene": "TEST",
            "validated_hgvs_c": "NM_000001.1:c.1A>G",
            "variation_id": "123",
        },
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )

    assert context["status"] == "exact_assertion_found"
    assert len(context["history"]) == 2
    assert assertions[0]["classification"] == "Likely Pathogenic"
    assert assertions[0]["external_assertion_only"] is True
    assert len(cards) == 1
    assert cards[0].criterion == "PM2"
    assert cards[0].strength == "PM2_Supporting"
    assert cards[0].evidence_status == "expert_panel_applied"
    assert cards[0].scenario_id == assertions[0]["scenario_id"]


def test_vcep_latest_release_uses_natural_version_order_when_dates_tie():
    version_9 = _vcep_row(version="9", assertion="VUS")
    version_10 = _vcep_row(version="10", assertion="Likely Pathogenic")
    version_9["Release Date"] = version_10["Release Date"] = "2026-08-01"
    source = _fact(
        "vcep-version-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [version_9, version_10]},
    )
    _context, assertions, _cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={
            "variation_id": "123",
            "hgvs_c": "NM_000001.1:c.1A>G",
        },
        disease="MONDO:0000001",
        inheritance="AD",
    )
    assert assertions[0]["version"] == "10"
    assert assertions[0]["classification"] == "Likely Pathogenic"


def test_vcep_disease_scenarios_remain_separate_and_mismatch_is_not_scored():
    first = _vcep_row(version="1", assertion="VUS", disease="MONDO:0000001")
    second = {
        **_vcep_row(version="1", assertion="Benign", disease="MONDO:0000002"),
        "Expert Panel": "OTHER VCEP",
    }
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [first, second]},
    )
    _context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"validated_hgvs_c": "NM_000001.1:c.1A>G"},
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )

    assert len(assertions) == 2
    assert len({row["scenario_id"] for row in assertions}) == 2
    assert {row["disease_match_status"] for row in assertions} == {
        "matched",
        "mismatch",
    }
    assert {card.scenario_id for card in cards} == {
        next(
            row["scenario_id"]
            for row in assertions
            if row["disease_match_status"] == "matched"
        )
    }


def test_vcep_requires_moi_match_and_does_not_use_substring_variant_identity():
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [_vcep_row(version="1", assertion="VUS")]},
    )
    _context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"validated_hgvs_c": "NM_000001.2:c.1A>G"},
        disease="MONDO:0000001",
        inheritance="autosomal recessive",
    )
    assert assertions == []
    assert cards == []

    _context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"validated_hgvs_c": "NM_000001.1:c.11A>G"},
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )
    assert assertions == []
    assert cards == []


def test_vcep_accepts_only_allele_level_identifiers_and_verified_aliases():
    row = _vcep_row(version="1", assertion="VUS")
    row["HGVS"] = ["NM_000001.1:c.1A>G", "NP_000001.1:p.Lys1Arg"]
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [row]},
    )

    context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={
            "validated_hgvs_c": "NM_000001.1:c.2A>G",
            "hgvs_p": "NP_000001.1:p.Lys1Arg",
            "rsid": "rs1",
        },
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )
    assert assertions == []
    assert cards == []
    assert context["history"][0]["identity_match_status"] == "candidate"
    assert (
        "protein_hgvs_is_context_only"
        in context["history"][0]["identity_rejection_reasons"]
    )

    _context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"variation_id": "123"},
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )
    assert assertions[0]["identity_match_basis"] == "clinvar_variation_id"
    assert cards

    _context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={
            "validated_hgvs_c": "NM_000001.2:c.1A>G",
            "normalization": {"verified_hgvs_aliases": ["NM_000001.1:c.1A>G"]},
        },
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )
    assert assertions[0]["identity_match_basis"] == "verified_allele_hgvs"
    assert cards


def test_vcep_moi_uses_controlled_exact_aliases():
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [_vcep_row(version="1", assertion="VUS")]},
    )
    for observed in ("adult onset", "sporadic"):
        row = _vcep_row(version="1", assertion="VUS")
        row["MOI"] = observed
        source = _fact(
            f"vcep-{observed}",
            tool_name="ClinGen_get_variant_classifications",
            features={"variant_classifications": [row]},
        )
        _context, assertions, cards = parse_vcep_assertions(
            {source.fact_id: source},
            identity={"validated_hgvs_c": "NM_000001.1:c.1A>G"},
            disease="MONDO:0000001",
            inheritance="AD",
        )
        assert assertions[0]["inheritance_match_status"] == "candidate"
        assert assertions[0]["applicability_status"] == "candidate"
        assert cards

    standard_source = _fact(
        "vcep-standard-ad",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [_vcep_row(version="1", assertion="VUS")]},
    )
    _context, assertions, cards = parse_vcep_assertions(
        {standard_source.fact_id: standard_source},
        identity={"validated_hgvs_c": "NM_000001.1:c.1A>G"},
        disease="MONDO:0000001",
        inheritance="AD",
    )
    assert assertions[0]["inheritance_match_status"] == "matched"
    assert assertions[0]["applicability_status"] == "matched"
    assert cards


def test_vcep_rsid_alone_is_only_a_visible_lead():
    row = _vcep_row(version="1", assertion="VUS")
    row["dbSNP"] = "rs123"
    source = _fact(
        "vcep-rsid",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [row]},
    )
    context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"rsid": "rs123"},
        disease="MONDO:0000001",
        inheritance="AD",
    )
    assert assertions == []
    assert cards == []
    assert context["history"][0]["identity_match_status"] == "candidate"
    assert (
        "rsid_alone_is_not_allele_specific"
        in context["history"][0]["identity_rejection_reasons"]
    )


def test_vcep_free_text_mentions_never_become_applied_criteria():
    row = _vcep_row(version="1", assertion="VUS")
    row["Applied Criteria"] = []
    row["Guidelines"] = "PVS1 was not met; PM2 was applied."
    row["Evidence Summaries"] = "BS1 not applicable. BP4 supporting was met."
    source = _fact(
        "vcep-source",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [row]},
    )
    context, assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"validated_hgvs_c": "NM_000001.1:c.1A>G"},
        disease="MONDO:0000001",
        inheritance="autosomal dominant",
    )
    assert cards == []
    assert assertions[0]["unparsed_criterion_mentions"]
    assert context["history"][0]["unparsed_criterion_mentions"]


def test_vcep_negative_structured_criteria_do_not_generate_cards():
    row = _vcep_row(version="1", assertion="VUS")
    row["Applied Criteria"] = [
        {
            "criterion": "PVS1",
            "strength": "Very Strong",
            "status": "Not Met (insufficient evidence)",
        },
        {"criterion": "BS1", "strength": "Strong", "status": "Not Applicable"},
        {"criterion": "PM3", "strength": "Moderate", "met": "false"},
        {"criterion": "PM2", "strength": "Supporting", "status": "Met"},
    ]
    source = _fact(
        "vcep-negative",
        tool_name="ClinGen_get_variant_classifications",
        features={"variant_classifications": [row]},
    )
    _context, _assertions, cards = parse_vcep_assertions(
        {source.fact_id: source},
        identity={"validated_hgvs_c": "NM_000001.1:c.1A>G"},
        disease="MONDO:0000001",
        inheritance="AD",
    )
    assert [(card.criterion, card.strength) for card in cards] == [
        ("PM2", "PM2_Supporting")
    ]


def test_deterministic_literature_extractor_ignores_query_text():
    candidate = {
        "publication_id": "pmid:1",
        "pmid": "1",
        "title": "A neutral title",
        "abstract": "",
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    fulltext = _fact(
        "fulltext",
        tool_name="EuropePMC_get_full_text",
        features={"query": "de novo case series"},
        request_arguments={"pmid": "1"},
    )

    extracted = extract_literature_facts(
        [candidate],
        {fulltext.fact_id: fulltext},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    assert extracted == {}


def test_literature_title_only_hit_remains_a_lead_without_evidence_fact():
    candidate = {
        "publication_id": "pmid:title-only",
        "pmid": "title-only",
        "title": "NM_000001.1:c.1A>G occurred de novo in one proband",
        "abstract": "",
        "match_class": "exact_variant_match",
        "source_fact_ids": ["index-record"],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    assert facts == {}


def test_abstract_fact_is_automatic_candidate_but_not_strict():
    candidate = {
        "publication_id": "pmid:2",
        "pmid": "2",
        "title": "The TEST variant in affected families",
        "abstract": "The NM_000001.1:c.1A>G variant cosegregated in one family.",
        "match_class": "exact_variant_match",
        "source_fact_ids": ["literature-index"],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
        disease="MONDO:0000001",
    )
    assert {fact.features["fact_type"] for fact in facts.values()} == {"segregation"}
    fact = next(
        fact for fact in facts.values() if fact.features["fact_type"] == "segregation"
    )
    assert fact.source_status == "abstract_only"
    assert fact.extraction_status == "rule_extracted"
    assert fact_is_strictly_verified(fact) is False


def test_document_anchored_llm_fact_needs_v3_target_and_requirement_checks():
    fact = SourceFact(
        fact_id="llm-document-fact",
        tool_name="EuropePMC_get_full_text",
        status="success",
        query_identity={"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"},
        result_identity={"gene": "TEST", "hgvs_c": "NM_000001.1:c.1A>G"},
        features={
            "anchor_status": "verified",
            "semantic_status": "verified",
            "document_truncated": False,
        },
        raw_result_hash="llm-document-hash",
        provider_version="2026-08-09",
        verification_level="machine_document_anchored",
        identity_status="matched",
        source_status="available",
        extraction_status="llm_extracted",
        version_status="versioned",
        disease_match_status="matched",
        independence_status="independent",
    )
    assert fact_is_strictly_verified(fact) is False

    complete = SourceFact(
        **{
            **fact.__dict__,
            "verification_level": "host_verified",
            "features": {
                **fact.features,
                "requirements_status": "complete",
                "target_link_status": "direct_variant",
                "negation_status": "not_negated",
            },
        }
    )
    assert fact_is_strictly_verified(complete) is True


def test_literature_extractor_emits_each_located_atom_but_does_not_assume_independence():
    candidate = {
        "publication_id": "pmid:3",
        "pmid": "3",
        "title": "Two observations",
        "abstract": (
            "NM_000001.1:c.1A>G occurred de novo in a proband. The variant was "
            "reported de novo in another family."
        ),
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    de_novo = [
        fact for fact in facts.values() if fact.features["fact_type"] == "de_novo"
    ]
    assert len(de_novo) == 2
    assert {fact.independence_status for fact in de_novo} == {"unknown"}


def test_literature_extractor_rejects_method_keywords_and_cross_paragraph_joining():
    candidate = {
        "publication_id": "pmid:method",
        "pmid": "method",
        "title": "A background table lists NM_000001.1:c.1A>G.",
        "abstract": (
            "We used de novo transcript assembly for unrelated patients. "
            "A separate cohort included 12 patients with other variants."
        ),
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    assert facts == {}


def test_literature_de_novo_requires_target_and_case_in_same_sentence():
    candidate = {
        "publication_id": "pmid:denovo",
        "pmid": "denovo",
        "title": "A TEST report",
        "abstract": (
            "NM_000001.1:c.1A>G occurred de novo in one proband. "
            "The variant was not de novo in a second family."
        ),
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    de_novo = [
        fact for fact in facts.values() if fact.features["fact_type"] == "de_novo"
    ]
    assert len(de_novo) == 1
    assert de_novo[0].features["target_link_status"] == "direct_variant"
    assert de_novo[0].features["requirements_status"] == "complete"
    assert de_novo[0].features["semantic_status"] == "verified"


def test_provider_linked_sentence_is_visible_but_unresolved():
    candidate = {
        "publication_id": "pmid:linked",
        "pmid": "linked",
        "title": "A linked report",
        "abstract": "The variant occurred de novo in one proband.",
        "match_class": "provider_linked_variant_match",
        "source_fact_ids": ["litvar-link"],
    }
    facts = extract_literature_facts(
        [candidate],
        {},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    fact = next(iter(facts.values()))
    assert fact.features["target_link_status"] == "provider_linked"
    assert fact.features["semantic_status"] == "unresolved"
    assert fact_is_strictly_verified(fact) is False


def test_fulltext_metadata_without_document_content_is_not_treated_as_fulltext():
    candidate = {
        "publication_id": "pmid:4",
        "pmid": "4",
        "title": "No evidence phrase",
        "abstract": "",
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    metadata_only = _fact(
        "metadata",
        tool_name="EuropePMC_get_full_text",
        features={
            "status": "success",
            "source": "europe_pmc_fulltextxml",
            "format": "xml",
            "url": "https://example.test/article.xml",
        },
        request_arguments={"pmid": "4"},
    )
    facts = extract_literature_facts(
        [candidate],
        {metadata_only.fact_id: metadata_only},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    assert facts == {}


def test_complete_fulltext_atom_can_be_strict_but_truncated_text_cannot():
    candidate = {
        "publication_id": "pmid:full",
        "pmid": "full",
        "title": "A TEST report",
        "abstract": "",
        "match_class": "exact_variant_match",
        "source_fact_ids": [],
    }
    content = "NM_000001.1:c.1A>G occurred de novo in one proband."
    complete = _fact(
        "fulltext-complete",
        tool_name="EuropePMC_get_full_text",
        features={
            "data": {"sections": [content]},
            "source": "europe_pmc_fulltextxml",
            "format": "xml",
            "url": "https://example.test/full.xml",
            "truncated": False,
        },
        request_arguments={"pmid": "full"},
    )
    facts = extract_literature_facts(
        [candidate],
        {complete.fact_id: complete},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    fact = next(iter(facts.values()))
    assert fact.features["requirements_status"] == "complete"
    assert fact.features["semantic_status"] == "verified"
    assert fact.features["reading_manifest"]["status"] == "complete"
    assert fact_is_strictly_verified(fact) is True

    truncated = _fact(
        "fulltext-truncated",
        tool_name="EuropePMC_get_full_text",
        features={
            "data": {"sections": [content]},
            "source": "europe_pmc_fulltextxml",
            "format": "xml",
            "url": "https://example.test/truncated.xml",
            "truncated": True,
            "truncated_sections": ["results"],
        },
        request_arguments={"pmid": "full"},
    )
    facts = extract_literature_facts(
        [candidate],
        {truncated.fact_id: truncated},
        identity={"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    fact = next(iter(facts.values()))
    assert fact.features["reading_manifest"]["status"] == "partial"
    assert fact_is_strictly_verified(fact) is False


def test_caller_clinical_observation_is_automatic_only_and_conflicts_fail_closed():
    raw = [
        {
            "observation_id": "case-1",
            "observation_type": "de_novo",
            "source_type": "lab_report",
            "source_id": "report-1",
            "values": {
                "case_id": "case-1",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "consistent",
            },
        }
    ]
    observations, errors = _normalize_clinical_observations(raw)
    assert errors == []
    facts, bound = _clinical_observation_facts(
        observations,
        {"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    fact = next(iter(facts.values()))
    assert fact.identity_status == "matched"
    assert fact.version_status == "unversioned"
    assert fact_is_strictly_verified(fact) is False
    assert bound[0]["source_fact_id"] == fact.fact_id

    from tooluniverse.acmg.models import EvidenceCard

    card = EvidenceCard(
        criterion="PS2",
        strength="PS2",
        evidence_status="source_backed_candidate",
        input_source="clinical observation",
        input_values={},
        clinvar_rule_applied="fork candidate policy",
        strength_source="acmg_base_candidate",
        rule_source={"type": "fork_candidate_policy"},
        rule_id="acmg-v3-clinical-candidate",
        rule_version="2026-08-08-v3",
        source_fact_ids=[fact.fact_id],
        verification_dimensions={
            "identity_status": fact.identity_status,
            "source_status": fact.source_status,
            "extraction_status": fact.extraction_status,
            "version_status": fact.version_status,
            "disease_match_status": fact.disease_match_status,
            "independence_status": fact.independence_status,
        },
    )
    assert is_automatic_evidence(card, known_source_fact_ids={fact.fact_id}) is True
    assert is_verified_evidence(card, verified_source_fact_ids={fact.fact_id}) is False

    conflicting, _bound = _clinical_observation_facts(
        [
            {
                **observations[0],
                "values": {**observations[0]["values"], "gene": "OTHER"},
            }
        ],
        {"gene": "TEST", "validated_hgvs_c": "NM_000001.1:c.1A>G"},
    )
    conflict_fact = next(iter(conflicting.values()))
    assert conflict_fact.identity_status == "conflict"


def test_clinical_observation_schema_rejects_duplicates_and_missing_values():
    normalized, errors = _normalize_clinical_observations(
        [
            {
                "observation_id": "same",
                "observation_type": "case_series",
                "source_type": "publication",
                "source_id": "PMID:1",
                "values": {},
            },
            {
                "observation_id": "same",
                "observation_type": "case_series",
                "source_type": "publication",
                "source_id": "PMID:2",
                "values": {},
            },
            {
                "observation_id": "missing-values",
                "observation_type": "case_series",
                "source_type": "publication",
                "source_id": "PMID:3",
            },
        ]
    )
    assert len(normalized) == 1
    assert len(errors) == 2


def _clinical_atom(observation_id: str, observation_type: str, values: dict) -> dict:
    return {
        "observation_id": observation_id,
        "observation_type": observation_type,
        "source_type": "publication",
        "source_id": f"PMID:{observation_id}",
        "source_fact_id": f"fact:{observation_id}",
        "values": values,
        "identity_status": "matched",
        "source_status": "available",
        "extraction_status": "structured",
        "version_status": "versioned",
        "disease_match_status": "matched",
        "independence_status": "independent",
    }


def test_pp1_pp4_clingen_points_are_coupled_and_capped():
    cards = clinical_evidence(
        inheritance_mode="autosomal dominant",
        clinical_observations=[
            _clinical_atom(
                "phenotype",
                "phenotype_specificity",
                {"diagnostic_yield": 0.68, "case_id": "case-1"},
            ),
            _clinical_atom(
                "family",
                "segregation",
                {
                    "segregation_direction": "cosegregates",
                    "affected_cosegregations": 2,
                    "family_id": "family-1",
                },
            ),
        ],
    )
    by_criterion = {card.criterion: card for card in cards}
    assert by_criterion["PP4"].strength == "PP4_Strong"
    assert by_criterion["PP1"].strength == "PP1_Supporting"
    assert by_criterion["PP1"].input_values["raw_points"] == 2.0
    assert by_criterion["PP1"].input_values["combined_pp1_pp4_points_capped"] == 5.0
    assert by_criterion["PP1"].rule_id == "clingen-svi-pp1-pp4-bs4"


def test_homogeneous_locus_uses_pp4_without_positive_pp1_double_counting():
    cards = clinical_evidence(
        inheritance_mode="autosomal dominant",
        clinical_observations=[
            _clinical_atom(
                "phenotype",
                "phenotype_specificity",
                {
                    "diagnostic_yield": 0.95,
                    "locus_homogeneous": True,
                    "case_id": "case-1",
                },
            ),
            _clinical_atom(
                "family",
                "segregation",
                {
                    "segregation_direction": "cosegregates",
                    "affected_cosegregations": 3,
                    "family_id": "family-1",
                },
            ),
        ],
    )
    by_criterion = {card.criterion: card for card in cards}
    assert by_criterion["PP4"].strength == "PP4_Strong"
    assert by_criterion["PP1"].evidence_status == "not_met"
    assert by_criterion["PP1"].input_values["raw_points"] == 0.0
    assert any("homogeneous locus" in caveat for caveat in by_criterion["PP1"].caveats)


def test_bs4_requires_applicable_nonsegregation_configuration():
    cards = clinical_evidence(
        inheritance_mode="autosomal dominant",
        clinical_observations=[
            _clinical_atom(
                "family",
                "segregation",
                {
                    "segregation_direction": "nonsegregation",
                    "affected_noncarrier_count": 1,
                    "phenotype_confirmed": True,
                    "penetrance_adequate": True,
                    "family_id": "family-1",
                },
            )
        ],
    )
    assert len(cards) == 1
    assert cards[0].criterion == "BS4"
    assert cards[0].strength == "BS4"
    assert cards[0].evidence_status == "rule_mapped"


def test_unknown_independence_is_retained_but_only_one_de_novo_atom_is_counted():
    rows = [
        {
            **_clinical_atom(f"case-{index}", "de_novo", {}),
            "case_id": f"case-{index}",
            "parental_relationships": "confirmed",
            "phenotype_consistency": "consistent",
            "independence_status": "unknown",
        }
        for index in (1, 2)
    ]
    cards = clinical_evidence(
        inheritance_mode="autosomal dominant", de_novo_probands=rows
    )
    ps2 = next(card for card in cards if card.criterion == "PS2")
    assert ps2.input_values["total_points"] == 1.0
    assert ps2.input_values["counted_case_ids"] == ["case-1"]
    assert ps2.input_values["uncounted_unknown_independence_case_ids"] == ["case-2"]
    assert ps2.evidence_status == "source_backed_candidate"


def test_numeric_case_control_observation_is_mapped_and_null_result_is_not_met():
    enriched = clinical_evidence(
        clinical_observations=[
            _clinical_atom(
                "cohort-1",
                "case_control",
                {"odds_ratio": 4.2, "ci_lower": 1.4, "cohort_id": "cohort-1"},
            )
        ]
    )[0]
    assert enriched.criterion == "PS4"
    assert enriched.evidence_status == "rule_mapped"

    null = clinical_evidence(
        clinical_observations=[
            _clinical_atom(
                "cohort-2",
                "case_control",
                {"odds_ratio": 1.1, "ci_lower": 0.8, "cohort_id": "cohort-2"},
            )
        ]
    )[0]
    assert null.evidence_status == "not_met"
    assert null.strength == "not_met"


def test_cspec_finite_parser_extracts_auditable_rules_and_flags_exceptions():
    parsed, gaps = _deterministic_text_contract(
        "PP3",
        "Apply at Supporting when REVEL >= 0.75; maximum strength Supporting; "
        "mutually exclusive with BP4.",
    )
    assert gaps == []
    assert parsed["predictor"] == "REVEL"
    assert parsed["operator"] == ">="
    assert parsed["threshold"] == 0.75
    assert parsed["strength"] == "PP3"
    assert parsed["strength_ceiling"] == "PP3"
    assert parsed["mutually_exclusive_with"] == ["BP4"]

    parsed, gaps = _deterministic_text_contract(
        "PS4", "Use at Strong for at least 3 independent cases unless mosaic."
    )
    assert parsed["case_count_threshold"] == 3
    assert gaps == ["unsupported_conditional_or_exception_clause"]


def test_all_28_criteria_have_one_v3_machine_contract():
    matrix = criterion_use_matrix()
    assert set(matrix) == set(ACMG_CRITERIA)
    assert len(matrix) == 28
    for criterion, contract in matrix.items():
        assert contract["criterion"] == criterion
        assert contract["direction"] in {"pathogenic", "benign"}
        assert contract["candidate_policy"]["policy_id"]
        assert contract["candidate_policy"]["version"]
        assert contract["hard_exclusions"]
        assert contract["scenario_isolation_required"] is True
    assert matrix["PP5"]["automation_level"] == "deprecated"
    assert matrix["BP6"]["automation_level"] == "deprecated"


def _scenario_row() -> dict:
    return {
        "card_id": "acmg-card:v3:generic",
        "criterion": "PP3",
        "strength": "PP3",
        "evidence_status": "rule_mapped",
        "scenario_id": "generic-svi",
        "source_fact_ids": ["predictor-fact"],
        "observed_facts": {"predictor_scores": {"REVEL": {"score": 0.8}}},
        "rule_id": "clingen-svi-pejaver-pp3-bp4",
        "rule_version": "2022.1",
        "rule_source": {"type": "versioned_svi"},
        "calculation_roles": {
            "automatic": True,
            "verified": True,
            "user_selected": False,
        },
        "verification_dimensions": {
            "identity_status": "matched",
            "source_status": "available",
            "extraction_status": "structured",
            "version_status": "versioned",
            "disease_match_status": "matched",
            "independence_status": "independent",
        },
    }


def _scenario_context(applicability: str, *, threshold: float = 0.75) -> dict:
    return {
        "rule_scenarios": [
            {
                "scenario_id": "generic-svi",
                "scenario_type": "generic_svi",
                "applicability_status": "applicable",
                "contract": None,
            },
            {
                "scenario_id": "cspec:test",
                "scenario_type": "vcep_cspec",
                "applicability_status": applicability,
                "specification": {"specification_id": "TEST:1"},
                "contract": {
                    "specification_id": "TEST:1",
                    "rule_id": "clingen-cspec-runtime-test",
                    "version": "1.0",
                    "content_hash": "hash-test",
                    "criteria": {
                        "PP3": {
                            "criterion": "PP3",
                            "rule_applicable": True,
                            "verification": "dynamic_cspec_structured",
                            "deterministic_parse_status": "parsed",
                            "predictor": "REVEL",
                            "operator": ">=",
                            "threshold": threshold,
                            "strength": "PP3",
                        }
                    },
                    "bayesian_odds": {"PP3": 2.08},
                },
            },
        ]
    }


def test_cspec_evaluator_executes_thresholds_and_does_not_remap_unmet_rules():
    met = evaluate_cspec_criterion(
        _scenario_row(),
        _scenario_context("matched")["rule_scenarios"][1]["contract"]["criteria"][
            "PP3"
        ],
    )
    assert met["status"] == "condition_met"
    assert met["mapped_strength"] == "PP3"

    not_met = evaluate_cspec_criterion(
        _scenario_row(),
        _scenario_context("matched", threshold=0.9)["rule_scenarios"][1]["contract"][
            "criteria"
        ]["PP3"],
    )
    assert not_met["status"] == "condition_not_met"
    assert not_met["mapped_strength"] == ""


def test_cspec_evaluator_executes_frequency_case_points_region_type_and_ceiling():
    row = deepcopy(_scenario_row())
    row["criterion"] = "PS4"
    row["strength"] = "PS4"
    row["observed_facts"] = {
        "af_global": 0.00001,
        "af_popmax": 0.00002,
        "case_count": 4,
        "total_points": 5,
        "protein_position": 42,
        "variant_type": "missense_variant",
    }
    evaluation = evaluate_cspec_criterion(
        row,
        {
            "criterion": "PS4",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "condition_logic": "all",
            "maximum_credible_af": 0.0001,
            "case_count_threshold": 3,
            "operator": ">=",
            "point_table": [{"minimum_points": 4, "strength": "PS4"}],
            "residues": [42],
            "variant_types": ["missense_variant"],
            "strength": "PS4",
            "strength_ceiling": "PS4_Supporting",
        },
    )
    assert evaluation["status"] == "condition_met"
    assert {condition["condition"] for condition in evaluation["conditions"]} == {
        "maximum_credible_af",
        "case_count_threshold",
        "point_table",
        "protein_region",
        "variant_types",
    }
    assert evaluation["mapped_strength"] == "PS4_Supporting"


def test_cspec_evaluator_applies_ceiling_without_repeated_target_strength():
    row = deepcopy(_scenario_row())
    row["criterion"] = "PS4"
    row["strength"] = "PS4"
    evaluation = evaluate_cspec_criterion(
        row,
        {
            "criterion": "PS4",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "strength_ceiling": "PS4_Supporting",
        },
    )
    assert evaluation["status"] == "condition_met"
    assert evaluation["mapped_strength"] == "PS4_Supporting"


def test_cspec_evaluator_requires_explicit_multi_condition_logic():
    contract = {
        "criterion": "PP3",
        "rule_applicable": True,
        "deterministic_parse_status": "parsed",
        "predictor": "REVEL",
        "operator": ">=",
        "threshold": 0.75,
        "case_count_threshold": 1,
        "strength": "PP3",
    }
    evaluation = evaluate_cspec_criterion(_scenario_row(), contract)
    assert evaluation["status"] == "unresolved"
    assert evaluation["missing_inputs"] == ["explicit_multi_condition_logic"]


def test_cspec_evaluator_short_circuits_known_and_or_conditions():
    any_result = evaluate_cspec_criterion(
        _scenario_row(),
        {
            "criterion": "PP3",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "condition_logic": "any",
            "predictor": "REVEL",
            "operator": ">=",
            "threshold": 0.75,
            "case_count_threshold": 2,
            "strength": "PP3",
        },
    )
    assert any_result["status"] == "condition_met"

    all_result = evaluate_cspec_criterion(
        _scenario_row(),
        {
            "criterion": "PP3",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "condition_logic": "all",
            "predictor": "REVEL",
            "operator": ">=",
            "threshold": 0.9,
            "case_count_threshold": 2,
            "strength": "PP3",
        },
    )
    assert all_result["status"] == "condition_not_met"


def test_cspec_malformed_point_or_region_rules_fail_closed():
    row = deepcopy(_scenario_row())
    row["observed_facts"] = {"points": 4, "protein_position": 42}
    point_result = evaluate_cspec_criterion(
        row,
        {
            "criterion": "PP3",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "point_table": [{"minimum_points": "not-a-number", "strength": "PP3"}],
        },
    )
    assert point_result["status"] == "unresolved"
    region_result = evaluate_cspec_criterion(
        row,
        {
            "criterion": "PP3",
            "rule_applicable": True,
            "deterministic_parse_status": "parsed",
            "regions": [{"start": "bad", "end": 50}],
        },
    )
    assert region_result["status"] == "unresolved"


def test_cspec_mismatch_is_visible_but_never_scored():
    result = build_scenario_results(
        [_scenario_row()],
        _scenario_context("mismatch"),
        [],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    mismatch = next(
        row
        for row in result["scenario_estimates"]
        if row["scenario_id"] == "cspec:test"
    )
    assert mismatch["automatic_bayesian"]["status"] == "not_calculated"
    assert mismatch["verified_bayesian"]["status"] == "not_calculated"
    assert mismatch["evidence_card_ids"] == []


def test_cspec_candidate_has_automatic_estimate_but_no_verified_estimate():
    result = build_scenario_results(
        [_scenario_row()],
        _scenario_context("candidate"),
        [],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    candidate = next(
        row
        for row in result["scenario_estimates"]
        if row["scenario_id"] == "cspec:test"
    )
    assert candidate["automatic_bayesian"]["status"] == "computed"
    assert candidate["automatic_bayesian"]["included_card_ids"]
    assert candidate["verified_bayesian"]["status"] == "not_calculated"
    assert candidate["rule_execution_trace"][0]["status"] == "condition_met"
    assert result["scenario_cards"][0]["card_id"].startswith("acmg-card:v3:")
    repeated = build_scenario_results(
        [_scenario_row()],
        _scenario_context("candidate"),
        [],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    assert (
        result["scenario_cards"][0]["card_id"]
        == repeated["scenario_cards"][0]["card_id"]
    )


def test_matched_cspec_inherits_unmodified_verified_generic_rules():
    context = _scenario_context("matched")
    context["rule_scenarios"][1]["contract"]["criteria"] = {}
    result = build_scenario_results(
        [_scenario_row()],
        context,
        [],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    estimate = next(
        row
        for row in result["scenario_estimates"]
        if row["scenario_id"] == "cspec:test"
    )
    inherited = next(
        row for row in result["scenario_cards"] if row["scenario_id"] == "cspec:test"
    )
    assert inherited["calculation_roles"]["verified"] is True
    assert inherited["card_id"] in estimate["verified_bayesian"]["included_card_ids"]
    assert estimate["rule_execution_trace"][0]["rule_scope"] == "generic_svi_inherited"


def test_user_selected_score_uses_only_compatibility_accepted_cards():
    first = _scenario_row()
    first["criterion"] = "PM2"
    first["strength"] = "PM2_Supporting"
    second = deepcopy(first)
    second["card_id"] = "acmg-card:v3:duplicate"
    second["source_fact_ids"] = ["predictor-fact-2"]
    score, report = _apply_evidence_decisions(
        [first, second],
        [
            {"card_id": first["card_id"], "decision": "accept"},
            {"card_id": second["card_id"], "decision": "accept"},
        ],
        known_source_fact_ids={"predictor-fact", "predictor-fact-2"},
    )
    assert len(score["included_card_ids"]) == 1
    assert len(report["compatibility_exclusions"]) == 1
    assert report["compatibility_exclusions"][0]["reason"] == "duplicate_criterion"


def test_user_selected_cross_scenario_mix_fails_closed():
    generic = _scenario_row()
    disease_scenario = deepcopy(generic)
    disease_scenario["card_id"] = "acmg-card:v3:disease-scenario"
    disease_scenario["scenario_id"] = "cspec:test"
    disease_scenario["source_fact_ids"] = ["predictor-fact-2"]
    score, report = _apply_evidence_decisions(
        [generic, disease_scenario],
        [
            {"card_id": generic["card_id"], "decision": "accept"},
            {"card_id": disease_scenario["card_id"], "decision": "accept"},
        ],
        known_source_fact_ids={"predictor-fact", "predictor-fact-2"},
    )
    assert score["included_card_ids"] == []
    assert report["selected_scenario_id"] == ""
    assert report["decision_errors"][0]["reason"] == "cross_scenario_user_selection"
    assert all(
        row["reason"] == "cross_scenario_user_selection"
        for row in report["compatibility_exclusions"]
    )


def test_partial_cspec_rule_remains_automatic_candidate_only():
    context = _scenario_context("matched")
    contract = context["rule_scenarios"][1]["contract"]["criteria"]["PP3"]
    contract["deterministic_parse_status"] = "partial"
    contract["deterministic_parse_gaps"] = ["unsupported_exception"]
    result = build_scenario_results(
        [_scenario_row()],
        context,
        [],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    estimate = next(
        row
        for row in result["scenario_estimates"]
        if row["scenario_id"] == "cspec:test"
    )
    assert estimate["automatic_bayesian"]["included_card_ids"]
    assert estimate["verified_bayesian"]["included_card_ids"] == []
    assert estimate["rule_execution_trace"][0]["status"] == "unresolved"


def test_cspec_does_not_promote_excluded_or_unconditional_not_met_cards():
    for evidence_status in ("excluded", "not_met"):
        row = deepcopy(_scenario_row())
        row["evidence_status"] = evidence_status
        row["strength"] = "not_met"
        row["calculation_roles"] = {
            "automatic": False,
            "verified": False,
            "user_selected": False,
        }
        context = _scenario_context("matched")
        criterion_contract = context["rule_scenarios"][1]["contract"]["criteria"]["PP3"]
        criterion_contract.pop("predictor")
        criterion_contract.pop("operator")
        criterion_contract.pop("threshold")
        result = build_scenario_results(
            [row],
            context,
            [],
            known_source_fact_ids={"predictor-fact"},
            verified_source_fact_ids={"predictor-fact"},
        )
        scenario_card = result["scenario_cards"][0]
        assert scenario_card["evidence_status"] == evidence_status
        assert scenario_card["calculation_roles"]["automatic"] is False


def test_matching_vcep_assertion_merges_with_cspec_and_wins_duplicate_criterion():
    context = _scenario_context("matched")
    specification = context["rule_scenarios"][1]["specification"]
    specification.update(
        {
            "vcep": "TEST VCEP",
            "diseases": [
                {
                    "mondo_id": "MONDO:0000001",
                    "inheritance": ["autosomal dominant"],
                }
            ],
        }
    )
    assertion = {
        "scenario_id": "vcep:test",
        "expert_panel": "TEST VCEP",
        "mondo_id": "MONDO:0000001",
        "inheritance": "autosomal dominant",
        "applicability_status": "matched",
    }
    vcep_card = deepcopy(_scenario_row())
    vcep_card.update(
        {
            "card_id": "acmg-card:v3:vcep",
            "scenario_id": "vcep:test",
            "evidence_status": "expert_panel_applied",
            "rule_source": {"type": "vcep_assertion"},
        }
    )
    result = build_scenario_results(
        [_scenario_row(), vcep_card],
        context,
        [assertion],
        known_source_fact_ids={"predictor-fact"},
        verified_source_fact_ids={"predictor-fact"},
    )
    estimate = next(
        row
        for row in result["scenario_estimates"]
        if row["scenario_id"] == "cspec:test"
    )
    assert len(estimate["automatic_bayesian"]["included_card_ids"]) == 1
    included_id = estimate["automatic_bayesian"]["included_card_ids"][0]
    included = next(
        row for row in result["scenario_cards"] if row["card_id"] == included_id
    )
    assert included["evidence_status"] == "expert_panel_applied"
    assert assertion["merged_into_scenario_id"] == "cspec:test"
