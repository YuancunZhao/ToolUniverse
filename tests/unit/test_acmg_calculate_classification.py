"""Unit tests for ACMG_calculate_classification (ClinicalCalculatorTool).

Deterministic Tavtigian 2020 point-system classification of germline small
variants. Expectations are fixed here BEFORE implementation per the delivery
plan; nothing in this file touches the network.
"""

import pytest

from tooluniverse.clinical_calculators_tool import ClinicalCalculatorTool

PATHOGENIC = [
    "PVS1", "PS1", "PS2", "PS3", "PS4",
    "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
    "PP1", "PP2", "PP3", "PP4", "PP5",
]
BENIGN = [
    "BA1", "BS1", "BS2", "BS3", "BS4",
    "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
]
ALL_CRITERIA = PATHOGENIC + BENIGN
assert len(ALL_CRITERIA) == 28


def tool():
    return ClinicalCalculatorTool(
        {"name": "ACMG_calculate_classification",
         "fields": {"calculator": "acmg_classification"}}
    )


def ev(criterion, status="not_assessed", **kw):
    rec = {
        "criterion": criterion,
        "status": status,
        "strength": None,
        "rationale": "",
        "source_refs": [],
        "rule_refs": [],
        "evidence_ids": [],
    }
    rec.update(kw)
    return rec


def met(criterion, strength, *, fact=None, paper="PMID:1", rule="SVI-PM2-v1"):
    return ev(
        criterion,
        "met",
        strength=strength,
        rationale=f"{criterion} is met at {strength} strength",
        source_refs=[paper],
        rule_refs=[rule],
        evidence_ids=[fact or f"fact-{criterion}"],
    )


def build_evidence(*met_items, base_status="not_assessed", per_criterion=None):
    records = {c: ev(c, base_status) for c in ALL_CRITERIA}
    for item in met_items:
        records[item["criterion"]] = item
    for criterion, kw in (per_criterion or {}).items():
        records[criterion] = ev(criterion, **kw)
    return list(records.values())


def args(evidence, *, variant_context=None, rule_context=None, blocking_issues=None, **extra):
    payload = {
        # Synthetic fixture: no real gene, disease, or variant is implied --
        # these tests prove the interface contract and arithmetic only.
        "variant_context": variant_context
        or {
            "variant": "NM_999999.1:c.1000C>T",
            "gene": "TESTGENE",
            "disease": "Synthetic fixture disease",
            "inheritance_mode": "Autosomal dominant inheritance",
        },
        "rule_context": rule_context
        or {
            "cspec_lookup_status": "no_released_spec",
            "combination_method": "tavtigian2020",
            "specification": None,
            "applicable_rules_complete": True,
        },
        "evidence": evidence,
        "blocking_issues": [] if blocking_issues is None else blocking_issues,
    }
    payload.update(extra)
    return payload


def run(payload):
    return tool().run(payload)


# --------------------------------------------------------------------------- #
# Boundary scores: -7/-6/-1/0/5/6/9/10 under Tavtigian 2020 thresholds
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "met_items, expected_total, expected_class",
    [
        # -7 -> Benign (boundary: <= -7)
        (
            [met("BS1", "Strong"), met("BS3", "Moderate"), met("BP4", "Supporting")],
            -7,
            "Benign",
        ),
        # -6 -> Likely Benign (boundary: -6 .. -1)
        ([met("BS1", "Strong"), met("BS2", "Moderate")], -6, "Likely Benign"),
        # -1 -> Likely Benign
        (
            [met("BS1", "Moderate"), met("PM2", "Supporting")],
            -1,
            "Likely Benign",
        ),
        # 0 -> VUS via independent positive+negative sum
        ([met("PP3", "Supporting"), met("BP4", "Supporting")], 0, "VUS"),
        # 5 -> VUS
        ([met("PS4", "Strong"), met("PM2", "Supporting")], 5, "VUS"),
        # 6 -> Likely Pathogenic
        ([met("PS4", "Strong"), met("PM2", "Moderate")], 6, "Likely Pathogenic"),
        # 9 -> Likely Pathogenic (the PVS1 + PM2_Supporting golden combination)
        ([met("PVS1", "VeryStrong"), met("PM2", "Supporting")], 9,
         "Likely Pathogenic"),
        # 10 -> Pathogenic (boundary: >= 10)
        ([met("PVS1", "VeryStrong"), met("PM2", "Moderate")], 10, "Pathogenic"),
    ],
)
def test_classification_boundaries(met_items, expected_total, expected_class):
    result = run(args(build_evidence(*met_items)))
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == expected_class
    assert data["total_score"] == expected_total
    assert data["method"]["name"] == "tavtigian2020"


def test_strength_upgrade_and_downgrade_move_points():
    # PS1 upgraded to VeryStrong scores 8; BS1 downgraded to Moderate scores -2.
    result = run(
        args(build_evidence(met("PS1", "VeryStrong"), met("BS1", "Moderate")))
    )
    data = result["data"]
    assert data["total_score"] == 6
    assert data["classification"] == "Likely Pathogenic"
    contributions = {c["criterion"]: c["points"] for c in data["point_contributions"]}
    assert contributions["PS1"] == 8
    assert contributions["BS1"] == -2


def test_positive_and_negative_contributions_both_shown():
    result = run(
        args(build_evidence(met("PM2", "Supporting"), met("BS1", "Strong")))
    )
    data = result["data"]
    assert data["total_score"] == -3
    assert data["classification"] == "Likely Benign"
    assert data["pathogenic_points"] == 1
    assert data["benign_points"] == -4


