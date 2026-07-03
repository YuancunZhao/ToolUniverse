# ACMG Overlay Architecture

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

For the staged path from guarded overlay extension to a higher-automation ACMG intelligent
rating assistant, see `docs/acmg_automation_roadmap.md`.

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

## Enforced Protocol Layers

ACMG final-classification workflows now use protocol-level enforcement rather than advisory tool metadata alone:

1. `pre_router.py` classifies raw user requests with the canonical intent detector and returns whether an ACMG assessment session, front-door tool, sandboxed source tools, and token-gated final labels are required.
2. `session.py` stores an explicit ACMG assessment session state machine. Source tools can add only source leads; user context can add only counted=false route candidates; counted evidence can come only from overlay-validated evidence or canonical finalizer-approved adapters.
3. `source_lead_sandbox.py` preserves medically necessary facts from GeneBe, InterVar, ClinVar, SpliceAI, CADD, AlphaMissense, REVEL, OpenCRAVAT, VEP, gnomAD, literature, ClinGen/G2P, and user context while quarantining final-like conclusions and automated criteria. Candidate routes remain counted=false.
4. `transaction.py` records required overlay actions as transaction steps. Universal PM2 rarity, BA1/BS1 frequency, and compatibility resolution baselines are required before finalization, with additional actions triggered by predictors, source assertions, literature, splice context, and conflicts.
5. `finalizer.py` issues an `acmg-final:v1:<hash>` token only after validator PASS, semantic combiner PASS, `final_classification_allowed=true`, required actions complete, literature ready when required, and non-empty overlay-validated counted evidence.
6. `final_answer_guard.py` blocks any English, shorthand, or Chinese ACMG final-like label unless the session is `FINALIZED` and the finalization token verifies.
7. `draft_policy.py` defines the only allowed blocked-output shape: variant normalization, source leads, sandbox summaries, counted=false route candidates, missing overlays/literature/coverage, why final classification is blocked, and next ToolUniverse actions.

This means a disclaimer such as "draft only" does not permit final labels. Draft/provisional wording that still contains a final-like ACMG label is blocked without a valid finalization token.

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

Finalization status is computed by `src/tooluniverse/acmg_gate/finalizer.py`. It is a small gate aggregator, not an ACMG rule engine: final output is allowed only when validator status is PASS, semantic combiner status is PASS, `final_classification_allowed` is true, a final classification was requested, compatibility-resolved counted evidence is present, online literature coverage/review is ready, required overlay transaction actions are complete, and a finalization token has been issued.

Fixture categories are declared in `evals/fixture_manifest.yaml`. The validator and entrypoint-bypass checkers report per-category summaries so regressions can be tied to semantic-combiner, source-lead, context-trigger, direct-final-label, wrong-skill, direct-tool, valid-gate, or malformed-bundle coverage.

## Final Answer Guard

`scripts/acmg_final_answer_guard.py` provides the final text-level check:

- `contains_final_acmg_label(text)` — detects full labels, paired abbreviations, standalone abbreviations (LP, LB, VUS), and contextual single-letter labels (P, B).
- `guard_acmg_final_answer(answer_text, session, finalization_token, intent)` — canonical text guard; returns BLOCK/PASS based on final-label detection, the canonical finalization gate, session state, finalization-token verification, and classification binding.
- `guard_final_answer(text, bundle_or_status)` — deprecated backward-compatible wrapper over `guard_acmg_final_answer`.
- False-positive protection: "LP score", "B cell", "P value", "pathogenic bacteria", "致病机制", "良性肿瘤", "protein B domain", "gene B", and "population frequency" are not treated as final labels.

## GeneBe and Other Source Tools

GeneBe is retained because its output is medically useful for audit, search, and route planning. In ACMG final-classification context it is always source-lead-only: automated labels and proposed criteria are preserved in `quarantined_conclusions`, converted to counted=false route candidates, and never used as counted evidence. The same pattern applies to InterVar and ClinVar source assertions.

SpliceAI, CADD, AlphaMissense, REVEL, VEP/OpenCRAVAT, MyVariant, and gnomAD/population tools are also preserved as evidence inputs. Numeric scores, allele frequencies, consequence annotations, model versions, transcript mapping, and coverage details remain reviewable features, but any direct PP3/BP4, PM2, BA1/BS1, benign/pathogenic, or final-classification suggestions are quarantined until the relevant overlay validates them.

Literature tools preserve PMID, title, abstract, methods, phenotype, variant mention, assay details, segregation/de novo claims, and quality indicators. They do not directly count PS3/BS3, PS2/PM6, PP1/PP4, PS4, or final classifications without literature review and overlay validation.

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

## ACMG Overlay MCP Tools (branch `acmg-overlay-mcp-tools`)

In addition to the 7-layer gate enforcement system on `codex/skills-overlay`, a new architecture is under development on branch `acmg-overlay-mcp-tools` that exposes each ACMG criterion as an independent deterministic MCP tool.

**Motivation:** The gate system requires the LLM to voluntarily enter `ACMG_overlay_gate_assess_variant`. If the LLM bypasses the gate, all 7 enforcement layers are skipped. The overlay MCP tools mitigate this by making individual criterion judgment tools independently callable — the LLM can call `ACMG_overlay_pm2` directly with gnomAD data and get a deterministic PM2_Supporting/not_met judgment without going through the Gate.

**Architecture:**
- `src/tooluniverse/acmg_overlay_tools/` — 10 modules (1183 lines)
  - `router.py`: variant type inference + overlay applicability routing
  - `pm2.py`, `pp3_bp4.py`, `ps1_pm5.py`, etc.: deterministic criterion judgment
  - `combine.py`: ACMG/AMP 2015 classification rules + ClinGen SVI PVS1+PM2→LP rule
  - `base.py`: shared output_template + hardcoded registry tables
- `src/tooluniverse/tools/ACMG_route_overlays.py` — MCP wrapper
- `src/tooluniverse/tools/ACMG_overlay_pm2.py` — MCP wrapper
- `src/tooluniverse/tools/ACMG_combine_criteria.py` — MCP wrapper

**Design principle:** LLM collects evidence from external data sources (gnomAD, ClinVar, MyVariant, SpliceAI, PubMed). LLM passes structured data to overlay tools. Overlay tools apply ClinGen/SVI rules deterministically. Same input → same output. LLM never does ACMG judgment — only evidence collection and literature extraction.
