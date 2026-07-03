# ClinGen/SVI Guarded Overlay Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Narrow the current fork into an upstream ToolUniverse-compatible ClinGen/SVI guarded overlay extension while preserving a path toward a reliable, highly automated ACMG intelligent rating workflow.

**Architecture:** Upstream ToolUniverse remains the evidence retrieval and tool execution platform. This fork adds a guarded ACMG overlay layer: direct variant/pathogenicity tools produce source leads, deterministic overlay tools apply ClinGen/SVI criterion-specific recommendations, and final wording is blocked unless validator, semantic combiner, finalizer token, and final-answer guard all pass. Skills are retained as literature-backed documentation and routing guidance, not as the runtime criterion engine.

**Tech Stack:** Python 3.12, ToolUniverse MCP tool wrappers in `src/tooluniverse/tools/`, deterministic overlay modules in `src/tooluniverse/acmg_overlay_tools/`, ACMG gate modules in `src/tooluniverse/acmg_gate/`, JSON tool metadata in `src/tooluniverse/data/`, pytest via `uv run pytest`.

---

## File Structure

### Runtime Boundary

- `src/tooluniverse/acmg_overlay_tools/base.py`
  - Owns shared overlay output semantics.
  - Must prevent free-form VCEP override from becoming `overlay_applied` automatically.

- `src/tooluniverse/acmg_overlay_tools/pp3_bp4.py`
  - Owns Pejaver 2022 PP3/BP4 calibrated interval execution.
  - Must distinguish ClinGen/SVI calibrated intervals from local tool-selection policy.

- `src/tooluniverse/acmg_overlay_tools/router.py`
  - Owns variant-type-to-overlay planning.
  - Must not infer missense from a bare coding substitution without consequence evidence.

- `src/tooluniverse/acmg_overlay_tools/overlays.py`
  - Owns current non-PP3 overlay implementations.
  - Near-term scope is safety and wrapper compatibility, not full biological completeness.

- `src/tooluniverse/tools/ACMG_overlay_*.py`
  - Thin MCP wrappers around deterministic overlay modules.
  - Must have signatures synchronized with the called functions.

- `src/tooluniverse/data/acmg_overlay_gate_tools.json`
  - Tool metadata exposed to ToolUniverse discovery.
  - Must match wrapper signatures and must not advertise unsafe final-classification shortcuts.

### Gate and Anti-Bypass

- `src/tooluniverse/acmg_gate/validate_acmg_overlay_bundle.py`
  - Owns bundle validation and anti-bypass checks.
  - Must bind resolved counted evidence to exact overlay route audit rows.

- `src/tooluniverse/acmg_gate/semantic_combiner.py`
  - Owns conservative semantic validation of final classification claims.
  - Must compute only from validator-approved counted evidence.

- `src/tooluniverse/acmg_gate/source_lead_sandbox.py`
  - Owns direct-tool output quarantine and route candidates.
  - Must emit registry `criterion_group` ids, not legacy skill route aliases.

- `src/tooluniverse/acmg_gate_search.py`
  - Owns ACMG-aware tool discovery injection.
  - Must describe `ACMG_combine_criteria` as draft-only.

### Documentation and Mirror Hygiene

- `README.md`
  - Should describe this fork as a ClinGen/SVI guarded overlay extension, not a standalone clinical classifier.

- `docs/acmg_overlay_architecture.md`
  - Should state the narrowed architecture and final automation roadmap.

- `TOOLUNIVERSE_OVERLAY_DIFF.md`
  - Must stay aligned when canonical `skills/` content changes.

- `skills/tooluniverse-acmg-*/`
  - Canonical skill documentation.
  - Must not be the runtime criterion engine.

- `plugin/skills/` and `plugins/tooluniverse/skills/`
  - Committed mirrors.
  - Must remain drift-free after any canonical skill changes.

---

## Milestone 1: Restore Safe Tool-First Runtime Semantics

### Task 1: Make VCEP Override Non-Bypassable

**Files:**
- Modify: `src/tooluniverse/acmg_overlay_tools/base.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/pp3_bp4.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/pm2.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/ps1_pm5.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/ba1_exception.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/benign_context.py`
- Modify: `src/tooluniverse/acmg_overlay_tools/overlays.py`
- Test: `tests/unit/test_acmg_overlay_vcep_override.py`

- [ ] **Step 1: Write failing VCEP override tests**

Create `tests/unit/test_acmg_overlay_vcep_override.py`:

```python
from __future__ import annotations

from tooluniverse.acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4
from tooluniverse.acmg_overlay_tools.pm2 import overlay_pm2
from tooluniverse.acmg_overlay_tools.overlays import overlay_functional_assay


def test_vcep_override_is_deferred_not_overlay_applied():
    result = overlay_pp3_bp4(vcep_override="PP3_Strong")

    assert result["strength"] == "PP3_Strong"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
    assert result["overlay_validated"] is False
    assert result["counted"] is True


def test_vcep_override_requires_validator_scope_before_final():
    result = overlay_pm2(vcep_override="PM2")

    assert result["strength"] == "PM2"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
    assert "VCEP" in result["reason"]


def test_vcep_override_does_not_mask_wrapper_runtime_errors():
    result = overlay_functional_assay(vcep_override="PS3")

    assert result["criterion"] == "PS3/BS3"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
```

