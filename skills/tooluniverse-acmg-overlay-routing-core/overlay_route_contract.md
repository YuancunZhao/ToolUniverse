# ACMG Overlay Route Contract

This contract turns the ACMG overlay routing guidance into a portable compliance
layer for ToolUniverse agents. It is intentionally lightweight: it defines the
route plan, overlay result, and final route audit that an agent should produce,
but it does not execute ToolUniverse skills or change any ACMG rule.

## Scope

Use this contract when an agent imports ToolUniverse ACMG overlay skills or when
another system wants to evaluate whether an agent bypassed those overlays.

This contract is not:

- a full ACMG classifier;
- a medical decision engine;
- a replacement for VCEP specifications;
- a runtime that guarantees tool invocation;
- a source of criterion-specific thresholds.

## Trigger Policy Model

The registry uses a two-stage trigger model so agents do not wait for
literature before assessing evidence classes that are always relevant to a
variant interpretation.

### Universal baseline

`universal_baseline` routes must appear in every germline variant route plan
when their applicability gate is in scope. These include disease/context
boundary, mechanism boundary, population frequency gates, PVS1 applicability,
and source assertion review when source assertions are available.

Missing an applicable universal baseline route is a compliance failure. The
agent must label the result `draft classification` until the route is added or
the item is explicitly shown to be out of scope.

### Variant-type baseline

`variant_type_baseline` routes must appear when the variant type or consequence
matches `applies_when`.

Examples:

- missense variants route PP3/BP4 prediction, PS1/PM5 comparison, PM1/PP2/BP1
  regional/mechanism context, and structured functional-discovery lookup such
  as MaveDB when available;
- LoF-like variants route the PVS1 LoF decision tree;
- splice/RNA candidates route splicing-specific PVS1 or PS1 logic;
- in-frame or protein-length candidates route PM4/BP3.

For PS3/BS3, literature functional assays are discovery evidence, but
structured functional databases such as MaveDB are baseline discovery sources
for missense variants. A database hit triggers the PS3/BS3 overlay; the agent
must not directly count the score outside the overlay.

### Evidence discovery

`evidence_discovery` routes are appended after literature, database, clinical,
or user-provided material creates a candidate signal.

Examples:

- PP1/BS4/PP4 after pedigree, family, segregation, cascade-screening, or
  affected-relative evidence appears;
- PS4 after case-control, cohort, meta-analysis, odds-ratio, confidence
  interval, unrelated case series, or recurrence evidence appears;
- PS2/PM6 after de novo, trio, or parental-testing evidence appears;
- PM3 after biallelic, in-trans, or phase evidence appears.

Missing a discovery route is not a failure by itself when no triggering evidence
was found and the agent states the literature/source coverage. Missing a route
after triggering evidence is found is a compliance failure for that criterion.

## Three-Layer Audit Model

### 1. Candidate detection

Candidate detection asks only whether the input might involve an ACMG criterion
covered by an overlay. It must be broad and conservative.

Example: a paper mentions a pedigree with affected relatives and genotypes. That
is enough to route PP1/BS4/PP4. It is not enough to assign PP1 strength.

The candidate detector may use:

- explicit ACMG codes from the user or source;
- evidence-type words such as segregation, functional assay, case-control,
  absence from gnomAD, de novo, in trans, hotspot, or same residue;
- database or literature assertions used as source leads;
- missing context needed before a criterion can be scored.

Candidate detection must not assign refined strengths such as `PP1_Moderate`,
`PS3_Strong`, `PM2_Supporting`, or `BP4_Moderate`.

### 2. Mandatory overlay route

For every applicable baseline route and every discovered candidate criterion or
criterion group listed in `overlay_registry.yaml`, the agent must route to the
registered overlay skill or explicitly record `overlay_deferred_to_vcep` when a
current VCEP specification supersedes the generic overlay.

The route plan should be produced before final evidence assignment. It should
include:

