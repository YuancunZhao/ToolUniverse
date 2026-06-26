# Quick Start: ACMG Overlay Gate

Use this routing core as a final-classification gate, not as another free-form ACMG checklist.

## Minimal Rule

No valid ACMG assessment bundle, no final ACMG classification.

An agent may summarize evidence without the bundle, but the output must stay `draft classification` until the bundle validates.

This rule also applies when evidence comes from direct ToolUniverse MCP tools such as GeneBe, ClinVar, SpliceAI, MyVariant, or Ensembl VEP. Those outputs are source leads, route triggers, or annotation inputs until they enter the bundle and the validator returns `PASS`.

## Required Bundle

Before final classification, emit one `acmg_assessment_bundle` compatible with `schemas/acmg_assessment_bundle.schema.json`:

```json
{
  "acmg_assessment_bundle": {
    "variant": {
      "gene": "LDLR",
      "hgvs_c": "NM_000527.5:c.1747C>T",
      "hgvs_p": "p.His583Tyr",
      "consequence": "missense_variant"
    },
    "classification_status": "draft classification",
    "disease_context": {
      "disease_entity": "familial hypercholesterolemia",
      "inheritance": "autosomal dominant",
      "mechanism": "LDLR loss of function / receptor dysfunction",
      "source": "ClinGen/GeneReviews/literature",
      "status": "resolved"
    },
    "penetrance_context": {
      "penetrance_type": "variable",
      "age_of_onset": "childhood to adulthood",
      "unaffected_carrier_interpretability": "context_dependent",
      "source": "GeneReviews/literature",
      "criteria_affected": ["BS1", "BS2", "BS4", "PP1", "PP4", "PM2", "PS4"],
      "status": "resolved"
    },
    "vcep_context": {
      "vcep_available": false,
      "scope_match": "none",
      "source": "VCEP search",
      "criteria_overridden": [],
      "generic_overlay_responsibilities": ["all triggered generic overlays"]
    },
    "route_plan": [],
    "coverage_audit": [],
    "overlay_results": [],
    "route_audit": [],
    "compatibility_resolution": {
      "current_counted_evidence_resolved": [],
      "unresolved_conflicts": []
    }
  }
}
```

The bundle may be compact, but it must include:

- `route_plan`: baseline and triggered discovery routes from `overlay_registry.yaml`.
- `disease_context`, `penetrance_context`, and `vcep_context`: shared context for inheritance, mechanism, penetrance-sensitive evidence, and VCEP precedence.
- `coverage_audit`: data sources checked, no-hits, unavailable sources, and triggered routes.
- `overlay_results`: overlay or VCEP trace for assessed criteria.
- `route_audit`: every potentially counted item and whether it was counted.
- `compatibility_resolution`: resolved counted evidence and unresolved conflicts.
- `classification_status`: `final classification` only when the validator passes.

A final classification with empty `current_counted_evidence_resolved` is invalid. Keep it as `draft classification` until at least one routed counted evidence item, or an explicitly routed stand-alone benign item such as BA1, appears in compatibility-resolved evidence.

## Validate

Run the dependency-free validator:

```bash
python3 .agents/skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py output.json --pretty
```

Validator outcomes:

- `PASS`: final classification may be presented if the clinical/scientific evidence also supports it.
- `DRAFT_ONLY`: keep the report as `draft classification`; add missing routes, coverage, or compatibility resolution before final combine.
- `FAIL`: direct bypass was detected, such as counted source labels or counted evidence without an acceptable overlay/VCEP route outcome.

The validator checks trace compliance only. It does not query databases, run ToolUniverse tools, assign ACMG evidence strength, or compute the final classification.

## Minimum Anti-Bypass Checks

- Counted evidence must have route outcome `overlay_applied` or `overlay_deferred_to_vcep`.
- Covered criteria without overlay/VCEP trace cannot enter counted evidence.
- ClinVar, HGMD, LOVD, VCEP, lab, or paper labels are source leads unless primary evidence is routed.
- Applicable baseline routes missing from the route plan force `draft classification`.
- Missing discovery routes are acceptable only when `coverage_audit` documents no trigger hit or source unavailability.
- Final classification requires literature/discovery coverage, or an explicit `unavailable` / `not_applicable` literature row.
- Missing compatibility resolution, or unresolved compatibility conflicts, force `draft classification`.
- Counted literature-backed evidence must include `literature_provenance`. Abstract-only or source-unavailable papers remain literature leads and may trigger PDF/supplement requests, but they cannot support final counted evidence unless a current VCEP explicitly allows abstract-level use.

## Missense Baseline

For a germline missense assessment, the route plan normally includes:

- population gates: BA1/BS1/PM2 family of routes;
- computational prediction: PP3/BP4 overlay;
- comparison variant review: PS1/PM5 overlay;
- regional/mechanism review: PM1/PP2/BP1 overlay;
- structured functional discovery: MaveDB or equivalent coverage, with PS3/BS3 routed only if a hit exists;
- PVS1 applicability gate, usually `not_applicable` for ordinary missense;
- disease and mechanism context gates;
- source review when source assertions are present.

## Regression Fixtures

Validator fixtures live in `evals/validator_fixtures/`:

```bash
python3 - <<'PY'
import json, subprocess, sys
from pathlib import Path

script = Path(".agents/skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py")
for fixture in sorted(Path(".agents/skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures").glob("*.json")):
    expected = json.loads(fixture.read_text())["expected_validator_status"]
    proc = subprocess.run([sys.executable, str(script), str(fixture)], text=True, capture_output=True)
    actual = json.loads(proc.stdout)["status"]
    print(f"{fixture.name}: expected={expected} actual={actual}")
PY
```

For the maintained fixture inventory and expected outcomes, see `evals/validator_fixtures/README.md`.
