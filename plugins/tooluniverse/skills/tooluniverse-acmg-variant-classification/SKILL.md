---

name: tooluniverse-acmg-variant-classification
description: "Automatically collect, map, and score source-backed evidence for germline small variants with ClinGen SVI and VCEP/CSpec rules. The result remains evidence-only and never supplies ToolUniverse's own five-tier classification."
---

# Germline Small-Variant ACMG Evidence Automation

This is the single user-visible ACMG Skill. The collector, not free-form model
reasoning, performs provider discovery, consequence recovery, literature fact
extraction, VCEP/CSpec rule mapping, conflict control, and Bayesian calculation.

## Scope and entry point

Before calling ACMG tools, distinguish a germline small variant from CNV/SV,
mitochondrial, somatic, and repeat-expansion requests. Intervals over 50 bp,
symbolic ALT, breakends, and DEL/DUP/INV/BND/CPX/CNV belong to
`tooluniverse-structural-variant-analysis`. Normalize hg19 to GRCh37 and hg38 to
GRCh38. Never assume a build for a bare genomic coordinate.

For a supported small variant call `ACMG_evidence_collector`. The
`ACMG_overlay_gate_assess_variant` tool is only a thin alias. The other five
evidence-group tools are optional focused-review surfaces:

- `ACMG_population_evidence`
- `ACMG_computational_evidence`
- `ACMG_clinical_evidence`
- `ACMG_functional_evidence`
- `ACMG_literature_evidence`

If ToolUniverse execution is unavailable, report that limitation. Do not
replace the collector with remembered exon structure, manual provider HTTP
calls, or model-invented ACMG scoring.

## Default workflow

1. Call `ACMG_evidence_collector` once with the variant and all known gene,
   transcript, disease, inheritance, build, protein, and clinical background.
   When the caller has case, family, phase, phenotype, assay, case-control, or
   case-series observations, pass them as `clinical_observations`.
2. If identity or scope is blocked, report the correction or recommended route.
   Otherwise directly present the EvidenceCard table, source facts, VCEP
   assertions, rule scenarios, conflicts, and estimates.
3. Show `automatic_bayesian`, `verified_bayesian`, `scenario_estimates`, and—if
   requested by the user—`user_selected_bayesian` as review estimates.
4. Call `ACMG_guard_final_answer` with the returned `guard_context` before
   returning criterion claims.

The collector automatically runs applicable consequence fallbacks, online
CSpec/VCEP discovery, literature retrieval, deterministic text extraction,
deduplication, rule mapping, and scoring. Do not ask the user whether papers or
alternative providers should be queried. Do not make normal completion depend
on a host LLM, `literature_proposals`, or `cspec_proposals`.

`literature_proposals` and `cspec_proposals` remain optional supplemental and
reproducibility inputs for passages that deterministic extraction could not
resolve. A second collector call is appropriate only when such supplemental
material or `evidence_decisions` is actually supplied. `reviewer` and
`decided_at` are optional and their absence never changes scoring.

## Evidence semantics

Every successful, empty, failed, stale, incomplete, or conflicting source is
retained as a SourceFact. An EvidenceCard is created when a criterion has an
actual source-backed fact; lack of information appears only in
`criterion_reviews`, never as an empty placeholder card.

EvidenceCard v3 uses these statuses:

- `expert_panel_applied`: an exact released VCEP application;
- `rule_mapped`: a versioned SVI or applicable CSpec rule was satisfied;
- `source_backed_candidate`: traceable evidence supports a legal candidate,
  but strict verification or an exact disease-specific rule may be absent;
- `not_met`: relevant facts were found but do not meet the rule;
- `excluded`: identity, contradiction, duplication, incompatibility, or rule
  applicability prevents use;
- `deprecated`: PP5/BP6 source assertions, never scored.

The answer must expose criterion, tool-proposed strength, evidence status,
`strength_source`, `rule_source`, sources/excerpts, verification dimensions,
calculation roles, limitations, and exclusion reasons. Candidate evidence is
not hidden merely because it is based on an abstract, snippet, generic domain,
unversioned source, or caller-supplied observation. Those limitations determine
whether the card enters the automatic or verified estimate; they do not erase
the information.

### Three calculation views

- `automatic_bayesian` includes legal source-backed candidates after criterion,
  case/family/cohort/experiment, correlation, and conflict deduplication.