- [ ] **Step 2: Run the new test to confirm current failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_vcep_override.py -q
```

Expected: FAIL because current `vcep_override` returns `overlay_applied` and `overlay_validated=True`.

- [ ] **Step 3: Add a shared VCEP output helper**

In `src/tooluniverse/acmg_overlay_tools/base.py`, add:

```python
def vcep_deferred_template(
    criterion: str,
    strength: str,
    *,
    reason: str = "",
    source_of_truth: str = "VCEP specification",
    next_action: str = "Validate VCEP disease, gene, transcript, variant type, and scope in acmg_assessment_bundle.vcep_context.",
) -> dict[str, Any]:
    return output_template(
        criterion,
        strength,
        status="applied",
        route_outcome="overlay_deferred_to_vcep",
        guidance_authority="VCEP-specific",
        reason=reason or f"VCEP-specific rule proposed {strength}; validator must confirm scope before final classification.",
        source_of_truth=source_of_truth,
        next_action=next_action,
    )
```

Also add `vcep_deferred_template` to `__all__`.

- [ ] **Step 4: Replace direct `vcep_override` returns**

In every overlay module listed in this task, replace this pattern:

```python
if vcep_override:
    return output_template("PP3/BP4", vcep_override, reason=f"VCEP override: {vcep_override}")
```

with:

```python
if vcep_override:
    from .base import vcep_deferred_template

    return vcep_deferred_template(
        "PP3/BP4",
        vcep_override,
        reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
    )
```

Use the correct criterion string for each overlay, such as `PM2`, `PS1/PM5`, `BA1`, `PS3/BS3`, `PVS1`, or `PP1/BS4`.

- [ ] **Step 5: Run VCEP override tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_vcep_override.py -q
```

Expected: PASS.

- [ ] **Step 6: Run validator VCEP scope regression**

Run:

```bash
uv run pytest tests/unit/test_acmg_harness_runner.py tests/unit/test_acmg_tool_search_fail_closed.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/tooluniverse/acmg_overlay_tools tests/unit/test_acmg_overlay_vcep_override.py
git commit -m "fix: defer VCEP overlay overrides to validator scope checks"
```

### Task 2: Synchronize MCP Wrapper Signatures With Overlay Functions

**Files:**
- Modify: `src/tooluniverse/tools/ACMG_overlay_functional_assay.py`
- Modify: `src/tooluniverse/tools/ACMG_overlay_segregation.py`
- Modify: `src/tooluniverse/tools/ACMG_overlay_pvs1_splicing.py`
- Modify: `src/tooluniverse/tools/ACMG_overlay_case_enrichment.py`
- Modify: `src/tooluniverse/tools/ACMG_overlay_de_novo.py`
- Modify: `src/tooluniverse/data/acmg_overlay_gate_tools.json`
- Test: `tests/unit/test_acmg_overlay_wrapper_signatures.py`

- [ ] **Step 1: Write failing wrapper tests**

Create `tests/unit/test_acmg_overlay_wrapper_signatures.py`:

```python
from __future__ import annotations

from tooluniverse.tools.ACMG_overlay_functional_assay import ACMG_overlay_functional_assay
from tooluniverse.tools.ACMG_overlay_segregation import ACMG_overlay_segregation
from tooluniverse.tools.ACMG_overlay_pvs1_splicing import ACMG_overlay_pvs1_splicing
from tooluniverse.tools.ACMG_overlay_case_enrichment import ACMG_overlay_case_enrichment
from tooluniverse.tools.ACMG_overlay_de_novo import ACMG_overlay_de_novo


def test_functional_assay_wrapper_accepts_runtime_fields():
    result = ACMG_overlay_functional_assay(
        functional_evidence="variant-specific assay",
        assay_type="enzyme activity",
        variant_specific=True,
        replicated=True,
        has_controls=True,
        statistically_significant=True,
        effect_direction="loss of function",
    )

    assert result["criterion"] == "PS3"
    assert result["counted"] is True


def test_segregation_wrapper_uses_meioses_not_affected_relatives():
    result = ACMG_overlay_segregation(
        segregation_present=True,
        affected_meioses=3,
        total_meioses=3,
    )

    assert result["criterion"] == "PP1"
    assert result["strength"] == "PP1"


def test_pvs1_splicing_wrapper_accepts_structured_splice_inputs():
    result = ACMG_overlay_pvs1_splicing(
        spliceai_dl=0.7,
        is_canonical_gt_ag=True,
        rna_evidence=False,
        nmd_predicted=True,
    )

    assert result["criterion"] == "PVS1"
    assert result["strength"] == "PVS1_Moderate"


def test_case_enrichment_wrapper_passes_case_control_fields():
    result = ACMG_overlay_case_enrichment(
        case_count=10,
        control_count=1000,
        odds_ratio=3.0,
        confidence_interval_lower=1.2,
        phenotype_consistent=True,
    )

    assert result["criterion"] == "PS4"
    assert result["counted"] is True


def test_de_novo_wrapper_passes_phenotype_fields():
    result = ACMG_overlay_de_novo(
        de_novo_confirmed=True,
        paternity_confirmed=True,
        phenotype_consistent=True,
    )

    assert result["criterion"] == "PS2"
    assert result["strength"] == "PS2_Moderate"
```

