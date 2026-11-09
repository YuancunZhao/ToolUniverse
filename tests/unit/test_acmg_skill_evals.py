"""Offline checks for the ACMG skill's acceptance case definitions.

Contract checks only: unique case ids, referenced attachments exist, and
the synthetic case-3 payload still yields the expected result through the
REAL calculator handler. They do not assert that any LLM followed the
skill (that is the separate, recorded host acceptance).
"""

import json
from pathlib import Path

from tooluniverse.clinical_calculators_tool import _acmg_classification

SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "tooluniverse-acmg-variant-classification"
)
EVALS = SKILL_DIR / "evals" / "evals.json"


def _cases():
    return json.loads(EVALS.read_text())["evals"]


def test_case_ids_unique_and_complete():
    ids = [case["id"] for case in _cases()]
    assert ids == [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    ]
    assert len(set(ids)) == 17


def test_attachments_exist():
    for case in _cases():
        for relative in case["files"]:
            assert (SKILL_DIR / "evals" / relative).exists(), (
                case["id"],
                relative,
            )


def test_synthetic_case3_payload_computes_expected_result():
    payload = json.loads(
        (SKILL_DIR / "evals" / "files" / "case3-synthetic-calculator-input.json")
        .read_text()
    )
    # The retired criteria must be recorded as deprecated, never met.
    for record in payload["evidence"]:
        if record["criterion"] in ("PP5", "BP6"):
            assert record["status"] == "deprecated"
    result = _acmg_classification(payload)
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9


def test_case_14_15_codon_consistency():
    """Cases 14/15 must be codon-coherent on transcript NM_999997.1.

    2026-10-14 review follow-up: the previous fixtures asserted two
    different single-nucleotide changes of one Arg codon both yielding
    p.Arg334Gln, which no standard codon supports. The corrected blocks
    use reference codon GGA (Gly) at residue 334 so that the three
    substitutions below are all codon-consistent. The check uses the four
    literal standard codons directly -- no HGVS parsing dependency.
    """
    text = (
        SKILL_DIR
        / "evals"
        / "files"
        / "case11-15-splice-predictor-boundary-facts.md"
    ).read_text()
    codons = {"GGA": "Gly", "AGA": "Arg", "CGA": "Arg", "GTA": "Val"}
    expectations = [
        ("NM_999997.1", "GGA", 1000, "G", "A", "Gly334Arg"),
        ("NM_999997.1", "GGA", 1000, "G", "C", "Gly334Arg"),
        ("NM_999997.1", "GGA", 1001, "G", "T", "Gly334Val"),
    ]
    for transcript, ref, pos, ref_base, alt_base, protein in expectations:
        nt = f"{transcript}:c.{pos}{ref_base}>{alt_base}"
        assert nt in text, nt
        mutated = list(ref)
        offset = pos - ((334 - 1) * 3 + 1)
        assert 0 <= offset <= 2
        assert mutated[offset] == ref_base, (ref, pos, ref_base)
        mutated[offset] = alt_base
        alt = "".join(mutated)
        assert alt in codons, alt
        aa_ref, aa_alt = codons[ref], codons[alt]
        assert protein == f"{aa_ref}334{aa_alt}", (protein, aa_ref, aa_alt)
        assert f"p.{protein}" in text, protein


def test_fact_attachments_carry_no_expected_outputs():
    """Neutral-facts rule: the fixture files must not embed expected
    scoring, classification or calculator outcomes (those live in
    evals.json). Case 16's facts are additionally criterion-neutral: they
    describe the predicted splice outcome without naming PVS1, so a host
    cannot read the expected criterion status off the attachment.
    """
    shared_ban = ("total_score", "no_scoring_evidence", "needs_review")
    files = {
        "case11-15-splice-predictor-boundary-facts.md": shared_ban,
        "case16-donor-rescue-na-facts.md": shared_ban
        + ("pvs1", "not applicable", "classification"),
        "case17-single-reference-facts.md": shared_ban
        + ("ps1", "pm5", "classification", "strong", "vus"),
    }
    for name, banned in files.items():
        normalized = " ".join(
            (SKILL_DIR / "evals" / "files" / name)
            .read_text()
            .replace("**", "")
            .replace("`", "")
            .split()
        ).casefold()
        for marker in banned:
            assert marker.casefold() not in normalized, (name, marker)