- `verified_bayesian` includes exact VCEP/CSpec, versioned SVI, and strictly
  anchored facts only.
- `user_selected_bayesian` includes accepted regenerated cards. A reason is
  required only for `strength_override`. All accepted cards must come from one
  scenario; never mix generic, disease, or inheritance scenarios.

Never invent source-quality discounts to Tavtigian odds. Use the difference
between automatic and verified estimates to communicate uncertainty. BA1 is a
special criterion and does not silently enter the ordinary odds product. All
posteriors use the fixed 0.1 prior and remain review estimates.

## Clinical observations

`clinical_context` is background used for retrieval and consistency checks.
`clinical_observations` is the structured evidence channel. Each item requires
`observation_id`, `observation_type`, `source_type`, `source_id`, and `values`;
`locator` and `excerpt` are optional. Supported types include de novo,
recessive case, segregation, phenotype specificity, healthy observation,
allelic phase, alternative cause, functional assay, case-control, and case
series.

Caller-supplied observations may enter `automatic_bayesian`. They enter
`verified_bayesian` only when a provider, publication, or re-fetchable report
anchors them. Never send private clinical observations to external providers
unless the user explicitly asks for that transmission.

## VCEP, CSpec, and literature

The collector searches the ClinGen CSpec Registry and Evidence Repository after
gene identity is confirmed. A uniquely matched released CSpec can modify
criterion applicability and strength. If disease or inheritance is missing or
multiple specifications could apply, the collector creates isolated
`rule_scenarios`; never combine criteria across scenarios.

An exact VCEP curation is an external expert assertion. Report its five-tier
label only with attribution such as “ClinGen VCEP classified this variant as
...”, including condition, inheritance, panel, version, release date, and URL.
Its applied criteria can become `expert_panel_applied` cards. Never present the
VCEP label as ToolUniverse's own final classification.

The internal literature chain is retrieval followed by deterministic rule
extraction. It checks VCEP/ERepo structured summaries, Europe PMC XML or HTML,
PubTator locations, tables/captions/supplements, PubMed abstracts, and
provider-linked snippets. Search queries do not prove a variant match. A PMID
or PMCID does not prove that full text was retrieved. If only an abstract or
snippet contains a clear fact, emit a source-backed candidate and identify the
limited source status; never claim the full article was read.

The deterministic fact map covers PS4, PS2/PM6, PM3, PS3/BS3, PP1/BS4, PP4,
BS2, BP2, BP5, PS1/PM5, PM1, PP2/BP1, PM4/BP3, and RNA-splicing facts. Optional
LLM extraction may resolve difficult prose, but is neither a runtime dependency
nor a completion requirement.

## Scientific boundaries

PVS1 never receives a generic fallback strength. It must pass the existing
transcript, consequence, native splice-site, frame/NMD, LoF mechanism, and
downgrade decision tree. Frameshift, stop-gained, LOFTEE HC, or HIGH impact
cannot supply missing exon count, PTC position, NMD, or disease mechanism.

For SpliceAI, report `DS_AG`, `DS_AL`, `DS_DG`, and `DS_DL`, their positions,
the maximum delta, and trigger channel. Do not recompute delta scores from raw
REF/ALT values. Donor loss uses DS_DL and acceptor loss uses DS_AL at the
selected-transcript boundary. A low loss score for a canonical insertion or
duplication is not proof of normal splicing.

PP3/BP4 follows the versioned calibrated predictor contract, not majority vote.
All available predictor values remain visible even when neither criterion is
met. ClinVar, GeneBe, InterVar, generic constraint/domain, HPO matches, and
author labels remain source assertions unless a valid rule maps the underlying
fact. PP5 and BP6 remain deprecated.

## Answer contract

Lead with a compact evidence table. Then show external VCEP assertions,
automatic/verified/user estimates, scenario separation, conflicts and important
limitations. Distinguish source observation, criterion candidate, verified
application, and user selection.

Use `ACMG_guard_final_answer` with `guard_context`. The Guard allows sourced
candidate criteria, external assertions with explicit attribution, and all
three review estimates. It blocks unsupported criterion claims and any
ToolUniverse-authored five-tier final classification. The collector always
returns `final_classification_allowed: false`.

See [QUICK_START.md](QUICK_START.md) for request examples.
