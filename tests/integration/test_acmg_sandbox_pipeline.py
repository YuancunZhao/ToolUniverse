"""End-to-end scoped source sandbox to deterministic evidence rule tests.

Covers: raw provider output → ACMG scoped executor → explicit rule input → group rule.

Test scope:
  - GeneBe sandbox remains a lead while an explicit population input reaches PM2 rule
  - Non-high-risk passthrough
  - Error status preservation
  - ClinVar criteria remain source assertions
"""

from __future__ import annotations


class _RawRuntime:
    def __init__(self, result):
        self.result = result

    def run_one_function(self, _call, **_kwargs):
        return self.result


def test_genebe_sandbox_to_overlay_pipeline():
    """GeneBe output stays quarantined while explicit population data reaches PM2."""
    from tooluniverse.acmg.policy import ACMGScopedExecutor
    from tooluniverse.acmg.population import population_evidence

    # Simulated GeneBe output with classification fields
    genebe_raw = {
        "classification": "Pathogenic",
        "clinical_significance": "Likely pathogenic",
        "acmg_criteria": ["PM2", "PP3"],
        "gene": "BRCA2",
        "transcript": "NM_000059.4",
        "allele_frequency": 0.00001,
        "allele_number": 50000,
    }

    # Step 1: Sanitize — high-risk tool must produce source-lead-only output
    sandboxed = ACMGScopedExecutor(_RawRuntime(genebe_raw)).call(
        "GeneBe_classify_variant",
        {},
    )
    assert sandboxed["source_lead_only"] is True
    assert sandboxed["final_classification_allowed"] is False
    sandbox = sandboxed["source_lead_sandbox"]
    assert sandbox["quarantined_conclusions"]["classification"] == "Pathogenic"
    assert sandbox["reviewable_features"]["gene"] == "BRCA2"

    # Step 2: Evaluate normalized population data through the group API.
    cards = population_evidence(
        gnomad_an=50000,
        gnomad_ac=0,
        gnomad_af_global=0.0,
        gnomad_af_popmax=0.0,
        coverage_adequate=True,
    )
    result = next(card for card in cards if card.criterion == "PM2")
    assert result.strength == "PM2_Supporting"
    assert result.evidence_status == "rule_mapped"
    assert result.rule_source["type"] == "versioned_svi"

    # Verify sanitized output has no leaked classification.
    assert "classification" not in sandbox["reviewable_features"]
    # Non-classification reviewable features are preserved
    assert sandbox["reviewable_features"]["gene"] == "BRCA2"
    assert sandbox["reviewable_features"]["transcript"] == "NM_000059.4"


def test_non_high_risk_passthrough():
    """Non-high-risk tools must pass through sanitize unchanged."""
    from tooluniverse.acmg.policy import ACMGScopedExecutor

    result = ACMGScopedExecutor(_RawRuntime({"value": 42, "status": "ok"})).call(
        "Some_normal_tool", {}
    )
    assert result == {"value": 42, "status": "ok"}


def test_high_risk_tool_passthrough_without_acmg_policy_context():
    """Ordinary ToolUniverse calls retain their upstream output contract."""
    raw = {"classification": "Pathogenic", "status": "ok"}
    result = _RawRuntime(raw).run_one_function(
        {"name": "GeneBe_classify_variant", "arguments": {}}
    )
    assert result is raw


def test_error_status_preserved_through_sandbox():
    """Error status on a high-risk tool is preserved in the sandbox envelope."""
    from tooluniverse.acmg.policy import ACMGScopedExecutor

    result = ACMGScopedExecutor(
        _RawRuntime({"status": "error", "error": "timeout"})
    ).call(
        "GeneBe_classify_variant",
        {},
    )
    assert result["status"] == "error"
    assert result["source_lead_only"] is True


def test_clinvar_sandbox_keeps_criteria_as_source_assertions():
    """ClinVar criteria remain quarantined source assertions, not route output."""
    from tooluniverse.acmg.policy import ACMGScopedExecutor

    result = ACMGScopedExecutor(
        _RawRuntime(
            {
                "clinicalSignificance": "Pathogenic",
                "criteria": "PM2, PP3",
                "variation_id": "12345",
                "reviewStatus": "criteria provided",
            }
        )
    ).call("ClinVar_get_clinical_significance", {})
    sandbox = result["source_lead_sandbox"]
    assert "candidate_routes" not in sandbox
    assert sandbox["quarantined_conclusions"]["criteria"] == "PM2, PP3"