- [ ] **Step 2: Run wrapper tests to confirm current failures**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_wrapper_signatures.py -q
```

Expected: FAIL on at least functional assay, segregation, PVS1 splicing, and missing metadata fields.

- [ ] **Step 3: Update wrapper function signatures**

Replace wrapper signatures so they exactly expose the underlying overlay function inputs.

For `src/tooluniverse/tools/ACMG_overlay_functional_assay.py`, use:

```python
def ACMG_overlay_functional_assay(
    functional_evidence="",
    assay_type="",
    assay_category="",
    assay_applicable_to_disease_mechanism=False,
    variant_specific=False,
    replicated=False,
    has_controls=False,
    statistically_significant=False,
    effect_direction="",
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_functional_assay(
        functional_evidence=functional_evidence,
        assay_type=assay_type,
        assay_category=assay_category,
        assay_applicable_to_disease_mechanism=assay_applicable_to_disease_mechanism,
        variant_specific=variant_specific,
        replicated=replicated,
        has_controls=has_controls,
        statistically_significant=statistically_significant,
        effect_direction=effect_direction,
        vcep_override=vcep_override,
    )
```

For `src/tooluniverse/tools/ACMG_overlay_segregation.py`, use `affected_meioses`, `total_meioses`, and `phenotype_highly_specific`.

For `src/tooluniverse/tools/ACMG_overlay_pvs1_splicing.py`, use `spliceai_dl`, `spliceai_da`, `is_canonical_gt_ag`, `rna_evidence`, and `nmd_predicted`.

For `src/tooluniverse/tools/ACMG_overlay_case_enrichment.py`, use `case_af`, `control_af`, `odds_ratio`, `confidence_interval_lower`, and `phenotype_consistent`.

For `src/tooluniverse/tools/ACMG_overlay_de_novo.py`, use `phenotype_highly_specific`, `phenotype_consistent`, and `genetic_heterogeneity_low`.

- [ ] **Step 4: Update JSON metadata for the same parameters**

In `src/tooluniverse/data/acmg_overlay_gate_tools.json`, update the parameter objects for the five tools so exposed JSON fields match the wrappers exactly. Remove obsolete fields:

```json
"effect_magnitude": {
  "type": "string",
  "description": "Magnitude of functional effect.",
  "default": ""
}
```

Replace with concrete boolean/string fields matching the wrapper signature.

- [ ] **Step 5: Run wrapper tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_wrapper_signatures.py -q
```

Expected: PASS.

- [ ] **Step 6: Run existing wrapper and harness tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_gate_notice_and_wrappers.py tests/unit/test_acmg_harness_runner.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/tooluniverse/tools src/tooluniverse/data/acmg_overlay_gate_tools.json tests/unit/test_acmg_overlay_wrapper_signatures.py
git commit -m "fix: synchronize ACMG overlay MCP wrapper signatures"
```

### Task 3: Require Exact Binding Between Route Audit and Resolved Counted Evidence

**Files:**
- Modify: `src/tooluniverse/acmg_gate/validate_acmg_overlay_bundle.py`
- Modify: `src/tooluniverse/acmg_gate/semantic_combiner.py`
- Test: `tests/unit/test_acmg_resolved_evidence_binding.py`

- [ ] **Step 1: Write failing mismatch test**

Create `tests/unit/test_acmg_resolved_evidence_binding.py`:

```python
from __future__ import annotations

from tooluniverse.acmg_gate.validate_acmg_overlay_bundle import validate


REGISTRY = [
    {
        "criterion_group": "pp3_bp4_missense_prediction",
        "scoring_criteria": ["PP3", "BP4"],
        "trigger_policy": "variant_type_baseline",
        "enforcement_level": "must_query",
        "applies_when": ["missense_variant"],
    }
]


def test_resolved_evidence_strength_must_match_counted_route_audit():
    bundle = {
        "variant": {"gene": "GENE", "consequence": "missense_variant"},
        "classification_status": "final classification",
        "classification": "Likely_pathogenic",
        "route_plan": [{"criterion_group": "pp3_bp4_missense_prediction"}],
        "coverage_audit": [
            {
                "source_category": "computational",
                "query_status": "success",
                "queried_sources": ["MyVariant"],
                "hits": [{"revel": 0.7}],
                "triggered_routes": ["pp3_bp4_missense_prediction"],
                "reason": "Retrieved predictor score.",
            },
            {
                "source_category": "literature",
                "query_status": "no_hit",
                "queried_sources": ["PubMed"],
                "query_terms": ["GENE variant"],
                "query_tool": "PubMed_search_articles",
                "not_triggered_routes": [
                    "pp1_bs4_pp4_segregation",
                    "ps4_case_enrichment",
                    "de_novo_ps2_pm6",
                    "pm3_in_trans",
                    "ps3_bs3_functional_assay",
                ],
                "reason": "No variant-specific evidence.",
            },
        ],
        "overlay_results": [],
        "route_audit": [
            {
                "criterion": "PP3",
                "proposed_evidence": "PP3_Supporting",
                "route_outcome": "overlay_applied",
                "guidance_authority": "ClinGen/SVI primary",
                "overlay_or_vcep_source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
                "counted": True,
                "reason": "REVEL 0.70.",
            }
        ],
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PP3", "strength": "PP3_Strong", "source": "manual"}
            ],
            "unresolved_conflicts": [],
        },
        "disease_context": {"status": "reviewed", "source": "ClinGen"},
        "vcep_context": {"scope_match": "not_applicable", "source": "none"},
        "penetrance_context": {"status": "reviewed", "source": "disease model"},
    }

    result = validate(bundle, REGISTRY)

    assert result["status"] != "PASS"
    assert any(v["code"] == "resolved_evidence_strength_mismatch" for v in result["violations"])
