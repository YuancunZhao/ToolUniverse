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

1. Call the known `ACMG_evidence_collector` directly with the supplied variant
   context and `response_detail="summary"`.
2. If `workflow_status` reports an identity/scope block, report that correction
   and stop. Otherwise build the answer directly from the returned fields.
3. Present the evidence table, external assertions, estimates, conflicts, and
   important limitations. A `degraded` or `partial` result does not hide cards
   that were successfully produced.
4. Call `ACMG_guard_final_answer` once with the draft and the returned
   `guard_context` object unchanged. Return only after `PASS`.

During this path do not list capabilities, call `get_tool_info`, run shell or
Python commands, write temporary files, inspect site-packages, directly import
the Guard, or repeat provider calls already performed by the collector. The
collector handles consequence fallbacks, literature retrieval and extraction,
VCEP/CSpec discovery, deduplication, conflict checks, and scoring internally.

Optional `literature_proposals` and `cspec_proposals` are supplemental
reproducibility inputs, not normal completion requirements. Optional
`evidence_decisions` requests a user-selected recalculation. `reviewer` and
`decided_at` are optional and never affect eligibility or scoring.

## Read the result, do not reconstruct it

Report in this order:

1. aggregated `evidence_cards`: criterion, strength, source, evidence status,
   primary rule reason, and caveats;
2. attributed `vcep_assertions` and isolated `rule_scenarios`;
3. `automatic_bayesian`, `verified_bayesian`, optional
   `user_selected_bayesian`, and `scenario_estimates`;
4. conflicts, provider limitations, and unresolved requirements.

`literature_candidates` is the complete compact lead index. A search hit is not
an EvidenceCard. A card is emitted only when a source-located atomic fact binds
the target and satisfies that criterion's minimum fields. Abstract or snippet
facts may support an automatic candidate when those fields are complete;
ordinary keyword/provider-linked leads do not enter Bayesian calculation.

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
  delta, and trigger channel. Maximum delta is not donor loss.
- PP3/BP4 uses the versioned calibrated predictor contract, not majority vote;
  all available predictor values remain visible when neither criterion is met.
- Provider failure is not absence evidence. Interpret `success`, `no_hit`,
  identity conflict, malformed contract, and technical failure separately.
- `final_classification_allowed` is always false. The Guard blocks unsupported
  criterion claims and ToolUniverse-authored five-tier labels, while allowing
  clearly attributed VCEP/ClinVar assertions.

See [QUICK_START.md](QUICK_START.md) for the exact compact-MCP and Reasonix call
shapes.
