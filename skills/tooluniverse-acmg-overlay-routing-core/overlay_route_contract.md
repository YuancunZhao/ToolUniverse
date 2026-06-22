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

Agents may use the Route Bundle Quick Planner in `SKILL.md` to create a compact
bundle route plan before expanding triggered bundles into registry route rows.
Bundles are an efficiency layer only. They do not count evidence, override
registry entries, or change any evidence-specific overlay threshold.

Use `schemas/bundle_route_plan.schema.json` for structured bundle output. Bundle
rows use `required_overlays` for ACMG overlay skills and `required_checks` for
non-ACMG intake or retrieval steps. For example, `cnv_sv_bundle` may list
`tooluniverse-structural-variant-analysis` in `required_checks`, but final
counted evidence still requires expanded ACMG overlay route rows or VCEP route
outcomes.

The registry also uses an enforcement model:

- `must_plan`: the route must appear in the route plan when the assessment is
  in scope, even if the expected result is `not_applicable`.
- `must_query`: the agent must query or explicitly mark unavailable the listed
  data-source category before claiming the route is absent or unassessed.
- `must_route_if_hit`: the route is mandatory only when coverage finds a
  trigger hit.
- `must_audit_if_counted`: any covered criterion entering counted evidence must
  have an acceptable route audit outcome.

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

For missense variants, structured functional databases are `must_query`
functional-discovery sources. If no structured functional database is available
or no hit is found, record that in the coverage audit rather than forcing a
PS3/BS3 overlay result.

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
was found and the agent provides a coverage audit. Missing a route after
triggering evidence is found is a compliance failure for that criterion.

## Coverage Audit Model

Use `schemas/coverage_audit.schema.json` to record query coverage for baseline
and discovery sources. Coverage audit is required when an agent:

- omits a discovery route because no trigger was found;
- claims a required data source was unavailable;
- uses source labels as leads without fan-out to evidence-specific overlays;
- performs structured functional-discovery lookup such as MaveDB.

Coverage rows must state:

- source category;
- queried sources;
- query status;
- hits found;
- routes triggered by those hits;
- routes not triggered and why.

`query_status: no_hit` is not the same as `query_status: unavailable`.
Unavailable sources should be listed as gaps, not as negative evidence.

## Source-Lead Fan-Out

ClinVar, HGMD, LOVD, VCEP, laboratory reports, and paper ACMG labels are source
leads by default. They trigger
`tooluniverse-acmg-pp5-bp6-reputable-source-refinement` but do not
automatically trigger every possible evidence-specific overlay.

Fan-out is allowed only when the source provides one of these:

- explicit ACMG criterion codes, such as `PS3+PM1+PM2+PM5+PP3`;
- primary-evidence keywords, such as functional assay, pedigree, segregation,
  case-control, cohort, de novo, in trans, same residue, or hotspot;
- retrievable primary evidence records that can be routed to a criterion-
  specific overlay.

A source label without primary evidence remains `source lead only` and must not
be counted.

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

- route bundle identifier when bundle planning is used;
- detected candidate criteria or groups;
- required overlay skills;
- trigger policy;
- enforcement level;
- route kind;
- applies-when conditions;
- baseline data-source categories;
- reason for routing;
- whether a VCEP-specific rule supersedes the generic overlay.

Bundle-level rows are compliant only when every triggered bundle is expanded to
the registered overlay rows before evidence is counted. A bundle can justify
`not_applicable` or `not_assessed` only when its expanded route rows and coverage
audit support that status.

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

### 4. Evidence compatibility resolution

After counted evidence audit passes, resolve compatibility before final
classification. This step is required because two criteria may both be routed
correctly but still consume the same primary evidence, depend on mutually
exclusive contexts, or require a cap.

Use `schemas/evidence_compatibility.schema.json`. The output must include:

- `current_counted_evidence_resolved`
- `not_used_due_to_overlap`
- `caps_applied`
- `context_splits`
- `unresolved_conflicts`
- `resolutions`

Only `current_counted_evidence_resolved` may enter ACMG/AMP qualitative
combination or Tavtigian Bayesian combination. If `unresolved_conflicts` is not
empty, the result remains `draft classification`.

