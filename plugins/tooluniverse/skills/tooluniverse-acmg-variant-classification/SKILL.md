---

name: tooluniverse-acmg-variant-classification
description: "Collect and evaluate evidence for germline small-variant ACMG requests through the ToolUniverse ClinGen/SVI evidence-only runtime. Use for pathogenicity, clinical-significance, ACMG-criteria, EvidenceCard, conflict-review, or Bayesian-review requests; it never produces a five-tier final classification."
---

# Germline Small-Variant ACMG Evidence Assessment

Use this Skill as the single ACMG routing and evidence-assessment contract.
Scientific criterion decisions belong to deterministic ToolUniverse rules, not
free-form model reasoning.

## Required Entry Point

First classify the input shape. Genomic intervals over 50 bp, symbolic ALT or
breakend notation, and DEL/DUP/INV/BND/CPX/CNV events are structural variants:
route them to `tooluniverse-structural-variant-analysis` without calling the
small-variant collector. Normalize hg19 to GRCh37 and hg38 to GRCh38. A
coordinate input with no explicit or accession-inferred build must stop for
input correction; never silently assume GRCh38.

For every germline small-variant ACMG request, call
`ACMG_evidence_collector`. `ACMG_overlay_gate_assess_variant` is a
backward-compatible alias with the same parameters and return structure; it has
no separate mode or business logic.

If `find_tools`, `get_tool_info`, `list_tools`, or `execute_tool` is unavailable,
stop the assessment and report `ToolUniverse MCP execution unavailable`. Do not
switch to direct provider HTTP requests, manual ACMG scoring, or general-model
inference as a fallback.

The collector returns SourceFacts, visible external leads, EvidenceCard
criterion/strength proposals, compatibility and conflict reports, a
system-preview Bayesian estimate, and—after explicit evidence decisions—a
separate user-selected estimate. It always returns
`final_classification_allowed: false`. `runtime_manifest` anchors the installed
runtime, schema, deterministic ruleset hash, available VCS revision, and
applicable dynamic CSpec.

If a mistakenly submitted event returns
`workflow_status: unsupported_variant_class`, execute the structural-variant
route in `next_actions`; do not reinterpret that response as a recoverable
consequence failure.

For targeted review, the five deterministic group tools are:

- `ACMG_population_evidence`
- `ACMG_computational_evidence`
- `ACMG_clinical_evidence`
- `ACMG_functional_evidence`
- `ACMG_literature_evidence`

Direct group calls are review tools; the collector is the full-pipeline entry
point that binds provider-verified facts into compatible EvidenceCards.

## Evidence Workflow

Run this state machine to completion in the same user task:

1. Call the collector with the variant and all known gene, transcript, disease,
   inheritance, phenotype, and protein context.
2. Inspect `workflow_status`, `recoverable_gaps`, `next_actions`,
   `review_readiness`, `criterion_reviews`, `consequence_profile`,
   `literature_review.review_requests`, and
   `rule_context.cspec_review_requests`.
3. The collector performs every applicable read-only consequence recovery
   query itself. Do not ask the user whether to try VariantValidator, FAVOR,
   OpenTargets, Mutalyzer, GenomeNexus, ProtVar, or another listed provider.
4. Execute every pending `next_actions` item assigned to `host_llm`. For
   literature, try each listed full-text tool once in order, read the complete
   accessible article section by section, and inspect relevant tables, figure
   captions, and supplements.
5. Generate source-located `literature_proposals` and/or `cspec_proposals`, then
   call the collector again automatically.
6. If that call discovers new exact/equivalent documents, process only the new
   request IDs and allow one incremental collector call. Never repeat a
   completed request or unchanged document hash.
7. End automated collection only when no mandatory request remains, or when
   the result is stably `blocked_external_full_text`. Return EvidenceCards,
   exclusions, conflicts, `review_readiness`, and `system_preview_bayesian`.
8. Call `ACMG_guard_final_answer` before returning criterion claims.

Read-only retrieval, consequence recovery, full-text reading, structured fact
extraction, proposal generation, and the system preview do not require
step-by-step user permission. Never ask “should I read the papers?” or “should
I call an alternative tool?” when `next_actions` or applicable ToolUniverse
providers can continue the task. The user decision round is separate and is
needed only when the user asks to accept, reject, or change cards for
`user_selected_bayesian`.