```

- [ ] **Step 2: Run test to confirm current failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_resolved_evidence_binding.py -q
```

Expected: FAIL because current validator accepts criterion-only matching.

- [ ] **Step 3: Add exact resolved-evidence matching helper**

In `validate_acmg_overlay_bundle.py`, replace `counted_row_matches_resolved` with logic that compares criterion and strength:

```python
def resolved_strength(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("strength") or item.get("applied_evidence") or item.get("proposed_evidence") or "")
    return resolved_item_text(item)


def counted_row_matches_resolved(row: dict[str, Any], resolved: list[Any]) -> bool:
    criterion = str(row.get("criterion", ""))
    proposed = str(row.get("proposed_evidence", ""))
    row_strength = str(row.get("strength") or proposed)
    source = text_of(row.get("overlay_or_vcep_source"))
    for item in resolved:
        text = resolved_item_text(item)
        item_strength = resolved_strength(item)
        item_source = text_of(item.get("source") or item.get("overlay_or_vcep_source")) if isinstance(item, dict) else ""
        criterion_matches = bool(criterion and criterion in text)
        strength_matches = bool(row_strength and row_strength in item_strength)
        source_matches = not item_source or not source or item_source == source
        if criterion_matches and strength_matches and source_matches:
            return True
    return False
```

- [ ] **Step 4: Emit a specific violation for criterion-only mismatch**

In the final-request compatibility block, when `resolved` exists and no exact match exists but a criterion-only match exists, add:

```python
add(
    DRAFT_ONLY,
    "resolved_evidence_strength_mismatch",
    "Resolved counted evidence must match route_audit by criterion and strength, not criterion alone.",
)
```

- [ ] **Step 5: Run binding tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_resolved_evidence_binding.py tests/unit/test_acmg_harness_runner.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tooluniverse/acmg_gate/validate_acmg_overlay_bundle.py src/tooluniverse/acmg_gate/semantic_combiner.py tests/unit/test_acmg_resolved_evidence_binding.py
git commit -m "fix: bind resolved ACMG evidence to exact route audit strengths"
```

### Task 4: Make PP3/BP4 Tool Selection Policy Explicit

**Files:**
- Modify: `src/tooluniverse/acmg_overlay_tools/pp3_bp4.py`
- Modify: `src/tooluniverse/tools/ACMG_overlay_pp3_bp4.py`
- Modify: `src/tooluniverse/data/acmg_overlay_gate_tools.json`
- Modify: `tests/unit/test_acmg_overlay_pp3_bp4.py`

- [ ] **Step 1: Update PP3/BP4 tests for explicit selection policy**

In `tests/unit/test_acmg_overlay_pp3_bp4.py`, replace the default-hierarchy counting expectation with:

```python
def test_no_selected_tool_returns_local_policy_not_assessed_when_multiple_scores_present():
    r = overlay_pp3_bp4(revel_score=0.80, cadd_phred=30.0)

    assert r["strength"] == "not_assessed"
    assert r["counted"] is False
    assert "selected_tool" in r["next_action"]
```

Add:

```python
def test_selected_tool_counts_pejaver_interval_as_clingen_svi_primary():
    r = overlay_pp3_bp4(selected_tool="REVEL", selection_policy="pre_specified", revel_score=0.80)

    assert r["criterion"] == "PP3"
    assert r["strength"] == "PP3_Moderate"
    assert r["guidance_authority"] == "ClinGen/SVI primary"
```

Add:

```python
def test_default_hierarchy_requires_local_policy_authority():
    r = overlay_pp3_bp4(cadd_phred=30.0, selection_policy="local_default_hierarchy")

    assert r["criterion"] == "PP3"
    assert r["strength"] == "PP3_Moderate"
    assert r["guidance_authority"] == "practice/local refinement"
```

- [ ] **Step 2: Run PP3/BP4 tests to confirm failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_pp3_bp4.py -q
```

Expected: FAIL because `selection_policy` is not implemented.

- [ ] **Step 3: Add `selection_policy` parameter**

In `overlay_pp3_bp4`, add:

```python
selection_policy: str | None = None,
```

Use these allowed policy values:

```python
EXPLICIT_SELECTION_POLICIES = {"pre_specified", "vcep_specific"}
LOCAL_SELECTION_POLICIES = {"local_default_hierarchy"}
```

If `selected_tool` is missing and `selection_policy != "local_default_hierarchy"`, return `not_assessed` with:

```python
next_action="Provide selected_tool with selection_policy='pre_specified' or explicitly use selection_policy='local_default_hierarchy'."
```

If `selection_policy == "local_default_hierarchy"`, keep the hierarchy but set:

```python
guidance_authority="practice/local refinement"
```

If `selected_tool` exists with `selection_policy in {"pre_specified", "vcep_specific"}`, keep:

