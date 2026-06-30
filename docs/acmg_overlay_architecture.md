# ACMG Overlay Architecture

## Canonical Skill Source

In this workspace, `skills/` is the canonical Skill source. `.agents/skills/`, `plugin/skills/`, and `plugins/tooluniverse/skills/` are treated as generated/deployment mirrors. Run `python3 scripts/check_skill_duplicate_drift.py` to ensure the protected ACMG and variant-interpretation Skill mirrors are byte-for-byte synchronized with canonical `skills/`.

The protected Skills are:
- `tooluniverse`
- `tooluniverse-variant-interpretation`
- `tooluniverse-acmg-variant-classification`
- `tooluniverse-acmg-overlay-routing-core`
- `tooluniverse-rare-disease-diagnosis`
- `tooluniverse-rare-disease-genomics`
- `tooluniverse-variant-functional-annotation`
- `tooluniverse-regulatory-variant-analysis`
- `tooluniverse-variant-to-mechanism`
- `tooluniverse-structural-variant-analysis`
- `tooluniverse-protein-sae-variant-interpretation`

The runtime Python implementation for shared ACMG guard policy lives in `src/tooluniverse/acmg_gate/`. Skill scripts under `skills/tooluniverse-acmg-overlay-routing-core/scripts/` are thin CLI wrappers around those canonical modules, and `src/tooluniverse/data/acmg_overlay_gate/scripts/` is the packaged runtime copy checked by the same drift tool.

## Runtime Boundary

ToolUniverse can enforce mandatory ACMG overlay routing once an agent enters ToolUniverse tool discovery or tool execution. It cannot globally intercept a final answer if the upper-level LLM runtime chooses not to call ToolUniverse at all.

Recommended deployment hooks:

- Pre-answer policy: if a user message matches `ACMG_FINAL_CLASSIFICATION` from `src/tooluniverse/acmg_gate/intent_detector.py`, call `ACMG_overlay_gate_assess_variant` before answering.
- Post-answer policy: if draft answer text contains ACMG final labels in English, shorthand, or Chinese from `src/tooluniverse/acmg_gate/final_label_detector.py`, call `ACMG_guard_final_answer` and block or downgrade unless the gate passes.

Without those hooks, skills and MCP tools provide fail-closed routing inside ToolUniverse, but they do not provide full global enforcement over arbitrary LLM text.

## Routing Flow

Germline ACMG/pathogenicity work starts at `ACMG_overlay_gate_assess_variant` or the `tooluniverse-acmg-overlay-routing-core` workflow. The variant-interpretation skill is intake-only: it normalizes requests, gathers source evidence, and identifies route candidates. It does not count ACMG evidence or emit final five-tier verdicts.

Route planning is driven by `tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml`. Criterion ownership, baseline route requirements, discovery routes, source-lead routes, and functional-database coverage semantics belong there rather than in ad hoc Python maps.

## Assessment Bundle

The `acmg_assessment_bundle` is the single required artifact for final ACMG classification. It contains:
- `bundle_route_plan` and `baseline_route_plan` — route planning
- `coverage_audit` — data-source coverage tracking
- `route_audit` — counted/un-counted evidence tracking
- `current_counted_evidence_resolved` — compatibility-resolved counted evidence
- `compatibility_resolution` — evidence conflict/compatibility docs
- `classification_status` — final or draft
- `classification` — the reported ACMG five-tier label

The schema is at `schemas/acmg_assessment_bundle.schema.json`.

## Policy Validator vs Semantic Combiner

Two independent validation layers gate any final ACMG classification:

1. **Policy Validator** (`scripts/validate_acmg_overlay_bundle.py`):
   - Trace and policy validation: route planning, coverage audit, source-lead bypass, context completeness, counted-evidence provenance.
   - Returns `PASS`, `DRAFT_ONLY`, or `FAIL`.

2. **Semantic Combiner** (`scripts/acmg_semantic_combiner.py`):
   - Conservative classification verification from `compatibility_resolution.current_counted_evidence_resolved`.
   - Implements explicit ACMG qualitative combination rules.
   - Blocks unsupported final labels (e.g., Pathogenic with PM2_Supporting only).
   - Returns `PASS`, `FAIL`, or `NOT_APPLICABLE`.

Both must pass (or the semantic combiner may return `NOT_APPLICABLE` for draft-only bundles) before `final_classification_allowed` can be true.

Finalization status is computed by `src/tooluniverse/acmg_gate/finalizer.py`. It is a small gate aggregator, not an ACMG rule engine: final output is allowed only when validator status is PASS, semantic combiner status is PASS, `final_classification_allowed` is true, a final classification was requested, compatibility-resolved counted evidence is present, and online literature coverage/review is ready.

Fixture categories are declared in `evals/fixture_manifest.yaml`. The validator and entrypoint-bypass checkers report per-category summaries so regressions can be tied to semantic-combiner, source-lead, context-trigger, direct-final-label, wrong-skill, direct-tool, valid-gate, or malformed-bundle coverage.

## Final Answer Guard

`scripts/acmg_final_answer_guard.py` provides the final text-level check:

- `contains_final_acmg_label(text)` — detects full labels, paired abbreviations, standalone abbreviations (LP, LB, VUS), and contextual single-letter labels (P, B).
- `guard_final_answer(text, bundle_or_status)` — returns BLOCK/DOWNGRADED/PASS based on whether validator_status is PASS, semantic_combiner_status is PASS, and final_classification_allowed is true.
- False-positive protection: "LP score", "B cell", "P value", "protein B domain", "gene B", "population frequency" are not treated as final labels.

## User Context Triggers

`scripts/acmg_context_triggers.py` detects user-provided clinical context and creates non-counted route candidates:

- de novo / trio / parents negative → PS2/PM6 (counted=false)
- segregation / pedigree → PP1/BS4/PP4 (counted=false)
- compound heterozygous / in trans / biallelic → PM3 (counted=false)
- HPO / phenotype specificity → PP4 (counted=false)
- unaffected adult carrier / healthy homozygote → BS2 (counted=false)
- alternate diagnosis → BP5 (counted=false)

User context must never directly become counted evidence.

## Functional Database Coverage

For missense variants, functional database coverage status must be explicitly recorded:

- `success` — query performed, usable hit found
- `no_hit` — query performed, no usable hit
- `unavailable` — tool/database unavailable
- `failed` — query attempted but failed
- `not_applicable` — only with explicit variant/context justification

`not_applicable` without an explicit reason causes a DRAFT_ONLY or FAIL result for missense variants.

## Adding Criteria Safely

When adding or changing an overlay:

1. Update `overlay_registry.yaml` first.
2. Add or update route-plan, coverage-audit, route-audit, and assessment-bundle schema examples if fields change.
3. Add validator fixtures for bypass, unsupported final labels, source-label misuse, missing coverage.
4. Add entrypoint bypass fixtures for any new final-label scenario.
5. Run:
   - `python3 skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py --fixtures skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures`
   - `python3 skills/tooluniverse-acmg-overlay-routing-core/scripts/check_entrypoint_bypass_fixtures.py --fixtures skills/tooluniverse-acmg-overlay-routing-core/evals/entrypoint_bypass_fixtures`
   - `python3 scripts/check_skill_duplicate_drift.py`

## Required Tests for New Overlays

Every new overlay must include:
- At least one validator fixture showing PASS behavior
- At least one validator fixture showing FAIL when the overlay is bypassed
- Entrypoint bypass fixtures covering direct final classification without the overlay
- The drift check must continue to pass after mirror sync
