"""Machine document anchoring for LLM-extracted ACMG facts."""

from tooluniverse.acmg.document_facts import verify_document_fact


def _fact(**overrides):
    fact = {
        "fact_id": "caller-controlled-id",
        "fact_type": "case_control",
        "pmid": "12345678",
        "locator": "results",
        "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
        "variant_identity": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "extractor": {"name": "fixture-extractor", "version": "1.0"},
        "verification_level": "host_verified",
        "values": {
            "variant_identity": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "case_count": 12,
            "control_count": 1000,
            "odds_ratio": 6.2,
            "ci_lower": 1.4,
        },
        "field_excerpts": {
            "case_count": "12 cases",
            "control_count": "1000 controls",
            "odds_ratio": "odds ratio 6.2",
            "ci_lower": "lower confidence limit 1.4",
        },
    }
    fact.update(overrides)
    return fact


def _document():
    return {
        "status": "success",
        "data": {
            "pmid": "12345678",
            "sections": {
                "results": (
                    "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases and "
                    "1000 controls with odds ratio 6.2 and lower confidence limit 1.4."
                )
            },
        },
    }


def _verify(fact):
    return verify_document_fact(
        fact,
        _document(),
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )


def test_complete_fact_is_machine_anchored_with_recomputed_stable_id():
    first = _verify(_fact())
    second = _verify(_fact(fact_id="different-caller-id"))

    assert first["verified"] is True
    assert first["verification_level"] == "machine_document_anchored"
    assert first["fact_id"].startswith("document-fact:v1:")
    assert first["fact_id"] == second["fact_id"]
    assert first["fact_id"] != "caller-controlled-id"


def test_public_verification_claim_cannot_bypass_excerpt_validation():
    fact = _fact()
    fact["field_excerpts"] = {**fact["field_excerpts"], "odds_ratio": "odds ratio 99"}
    result = _verify(fact)

    assert result["verified"] is False
    assert result["verification_level"] == "unverified"
    assert "field_excerpt_not_found:odds_ratio" in result["validation_errors"]


def test_numeric_value_contradiction_is_separate_from_document_anchor():
    fact = _fact()
    fact["values"] = {**fact["values"], "odds_ratio": 9.9}
    result = _verify(fact)

    assert result["anchor_status"] == "verified"
    assert result["semantic_status"] == "contradicted"
    assert result["field_semantics"]["odds_ratio"] == "contradicted"
    assert result["verified"] is False


def test_unparseable_enum_keeps_verified_anchor_for_user_review():
    fact = {
        "fact_id": "mechanism",
        "fact_type": "mechanism",
        "pmid": "12345678",
        "locator": "results",
        "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
        "variant_identity": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "extractor": {"name": "fixture-extractor", "version": "1.0"},
        "values": {
            "variant_identity": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "gene_disease_mechanism": "loss_of_function",
        },
        "field_excerpts": {"gene_disease_mechanism": "observed in 12 cases"},
    }
    result = _verify(fact)

    assert result["anchor_status"] == "verified"
    assert result["semantic_status"] == "unresolved"
    assert result["verified"] is True


def test_document_identity_and_locator_must_match():
    wrong_document = _document()
    wrong_document["data"]["pmid"] = "87654321"
    result = verify_document_fact(
        _fact(locator="table 9"),
        wrong_document,
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )

    assert result["verified"] is False
    assert "document_identity_mismatch" in result["validation_errors"]
    assert "locator_not_found" in result["validation_errors"]
