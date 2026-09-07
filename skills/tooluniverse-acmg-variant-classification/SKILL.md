---
name: tooluniverse-acmg-variant-classification
description: Automatically collect, map, deduplicate, and score source-backed evidence for germline small variants with ClinGen SVI and VCEP/CSpec rules. ToolUniverse remains evidence-only and does not issue a five-tier classification.
---

# Germline small-variant ACMG evidence

Use this single Skill for germline SNVs and indels up to 50 bp. Route larger
intervals, symbolic ALT, breakends, DEL/DUP/INV/BND/CPX/CNV, somatic,
mitochondrial, and repeat-expansion requests to their dedicated workflows.
Normalize hg19 to GRCh37 and hg38 to GRCh38; do not assume a build for a bare
genomic coordinate.

## Normal path: exactly two tool calls

Use `evidence_cards.observed_facts` for card-specific numbers and the indicated
summary references for shared consequence/predictor/population values. Do not
drop zero or false values. Every criterion review now states its own status;
there is no `criterion_review_defaults`. Literature titles and
`abstract_available` describe what was actually retrieved.

`literature_review.fact_reviews` preserves incomplete and target-linked negative
observations; these are review-only, not extra cards or user-selectable evidence.
`serialization_diagnostics` records invalid card outputs without claim IDs.
Discuss these limits without promoting them to a criterion or score.

For an explicitly requested wider search, pass `literature_search_limits`
with any of `pubmed`, `europe_pmc`, `litvar`, `pubtator` (integers 1–1000).
Defaults are 50/100/50/10. PubTator pages are sequential and counted before
score filtering. `literature_review.search_summary` reports actual queries,
returned/retained/filtered counts, unknown totals as null, and stop reasons.
`fulltext_match_classes` can broaden retrieval to existing match classes;
an empty list disables normal automatic fulltext and annotations, not explicit
proposal re-anchoring. Retrieval scope never changes target-link or evidence
eligibility. Use returned summaries intact, including results larger than 40 KB.

External laboratory conclusions may be quoted with a named laboratory/report
and explicit attribution. This is permission to cite, not a claim that Guard
verified that laboratory conclusion. ToolUniverse must not add its own label.

This Skill is already-loaded execution guidance, not a capability to invoke.
Do not call `skill:...` or rediscover either ACMG tool.

1. Call the known `ACMG_evidence_collector` directly with the supplied variant
   context and `response_detail="summary"`.
2. If `workflow_status` reports an identity/scope block, report that correction
   and stop. Otherwise build the answer directly from the returned fields.
3. Present the evidence table, external assertions, estimates, conflicts, and
   important limitations. A `degraded` or `partial` result does not hide cards
   that were successfully produced.
4. Call `ACMG_guard_final_answer` once with the complete final answer text and
   the returned `guard_context` unchanged. After `PASS`, return that exact text;
   do not append unguarded scientific interpretations.

During this path do not list capabilities, call `get_tool_info`, run shell or
Python commands, write temporary files, inspect site-packages, directly import
the Guard, or repeat provider calls already performed by the collector. The
collector handles consequence fallbacks, literature retrieval and extraction,
VCEP/CSpec discovery, deduplication, conflict checks, and scoring internally.
For multiple variants, repeat the same two calls independently for each
variant; do not combine their cards or Guard contexts.
Wait for the configured long-running MCP call. A timeout is an execution issue,
not absence of evidence; do not rerun to "warm the cache" or switch to an
unverified local `tu`/Python environment. Report an installation/timeout issue
if the configured MCP call cannot finish.

The two-call rule is the normal path, not a ban on collector self-recovery.
Inside that call, transient failures receive one bounded collector retry;
failed and successful attempts remain sourced. Selected-transcript structure
can fall back to Tark MANE/transcript records and GRCh38 Ensembl exon overlap.
OMIM gaps can fall back to the existing multi-source gene-disease tool. A
ClinVar gene hit is a coverage signal, not proof of a particular OMIM disease
or LoF mechanism. Zero returned associations with failed sources means a
provider gap, not confirmed biological absence.

Only after an unresolved degraded result, optional `recoverable_gaps.repair_plan`
steps may be executed as a targeted enrichment round. Resolve the declared
argument dependencies; never guess ENST, coordinates or build. Return the
named tool's original result via `caller_verified_context` with `context_id`,
`context_type`, `tool_name`, `query`, `values`, `provider_version` and timezone-
qualified `retrieved_at`. Despite the legacy-looking input name, these are
caller-attributed facts, not independently verified facts. They never directly
enter the verified estimate. Do not turn a manual tool response into a card;
run the collector with the original variant plus the enrichment, then use only
that new run's unchanged Guard context. Do not repeat identical failed steps
or rerun just to warm caches. No shell or files are needed for enrichment.

Call the compact MCP surface with this exact shape:

```json
{"tool_name":"ACMG_evidence_collector","arguments":{"variant":"<original user string>","gene":"<submitted gene if any>","clinical_context":{"zygosity":"<if supplied>"},"response_detail":"summary"}}
```

Preserve the original `gene;NM_:c.(p.)` string in `variant`. Put a supplied
heterozygous/homozygous state in `clinical_context.zygosity`; do not strip it or
silently rewrite the submitted gene. Then pass the returned context unchanged:

```json
{"tool_name":"ACMG_guard_final_answer","arguments":{"final_answer_text":"<draft evidence-only answer>","guard_context":{"<exact collector guard_context>":"..."}}}
```