```python
guidance_authority="ClinGen/SVI primary"
```

- [ ] **Step 4: Update wrapper and metadata**

Add `selection_policy=None` to `src/tooluniverse/tools/ACMG_overlay_pp3_bp4.py` and pass it through.

Add JSON metadata:

```json
"selection_policy": {
  "type": "string",
  "description": "How the selected predictor was chosen. Use pre_specified for a pre-score local/lab selection, vcep_specific for an in-scope VCEP rule, or local_default_hierarchy for this tool's documented fallback hierarchy."
}
```

- [ ] **Step 5: Run PP3/BP4 and tool metadata tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_overlay_pp3_bp4.py tests/unit/test_acmg_gate_notice_and_wrappers.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tooluniverse/acmg_overlay_tools/pp3_bp4.py src/tooluniverse/tools/ACMG_overlay_pp3_bp4.py src/tooluniverse/data/acmg_overlay_gate_tools.json tests/unit/test_acmg_overlay_pp3_bp4.py
git commit -m "fix: make PP3 BP4 predictor selection policy explicit"
```

### Task 5: Stop Router From Inferring Missense From Bare Coding Substitution

**Files:**
- Modify: `src/tooluniverse/acmg_overlay_tools/router.py`
- Test: `tests/unit/test_acmg_route_policy.py`

- [ ] **Step 1: Add router tests**

In `tests/unit/test_acmg_route_policy.py`, add:

```python
from tooluniverse.acmg_overlay_tools.router import route_overlays


def test_bare_coding_substitution_without_consequence_is_unknown():
    result = route_overlays(variant="NM_000000.0:c.742C>T", gene="GENE")

    assert result["variant_type"] == "unknown"
    assert "pp3_bp4_missense_prediction" not in result["baseline_overlays"]


def test_explicit_missense_consequence_routes_missense_overlays():
    result = route_overlays(
        variant="NM_000000.0:c.742C>T",
        gene="GENE",
        consequence="missense_variant",
    )

    assert result["variant_type"] == "missense"
    assert "pp3_bp4_missense_prediction" in result["baseline_overlays"]
```

- [ ] **Step 2: Run router tests to confirm failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_route_policy.py -q
```

Expected: FAIL on the bare coding substitution case.

- [ ] **Step 3: Change `_infer_variant_type` substitution behavior**

In `router.py`, replace:

```python
if sub_match:
    return "missense"
```

with:

```python
if sub_match:
    return "unknown"
```

Keep missense routing only through explicit `consequence`, explicit `variant_type`, or protein HGVS missense pattern.

- [ ] **Step 4: Update evidence source guidance**

In `route_overlays`, when `inferred_type == "unknown"`, include this action:

```python
"Resolve molecular consequence with EnsemblVEP_annotate_hgvs or VariantValidator before selecting missense, splicing, LoF, or protein-length overlays."
```

- [ ] **Step 5: Run router tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_route_policy.py tests/unit/test_acmg_harness_runner.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tooluniverse/acmg_overlay_tools/router.py tests/unit/test_acmg_route_policy.py
git commit -m "fix: require explicit consequence before missense overlay routing"
```

### Task 6: Align Source-Lead Sandbox Route IDs With Registry

**Files:**
- Modify: `src/tooluniverse/acmg_gate/source_lead_sandbox.py`
- Test: `tests/unit/test_acmg_source_lead_sandbox.py`

- [ ] **Step 1: Add registry-route tests**

In `tests/unit/test_acmg_source_lead_sandbox.py`, add:

```python
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output


def test_myvariant_candidate_routes_use_registry_ids():
    result = sandbox_source_output(
        tool_name="MyVariant_get_pathogenicity_scores",
        raw_output={"revel_score": 0.8, "cadd_phred": 30},
    )

    routes = {row["route"] for row in result["candidate_routes"]}
    assert "pp3_bp4_missense_prediction" in routes
    assert "computational_evidence_overlay" not in routes
    assert "pp3_bp4_prediction_refinement" not in routes


def test_spliceai_candidate_routes_use_registry_ids():
    result = sandbox_source_output(
        tool_name="SpliceAI_predict_splice",
        raw_output={"DS_DG": 0.8},
    )

    routes = {row["route"] for row in result["candidate_routes"]}
    assert "pvs1_splicing" in routes
    assert "ps1_splicing_similarity" in routes
```

- [ ] **Step 2: Run sandbox tests to confirm failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_source_lead_sandbox.py -q
```

Expected: FAIL because old route aliases are emitted.

- [ ] **Step 3: Replace route aliases**

In `source_lead_sandbox.py`, replace:

```python
{"route": "computational_evidence_overlay", ...}
{"route": "pp3_bp4_prediction_refinement", ...}
```

with:

```python
{"route": "pp3_bp4_missense_prediction", "route_label": "computational prediction context", ...}
```

For SpliceAI, replace:

```python
{"route": "pp3_bp4_splicing_prediction", ...}
{"route": "pvs1_splicing_refinement", ...}
```

with:

```python
{"route": "pvs1_splicing", "route_label": "splicing loss-of-function route", ...}
{"route": "ps1_splicing_similarity", "route_label": "same splicing event comparison route", ...}
```