`review_readiness.status=ready_for_evidence_review` means every currently
executable collection action has finished. It does not mean all 28 criteria
have evidence and never means a five-tier classification is ready. Read each
criterion's `route_status`: `assessed`, `proposal_validated`,
`candidate_available`, `review_pending`, `insufficient_information`,
`not_applicable`, or `deprecated`. Missing optional family, case, phenotype,
or literature evidence remains `insufficient_information` and does not by
itself block evidence review.

See [QUICK_START.md](QUICK_START.md) for the three-round request shape.

## CSpec and Literature Contracts

A CSpec applies only after a unique released gene, MONDO disease, and
inheritance match. Structured online fields may drive deterministic rules.
Natural-language thresholds remain in `rule_context.cspec_review_requests`
until a host-LLM proposal is re-anchored to the current specification ID,
version, content hash, locator, and excerpt. Local CSpec contracts are
exact-hash caches or fixtures, never an online-rule whitelist.

For every exact/equivalent paper, follow
`literature_review.review_requests`. A PMID, `inEPMC`, snippet, or text-mining
hit does not prove full-text availability. Try the ordered `tool_attempts`;
abstract-only or unavailable material remains a source lead.

Read Methods, Results, tables, figure captions, and accessible supplements—not
only the abstract. Submit a `reading_manifest` with publication identifiers,
document hash when available, `complete|partial|abstract_only|unavailable`
status, sections/tables/figures/supplements read, variant-match locations, and
limitations. Literature proposals must include a PMID or PMCID, exact locator,
excerpt, structured values with per-field excerpts, interpretation, confidence,
extractor name/version, and unresolved questions. `criterion` and
`suggested_strength` are optional suggestions; the collector independently
enforces the fact-type-to-criterion matrix.

When relevant evidence is available only in a paper figure, panel, plot, or
table image, route extraction to
`tooluniverse-literature-figure-evidence-extraction` first. Feed its
source-located, excerpt-backed structured result into `literature_proposals`;
the figure Skill does not assign or count ACMG criteria by itself.

ToolUniverse re-fetches source documents and reports `anchor_status` separately
from `semantic_status`. Unavailable or mismatched full text and contradicted
semantics remain visible but do not enter the system preview. A verified anchor
with unresolved machine semantics remains a review-required proposal.
Deterministic PS2/PM6, PM3, and PS3/BS3 processing emits one rule card and
stores the LLM interpretation on that card rather than double-counting it.

## Deterministic Rule Boundaries

Never assign a criterion directly from ClinVar, GeneBe, InterVar, CADD, gnomAD,
an abstract keyword, or general model knowledge. Preserve database conclusions,
constraint, HPO matches, actionability, uncalibrated predictors, and domain
overlap as visible source leads or review context until a versioned SVI/CSpec
rule maps them.

The collector resolves one selected-transcript ConsequenceProfile from all
applicable identity-bound observations. VEP is not a required single point of
failure: VariantValidator/VariantFormatter, FAVOR, OpenTargets transcript
consequences, Mutalyzer, GRCh37 GenomeNexus, protein-representable ProtVar, and
single-allele rsID sources are attempted when applicable. `vep_derived`
aggregators are labeled and never presented as independent consensus. The
resolver uses exact RefSeq, unique MANE mapping, then version-compatible
transcripts; it never uses majority voting. Build, allele, gene, or transcript
conflicts fail closed.

Consequence controls criterion applicability but does not itself establish
evidence strength. Frameshift/stop-gained, LOFTEE HC, or HIGH impact cannot
supply exon count, PTC position, NMD, or disease mechanism. Never fill those
facts from model memory or promote a manually called provider directly into
PVS1; every fact must return through the collector. Generic UniProt/InterPro
overlap is PM1 review context only; PM1 requires an exact online-bound CSpec
region contract.

Only cards with `assessment_status: met`, `system_preview_included: true`,
`overlay_validated: true`, and trusted non-empty `source_fact_ids` support the
system-preview estimate. `not_met`, `not_assessed`, `not_applicable`,
deprecated cards, and source leads do not enter it. PP5 and BP6 remain
deprecated.