- detected candidate criteria or groups;
- required overlay skills;
- trigger policy;
- applies-when conditions;
- baseline data-source categories;
- reason for routing;
- whether a VCEP-specific rule supersedes the generic overlay.

If an agent cannot invoke the overlay skill directly, it may apply the overlay
SKILL.md logic manually, but the route audit must still identify the overlay as
the source of truth. If neither invocation nor manual application is possible,
the criterion is `overlay_not_assessed`.

### 3. Counted evidence audit

Before final classification, every potentially counted evidence item must have a
route audit row. Only these route outcomes may be counted:

- `overlay_applied`
- `overlay_deferred_to_vcep`

These outcomes must not be counted:

- `overlay_not_applicable`
- `overlay_not_assessed`

If any covered criterion is counted without an acceptable route outcome, the
agent must label the result `draft classification` and remove the unrouted item
from current counted evidence.

## Required Artifacts

### Route plan

Use `schemas/route_plan.schema.json` for machine-checkable output.

Minimum fields:

- `candidate_criteria`
- `required_overlays`
- `trigger_policy`
- `applies_when`
- `baseline_data_sources`
- `reason_for_routing`
- `vcep_deferred`

### Overlay result

Use `schemas/overlay_result.schema.json` for each overlay-like result.

Minimum fields:

- `overlay_skill`
- `criterion`
- `applied_evidence`
- `status`
- `guidance_authority`
- `reason`
- `consumed_evidence`
- `source_of_truth`

### Route audit

Use `schemas/route_audit.schema.json` for the final report audit.

Minimum fields for each potentially counted item:

- `criterion`
- `proposed_evidence`
- `route_outcome`
- `overlay_or_vcep_source`
- `counted`
- `reason`

## PP1 Example

Do this:

1. Run baseline routes first for the variant class and disease context.
2. After literature expansion, input mentions a family, pedigree, meioses,
   affected relatives, cascade screening, or literature family series.
3. Mark PP1/BS4/PP4 as evidence-discovery candidate criteria.
4. Route to `tooluniverse-acmg-pp1-segregation-refinement`.
5. Let that overlay decide `applied`, `no_evidence`, `not_assessed`, or
   `not_applicable` and any evidence strength.

Do not do this:

1. Read the literature.
2. Decide outside the overlay that PP1 is Supporting, Moderate, or Strong.
3. Add PP1 to counted evidence without overlay trace.

## LDLR-Like Missense Baseline Example

For a germline missense variant such as `LDLR;NM_000527.5:c.1747C>T
(p.His583Tyr)`, the initial route plan should include applicable baseline
routes even before variant-specific literature is read:

- population frequency gates: BA1/BS1/PM2 overlays;
- computational prediction: PP3/BP4 overlay;
- comparison-variant review: PS1/PM5 overlay;
- regional/mechanism context: PM1/PP2/BP1 overlay;
- source assertion review when ClinVar, LOVD, HGMD, VCEP, or paper labels are
  available;
- disease/mechanism boundary overlays;
- PVS1 applicability gate, usually returning `not_applicable` for a pure
  missense variant unless another LoF-like consequence is present.

PP1 is not required at baseline. It is appended only if literature or user data
contains pedigree, segregation, family, cascade-screening, or affected-relative
evidence.

## Source Assertion Example

ClinVar, HGMD, LOVD, VCEP, a paper's ACMG table, or a laboratory report can
trigger routing, but it is a source lead until primary evidence is reviewed.

Route source assertions to
`tooluniverse-acmg-pp5-bp6-reputable-source-refinement`, then route primary
evidence to the criterion-specific overlay. Do not count PP5/BP6 by default.

## Future CLI Compatibility

This layout is designed so a future CLI can reuse the same files:

```bash
tooluniverse-acmg-gate validate output.json
tooluniverse-acmg-gate plan input.json
tooluniverse-acmg-gate eval evals/evals.json
```

Version 1 intentionally provides contract, schemas, registry, and eval cases
only. Runtime enforcement belongs in a later validator or harness.