- [ ] **Step 4: Run sandbox and validator tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_source_lead_sandbox.py tests/unit/test_acmg_harness_runner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tooluniverse/acmg_gate/source_lead_sandbox.py tests/unit/test_acmg_source_lead_sandbox.py
git commit -m "fix: align source lead candidate routes with overlay registry"
```

### Task 7: Fix Tool Discovery Drift Around Draft-Only Combiner

**Files:**
- Modify: `src/tooluniverse/acmg_gate_search.py`
- Test: `tests/unit/test_acmg_tool_search_fail_closed.py`

- [ ] **Step 1: Add discovery description test**

In `tests/unit/test_acmg_tool_search_fail_closed.py`, add:

```python
from tooluniverse.acmg_gate_search import add_acmg_gate_to_search_payload
from tooluniverse.acmg_gate.intent_detector import ACMGIntent


def test_combine_criteria_discovery_is_draft_only():
    payload = {
        "tools": [
            {
                "name": "ACMG_combine_criteria",
                "description": "old description",
            }
        ]
    }

    result = add_acmg_gate_to_search_payload(payload, intent=ACMGIntent.ACMG_FINAL_CLASSIFICATION)
    combine = next(tool for tool in result["tools"] if tool["name"] == "ACMG_combine_criteria")

    assert "draft-only" in combine["description"].lower()
    assert "5-tier" not in combine["description"]
    assert "finalizer" in combine["description"].lower()
```

- [ ] **Step 2: Run test to confirm failure**

Run:

```bash
uv run pytest tests/unit/test_acmg_tool_search_fail_closed.py -q
```

Expected: FAIL because discovery currently says the combiner outputs a five-tier classification.

- [ ] **Step 3: Update discovery injection text**

In `src/tooluniverse/acmg_gate_search.py`, replace the `ACMG_combine_criteria` description with:

```python
"ACMG_combine_criteria": (
    "Draft-only ACMG criterion strength summary. "
    "Input: deterministic overlay outputs. "
    "Output: counted criterion strength summary and next steps, not a final five-tier classification. "
    "Final ACMG/pathogenicity wording requires validator PASS, semantic_combiner PASS, finalizer token, and ACMG_guard_final_answer PASS."
),
```

- [ ] **Step 4: Run discovery tests**

Run:

```bash
uv run pytest tests/unit/test_acmg_tool_search_fail_closed.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tooluniverse/acmg_gate_search.py tests/unit/test_acmg_tool_search_fail_closed.py
git commit -m "fix: describe ACMG combiner discovery as draft only"
```

---

## Milestone 2: Reframe the Fork as a Guarded Overlay Extension

### Task 8: Rewrite Project Positioning Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/acmg_overlay_architecture.md`
- Modify: `TOOLUNIVERSE_OVERLAY_DIFF.md`

- [ ] **Step 1: Update README positioning**

In `README.md`, replace fork-positioning language with:

```markdown
> This fork is a ClinGen/SVI guarded overlay extension for upstream ToolUniverse.
> Upstream ToolUniverse remains the evidence retrieval and tool-execution platform.
> This extension adds deterministic ACMG/ClinGen overlay tools, source-lead sandboxing,
> route-audit validation, and final-answer guards so agents cannot directly convert
> GeneBe, InterVar, ClinVar, SpliceAI, MyVariant, VEP, gnomAD, literature, or user
> context into counted ACMG evidence.
```

Add:

```markdown
This fork is not a standalone clinical classifier. Its near-term purpose is to make
ACMG-related agent workflows harder to bypass and easier to audit. The long-term
direction is a higher-automation ACMG intelligent rating tool, built incrementally
from validated overlay routes and evidence provenance.
```

- [ ] **Step 2: Update architecture doc**

In `docs/acmg_overlay_architecture.md`, add a top-level section:

```markdown
## Project Scope

The project is temporarily scoped as an upstream ToolUniverse-compatible ClinGen/SVI
guarded overlay extension. The extension does three things:

1. Converts direct ToolUniverse variant evidence outputs into source leads or route inputs.
2. Applies ClinGen/SVI criterion-specific recommendations through deterministic overlay tools.
3. Blocks final ACMG wording unless bundle validation, semantic combination, finalization token,
   and final-answer guard all pass.

The extension intentionally does not replace upstream ToolUniverse evidence retrieval,
does not trust automated source labels as counted evidence, and does not claim complete
clinical-grade ACMG automation until every criterion path has validated route contracts.
```

- [ ] **Step 3: Update overlay diff**

In `TOOLUNIVERSE_OVERLAY_DIFF.md`, add:

```markdown
## Current Scope: Guarded Overlay Extension

This branch narrows the ACMG work to a ToolUniverse-compatible guarded overlay layer.
Canonical ToolUniverse tools continue to retrieve evidence. ACMG additions provide
deterministic overlay judgment, source-lead quarantine, route audit validation, and
final-answer gating.
```

- [ ] **Step 4: Run docs grep**

Run:

```bash
rg -n "standalone clinical classifier|complete clinical|ACMG Enhanced fork|5-tier classification" README.md docs TOOLUNIVERSE_OVERLAY_DIFF.md
```