Optional `literature_proposals` and `cspec_proposals` are supplemental
reproducibility inputs, not normal completion requirements. Optional
`evidence_decisions` requests a user-selected recalculation. `reviewer` and
`decided_at` are optional and never affect eligibility or scoring.
Every submitted literature item appears once in `proposal_report`. If a cited
document cannot be independently retrieved, a proposal with a valid document
SHA-256, literal excerpt, locator, publication identifier, and versioned
extractor may appear as an `externally_anchored` review card. Such a card is
never automatic or verified; a user may select it only with a legal existing
strength or a direction-consistent `strength_override` plus `reason`. Report
that boundary explicitly and do not describe the document as independently
verified.

## Read the result, do not reconstruct it

Report in this order:

1. aggregated `evidence_cards`: criterion, strength, source, evidence status,
   primary rule reason, and caveats;
2. attributed `vcep_assertions` and isolated `rule_scenarios`;
3. `automatic_bayesian`, `verified_bayesian`, optional
   `user_selected_bayesian`, and `scenario_estimates`;
4. `population_observations`, predictor values, conflicts, provider limitations,
   and unresolved requirements, including `criterion_reviews.rule_evaluations`.

Population AF/AC/AN remains available without a PM2 card. Preserve the dataset,
callset and exact subgroup label (e.g. `eas_XX`, not all East Asian individuals).
An observed allele is not absent. Generic BA1 uses 5%, not 1%; a failed fork
PM2 candidate filter is not a definitive disease-specific PM2 exclusion.
Summary consequence `observation_groups` factors out `shared` fields and gives
`columns` with corresponding `rows`; all distinct observations are retained.
The selected consequence is explicit. Do not write code to expand the index.
40 KB is a summary optimization target, not a failure boundary. Larger results
remain complete: do not retry collection, request full, or hide evidence because
of response size. All referenced SourceFacts are indexed in the summary; report
any `source_reference_unresolved` limitation without inventing provenance.
`criterion_reviews.other_card_results` groups equal explanations within one
representative card and scenario; `card_ids` retains the atomic IDs. This is
display-only, not an additional scoring or case-aggregation step.
Use the returned data directly. A concise final answer need not recite every
background index, but must not imply those entries were absent from the tool
result. Do not use shell, files, directory enumeration, or manual JSON
reconstruction to consume a larger summary.

`literature_candidates` is the complete compact lead index. A search hit is not
an EvidenceCard. A card is emitted only when a source-located atomic fact binds
the target and satisfies that criterion's minimum fields. Abstract or snippet
facts may support an automatic candidate when those fields are complete;
ordinary keyword/provider-linked leads do not enter Bayesian calculation.
The collector obtains one canonical body per publication: Europe PMC/PMC JATS
first, PubTator BioC full text when the PMC body is incomplete or target binding
needs annotation, then an open-access PDF snippet fallback. PubTator search
failure does not disable PMID export or the other discovery sources. CORE
snippets never enter the verified estimate, and inaccessible supplements remain
an explicit limitation rather than guessed evidence.
In summary mode, merge `literature_candidate_defaults` into each candidate row;
per-record values override defaults, and explicit null stays unknown. This does
not truncate leads.

`clinical_context` is retrieval background. Structured case, family, phase,
phenotype, assay, case-control, or case-series evidence belongs in
`clinical_observations`. Caller-supplied observations may enter the automatic
estimate; only independently re-anchored observations enter the verified
estimate.

The calculation views are review estimates with fixed prior 0.1:

- `automatic_bayesian`: legal source-backed representative cards;
- `verified_bayesian`: strictly identity-, source-, and rule-verified cards;
- `user_selected_bayesian`: accepted regenerated cards only.

Never combine cards across disease/inheritance scenarios. BA1 remains special.
PP5/BP6 and database labels remain attributed source assertions rather than
criteria. An exact released VCEP label may be reported only as an external
expert assertion, never as ToolUniverse's own conclusion.

## Scientific boundaries retained by the runtime

- PVS1 must pass the existing selected-transcript, native splice-site,
  frame/NMD, LoF mechanism, and downgrade decision tree; no generic fallback.
- SpliceAI reports `DS_AG`, `DS_AL`, `DS_DG`, and `DS_DL`, positions, maximum
  delta, and trigger channel. Read the selected-transcript four-channel maximum
  separately from the provider-global maximum; a higher score on another
  transcript is context, not a conflict. Maximum delta is not donor loss.
- Multi-provider consequence collection is not majority voting. One
  allele-bound authoritative selected-transcript result is usable; alternate
  transcripts, empty rows, `no_hit`, and provider failures remain visible but
  do not veto it. Mutalyzer and g:Profiler are normalization context: a
  different HGVS string without a directly comparable genomic allele is not a
  conflict. Only explicit authoritative allele/build conflict or incompatible
  authoritative results on the same selected transcript fail closed.
- PP3/BP4 uses the versioned calibrated predictor contract, not majority vote;
  all available predictor values remain visible when neither criterion is met.
  Low SpliceAI does not exclude a missense/inframe protein effect or cancel
  REVEL PP3. Use the runtime's protein_effect/splicing scope and rule reasons.
  Do not infer criteria from "多数预测耐受/无害" or "高度一致有害".
- Provider failure is not absence evidence. Interpret `success`, `no_hit`,
  identity conflict, malformed contract, and technical failure separately.
- `criterion_reviews` may be discussed exactly as review-only,
  not-applicable, or insufficient-information results; these are not
  EvidenceCards and never enter Bayesian calculation. The returned
  `guard_context` carries those review claims automatically.
- `final_classification_allowed` is always false. The Guard blocks unsupported
  criterion claims and ToolUniverse-authored five-tier labels, while allowing
  clearly attributed VCEP/ClinVar assertions.

[QUICK_START.md](QUICK_START.md) contains the same two calls for copy/paste, but
reading it is not a prerequisite for a normal evaluation.