def test_case16_requires_predicted_functional_donor_without_experiments():
    """Case 16 pins the rescue N/A boundary the reference must support.

    The facts must state a sourced, framework-supported prediction of a
    functional GC donor (no variant-specific RNA/protein experiments)
    while explicitly NOT demanding such experiments for the N/A path;
    the eval's expected output must be the faithful needs_review pause
    (no met criteria -> no score), never a fabricated total.
    """
    facts = (
        SKILL_DIR / "evals" / "files" / "case16-donor-rescue-na-facts.md"
    ).read_text()
    normalized = " ".join(facts.replace("**", "").replace("`", "").split()).casefold()
    for marker in (
        "nm_999996.1:c.1200+2t>c",
        "gc",
        "predicted",
        "no variant-specific",
    ):
        assert marker in normalized, marker
    case16 = next(c for c in _cases() if c["id"] == 16)
    joined = " ".join(
        [case16["expected_output"]] + case16["assertions"]
    ).casefold()
    assert "needs_review" in joined
    assert "no_scoring_evidence" in joined
    assert "not applicable" in joined
    assert "experiment" in joined


def test_case_17_single_reference_codon_consistency():
    """Case 17 must be codon-coherent on transcript NM_999995.1.

    2026-10-23 review follow-up: one reference variant (c.1000G>C) must not
    be allowed to support BOTH the same-amino-acid comparison and the
    different-amino-acid comparison. Reference codon GGA (Gly) at residue
    334 spans c.1000_1002, so both c.1000 substitutions below are
    codon-consistent. The check uses the four literal standard codons
    directly -- no HGVS parsing dependency.
    """
    text = (
        SKILL_DIR / "evals" / "files" / "case17-single-reference-facts.md"
    ).read_text()
    codons = {"GGA": "Gly", "AGA": "Arg", "CGA": "Arg", "GTA": "Val"}
    expectations = [
        ("NM_999995.1", "GGA", 1000, "G", "A", "Gly334Arg"),
        ("NM_999995.1", "GGA", 1000, "G", "C", "Gly334Arg"),
    ]
    for transcript, ref, pos, ref_base, alt_base, protein in expectations:
        nt = f"{transcript}:c.{pos}{ref_base}>{alt_base}"
        assert nt in text, nt
        mutated = list(ref)
        offset = pos - ((334 - 1) * 3 + 1)
        assert 0 <= offset <= 2
        assert mutated[offset] == ref_base, (ref, pos, ref_base)
        mutated[offset] = alt_base
        alt = "".join(mutated)
        assert alt in codons, alt
        aa_ref, aa_alt = codons[ref], codons[alt]
        assert protein == f"{aa_ref}334{aa_alt}", (protein, aa_ref, aa_alt)
        assert f"p.{protein}" in text, protein


def test_case_17_expected_outcome_lives_only_in_assertions():
    """Case 17 pins the one-reference-one-comparison boundary.

    The single reference variant establishes the same amino-acid change,
    so only the same-change comparison is supported; the different-change
    comparison has no reference at all. Expected codes live in evals.json
    (PS1 Strong, PM5 unsatisfied, calculator receipt computed/VUS at 4
    points), never in the fact attachment.
    """
    facts = (
        SKILL_DIR / "evals" / "files" / "case17-single-reference-facts.md"
    ).read_text()
    normalized = " ".join(facts.replace("**", "").replace("`", "").split()).casefold()
    for marker in (
        "nm_999995.1",
        "gga",
        "c.1000g>a",
        "c.1000g>c",
        "no other pathogenic",
    ):
        assert marker in normalized, marker
    case17 = next(c for c in _cases() if c["id"] == 17)
    joined = " ".join(
        [case17["expected_output"]] + case17["assertions"]
    ).casefold()
    assert "ps1" in joined
    assert "strong" in joined
    assert "pm5" in joined
    assert "computed" in joined
    assert "vus" in joined
    assert "total_score" in joined and "4" in joined


