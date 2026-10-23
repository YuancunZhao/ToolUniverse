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
    (PS1 Strong, PM5 unsatisfied, calculator VUS at 4 points), never in
    the fact attachment.
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
    assert "uncertain significance" in joined
    assert "total_score" in joined or "4" in joined
