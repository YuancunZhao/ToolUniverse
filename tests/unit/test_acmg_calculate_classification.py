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
        "variant_context": variant_context
        or {
            "variant": "NM_000715.3:c.1000C>T",
            "gene": "MYOC",
            "disease": None,
            "inheritance_mode": None,
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


def test_missing_rules_complete_flag_fails_closed():
    rc = _spec_rule_context("released_spec_found")
    del rc["applicable_rules_complete"]
    result = run(args(build_evidence(met("PM2", "Supporting")), rule_context=rc))
    assert result["data"]["classification_status"] == "needs_review"


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
