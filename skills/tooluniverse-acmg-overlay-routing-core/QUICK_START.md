# Quick Start: ACMG Overlay Routing Core

Use this skill before criterion-specific overlays when the interpretation could depend on disease context, mechanism, clinical context, literature extraction, or source assertions.

## Minimal Workflow

1. Normalize the variant and transcript.
2. Emit a compact `Bundle Route Plan` first when possible. Use the Route Bundle Quick Planner in `SKILL.md` and `schemas/bundle_route_plan.schema.json` to decide which bundles are triggered: baseline context, population frequency, consequence/LoF, splice, missense, protein length, clinical observation, literature/functional evidence, CNV/SV, and final combine.
3. Expand triggered bundles into detailed route-plan rows using `overlay_registry.yaml` before assigning evidence strength:
   - include every applicable `universal_baseline` route for germline assessment;
   - include every `variant_type_baseline` route whose `applies_when` condition matches the variant consequence;
   - include `trigger_policy`, `enforcement_level`, `route_kind`, `applies_when`, `baseline_data_sources`, and `expected_default_status` in structured route-plan rows.
4. For missense variants, baseline routes normally include population gates, PP3/BP4, PS1/PM5, PM1/PP2/BP1, structured functional-discovery lookup such as MaveDB when available, and the PVS1 applicability gate returning `not_applicable` when appropriate.
5. Resolve disease-entity boundary if the gene has multiple disorders or mechanisms.
6. Resolve mechanism boundary if LoF, gain-of-function, dominant-negative, antimorphic, or mixed mechanism affects evidence use.
7. Treat secondary assertions as leads, not counted evidence.
8. Emit coverage audit rows compatible with `schemas/coverage_audit.schema.json`; record queried sources, query status, hits, triggered routes, and routes not triggered.
9. Expand source, database, and literature coverage; append `evidence_discovery` routes only when a triggering signal appears.
10. Collect clinical context when phenotype, family, phase, de novo, unaffected status, or alternate diagnosis is required.
11. Apply the evidence-specific overlay and emit an overlay result compatible with `schemas/overlay_result.schema.json`.
12. Emit a final route audit compatible with `schemas/route_audit.schema.json`; count only `overlay_applied` or `overlay_deferred_to_vcep`.
13. Run Evidence Compatibility Resolution compatible with `schemas/evidence_compatibility.schema.json`.
14. Send only `current_counted_evidence_resolved` into ACMG qualitative combine and Tavtigian Bayesian combine.

If a covered criterion is counted without overlay or VCEP trace, label the result `draft classification`. If an applicable baseline route is missing, also label the result `draft classification`. If no discovery trigger was found, a missing discovery route is acceptable only when the report includes coverage audit rows supporting that absence. If compatibility resolution has unresolved conflicts, keep the result as `draft classification` and do not run final combine.

## Portable Compliance Files

- `overlay_registry.yaml`: criterion/group to mandatory overlay skill mapping with trigger policies, applies-when conditions, and baseline data-source categories.
- `overlay_route_contract.md`: baseline planning, discovery expansion, routing, and audit rules.
- `schemas/bundle_route_plan.schema.json`: JSON Schema for compact bundle-level execution planning.
- `schemas/`: JSON Schemas for route plans, coverage audits, overlay results, and route audits.
- `schemas/evidence_compatibility.schema.json`: JSON Schema for final-combine compatibility resolution.
- `evals/evals.json`: regression cases for overlay-bypass behavior.

These files are designed for sharing with other agents and for later Full Harness CLI validation. They do not execute tools or change ACMG thresholds.

## Standard Result Block

## Bundle Route Plan Block

```markdown
Bundle route plan:
| Bundle | Trigger found? | Required overlays/checks | Coverage required | Status | Reason |
| --- | --- | --- | --- | --- | --- |
| population_frequency_bundle | yes | BA1 exception, PM2 rarity, benign-context if high AF/healthy-carrier/alternate-diagnosis evidence appears | gnomAD/ClinVar frequency, ancestry, coverage | planned | Required for all germline ACMG assessments |
```

Bundle rows are not counted evidence. Expand each triggered bundle into detailed route-plan rows before any evidence strength is counted.

When emitting structured output, validate the compact bundle table against `schemas/bundle_route_plan.schema.json`. Use `required_checks` for non-ACMG intake steps, such as `tooluniverse-structural-variant-analysis`; keep `required_overlays` for ACMG overlay skills only.

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
- Fan out only when the source lists explicit ACMG criterion codes, primary-evidence keywords, or retrievable primary evidence.
- If primary evidence is unavailable, report source evidence as `not_assessed` or `not_used`, not counted PP5/BP6.

### LDLR-Like Missense Without Literature

Scenario: `LDLR;NM_000527.5:c.1747C>T (p.His583Tyr)` is assessed as a germline heterozygous missense variant and no variant-specific literature has been read yet.

Expected:

- Produce a bundle route plan with `baseline_context_bundle`, `population_frequency_bundle`, `missense_bundle`, and `final_combine_bundle`; include `literature_functional_bundle` coverage but do not trigger PP1/PS4/PS3 without evidence hits.
- Include population frequency gates, PP3/BP4, PS1/PM5, PM1/PP2/BP1, disease/mechanism boundary, source review when source assertions exist, and PVS1 applicability in the baseline route plan.
- Include coverage audit for population databases, ClinVar/source assertions, computational predictors, MaveDB or equivalent structured functional databases, and literature.
- Record PVS1 as an applicability gate and usually `not_applicable` for a non-LoF missense consequence.
- Do not require PP1 at baseline.
- Append PP1/BS4/PP4 only after pedigree, segregation, cascade-screening, family, or affected-relative evidence appears.

### CNV/SV Intake Without Standalone Final Classification

Scenario: a deletion overlaps a dosage-sensitive gene.

Expected:

- Use `cnv_sv_bundle` to collect coordinates, gene content, dosage sensitivity, breakpoint precision, population SV frequency, reciprocal-overlap matches, and inheritance.
- Route final ACMG evidence through the relevant overlays, such as PVS1 LoF decision tree, PM4/BP3, PM2/BA1/BS1, PS2/PM6, PS4, PP1/BS4/PP4, and compatibility resolution.
- Do not present a final germline ACMG classification from the SV intake skill alone.

### Structured Functional Database Hit

Scenario: a missense variant has a MaveDB or similar structured functional score.

Expected:

- Treat the database search as a variant-type baseline functional-discovery source.
- Route any hit to `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.
- If no hit is found, record `query_status: no_hit` in coverage audit and do not force PS3/BS3 overlay.
- Do not count PS3 or BS3 directly from the score without overlay result and route audit.

### Final Compatibility Before Combine

Scenario: route audit has `PVS1_Strength (RNA)` and `PS3` from the same RNA assay.

Expected:

- Run Evidence Compatibility Resolution before final combine.
- Keep `PVS1_Strength (RNA)`.
- Mark `PS3` as `not_used_due_to_overlap`.
- Enter only `current_counted_evidence_resolved` into qualitative ACMG and Bayesian combination.