Evidence compatibility resolution does not assign ACMG evidence strength. It
keeps, drops, caps, splits, or blocks evidence already routed through overlays
or VCEP rules.

## Required Artifacts

### Bundle route plan

Use `schemas/bundle_route_plan.schema.json`. The bundle plan is a compact
human/agent-facing artifact. It should include:

- bundle identifier;
- trigger found status;
- required overlays or non-overlay checks;
- coverage required;
- status;
- reason.
- whether expanded route rows are required;
- expanded route row identifiers after expansion, when available.

The bundle plan helps agents avoid invoking every overlay for every variant.
It is not enough for counted evidence; counted evidence still requires detailed
route rows, overlay results, route audit, compatibility resolution, and final
combine checks.

### Route plan

Use `schemas/route_plan.schema.json` for machine-checkable output.

Minimum fields:

- `candidate_criteria`
- `required_overlays`
- `trigger_policy`
- `enforcement_level`
- `route_kind`
- `applies_when`
- `baseline_data_sources`
- `reason_for_routing`
- `vcep_deferred`

### Coverage audit

Use `schemas/coverage_audit.schema.json` whenever discovery routes are omitted
or structured/source/literature coverage determines whether routes are
mandatory.

Minimum fields:

- `source_category`
- `queried_sources`
- `query_status`
- `hits`
- `triggered_routes`
- `not_triggered_routes`
- `reason`

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

### Evidence compatibility resolution

Use `schemas/evidence_compatibility.schema.json` before final combine.

Minimum fields for each resolution:

- `conflict_group`
- `evidence_items`
- `conflict_type`
- `resolution`
- `kept_evidence`
- `removed_or_capped_evidence`
- `reason`
- `status`

Allowed resolution values are:

- `keep_more_specific`
- `keep_primary_evidence`
- `keep_mechanism_appropriate`
- `drop_as_not_used`
- `cap_combined_strength`
- `split_by_context`
- `defer_to_vcep`
- `unresolved_draft_only`

Common compatibility rules:

- BA1 excludes PM2/BS1 for the same disease context; BS1/BS2 exclude PM2 for
  the same frequency or healthy-carrier rationale.
- PP2 and BP1 are mutually exclusive.
- PVS1 canonical splice excludes same-mechanism PP3; PVS1_RNA and BP7_RNA
  consume RNA evidence before PS3/BS3, PP3/BP4, or contradicted PS1-splicing.
- PVS1 and PM4 cannot use the same protein-length or LoF consequence; PM4 and
  BP3 are mutually exclusive.
- PS3/BS3 consumes assay evidence before PP3/BP4; do not stack multiple assays
  unless VCEP, formal OddsPath, or validated combination rules permit it.
- PM1/PP2/BP1/PP3 interactions follow the PM1 overlay; PM1+PP3 is capped at
  Strong contribution.
- PS1 and PM5 cannot both use the same comparison relationship.
- The same proband, individual, family, or affected observation cannot be
  counted as PS4 plus PM3, PS2/PM6, PP1, or PP4.
- PP1/PP4 locus evidence is capped at +5.0 and cannot mix Biesecker points with
  informative-meioses fallback for the same pedigree.
- PM3 circularity, duplicate probands, homozygous cap, and PS2/PM6 high
  heterogeneity cap must be checked before final combine.
- Multiple-disorder or mechanism conflicts require `split_by_context`.
- Source assertions, inaccessible evidence, unread supplements, and
  low-confidence figure/OCR evidence cannot enter resolved counted evidence.

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
- structured functional-discovery coverage such as MaveDB; a hit triggers the
  PS3/BS3 overlay, but no hit should be recorded as coverage rather than as
  counted evidence;
- source assertion review when ClinVar, LOVD, HGMD, VCEP, or paper labels are
  available;
- disease/mechanism boundary overlays;
- PVS1 applicability gate, usually returning `not_applicable` for a pure
  missense variant unless another LoF-like consequence is present.

PP1 is not required at baseline. It is appended only if literature or user data
contains pedigree, segregation, family, cascade-screening, or affected-relative
evidence. If no such evidence is found, the report must include literature or
source coverage audit explaining why PP1 was not triggered.

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
