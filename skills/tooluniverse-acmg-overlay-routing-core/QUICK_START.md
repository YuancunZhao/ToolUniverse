# Quick Start: ACMG Overlay Routing Core

Use this skill before criterion-specific overlays when the interpretation could depend on disease context, mechanism, clinical context, literature extraction, or source assertions.

## Minimal Workflow

1. Normalize the variant and transcript.
2. Use `overlay_registry.yaml` to emit a baseline route plan before assigning evidence strength:
   - include every applicable `universal_baseline` route for germline assessment;
   - include every `variant_type_baseline` route whose `applies_when` condition matches the variant consequence;
   - include `trigger_policy`, `applies_when`, and `baseline_data_sources` in structured route-plan rows.
3. For missense variants, baseline routes normally include population gates, PP3/BP4, PS1/PM5, PM1/PP2/BP1, structured functional-discovery lookup such as MaveDB when available, and the PVS1 applicability gate returning `not_applicable` when appropriate.
4. Resolve disease-entity boundary if the gene has multiple disorders or mechanisms.
5. Resolve mechanism boundary if LoF, gain-of-function, dominant-negative, antimorphic, or mixed mechanism affects evidence use.
6. Treat secondary assertions as leads, not counted evidence.
7. Expand source, database, and literature coverage; append `evidence_discovery` routes only when a triggering signal appears.
8. Collect clinical context when phenotype, family, phase, de novo, unaffected status, or alternate diagnosis is required.
9. Apply the evidence-specific overlay and emit an overlay result compatible with `schemas/overlay_result.schema.json`.
10. Emit a final route audit compatible with `schemas/route_audit.schema.json`; count only `overlay_applied` or `overlay_deferred_to_vcep`.

If a covered criterion is counted without overlay or VCEP trace, label the result `draft classification`. If an applicable baseline route is missing, also label the result `draft classification`. If no discovery trigger was found, a missing discovery route is acceptable only when the report states the source/literature coverage.

## Portable Compliance Files

- `overlay_registry.yaml`: criterion/group to mandatory overlay skill mapping with trigger policies, applies-when conditions, and baseline data-source categories.
- `overlay_route_contract.md`: baseline planning, discovery expansion, routing, and audit rules.
- `schemas/`: JSON Schemas for route plans, overlay results, and route audits.
- `evals/evals.json`: regression cases for overlay-bypass behavior.

These files are designed for sharing with other agents and for later Full Harness CLI validation. They do not execute tools or change ACMG thresholds.

## Standard Result Block

```markdown
ACMG overlay result:
- overlay: [skill name]
- criterion: [ACMG code or context gate]
- applied_evidence: [evidence label or none]
- status: [applied / no_evidence / not_assessed / not_applicable / not_used]
- reason: [short rationale]
- consumed_evidence: [evidence already used]
- routed_to: [next overlay if applicable]
```

## Examples

### Multiple Disorders Before PVS1

Scenario: A gene has a recessive LoF disease and a dominant missense/dominant-negative disease.

Expected:

- Run multiple-disorder context first.
- Run mechanism overlay if disease mechanism remains uncertain.
- Apply PVS1 only in the LoF-compatible disease context.

### BA1 High Frequency

Scenario: AF is greater than 0.05 in a general continental population.

Expected:

- Run BA1 exception-list review first.
- If BA1 applies, report `BA1` and do not also apply PM2 or BS1 for the same disease context.
- If BA1 is blocked, route to benign-context BS1 review only when disease-specific thresholds support it.

### PP4 With Segregation

Scenario: A family has a highly specific phenotype and segregation evidence.

Expected:

- Use phenotype-dependent refinement for intake.
- Use PP1 segregation refinement for combined PP1/BS4/PP4 points, evidence apportionment, and the +5.0 cap.

### Reputable Source Assertion

Scenario: ClinVar or another source asserts Pathogenic but primary evidence is not visible.

Expected:

- Run PP5/BP6 source refinement.
- Record the assertion as a lead.
- Retrieve and score primary evidence directly.
- If primary evidence is unavailable, report source evidence as `not_assessed` or `not_used`, not counted PP5/BP6.

### LDLR-Like Missense Without Literature

Scenario: `LDLR;NM_000527.5:c.1747C>T (p.His583Tyr)` is assessed as a germline heterozygous missense variant and no variant-specific literature has been read yet.

Expected:

- Include population frequency gates, PP3/BP4, PS1/PM5, PM1/PP2/BP1, disease/mechanism boundary, source review when source assertions exist, and PVS1 applicability in the baseline route plan.
- Record PVS1 as an applicability gate and usually `not_applicable` for a non-LoF missense consequence.
- Do not require PP1 at baseline.
- Append PP1/BS4/PP4 only after pedigree, segregation, cascade-screening, family, or affected-relative evidence appears.

### Structured Functional Database Hit

Scenario: a missense variant has a MaveDB or similar structured functional score.

Expected:

- Treat the database search as a variant-type baseline functional-discovery source.
- Route any hit to `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.
- Do not count PS3 or BS3 directly from the score without overlay result and route audit.
