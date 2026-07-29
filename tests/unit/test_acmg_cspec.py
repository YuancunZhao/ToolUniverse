from tooluniverse.acmg.cspec import (
    build_dynamic_cspec_contract,
    cspec_content_hash,
)
from tooluniverse.acmg.collector import ACMGEvidencePipeline, SourceCall


def _candidate():
    return {
        "specification_id": "GN078",
        "gene": "VHL",
        "version": "1.1.0",
        "status": "released",
        "url": "https://cspec.example/GN078",
        "diseases": [
            {
                "mondo_id": "MONDO:0008667",
                "inheritance": ["Autosomal dominant inheritance"],
            }
        ],
        "criterion_modifications": [
            {
                "criterion": "PM2",
                "applicability": "Applicable",
                "default_strength": "Supporting",
                "instructions": "Use PM2 at supporting strength.",
                "criterion_id": "criterion-pm2",
            }
        ],
    }


def test_online_structured_cspec_is_executable_without_local_catalog():
    contract = build_dynamic_cspec_contract(_candidate())

    assert contract["rule_source"] == "online_clingen_cspec"
    assert contract["criteria"]["PM2"]["strength"] == "PM2_Supporting"
    assert contract["criteria"]["PM2"]["verification"] == "dynamic_cspec_structured"
    assert contract["review_requests"][0]["criterion"] == "PM2"


def test_unbound_compiled_contract_is_ignored():
    contract = build_dynamic_cspec_contract(
        _candidate(),
        compiled_contract={
            "content_hash": "stale",
            "criteria": {"PM2": {"maximum_credible_af": 0.001}},
        },
    )

    assert contract["compiled_contract_status"] == "ignored_hash_unbound"
    assert "maximum_credible_af" not in contract["criteria"]["PM2"]


def test_cspec_llm_proposal_requires_exact_hash_and_excerpt():
    candidate = _candidate()
    proposal = {
        "specification_id": "GN078",
        "version": "1.1.0",
        "content_hash": cspec_content_hash(candidate),
        "criterion": "PM2",
        "excerpt": "Use PM2 at supporting strength.",
        "locator": "criterion-pm2",
        "structured_interpretation": {
            "strength": "PM2_Supporting",
            "maximum_credible_af": 0.0001,
        },
        "suggested_strength": "PM2_Supporting",
        "interpretation": "The VCEP retains PM2 at supporting strength.",
        "confidence": 0.9,
        "extractor": {"name": "fixture-llm", "version": "1"},
    }
    contract = build_dynamic_cspec_contract(candidate, proposals=[proposal])

    assert contract["proposal_reports"][0]["status"] == "verified"
    assert contract["criteria"]["PM2"]["maximum_credible_af"] == 0.0001
    assert contract["criteria"]["PM2"]["verification"] == "dynamic_cspec_llm"

    stale = {**proposal, "content_hash": "stale"}
    rejected = build_dynamic_cspec_contract(candidate, proposals=[stale])
    assert rejected["proposal_reports"][0]["status"] == "rejected"
    assert "maximum_credible_af" not in rejected["criteria"]["PM2"]


def test_explicitly_non_applicable_cspec_criterion_is_not_executable():
    candidate = _candidate()
    candidate["criterion_modifications"][0]["applicability"] = "Not Applicable"
    candidate["criterion_modifications"][0]["default_strength"] = "Supporting"
    proposal = {
        "specification_id": "GN078",
        "version": "1.1.0",
        "content_hash": cspec_content_hash(candidate),
        "criterion": "PM2",
        "excerpt": "Use PM2 at supporting strength.",
        "structured_interpretation": {"strength": "PM2_Supporting"},
        "suggested_strength": "PM2_Supporting",
        "extractor": {"name": "fixture-llm", "version": "1"},
    }

    contract = build_dynamic_cspec_contract(candidate, proposals=[proposal])

    assert contract["criteria"]["PM2"]["rule_applicable"] is False
    assert "strength" not in contract["criteria"]["PM2"]
    assert "PM2_Supporting" not in contract["countable_strengths"]
    assert contract["proposal_reports"][0]["status"] == "rejected"
    assert (
        "criterion_not_applicable_in_matched_cspec"
        in contract["proposal_reports"][0]["errors"]
    )


def test_multiple_context_matches_remain_visible_and_are_not_selected():
    first = _candidate()
    second = {**_candidate(), "specification_id": "GN079"}
    call = SourceCall(
        tool_name="ClinGen_search_cspec",
        category="rule_context",
        status="success",
        result={"status": "success", "data": [first, second]},
    )

    context = ACMGEvidencePipeline._rule_context(
        call,
        gene="VHL",
        disease_context={"mondo_id": "MONDO:0008667"},
        inheritance="AD",
    )

    assert context["cspec_status"] == "ambiguous"
    assert context["multiple_applicable_specifications"] is True
    assert len(context["matched_specifications"]) == 2
    assert context["applicable_specification"] is None
    assert context["fallback_policy"] == "general_clingen_svi"


def test_network_failure_does_not_use_local_contract_as_current_rule():
    call = SourceCall(
        tool_name="ClinGen_search_cspec",
        category="rule_context",
        status="error",
        error="network unavailable",
    )

    context = ACMGEvidencePipeline._rule_context(
        call,
        gene="PTEN",
        disease_context={"mondo_id": "MONDO:0017623"},
        inheritance="AD",
    )

    assert context["cspec_status"] == "cspec_unavailable"
    assert context["executable_contract"] is None
    assert context["fallback_policy"] == "general_clingen_svi"