# --------------------------------------------------------------------------- #
# BA1 stand-alone path
# --------------------------------------------------------------------------- #
def test_ba1_standalone_alone_gives_benign_with_null_score():
    result = run(args(build_evidence(met("BA1", "StandAlone"))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Benign"
    assert data["ba1_standalone"] is True
    # BA1 does not convert into ordinary points; the point total is null.
    assert data["total_score"] is None


def test_ba1_standalone_allows_null_strength():
    result = run(args(build_evidence(met("BA1", None))))
    assert result["data"]["classification"] == "Benign"


def test_ba1_standalone_with_additional_benign_still_benign():
    result = run(
        args(build_evidence(met("BA1", "StandAlone"), met("BS1", "Strong")))
    )
    data = result["data"]
    assert data["classification"] == "Benign"
    assert data["total_score"] is None
    assert data["benign_points"] == -4  # BS1 contribution still shown


def test_ba1_with_pathogenic_evidence_pauses():
    result = run(
        args(build_evidence(met("BA1", "StandAlone"), met("PM2", "Supporting")))
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "ba1_pathogenic_conflict" in reasons


def test_ba1_strength_restricted_to_standalone():
    result = run(args(build_evidence(met("BA1", "Strong"))))
    assert result["status"] == "error"
    assert "BA1" in result["error"]


def test_standalone_strength_rejected_outside_ba1():
    result = run(args(build_evidence(met("BS1", "StandAlone"))))
    assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# Input contract: 28 records, one per code, complete scoring metadata
# --------------------------------------------------------------------------- #
def test_missing_criterion_is_error():
    evidence = build_evidence(met("PM2", "Supporting"))
    evidence = [e for e in evidence if e["criterion"] != "PP4"]
    result = run(args(evidence))
    assert result["status"] == "error"
    assert "PP4" in result["error"]


def test_duplicate_criterion_is_error():
    evidence = build_evidence(met("PM2", "Supporting"))
    evidence.append(met("PM2", "Supporting"))
    result = run(args(evidence))
    assert result["status"] == "error"
    assert "PM2" in result["error"]


def test_unknown_criterion_is_error():
    evidence = build_evidence()
    evidence.append(ev("PX9", "not_assessed"))
    result = run(args(evidence))
    assert result["status"] == "error"


def test_met_without_strength_is_error():
    result = run(args(build_evidence(met("PM2", None))))
    assert result["status"] == "error"


def test_met_with_illegal_strength_is_error():
    result = run(args(build_evidence(met("PM2", "Extremely Strong"))))
    assert result["status"] == "error"


def test_met_without_rationale_is_error():
    bad = met("PM2", "Supporting")
    bad["rationale"] = "  "
    result = run(args(build_evidence(bad)))
    assert result["status"] == "error"
    assert "rationale" in result["error"]


@pytest.mark.parametrize("missing", ["source_refs", "rule_refs", "evidence_ids"])
def test_met_without_references_is_error(missing):
    bad = met("PM2", "Supporting")
    bad[missing] = []
    result = run(args(build_evidence(bad)))
    assert result["status"] == "error"
    assert missing in result["error"]


def test_non_met_with_strength_is_error():
    result = run(args(build_evidence(per_criterion={"PM2": dict(status="not_met", strength="Supporting")})))
    assert result["status"] == "error"


def test_illegal_status_is_error():
    result = run(args(build_evidence(per_criterion={"PM2": dict(status="maybe")})))
    assert result["status"] == "error"


def test_evidence_item_with_extra_key_is_error():
    bad = met("PM2", "Supporting")
    bad["points"] = 8
    result = run(args(build_evidence(bad)))
    assert result["status"] == "error"


def test_pp5_and_bp6_cannot_score():
    for code in ("PP5", "BP6"):
        result = run(args(build_evidence(met(code, "Supporting"))))
        assert result["status"] == "error", code
        assert code in result["error"]


def test_caller_supplied_total_score_is_rejected():
    result = run(args(build_evidence(met("PM2", "Supporting")), total_score=10))
    assert result["status"] == "error"


def test_caller_supplied_expected_classification_is_rejected():
    result = run(
        args(build_evidence(met("PM2", "Supporting")),
             expected_classification="Pathogenic")
    )
    assert result["status"] == "error"


def test_missing_blocking_issues_field_is_error():
    payload = args(build_evidence(met("PM2", "Supporting")))
    del payload["blocking_issues"]
    result = run(payload)
    assert result["status"] == "error"


def test_blocking_issues_must_be_list():
    result = run(args(build_evidence(met("PM2", "Supporting")), blocking_issues="none"))
    assert result["status"] == "error"


def test_variant_context_requires_variant_and_gene():
    ctx = {"variant": "", "gene": "MYOC", "disease": None, "inheritance_mode": None}
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    assert result["status"] == "error"


def test_rule_context_requires_status_and_method():
    rc = {"cspec_lookup_status": "no_released_spec"}
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# Scoring consistency
# --------------------------------------------------------------------------- #
def test_same_fact_used_twice_requires_review():
    shared = "gnomad-MYOC-af-zero"
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting", fact=shared),
                met("BS1", "Strong", fact=shared),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "duplicate_scoring_facts" in reasons


def test_same_paper_different_facts_is_not_duplicate():
    result = run(
        args(
            build_evidence(
                met("PS3", "Strong", fact="assay-lof", paper="PMID:9"),
                met("BS3", "Strong", fact="assay-wt", paper="PMID:9"),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 0


def test_no_scoring_evidence_pauses_rather_than_zero_vus():
    result = run(args(build_evidence(base_status="not_met")))
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "no_scoring_evidence" in reasons


def test_criterion_marked_needs_review_stays_uncounted():
    result = run(
        args(
            build_evidence(
                met("PP3", "Supporting"),
                per_criterion={"PM2": dict(status="needs_review")},
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 1
    uncounted = {u["criterion"]: u for u in data["uncounted_records"]}
    assert uncounted["PM2"]["status"] == "needs_review"


def test_phase_and_validation_gaps_are_kept_not_assumed():
    # Plan acceptance: insufficient segregation phase (PM3/BP2) and
    # under-validated functional data (PS3) must stay visible gaps -- they are
    # recorded uncounted and never silently upgraded to met evidence.
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                per_criterion={
                    "PM3": dict(
                        status="needs_review",
                        rationale="variant in trans with pathogenic allele; phase unconfirmed",
                    ),
                    "BP2": dict(
                        status="needs_review",
                        rationale="possible cis configuration; phase unknown",
                    ),
                    "PS3": dict(
                        status="needs_review",
                        rationale="single biochemical study without benign controls",
                    ),
                },
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 1  # only PM2_Supporting scores
    uncounted = {u["criterion"]: u for u in data["uncounted_records"]}
    for code in ("PM3", "BP2", "PS3"):
        assert uncounted[code]["status"] == "needs_review"
    scored = [c["criterion"] for c in data["point_contributions"]]
    assert scored == ["PM2"]


def test_deprecated_status_recorded_not_scored():
    result = run(
        args(
            build_evidence(
                met("PP3", "Supporting"),
                per_criterion={"PP5": dict(status="deprecated"),
                               "BP6": dict(status="deprecated")},
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 1
    uncounted = {u["criterion"]: u for u in data["uncounted_records"]}
    assert uncounted["PP5"]["status"] == "deprecated"
    assert uncounted["BP6"]["status"] == "deprecated"


# --------------------------------------------------------------------------- #
# Pause behavior: unresolved CSpec, incomplete material, unsupported combos
# --------------------------------------------------------------------------- #
def _spec_rule_context(status, complete=True, method="tavtigian2020"):
    return {
        "cspec_lookup_status": status,
        "combination_method": method,
        "specification": {
            "id": "GN019",
            "version": "2.1",
            "source_url": "https://cspec.genome.network/cspec/ui/svi/doc/GN019",
            "vcep": "Glaucoma Variant Curation Expert Panel",
        },
        "applicable_rules_complete": complete,
    }


def test_cspec_lookup_failed_pauses():
    result = run(
        args(
            build_evidence(met("PM2", "Supporting")),
            rule_context=_spec_rule_context("failed"),
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "cspec_applicability_unresolved" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_cspec_applicability_unresolved_pauses():
    result = run(
        args(
            build_evidence(met("PM2", "Supporting")),
            rule_context=_spec_rule_context("unresolved"),
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None


def test_incomplete_specification_material_pauses():
    result = run(
        args(
            build_evidence(met("PM2", "Supporting")),
            rule_context=_spec_rule_context("released_spec_found", complete=False),
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "incomplete_specification_material" in reasons


def test_missing_rules_complete_flag_is_input_error():
    # All four rule_context keys are required; omitting one is a structural
    # error, distinct from an explicit applicable_rules_complete=false.
    rc = _spec_rule_context("released_spec_found")
    del rc["applicable_rules_complete"]
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"
    assert "applicable_rules_complete" in result["error"]


def test_incomplete_generic_rules_pause():
    payload = args(build_evidence(
        met("PVS1", "VeryStrong"),
        met("PM2", "Supporting"),
    ))
    payload["rule_context"]["applicable_rules_complete"] = False

    data = run(payload)["data"]

    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "incomplete_specification_material" in {
        reason["reason"] for reason in data["review_reasons"]
    }


def test_incomplete_material_detail_does_not_suggest_generic_bypass():
    payload = args(build_evidence(met("PM2", "Supporting")))
    payload["rule_context"]["applicable_rules_complete"] = False

    reasons = run(payload)["data"]["review_reasons"]
    detail = next(
        r["detail"] for r in reasons
        if r["reason"] == "incomplete_specification_material"
    )
    assert "generic rules" not in str(detail).lower() or "do not" in str(detail).lower()
    # The old wording explicitly invited switching to generic rules; it must
    # be gone.
    assert "classify under generic rules explicitly" not in str(detail)


def test_ba1_gated_by_material_completeness():
    # BA1 must not short-circuit to Benign while the rule materials are
    # incomplete, whatever the CSpec status.
    payload = args(build_evidence(met("BA1", "StandAlone")))
    payload["rule_context"]["applicable_rules_complete"] = False

    data = run(payload)["data"]

    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "incomplete_specification_material" in {
        r["reason"] for r in data["review_reasons"]
    }


def test_unsupported_combination_method_pauses():
    # MYOC-style case: CSpec carries combination caps the fixed point system
    # cannot express (and PVS1 is not applicable per the specification).
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                per_criterion={"PVS1": dict(status="not_applicable")},
            ),
            rule_context=_spec_rule_context(
                "released_spec_found", complete=True, method="cspec_specific"
            ),
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "unsupported_combination_method" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_blocking_issues_pause_classification():
    result = run(
        args(
            build_evidence(met("PM2", "Supporting")),
            blocking_issues=["Variant identity ambiguous between transcripts"],
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "blocking_issues_present" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_needs_review_preserves_full_evidence_record():
    evidence = build_evidence(met("PM2", "Supporting"))
    result = run(args(evidence, blocking_issues=["unresolved segregation"]))
    data = result["data"]
    assert len(data["evidence"]) == 28
    pm2 = next(e for e in data["evidence"] if e["criterion"] == "PM2")
    assert pm2["status"] == "met"
    assert pm2["evidence_ids"] == ["fact-PM2"]


def test_released_spec_with_complete_materials_classifies():
    result = run(
        args(
            build_evidence(met("PVS1", "VeryStrong"), met("PM2", "Supporting")),
            rule_context=_spec_rule_context("released_spec_found", complete=True),
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9


# --------------------------------------------------------------------------- #
# SVI combination caps (enforced by the calculator)
# --------------------------------------------------------------------------- #
def test_pp1_pp4_locus_cap_pauses_above_five():
    # Biesecker 2023: PP1 + PP4 locus evidence capped at +5 points.
    result = run(
        args(build_evidence(met("PP1", "Strong"), met("PP4", "Moderate")))
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "locus_evidence_cap_exceeded" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_pp1_pp4_locus_cap_allows_five():
    result = run(
        args(build_evidence(met("PP1", "Strong"), met("PP4", "Supporting")))
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 5


def test_pp4_alone_above_locus_cap_pauses():
    # A single locus-evidence code above +5 also breaches the cap.
    result = run(args(build_evidence(met("PP4", "VeryStrong"))))
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert "locus_evidence_cap_exceeded" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_pp3_pm1_combined_cap_pauses_above_strong():
    # Pejaver 2022: PP3 + PM1 summed strength must not exceed Strong (= 4).
    result = run(
        args(build_evidence(met("PP3", "Strong"), met("PM1", "Moderate")))
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert "pp3_pm1_strength_cap_exceeded" in [
        r["reason"] for r in data["review_reasons"]
    ]


def test_pp3_pm1_combined_cap_allows_strong_sum():
    result = run(
        args(build_evidence(met("PP3", "Moderate"), met("PM1", "Moderate")))
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 4


# --------------------------------------------------------------------------- #
# Contract repair: strict types, completeness vs structure, references
# --------------------------------------------------------------------------- #
def test_variant_context_missing_key_is_error():
    ctx = {"variant": "NM_999999.1:c.1000C>T", "gene": "TESTGENE"}
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    assert result["status"] == "error"
    assert "disease" in result["error"]


@pytest.mark.parametrize("field", ["variant", "gene"])
@pytest.mark.parametrize("bad", [123, {}, [], None, "   "])
def test_variant_context_non_string_identity_is_error(field, bad):
    ctx = {
        "variant": "NM_999999.1:c.1000C>T",
        "gene": "TESTGENE",
        "disease": "Synthetic fixture disease",
        "inheritance_mode": "Autosomal dominant inheritance",
    }
    ctx[field] = bad
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    assert result["status"] == "error"


def test_disease_null_pauses_not_classifies():
    ctx = {
        "variant": "NM_999999.1:c.1000C>T",
        "gene": "TESTGENE",
        "disease": None,
        "inheritance_mode": "Autosomal dominant inheritance",
    }
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "incomplete_variant_context" in reasons


def test_inheritance_mode_blank_pauses():
    ctx = {
        "variant": "NM_999999.1:c.1000C>T",
        "gene": "TESTGENE",
        "disease": "Synthetic fixture disease",
        "inheritance_mode": "   ",
    }
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    assert "incomplete_variant_context" in [
        r["reason"] for r in result["data"]["review_reasons"]
    ]


def test_disease_wrong_type_is_error():
    ctx = {
        "variant": "NM_999999.1:c.1000C>T",
        "gene": "TESTGENE",
        "disease": {"mondo_id": "MONDO:1"},
        "inheritance_mode": "Autosomal dominant inheritance",
    }
    result = run(args(build_evidence(met("PM2", "Supporting")), variant_context=ctx))
    assert result["status"] == "error"


@pytest.mark.parametrize("bad", ["true", 1, None, []])
def test_applicable_rules_complete_must_be_boolean(bad):
    rc = _spec_rule_context("released_spec_found", complete=True)
    rc["applicable_rules_complete"] = bad
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"


def test_specification_empty_object_is_error():
    rc = _spec_rule_context("released_spec_found", complete=True)
    rc["specification"] = {}
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"


def test_specification_missing_field_is_error():
    rc = _spec_rule_context("released_spec_found", complete=True)
    del rc["specification"]["version"]
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"
    assert "version" in result["error"]


@pytest.mark.parametrize("bad_url", ["not-a-url", "ftp://example.org/doc", ""])
def test_specification_bad_source_url_is_error(bad_url):
    rc = _spec_rule_context("released_spec_found", complete=True)
    rc["specification"]["source_url"] = bad_url
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"
    assert "source_url" in result["error"]


def test_no_released_spec_with_specification_is_contradiction():
    rc = {
        "cspec_lookup_status": "no_released_spec",
        "combination_method": "tavtigian2020",
        "specification": _spec_rule_context("released_spec_found")["specification"],
        "applicable_rules_complete": True,
    }
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["status"] == "error"
    assert "contradictory" in result["error"]


def test_released_spec_found_without_specification_pauses():
    rc = _spec_rule_context("released_spec_found", complete=True)
    rc["specification"] = None
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "missing_specification_identity" in [
        r["reason"] for r in data["review_reasons"]
    ]


@pytest.mark.parametrize("field", [
    "source_refs", "rule_refs", "evidence_ids",
])
@pytest.mark.parametrize("bad", [None, "", "   ", 123, {}])
def test_met_rejects_invalid_reference_items(field, bad):
    record = met("PM2", "Supporting")
    record[field] = [bad]
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"
    assert field in result["error"]


def test_non_met_rejects_invalid_reference_items():
    # Empty lists are fine for non-met records, but [null]/[{}]/numbers are
    # not valid references in any state.
    record = ev("PM2", "not_met", source_refs=[None])
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"


def test_mixed_valid_and_invalid_reference_items_rejected():
    record = met("PM2", "Supporting")
    record["evidence_ids"] = ["fact-PM2", 42]
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"


def test_rationale_non_string_is_error():
    record = met("PM2", "Supporting")
    record["rationale"] = 123
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"


def test_blocking_issues_blank_string_is_error():
    result = run(
        args(build_evidence(met("PM2", "Supporting")), blocking_issues=["  "])
    )
    assert result["status"] == "error"


def test_criterion_non_string_is_error():
    evidence = build_evidence()
    evidence.append(ev(["PM2"], "not_met"))
    result = run(args(evidence))
    assert result["status"] == "error"


def test_status_non_string_is_error():
    record = ev("PM2", 5)
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"


def test_strength_non_string_for_met_is_error():
    record = met("PM2", {"level": 4})
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# Public SDK entry: key scenarios through the tool-manager path
# --------------------------------------------------------------------------- #
def _sdk_run(payload):
    from tooluniverse.tools import ACMG_calculate_classification

    return ACMG_calculate_classification(
        payload["variant_context"],
        payload["rule_context"],
        payload["evidence"],
        payload["blocking_issues"],
    )


# 2026-09-24 guardrail docs fix: the calculator has always accepted
# PM1 met/Moderate with no Released CSpec (the generic ACMG/AMP 2015
# rule). This regression FIXES that contract so a future eligibility
# gate cannot silently appear; it was NOT failing before the docs fix
# and must not be presented as a bug fix.
@pytest.mark.parametrize("invoke", [run, _sdk_run], ids=["handler", "sdk"])
def test_pm1_moderate_without_cspec_uses_generic_rule(invoke):
    payload = args(
        build_evidence(
            met("PM1", "Moderate", paper="synthetic:domain-evidence",
                rule="Richards2015:PM1", fact="synthetic-domain-1"),
            per_criterion={
                "PP5": {"status": "deprecated"},
                "BP6": {"status": "deprecated"},
            },
        ),
        rule_context={
            "cspec_lookup_status": "no_released_spec",
            "specification": None,
            "applicable_rules_complete": True,
            "combination_method": "tavtigian2020",
        },
    )
    assert len(payload["evidence"]) == 28
    result = invoke(payload)
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 2
    assert data["point_contributions"] == [
        {"criterion": "PM1", "strength": "Moderate",
         "points": 2, "direction": "pathogenic"}
    ]
    assert not data.get("review_reasons")


def test_sdk_computes_valid_synthetic_case():
    result = _sdk_run(
        args(build_evidence(met("PVS1", "VeryStrong"), met("PM2", "Supporting")))
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9


def test_sdk_rejects_illegal_reference_item():
    payload = args(build_evidence(met("PM2", "Supporting")))
    for record in payload["evidence"]:
        if record["criterion"] == "PM2":
            record["evidence_ids"] = [None]
    result = _sdk_run(payload)
    # Rejected with an explicit error (schema validation or handler) -- a
    # connection or parse failure must not satisfy this assertion either.
    assert isinstance(result, dict)
    assert result.get("status") == "error", result
    assert "error" in result


def test_sdk_pauses_incomplete_context():
    payload = args(build_evidence(met("PM2", "Supporting")))
    payload["variant_context"] = dict(payload["variant_context"], disease=None)
    result = _sdk_run(payload)
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None


def test_sdk_pauses_incomplete_rules_under_generic_context():
    payload = args(build_evidence(met("PVS1", "VeryStrong"), met("PM2", "Supporting")))
    payload["rule_context"]["applicable_rules_complete"] = False
    result = _sdk_run(payload)
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "incomplete_specification_material" in {
        r["reason"] for r in data["review_reasons"]
    }


# --------------------------------------------------------------------------- #
# Envelope and registration
# --------------------------------------------------------------------------- #
def test_envelope_marks_variant_classification_metadata():
    result = run(args(build_evidence(met("PM2", "Supporting"))))
    assert result["status"] == "success"
    assert result["metadata"] == {"calculator_type": "variant_classification"}


def test_error_envelope_for_illegal_input():
    result = run(args(build_evidence(met("PM2", None))))
    assert result == {"status": "error", "error": result["error"]}


def test_uncounted_records_cover_all_non_met():
    result = run(args(build_evidence(met("PM2", "Supporting"))))
    data = result["data"]
    assert len(data["uncounted_records"]) == 27
    assert data["point_contributions"] == [
        {
            "criterion": "PM2",
            "strength": "Supporting",
            "points": 1,
            "direction": "pathogenic",
        }
    ]


# --------------------------------------------------------------------------- #
# Repeated fact references within ONE criterion are not double counting
# --------------------------------------------------------------------------- #
def test_repeated_fact_within_one_code_does_not_block_sdk():
    record = met("PVS1", "VeryStrong", fact="assay-1")
    record["evidence_ids"].append("assay-1")
    payload = args(build_evidence(record, met("PM2", "Supporting")))

    data = _sdk_run(payload)["data"]

    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9


def test_repeated_fact_within_one_code_and_cross_code_sharing():
    # Same fact repeated inside PVS1 AND referenced by PM2: the review
    # still pauses (genuinely shared across codes), but the owner list
    # must not repeat the criterion.
    record = met("PVS1", "VeryStrong", fact="assay-1")
    record["evidence_ids"].extend(["assay-1", "assay-1"])
    pm2 = met("PM2", "Supporting", fact="assay-1")
    payload = args(build_evidence(record, pm2))

    data = run(payload)["data"]

    assert data["classification_status"] == "needs_review"
    reasons = {r["reason"]: r for r in data["review_reasons"]}
    detail = reasons["duplicate_scoring_facts"]["detail"]
    assert set(detail["shared_evidence_ids"]["assay-1"]) == {"PVS1", "PM2"}
    # No criterion appears twice in the owner list despite the repeats.
    assert len(detail["shared_evidence_ids"]["assay-1"]) == 2
    # The raw evidence record is preserved untouched, duplicates included.
    pvs1 = next(e for e in data["evidence"] if e["criterion"] == "PVS1")
    assert pvs1["evidence_ids"] == ["assay-1", "assay-1", "assay-1"]


# --------------------------------------------------------------------------- #
# 2026-11-03 (Batch A): raw SVI points for PP1/PP4 via optional svi_points.
#
# Biesecker et al., AJHG 2024;111:24-38 (online 2023-12,
# doi:10.1016/j.ajhg.2023.11.009): PP4 diagnostic-yield points (Table 2)
# and PP1 co-segregation points (Table 3) are fractional and NOT one-to-one
# with the Supporting/Moderate/Strong/VeryStrong ladder -- Table 4's 3-3.9
# and >=5 tiers have NO single-code label. Encoding e.g. yield 58.9%
# (rounds down to the 50.6% row -> 3.0 points) as Moderate(2) vs Strong(4)
# flipped a real TYR case between VUS and LP: the contract, not the caller,
# was defective. Optional svi_points (PP1/PP4, status met, finite, > 0)
# now carries the exact arithmetic; the cap CLAMPS to +5.0 per the paper
# ("evidence is capped at +5.0 points for all locus evidence"), while the
# integer-only path keeps its fail-closed pause.
# --------------------------------------------------------------------------- #
def met_sv(criterion, strength, svi_points, *, fact=None, paper="PMID:1"):
    rec = met(criterion, strength, fact=fact, paper=paper)
    rec["svi_points"] = svi_points
    return rec


def test_svi_points_pp4_raw_table_value_scores_exactly():
    # TYR NM_000372.5:c.1247C>A receipt shape: PM2 Sup(1) + PP3 Mod(2)
    # + PP4 3.0 (yield 58.9% rounds down to the 50.6% Table 2 row).
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                met("PP3", "Moderate"),
                met_sv("PP4", "Moderate", 3.0),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 6
    pp4 = next(c for c in data["point_contributions"] if c["criterion"] == "PP4")
    assert pp4["svi_points"] == 3.0
    assert pp4["points"] == 3.0
    locus = data["locus_evidence"]
    assert locus["raw_total"] == 3.0
    assert locus["applied_total"] == 3.0
    assert locus["capped"] is False


def test_svi_points_pp4_3_5_keeps_fractional_total():
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                met("PP3", "Moderate"),
                met_sv("PP4", "Strong", 3.5),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 6.5


def test_svi_points_score_is_independent_of_strength_label():
    # The original defect: same evidence, two strength labels, two
    # classifications. With svi_points the arithmetic no longer depends
    # on the label at all.
    totals = []
    for label in ("Supporting", "Moderate", "Strong", "VeryStrong"):
        result = run(
            args(
                build_evidence(
                    met("PM2", "Supporting"),
                    met("PP3", "Moderate"),
                    met_sv("PP4", label, 3.5),
                )
            )
        )
        totals.append((result["data"]["total_score"], result["data"]["classification"]))
    assert all(t == totals[0] for t in totals)


def test_svi_points_above_cap_clamps_to_five_with_disclosure():
    # Yield 86.4% -> Table 2 row 5.5; the paper CLAMPS locus evidence at
    # +5.0 ("capped at +5.0 points for all locus evidence"), it does not
    # pause. No review reason fires.
    result = run(args(build_evidence(met_sv("PP4", "VeryStrong", 5.5))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 5
    assert "review_reasons" not in data
    locus = data["locus_evidence"]
    assert locus["raw_total"] == 5.5
    assert locus["applied_total"] == 5.0
    assert locus["capped"] is True
    pp4 = next(c for c in data["point_contributions"] if c["criterion"] == "PP4")
    assert pp4["svi_points"] == 5.5
    assert pp4["points"] == 5.0


def test_svi_points_mixed_with_integer_counterpart_clamps_sum():
    # PP1 fractional 1.2 (Table 3, three AR unaffected) + integer PP4
    # Strong(4): raw 5.2 clamps to 5.0.
    result = run(
        args(
            build_evidence(
                met_sv("PP1", "Moderate", 1.2),
                met("PP4", "Strong"),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 5
    locus = data["locus_evidence"]
    assert locus["pp1_points"] == 1.2
    assert locus["pp4_points"] == 4
    assert locus["raw_total"] == 5.2
    assert locus["applied_total"] == 5.0
    assert locus["capped"] is True


def test_svi_points_pp1_unaffected_fractional_below_supporting():
    # Table 3 AR unaffected: 0.4 per relative -- below Supporting(1) and
    # unencodable before. One unaffected relative alone stays VUS at 0.4.
    result = run(args(build_evidence(met_sv("PP1", "Supporting", 0.4))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 0.4


def test_svi_points_rejected_outside_pp1_pp4():
    result = run(
        args(build_evidence(met_sv("PS4", "Strong", 3.0)))
    )
    assert result["status"] == "error"
    assert "PP1" in result["error"] and "PP4" in result["error"]


def test_svi_points_requires_met_status():
    result = run(
        args(build_evidence(ev("PP4", "not_met", svi_points=2.0)))
    )
    assert result["status"] == "error"


@pytest.mark.parametrize(
    "bad",
    [0, -1, True, float("nan"), float("inf"), float("-inf"), "3.5", None],
    ids=["zero", "negative", "bool", "nan", "inf", "-inf", "string", "null"],
)
def test_svi_points_must_be_positive_finite_number(bad):
    result = run(
        args(build_evidence(met_sv("PP4", "Moderate", bad)))
    )
    assert result["status"] == "error"


def test_pp4_ps4_both_met_independent_facts_compute():
    # 2026-11-09 (Batch B): the unconditional PP4+PS4 both-met pause is
    # removed. Biesecker 2024 still holds that a proband counts for one
    # code or the other -- but whether the two proband sets are
    # independent is a case-level fact the Skill workflow verifies, not
    # something the calculator can see. Distinct facts, no blocking
    # issue -> the calculator scores normally (2 + 4 = 6 -> LP).
    result = run(
        args(
            build_evidence(
                met("PP4", "Moderate", fact="cohort-yield"),
                met("PS4", "Strong", fact="case-count"),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 6
    assert "review_reasons" not in data


def test_pp4_ps4_both_met_unknown_independence_pauses_via_blocking_issues():
    # Independence unconfirmed -> the workflow carries it in
    # blocking_issues; the calculator pauses through the existing
    # blocking_issues_present reason and emits NO total_score. No
    # dedicated exclusivity machinery is added.
    result = run(
        args(
            build_evidence(
                met("PP4", "Moderate", fact="cohort-yield"),
                met("PS4", "Strong", fact="case-count"),
            ),
            blocking_issues=[
                "PP4/PS4 proband-set independence not yet confirmed"
            ],
        )
    )
    data = result["data"]
    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "total_score" not in data
    reasons = [r["reason"] for r in data["review_reasons"]]
    assert "blocking_issues_present" in reasons
    assert "pp4_ps4_proban_exclusivity" not in reasons


def test_pp4_ps4_shared_fact_flags_duplicate_only():
    # Shared evidence_ids keep the existing duplicate-fact pause; the
    # removed exclusivity reason must NOT reappear.
    result = run(
        args(
            build_evidence(
                met("PP4", "Moderate", fact="same-cohort"),
                met("PS4", "Strong", fact="same-cohort"),
            )
        )
    )
    reasons = [r["reason"] for r in result["data"]["review_reasons"]]
    assert "duplicate_scoring_facts" in reasons
    assert "pp4_ps4_proban_exclusivity" not in reasons


def test_pp4_ps4_same_paper_distinct_facts_are_not_duplicates():
    # Different facts from the same paper are NOT double counting --
    # existing dedup semantics, now guarding the PP4/PS4 pair directly.
    result = run(
        args(
            build_evidence(
                met("PP4", "Moderate", fact="pmid-9-yield", paper="PMID:9"),
                met("PS4", "Strong", fact="pmid-9-count", paper="PMID:9"),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert "review_reasons" not in data


def test_integer_locus_cap_pause_unchanged_when_no_svi_points():
    # Integer-only path keeps the fail-closed pause (existing pinned
    # behavior; Table 4's legal integer combos never exceed +5).
    result = run(
        args(build_evidence(met("PP1", "Strong"), met("PP4", "Moderate")))
    )
    assert result["data"]["classification_status"] == "needs_review"
    assert "locus_evidence_cap_exceeded" in [
        r["reason"] for r in result["data"]["review_reasons"]
    ]
    # No locus_evidence disclosure block on the integer path: existing
    # receipt shapes stay byte-stable.
    assert "locus_evidence" not in result["data"]


def test_svi_points_absent_keeps_receipt_shape_unchanged():
    # Control: without svi_points no locus_evidence block, no method
    # extension -- the pre-existing receipt shape is preserved exactly.
    result = run(args(build_evidence(met("PP4", "Moderate"))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 2
    assert "locus_evidence" not in data
    assert "svi_points" not in data["method"]
    pp4 = next(c for c in data["point_contributions"] if c["criterion"] == "PP4")
    assert "svi_points" not in pp4


# --------------------------------------------------------------------------- #
# 2026-11-09 (Batch A): fractional arithmetic, extreme values, and the
# continuous Likely-Benign interval.
#
# Acceptance findings being remediated here:
#   A1. _acmg_num rounded totals to one decimal -- 1 + 2 + 2.99 = 5.99 was
#       reported as 6. (Provenance corrected 2026-11-09 closeout: ec350710
#       actually returned VUS with total_score 6.0 -- a self-contradictory
#       receipt, since classification used the unrounded 5.99 while the
#       reported score sat in the LP band. A synthetic contract
#       counterexample, not a real clinical case, and not an actual
#       Likely Pathogenic return.)
#   A2. The locus clamp subtracted its way back from the raw total
#       (raw - 5.0, then drain entries). At 1e20 the subtraction is
#       absorbed by the float and the entry is zeroed instead of capped:
#       a single 1e20 svi_points scored 0, not 5.
#   A3. PP1 0.4 + benign -7 = -6.6 fell to Benign: only integer interval
#       boundaries (-6/-7) existed for the Likely Benign band.
#   A4. PP1 1e308 + PP4 1e308 overflowed to inf and silently scored 0
#       -- no explicit error.
#   A5. Non-svi contributions were float-coerced (4.0 instead of 4).
# Sums use math.fsum; totals are emitted at full computed precision
# (integral sums stay int) and classified on the same unrounded value.
# --------------------------------------------------------------------------- #
import json  # noqa: E402  (local to the 2026-11-09 acceptance block)


def test_fractional_2_99_is_not_rounded_up_to_six():
    # 1 + 2 + 2.99 = 5.99 -> VUS. The old defect (ec350710): the receipt
    # said total_score 6.0 while classification stayed VUS -- score and
    # classification contradicted each other. Never round the reported
    # total away from the value the classification used.
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                met("PP3", "Moderate"),
                met_sv("PP4", "Moderate", 2.99),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == pytest.approx(5.99)
    assert data["total_score"] < 6


@pytest.mark.parametrize(
    "pp4_points, expected_class, expected_total",
    [
        (2.99, "Likely Pathogenic", pytest.approx(9.99)),
        (3.0, "Pathogenic", 10),
    ],
    ids=["9.99-stays-lp", "10.0-is-p"],
)
def test_lp_pathogenic_boundary_is_not_moved_by_rounding(
    pp4_points, expected_class, expected_total
):
    # 7 integer points (PS1 Strong 4 + PM1 Moderate 2 + PM2 Supporting 1)
    # plus PP4: 9.99 must stay Likely Pathogenic; 10 is Pathogenic.
    result = run(
        args(
            build_evidence(
                met("PS1", "Strong"),
                met("PM1", "Moderate"),
                met("PM2", "Supporting"),
                met_sv("PP4", "Moderate", pp4_points),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == expected_class
    assert data["total_score"] == expected_total


_BENIGN_MINUS_7 = (
    met("BS1", "Strong"),
    met("BS3", "Moderate"),
    met("BP4", "Supporting"),
)


def test_pp1_0_4_with_benign_minus_7_is_likely_benign():
    # -7 + 0.4 = -6.6: inside the continuous Likely Benign band
    # (-7 < total < 0), not Benign.
    result = run(
        args(build_evidence(met_sv("PP1", "Supporting", 0.4), *_BENIGN_MINUS_7))
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Benign"
    assert data["total_score"] == pytest.approx(-6.6)
    assert -7 < data["total_score"] < 0


@pytest.mark.parametrize(
    "pp1_points, benign_items, expected_class",
    [
        (0.001, _BENIGN_MINUS_7, "Likely Benign"),  # -6.999, just above -7
        (0.6, (met("BS1", "Supporting"),), "Likely Benign"),  # -0.4, just below 0
    ],
    ids=["minus-6.999-lb", "minus-0.4-lb"],
)
def test_fractional_benign_band_intervals(pp1_points, benign_items, expected_class):
    result = run(
        args(build_evidence(met_sv("PP1", "Supporting", pp1_points), *benign_items))
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == expected_class
    assert -7 < data["total_score"] < 0


def test_integer_minus_seven_boundary_stays_benign():
    # Integer control: -7 exactly remains Benign (<= -7 boundary kept).
    result = run(args(build_evidence(*_BENIGN_MINUS_7)))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Benign"
    assert data["total_score"] == -7


@pytest.mark.parametrize("code", ["PP1", "PP4"])
def test_single_1e20_caps_to_five(code):
    # A single huge svi_points must cap at the +5.0 locus budget, not be
    # zeroed by raw-minus-cap float absorption (defect A2).
    result = run(args(build_evidence(met_sv(code, "Strong", 1e20))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 5
    locus = data["locus_evidence"]
    assert locus["raw_total"] == 1e20
    assert locus["applied_total"] == 5.0
    assert locus["capped"] is True
    entry = next(c for c in data["point_contributions"] if c["criterion"] == code)
    assert entry["points"] == 5.0


def test_single_1e308_still_caps_cleanly():
    # One 1e308 alone does not overflow anything: locus raw sum is finite,
    # applied is 5.
    result = run(args(build_evidence(met_sv("PP4", "Strong", 1e308))))
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["total_score"] == 5
    locus = data["locus_evidence"]
    assert locus["raw_total"] == 1e308
    assert locus["applied_total"] == 5.0


def test_pp1_pp4_1e308_pair_errors_explicitly():
    # 1e308 + 1e308 overflows the float range: the calculator must return
    # an explicit status:"error" receipt (never inf/NaN in the payload,
    # never a silently-zeroed score) and the receipt must remain strictly
    # JSON-serializable.
    result = run(
        args(
            build_evidence(
                met_sv("PP1", "Strong", 1e308),
                met_sv("PP4", "Strong", 1e308),
            )
        )
    )
    assert result["status"] == "error"
    lowered = result["error"].lower()
    assert "overflow" in lowered or "float" in lowered or "finite" in lowered
    json.dumps(result, allow_nan=False)  # raises on Infinity/NaN tokens


def test_integer_receipts_keep_native_int_types():
    # Integer-only receipts (LP 9 here) keep native int point types:
    # contributions, pathogenic_points, and total_score (defect A5).
    result = run(
        args(
            build_evidence(
                met("PM2", "Supporting"),
                met("PS1", "Strong"),
                met("PS4", "Strong"),
            )
        )
    )
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert type(data["total_score"]) is int
    assert type(data["pathogenic_points"]) is int
    assert all(type(c["points"]) is int for c in data["point_contributions"])


def test_contribution_sums_reconcile_with_reported_totals():
    # Consistency invariant: contributions sum to pathogenic+benign and to
    # total_score; locus applied_total == min(raw_total, cap).
    cases = (
        [met("PM2", "Supporting"), met("PP3", "Moderate"),
         met_sv("PP4", "Moderate", 2.99)],
        [met_sv("PP1", "Moderate", 1.2), met("PP4", "Strong")],
        [met_sv("PP1", "Supporting", 0.4), *_BENIGN_MINUS_7],
    )
    for met_items in cases:
        data = run(args(build_evidence(*met_items)))["data"]
        p = sum(
            c["points"] for c in data["point_contributions"]
            if c["direction"] == "pathogenic"
        )
        b = sum(
            c["points"] for c in data["point_contributions"]
            if c["direction"] == "benign"
        )
        assert p == pytest.approx(data["pathogenic_points"])
        assert b == pytest.approx(data["benign_points"])
        assert p + b == pytest.approx(data["total_score"])
        locus = data["locus_evidence"]
        assert locus["applied_total"] == pytest.approx(
            min(locus["raw_total"], locus["cap"])
        )


def test_threshold_strings_track_the_scoring_path():
    # Integer receipts keep the classic integer table; svi_points receipts
    # carry the continuous fractional intervals in method.thresholds.
    integer_data = run(args(build_evidence(met("PP4", "Moderate"))))["data"]
    assert integer_data["method"]["thresholds"]["likely_pathogenic"] == "6 to 9"
    svi_data = run(args(build_evidence(met_sv("PP4", "Moderate", 3.5))))["data"]
    thresholds = svi_data["method"]["thresholds"]
    assert thresholds["pathogenic"] == "total >= 10"
    assert thresholds["likely_pathogenic"] == "6 <= total < 10"
    assert thresholds["vus"] == "0 <= total < 6"
    assert thresholds["likely_benign"] == "-7 < total < 0"
    assert thresholds["benign"] == "total <= -7"