def test_case_17_receipt_matches_real_calculator():
    """2026-10-28 follow-up (Batch B): the case-17 expected receipt must
    match what the REAL calculator returns for the case-17 evidence
    pattern -- 28 records, PS1 met at Strong as the only scorer, PM5
    not_met, PP5/BP6 deprecated, everything else not_assessed. The old
    wording claimed "Uncertain significance", a label the calculator
    never emits (it returns classification "VUS"). This is an offline
    calculator-contract test, NOT an LLM acceptance.
    """

    def ev(criterion, status="not_assessed", **kw):
        record = {
            "criterion": criterion,
            "status": status,
            "strength": None,
            "rationale": "",
            "source_refs": [],
            "rule_refs": [],
            "evidence_ids": [],
        }
        record.update(kw)
        return record

    pathogenic = [
        "PVS1", "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
    ]
    benign = [
        "BA1", "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
    ]
    special = {
        "PS1": ev(
            "PS1",
            "met",
            strength="Strong",
            rationale=(
                "Reference variant NM_999995.1:c.1000G>C (p.Gly334Arg, "
                "expert-panel established) carries the same amino-acid "
                "change; neither variant acts through splicing"
            ),
            source_refs=["SCV000000000 (fixture)"],
            rule_refs=["ACMG/AMP 2015 PS1"],
            evidence_ids=["fixture:17-ps1-reference"],
        ),
        "PM5": ev(
            "PM5",
            "not_met",
            rationale=(
                "The sole reference carries the same amino-acid change, so "
                "no different-change reference exists at residue 334"
            ),
        ),
        "PP5": ev(
            "PP5",
            "deprecated",
            rationale=(
                "Retired criterion (ClinGen SVI PP5/BP6 discontinuation); "
                "recorded, never scored"
            ),
        ),
        "BP6": ev(
            "BP6",
            "deprecated",
            rationale=(
                "Retired criterion (ClinGen SVI PP5/BP6 discontinuation); "
                "recorded, never scored"
            ),
        ),
    }
    evidence = [special.get(c, ev(c)) for c in pathogenic + benign]
    assert len(evidence) == 28
    payload = {
        "variant_context": {
            "variant": "NM_999995.1:c.1000G>A",
            "gene": "TESTGENE4",
            "disease": "Synthetic single-reference disease",
            "inheritance_mode": "Autosomal dominant inheritance",
        },
        "rule_context": {
            "cspec_lookup_status": "no_released_spec",
            "combination_method": "tavtigian2020",
            "specification": None,
            "applicable_rules_complete": True,
        },
        "evidence": evidence,
        "blocking_issues": [],
    }
    result = _acmg_classification(payload)
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 4
    # The canonical receipt phrase built from the ACTUAL return must be
    # present verbatim (casefolded) in the case-17 eval text.
    receipt = (
        f'classification_status "{data["classification_status"]}", '
        f'classification "{data["classification"]}", '
        f'total_score {data["total_score"]}'
    ).casefold()
    case17 = next(c for c in _cases() if c["id"] == 17)
    joined = " ".join(
        [case17["expected_output"]] + case17["assertions"]
    ).casefold()
    assert receipt in joined, receipt