Expected: no wording that claims this fork is a complete clinical classifier. Existing references to forbidden final labels are acceptable only when describing guarded output restrictions.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/acmg_overlay_architecture.md TOOLUNIVERSE_OVERLAY_DIFF.md
git commit -m "docs: reframe fork as ClinGen SVI guarded overlay extension"
```

### Task 9: Restore Skill Reference and Mirror Hygiene

**Files:**
- Create: `skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/references/pejaver_2022_pp3_bp4_summary.md`
- Modify: `TOOLUNIVERSE_OVERLAY_DIFF.md`
- Mirrors: `plugin/skills/` and `plugins/tooluniverse/skills/` as required by project mirror process

- [ ] **Step 1: Create missing Pejaver reference summary**

Create `skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/references/pejaver_2022_pp3_bp4_summary.md`:

```markdown
# Pejaver 2022 PP3/BP4 Summary

Pejaver et al. 2022 calibrated missense computational predictors for ACMG/AMP PP3
and BP4 evidence strengths. The recommendation is to use calibrated score intervals,
not uncalibrated predictor majority voting.

Operational rules for this fork:

- Select one calibrated predictor before score interpretation, or document an explicit
  local hierarchy as practice/local refinement.
- Map the raw score to the calibrated interval table.
- Do not count AlphaMissense, EVE, aggregator PP3/BP4 labels, developer-default CADD,
  SIFT, or PolyPhen thresholds unless a current VCEP or validated calibration says so.
- Do not use SpliceAI for missense PP3/BP4; route splicing predictions to splicing overlays.
- Preserve raw score source, version, transcript/build context, and selection policy.

Reference:

Pejaver V, Byrne AB, Feng B, Pagel KA, Mooney SD, Karchin R, O'Donnell-Luria A,
Harrison SM, Tavtigian SV, Greenblatt MS, Biesecker LG, Brenner SE, ClinGen Sequence
Variant Interpretation Working Group. Calibration of computational tools for missense
variant pathogenicity classification and ClinGen recommendations for PP3/BP4 criteria.
American Journal of Human Genetics. 2022;109:2163-2177. PMID:36413997.
```

- [ ] **Step 2: Sync committed skill mirrors**

Run the project’s existing mirror sync command if present. If no sync command exists, copy the canonical skill directory into both committed mirrors:

```bash
rsync -a skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/ plugin/skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/
rsync -a skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/ plugins/tooluniverse/skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/
```

- [ ] **Step 3: Update overlay diff**

In `TOOLUNIVERSE_OVERLAY_DIFF.md`, add a line under skill additions:

```markdown
- `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement`: reference-only skill documenting Pejaver 2022 PP3/BP4 calibrated intervals; runtime judgment belongs to `ACMG_overlay_pp3_bp4`.
```

- [ ] **Step 4: Run duplicate drift check**

Run:

```bash
python3 scripts/check_skill_duplicate_drift.py
```

Expected: `PASS: protected Skill mirrors and packaged ACMG wrapper scripts match canonical sources`.

- [ ] **Step 5: Commit**

```bash
git add skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement plugin/skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement plugins/tooluniverse/skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement TOOLUNIVERSE_OVERLAY_DIFF.md
git commit -m "docs: restore PP3 BP4 Pejaver reference and skill mirrors"
```

---

## Milestone 3: Preserve Path Toward Higher Automation

### Task 10: Add Automation Roadmap Without Expanding Current Runtime Scope

**Files:**
- Create: `docs/acmg_automation_roadmap.md`
- Modify: `docs/acmg_overlay_architecture.md`

- [ ] **Step 1: Create automation roadmap**

Create `docs/acmg_automation_roadmap.md`:

```markdown
# ACMG Automation Roadmap

## Current Phase: Guarded Overlay Extension

The current branch narrows scope to a ClinGen/SVI guarded overlay extension on top of
upstream ToolUniverse. The system retrieves evidence with existing ToolUniverse tools,
quarantines source labels, applies deterministic overlay rules, validates route audit
rows, and blocks final wording without finalizer and guard approval.

## Next Phase: Evidence-to-Overlay Automation

Increase automation by improving structured evidence extraction:

- Map MyVariant/dbNSFP predictor fields into `ACMG_overlay_pp3_bp4` inputs.
- Map gnomAD coverage and allele frequency fields into `ACMG_overlay_pm2`.
- Map ClinVar same-amino-acid and same-residue comparators into `ACMG_overlay_ps1_pm5`.
- Map MaveDB and literature functional assay fields into `ACMG_overlay_functional_assay`.
- Map family/de novo/segregation fields into dedicated clinical-context overlays.

All mappings remain source lead or route input until deterministic overlay tools pass.

## Later Phase: Intelligent ACMG Rating Assistant

The long-term goal is a reliable and highly automated ACMG intelligent rating tool.
That tool should produce machine-checkable assessment bundles with:

- normalized variant identity,
- disease and transcript context,
- evidence coverage audit,
- overlay results,
- route audit,
- compatibility resolution,
- semantic-combiner result,
- finalization token when allowed.

The assistant may draft final wording only after the final-answer guard passes.

## Non-Goals Before Full Validation