For missense variants, same-residue EBI Proteins records and ClinVar Variation
IDs are `prior_variant_candidates` only. Automatically execute their
`prior_variant` full-text requests; PS1/PM5 requires an independently anchored
prior-variant identity and pathogenic evidence. A database label alone must
never enter Bayesian computation. Generic domains, constraint, and validity
are likewise PM1/PP2/BP1 context only. Identity-bound in-frame or stop-loss
facts may generate review-required PM4/BP3 proposals only when repeat and
functional-feature overlap are explicitly resolved.

`clinical_context` is caller-provided background for search and consistency
checking, not a clinical observation channel. Zygosity, phase, phenotype, HPO,
parental-origin, and second-allele values there never generate PP1/BS4, PP4,
BS2, BP2, BP5, PS2/PM6, or PM3. Such evidence must arrive as re-fetchable,
full-text-anchored `literature_proposals`.

`gnomad_get_site_callability` records auditable coverage. Without an applicable
CSpec, general ClinGen/SVI may suggest PM2_Supporting for AC=0 with verified
callability. BS1 still requires a disease-specific maximum credible allele
frequency.

## SpliceAI and PVS1

Generic Walker SpliceAI evidence is Supporting only: raw max delta >=0.2 may
suggest PP3_Supporting and <=0.1 may suggest BP4_Supporting. The collector
requires the calibrated 1.3.1/MANE/raw/unmasked/distance-500 run contract and
one identity-bound score row. After strict BP4, eligible synonymous or
deep-intronic variants may suggest BP7_Supporting using the +7/-21 boundaries.
Direct RNA-splicing assays never generate PS3/BS3.

Treat `DS_AG`, `DS_AL`, `DS_DG`, and `DS_DL` as the provider's four delta
scores; never recompute them from REF/ALT raw scores. Report all four scores and
positions, the maximum delta, and every trigger channel. For canonical PVS1,
donor sites use `DS_DL` and acceptor sites use `DS_AL`, paired with the matching
DP position at the selected-transcript exon boundary. General native-site loss
uses score >=0.5; canonical `+2T>C` uses >=0.8. Gain events are alternative-site
context and cannot replace native-site loss.

Canonical insertions or duplications may leave or recreate GT/AG motifs. Do not
stop before SpliceAI interpretation, but do not treat a low Loss score as proof
of normal splicing. A boundary-matched Loss score meeting the applicable
threshold may enter the existing PVS1 frame/NMD decision tree; unresolved
native-site loss or transcript/frame consequences remain `not_assessed`.
Verified RNA or an exact-hash operation-specific CSpec may resolve remaining
branches. Literature mechanism facts may feed PVS1 only with a controlled
mechanism value and `semantic_status=verified`; they cannot bypass the
deterministic decision tree.

## Review and Recalculation

Treat every card as a proposal, not a clinical decision:

- `system_preview_included` is card inclusion in
  `system_preview_bayesian`, ToolUniverse's review estimate.
- A valid `requires_user_review` proposal may enter that preview after identity,
  source, strength, and compatibility checks.
- Same-criterion duplicates, shared cases/families/cohorts/experiments, splice
  overlap, and directional conflicts are excluded by compatibility rules while
  remaining visible.
- `user_selected_bayesian` includes accepted regenerated cards only.

Each evidence decision requires `card_id` and `decision=accept|reject`. A
strength override must remain direction-consistent and include a reason.
Unmatched stable IDs and invalid overrides remain explicit decision errors.
`reviewer` and `decided_at` are optional provenance fields: never require them,
warn about their absence, exclude evidence, or alter scoring when omitted.

## Answer Policy

Clearly distinguish observed facts, source leads, system suggestions,
system-preview inclusion, and user acceptance. The Bayesian posterior is a
review estimate, not a final classification.

Call `ACMG_guard_final_answer` before returning criterion claims. The runtime
blocks Pathogenic, Likely Pathogenic, VUS, Likely Benign, Benign, and equivalent
Chinese five-tier labels. ToolUniverse enforcement begins only after the agent
enters its explicit ACMG policy context; global enforcement requires host
pre-answer and post-answer hooks. The framework-neutral reference is
`examples/acmg_host_hooks.py`.