# --------------------------------------------------------------------------- #
# 2026-11-03 follow-up (Batch B): the PP4 entry documented only a gloss of
# Biesecker Table 2 ("floor +1.0 at ~20%"), which contradicted the table's
# own lowest row (19.1% -> 1.0), omitted Table 4's combined tiers, and
# never defined how fractional points encode. These guards pin the
# corrected documentation: verbatim Table 2 rows, the <19.1% boundary, the
# paper's diagnostic-yield definition, the no-single-label tiers, and the
# svi_points calculator contract.
# --------------------------------------------------------------------------- #
def _reference_text():
    # Whitespace-normalized: documented phrases wrap across lines.
    return " ".join(
        (SKILL_DIR / "SVI_REFERENCE.md").read_text().replace("`", "").split()
    ).casefold()


def test_svi_reference_pp4_table2_rows_are_verbatim():
    text = _reference_text()
    for row in (
        "19.1%→1.0",
        "25.4%→1.5",
        "50.6%→3.0",
        "59.6%→3.5",
        "68.0%→4.0",
        "81.6%→5.0",
        "86.4%→5.5",
        "90.2%→6.0",
        "99.9%→12.0",
    ):
        assert row in text, row
    # The corrected boundary replaces the old governing sentence (the
    # correction note itself may quote the old "<20%" gloss).
    assert "<19.1%" in text
    assert "yield <20%" not in text


def test_svi_reference_pp4_carries_paper_yield_definition():
    text = _reference_text()
    for phrase in (
        "historical demonstrated yield",
        "similar to the methodology",
        "phenotype criteria matching",
    ):
        assert phrase in text, phrase


def test_svi_reference_documents_table4_and_no_single_label_tiers():
    text = _reference_text()
    assert "3–3.9" in text or "3-3.9" in text
    assert "no single-code strength label" in text
    assert "supporting+moderate" in text


def test_svi_reference_documents_svi_points_contract():
    text = _reference_text()
    for phrase in (
        "svi_points",
        "positive finite",
        "clamps the sum at +5.0",
    ):
        assert phrase in text, phrase
    # 2026-11-09 (Batch B): the unconditional PP4+PS4 pause is gone; the
    # reference must describe the workflow-owned three-state check instead.
    assert "proban_exclusivity" not in text
    for phrase in (
        "confirmed independent",
        "independence unknown",
        "confirmed overlap",
        "blocking_issues",
        "duplicate_scoring_facts",
    ):
        assert phrase in text, phrase


def _skill_step(number):
    """Extract one 'Fixed Pipeline' step body from SKILL.md.

    Steps are marked '**N.'; the body runs to the next step marker or the
    next '## ' heading, whichever comes first. Backticks are stripped and
    whitespace joined to match the whole-document normalization below.
    """
    text = (SKILL_DIR / "SKILL.md").read_text().replace("`", "")
    start = text.index(f"**{number}.")
    ends = [
        i
        for i in (
            text.find(f"**{n}.", start + 1) for n in range(number + 1, 9)
        )
        if i != -1
    ]
    heading = text.find("\n## ", start + 1)
    if heading != -1:
        ends.append(heading)
    end = min(ends) if ends else len(text)
    return " ".join(text[start:end].split()).casefold()


def test_skill_documents_svi_points_and_independence_workflow():
    text = " ".join(
        (SKILL_DIR / "SKILL.md").read_text().replace("`", "").split()
    ).casefold()
    assert "svi_points" in text
    assert "clamps the locus sum at +5" in text
    assert "the only sanctioned numeric field" in text
    assert "biesecker 2024" in text
    # 2026-11-09 (Batch B): independence is decided in step 5 -- three
    # states, no calculator pause, no dedicated confirmation machinery.
    assert "proband-set independence" in text
    assert "confirmed independent" in text
    assert "independence unknown" in text
    assert "confirmed overlap" in text
    assert "no longer pauses on a bare pp4+ps4 both-met" in text
    # 2026-11-09 closeout (Batch C): steps 4 and 6 must each name PP1, PP4,
    # and the optional svi_points in their own text -- a mention that lives
    # only in Standing Rules does not satisfy the fixed pipeline.
    for number in (4, 6):
        step = _skill_step(number)
        for phrase in ("pp1", "pp4", "the optional svi_points"):
            assert phrase in step, (number, phrase)