- Do not claim complete clinical-grade ACMG classification.
- Do not trust GeneBe, InterVar, ClinVar, paper labels, or aggregator ACMG labels as counted evidence.
- Do not let LLM-generated criterion assignments bypass deterministic overlays.
- Do not add new predictor or literature tools as counted evidence without source provenance and overlay contracts.
```

- [ ] **Step 2: Link roadmap from architecture doc**

In `docs/acmg_overlay_architecture.md`, add:

```markdown
For the staged path from guarded overlay extension to a higher-automation ACMG intelligent
rating assistant, see `docs/acmg_automation_roadmap.md`.
```

- [ ] **Step 3: Run documentation grep**

Run:

```bash
rg -n "ACMG intelligent rating|guarded overlay extension|source lead|final-answer guard" docs/acmg_overlay_architecture.md docs/acmg_automation_roadmap.md
```

Expected: both files mention the narrowed current scope and later automation direction.

- [ ] **Step 4: Commit**

```bash
git add docs/acmg_automation_roadmap.md docs/acmg_overlay_architecture.md
git commit -m "docs: add staged ACMG automation roadmap"
```

---

## Milestone 4: Verification and Merge Readiness

### Task 11: Run Guarded Overlay Verification Suite

**Files:**
- No code files modified.

- [ ] **Step 1: Run focused ACMG test suite**

Run:

```bash
uv run pytest \
  tests/unit/test_acmg_overlay_pp3_bp4.py \
  tests/unit/test_acmg_overlay_pm2.py \
  tests/unit/test_acmg_overlay_ps2_pm6.py \
  tests/unit/test_acmg_overlay_wrapper_signatures.py \
  tests/unit/test_acmg_overlay_vcep_override.py \
  tests/unit/test_acmg_resolved_evidence_binding.py \
  tests/unit/test_acmg_source_lead_sandbox.py \
  tests/unit/test_acmg_tool_search_fail_closed.py \
  tests/unit/test_acmg_harness_runner.py \
  tests/unit/test_acmg_finalizer.py \
  tests/unit/test_acmg_final_answer_guard.py \
  tests/unit/test_acmg_finalization_gate_consistency.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run registry and skill drift checks**

Run:

```bash
python3 scripts/check_skill_duplicate_drift.py
uv run python scripts/validate_overlay_registry_coverage.py
```

Expected:

```text
PASS: protected Skill mirrors and packaged ACMG wrapper scripts match canonical sources
```

Registry coverage script should exit 0.

- [ ] **Step 3: Run integration and red-team checks**

Run:

```bash
uv run pytest \
  tests/integration/test_acmg_no_manual_assignment_pipeline.py \
  tests/integration/test_acmg_pipeline.py \
  tests/redteam/acmg/test_fgfr3_real_bypass_regression.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git diff --stat
git diff --check
```

Expected: `git diff --check` exits 0. Diff should be limited to runtime safety fixes, wrapper metadata, tests, and docs.

- [ ] **Step 5: Commit verification-only updates if any**

If verification required small fixture/doc updates, commit them:

```bash
git add <verified-files>
git commit -m "test: verify guarded ACMG overlay extension"
```

If no files changed, do not create an empty commit.

### Task 12: Final Code Review Checkpoint

**Files:**
- No code files modified.

- [ ] **Step 1: Request code review with superpowers**

Use `superpowers:requesting-code-review` with:

```text
DESCRIPTION:
Narrowed ACMG branch into an upstream ToolUniverse-compatible ClinGen/SVI guarded overlay extension. Fixed VCEP override counting, wrapper signature drift, route/resolved evidence binding, PP3/BP4 selection policy, router missense inference, source-lead route ids, and discovery docs.

REQUIREMENTS:
Direct ToolUniverse variant tools remain source leads. Deterministic overlay tools own criterion judgments. Final wording requires validator PASS, semantic combiner PASS, finalizer token, and guard PASS. Current scope is guarded overlay extension, with future automation staged in docs.

BASE_SHA:
origin/main

HEAD_SHA:
current branch HEAD
```

- [ ] **Step 2: Triage review findings**

Fix any Critical or Important findings before merge. For Minor findings, either fix them immediately or record them in `docs/acmg_automation_roadmap.md` if they belong to later automation.

- [ ] **Step 3: Run final verification**

Run:

```bash
uv run pytest tests/unit/test_acmg_harness_runner.py tests/unit/test_acmg_tool_search_fail_closed.py tests/unit/test_acmg_final_answer_guard.py -q
python3 scripts/check_skill_duplicate_drift.py
git diff --check
```

Expected: all commands pass.

---

## Self-Review

### Spec Coverage

- Current scope narrowed to upstream ToolUniverse-compatible ClinGen/SVI guarded overlay extension: Tasks 8 and 10.
- Keep upstream tools as evidence retrieval/source leads: Tasks 6, 7, 8, and 10.
- Deterministic overlay tools own ClinGen/SVI judgments: Tasks 1, 2, 4, and 5.
- Prevent agent bypass: Tasks 1, 3, 6, 7, 11, and 12.
- Preserve long-term goal of reliable high-automation ACMG intelligent rating: Task 10.

### Placeholder Scan

The plan contains no unresolved placeholder markers or unspecified implementation steps. Every code-changing task names exact files, includes concrete test code or replacement snippets, and includes verification commands.

### Type Consistency

The plan consistently uses `route_outcome`, `guidance_authority`, `selected_tool`, `selection_policy`, `overlay_deferred_to_vcep`, `overlay_applied`, `current_counted_evidence_resolved`, and registry `criterion_group` route ids.
