# Quick Start: ACMG Overlay Routing Core

Use this skill before criterion-specific overlays when the interpretation could depend on disease context, mechanism, clinical context, literature extraction, or source assertions.

## Minimal Workflow

1. Normalize the variant and transcript.
2. Resolve disease-entity boundary if the gene has multiple disorders or mechanisms.
3. Resolve mechanism boundary if LoF, gain-of-function, dominant-negative, antimorphic, or mixed mechanism affects evidence use.
4. Collect clinical context when phenotype, family, phase, de novo, unaffected status, or alternate diagnosis is required.
5. Treat secondary assertions as leads, not counted evidence.
6. Apply the evidence-specific overlay.
7. Report status and consumed evidence explicitly.

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
