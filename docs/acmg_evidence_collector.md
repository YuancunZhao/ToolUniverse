# ACMG Evidence Collector v3

`ACMG_evidence_collector` is an automated evidence workbench for germline small
variants. It exhaustively collects traceable facts, maps them through ClinGen
SVI and applicable VCEP/CSpec rules, removes duplicates and hard conflicts, and
returns three Bayesian review views. It does not issue ToolUniverse's own
Pathogenic, Likely Pathogenic, VUS, Likely Benign, or Benign classification.

## Scope and identity

The collector classifies the input before calling evidence providers:

- hg19/GRCh37 and hg38/GRCh38 are normalized without changing coordinates;
- coordinate input without an explicit or accession-inferred build fails
  closed;
- intervals up to 50 bp may use the small-variant route;
- intervals over 50 bp, symbolic ALT, breakends, and DEL/DUP/INV/BND/CPX/CNV
  events route to `tooluniverse-structural-variant-analysis`;
- mitochondrial, somatic, repeat-expansion, and CNV/SV interpretation are not
  handled by this ACMG runtime.

`variant_scope` records the input kind, span, normalized build, resolution
source, support status, and recommended route. Unsupported variants do not run
small-variant PVS1, PM2, EvidenceCard, or Bayesian logic.

For supported input, identity normalization preserves all allele and transcript
candidates. Numeric ClinVar Variation ID, rsID, selected-transcript HGVS, VCF,
RefSeq/Ensembl MANE mapping, and genomic projections are cross-checked. Build,
allele, gene, or transcript ambiguity fails closed rather than selecting the
first or most pathogenic-looking record.

## Inputs

The collector accepts:

- required `variant`;
- optional `gene`, `transcript`, `disease`, `inheritance`, `genome_build`, and
  `protein_accession`;
- optional `clinical_context` for retrieval and consistency background;
- optional `clinical_observations` for structured case/family/assay evidence;
- optional `source_outputs_or_leads` for reproducible provider inputs;
- optional supplemental `literature_proposals` and `cspec_proposals`;
- optional `evidence_decisions`;
- `response_detail=summary|full`.

`clinical_context` never becomes case evidence by itself. Each
`clinical_observations` item requires:

```json
{
  "observation_id": "case-001",
  "observation_type": "de_novo",
  "source_type": "lab_report",
  "source_id": "report-001",
  "locator": "page 3",
  "excerpt": "optional source text",
  "values": {}
}
```

Supported observation types are `de_novo`, `recessive_case`, `segregation`,
`phenotype_specificity`, `healthy_observation`, `allelic_phase`,
`alternative_cause`, `functional_assay`, `case_control`, and `case_series`.
Caller-supplied observations may enter the automatic estimate. A provider,
publication, or re-fetchable report anchor is required for the verified
estimate. The collector never transmits private clinical observations to
external providers without an explicit caller action.

## SourceFact v3

Every attempted source remains visible, including successes, empty responses,
failures, stale versions, incomplete extraction, and identity conflicts. Each
SourceFact records independent status dimensions:

- `identity_status`: matched, partial, conflict, or unknown;
- `source_status`: available, abstract-only, snippet-only, unavailable, or
  failed;
- `extraction_status`: structured, rule-extracted, LLM-extracted, unresolved,
  or contradicted;
- `version_status`: versioned, unversioned, or stale;
- `disease_match_status`: matched, candidate, mismatch, or unspecified;
- `independence_status`: independent, overlapping, or unknown.

Facts do not disappear merely because they cannot be scored. Their normalized
values, query representation, dataset/release, provider URL, identity check,
and raw-result hash remain auditable.

## Consequence and prediction collection

Consequence resolution is conditional and multi-source. Applicable providers
include VEP HGVS/genomic/region paths, VariantValidator/VariantFormatter,
FAVOR, OpenTargets transcript consequences, Mutalyzer, GRCh37 GenomeNexus,
and protein-representable ProtVar. Aggregated VEP-derived results are labeled
and do not count as independent agreement.

The resolver selects exact versioned RefSeq, unique MANE mapping, then
version-compatible transcript observations. It never votes. The resulting
`consequence_profile` exposes all observations, selected/corroborating facts,
failures, conflicts, mapping reason, and missing requirements.

MyVariant and related providers retain all available REVEL, CADD,
AlphaMissense, SIFT, PolyPhen-2 HDIV, MetaRNN, GERP, phyloP, phastCons, VEST4,
MutationTaster, and SpliceAI values with versions and input identity. PP3/BP4
uses only versioned calibrated rules; predictor majority voting is prohibited.

SpliceAI output always preserves `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, the four
positions, maximum delta, and trigger channel. Delta scores are never
recomputed from raw REF/ALT values. Canonical donor loss uses DS_DL and
acceptor loss uses DS_AL at the selected-transcript boundary. Low native-site
loss for an insertion or duplication is not proof of normal splicing.

PVS1 has no generic fallback. It must pass the existing transcript,
consequence, splice-site, reading-frame/NMD, LoF disease-mechanism, and
downgrade decision tree. HIGH impact, frameshift, stop-gained, LOFTEE HC,
constraint, or a database label cannot fill missing PVS1 facts.

## EvidenceCard v3

No-information criteria appear only in `criterion_reviews`; the runtime does
not fabricate placeholder cards. Every EvidenceCard has source facts and one
of these statuses:

- `expert_panel_applied`;
- `rule_mapped`;
- `source_backed_candidate`;
- `not_met`;
- `excluded`;
- `deprecated`.

Cards expose criterion, tool-proposed strength and direction, facts and excerpt
IDs, `strength_source`, `rule_source`, rule ID/version/hash, VCEP/CSpec and
publication identifiers, verification dimensions, calculation roles,
correlation keys, scenario ID, limitations, and missing requirements.

The 28-criterion machine matrix records provider routes, literature fact
types, candidate and strict fact requirements, generic candidate strength,
SVI/VCEP modifications, exclusions, deduplication keys, and compatibility
rules. Generic ACMG strengths are explicitly fork candidate policy, not a
claim of deterministic ClinGen application. PVS1 and other criteria with core
minimum scientific definitions cannot bypass those definitions.

PP5 and BP6 remain deprecated. ClinVar, GeneBe, InterVar, HPO, actionability,
constraint, domain annotations, and author classifications are visible source
assertions; they do not become PP5/BP6 or another criterion without an
underlying rule-mappable fact.

## VCEP and CSpec scenarios

After gene identity is confirmed, the collector queries the online ClinGen
CSpec Registry and Evidence Repository. It retains specification and curation
identity, version/date, condition, mode of inheritance, panel, URL, content
hash, historical versions, and parsing limitations.

Structured rules and safely parsed numeric inequalities, point tables,
predictor thresholds, residue/region lists, variant-type clauses, strength
modifications, combinations, and caps can drive scenario rules. Unparsed prose
remains visible and falls back to general SVI or a versioned source-backed
candidate instead of blocking the collector. Optional `cspec_proposals` may
supplement unresolved prose but are not required for normal operation.

If disease or inheritance is insufficient, general SVI and each plausibly
applicable released CSpec/VCEP are returned as separate `rule_scenarios` and
`scenario_estimates`. Cards from different scenarios are never multiplied
together.

An exact released VCEP classification is returned in `vcep_assertions` as an
external expert conclusion, never as ToolUniverse's final classification.
Exact identity requires a matching ClinVar Variation ID, CAID, or
resolver-verified coding/genomic HGVS equivalence; rsID or protein HGVS alone
is only a lead. Only structured applied/met criteria become cards. Negated,
not-applicable, excluded, and free-text criterion mentions remain visible but
are not scored. VCEP cards take precedence over corroborating local derivations
of the same fact and criterion.

## Automated literature evidence

The normal chain runs inside the collector:

`search -> retrieve -> deterministic extract -> SourceFact -> EvidenceCard`

Sources are checked in this order: VCEP/ERepo structured summaries, Europe PMC
XML/HTML, PubTator entities and locations, available tables/captions/
supplements, PubMed abstract, and provider-linked snippet. PMID, PMCID, and DOI
are merged as an identifier graph while preserving source hits and conflicts.

Search queries never prove exact variant matching. PMCID and `inEPMC` do not
prove full-text retrieval. The runtime records actual source, format, URL,
retrieval trace, content hash, truncation, and sections read. It never claims
to have read inaccessible full text.

Clear facts in an abstract or snippet can create a source-backed candidate for
the automatic estimate. Truncated or non-full-text facts cannot enter the
verified estimate. A record with no evidence-bearing text remains only a
literature lead.

Deterministic extraction covers case-control/case-series PS4, de novo PS2/PM6,
recessive phase PM3, functional assay PS3/BS3, segregation PP1/BS4, phenotype
PP4, healthy adults BS2, phase/co-occurrence BP2, alternative causes BP5,
prior variants PS1/PM5, mechanism/region PP2/BP1/PM1, protein length/repeats
PM4/BP3, and RNA-splicing facts. Extraction proceeds per proband, family,
cohort, assay, experiment, and prior variant so one bad record cannot erase
valid records.

Optional `literature_proposals` can supplement unresolved text and reproduce
an earlier extraction. They are re-anchored to document identity, hash,
locator, excerpt, variant/gene/disease, and per-field value excerpts. A general
LLM is not a runtime dependency and absence of LLM output does not prevent
candidate cards or automatic scoring.

## Compatibility and Bayesian views

All calculation paths share criterion, case/family/cohort/experiment,
publication, prior-variant, computational-source, CSpec-rule, PVS1/splice, and
directional-conflict checks. One fact observed by multiple providers produces
one representative card with corroborating sources.

Hard exclusion is limited to identity conflict, explicit semantic
contradiction, illegal criterion/strength direction, missing traceable source,
confirmed duplicate or hard conflict, explicit CSpec inapplicability, and
deprecated criteria.

Top-level estimates are:

- `automatic_bayesian`: all compatible legal source-backed candidates;
- `verified_bayesian`: exact VCEP/CSpec, versioned SVI, and strictly anchored
  facts;
- `user_selected_bayesian`: accepted regenerated cards;
- `scenario_estimates`: independent automatic and verified results for each
  applicable rule scenario.

User-selected cards must all belong to one `scenario_id`. Cross-scenario
selection fails closed and is reported in `decision_report`; compatibility
exclusions are removed before the selected Bayesian score is calculated.

No source-quality discount odds are invented. Exact rules use their catalogued
odds; other legal candidate strengths use generic Tavtigian odds with the
source recorded. BA1 remains a special criterion. The prior stays fixed at
0.1. Every posterior is labeled a review estimate and is not mapped to a
five-tier classification.

Evidence decisions require `card_id` and `decision=accept|reject`. A
direction-consistent `strength_override` requires `reason`. `reviewer` and
`decided_at` are optional. Stale card IDs remain unmatched and cannot silently
alter another card.

## Output detail

Principal outputs include:

- `variant_scope`, identity, consequence, SourceFacts and provider coverage;
- predictor scores and literature/source indexes;
- `criterion_reviews` and `evidence_cards`;
- `vcep_context`, `vcep_assertions`, and `rule_scenarios`;
- compatibility/conflict reports;
- `automatic_bayesian`, `verified_bayesian`, `user_selected_bayesian`, and
  `scenario_estimates`;
- `automation_report`, `decision_report`, `runtime_manifest`, `guard_context`,
  and limitations.

Summary mode keeps every clinically relevant card, predictor, literature item,
source index, and conflict while omitting full text, full CSpec documents, and
raw provider payloads. Representative summaries target less than 100 KB
without truncating clinical lists. Full mode retains normalized facts,
excerpts, rule content, provenance, and raw-result hashes without a 100 KB
limit.

`runtime_manifest` anchors package/runtime/schema versions, upstream base,
VCS commit when available, dynamic CSpec hashes, and a `ruleset_hash` covering
the 28 contracts, candidate policy, extractors, scenario policy, compatibility,
fixed prior, and odds.

`guard_context` is a compact self-checking transport contract. The Guard
recomputes its hash, allows source-backed candidate claims, explicitly
attributed external VCEP/ClinVar assertions, and Bayesian review estimates,
but blocks unsupported criteria and ToolUniverse-authored five-tier labels.
The checksum detects accidental change; it is not a digital signature.

## v2 to v3 migration

The v3 runtime does not dual-write old evidence-gate fields. Migrate broad
preview consumers to `automatic_bayesian`, strict consumers to
`verified_bayesian`, and card inclusion checks to
`calculation_roles.automatic|verified|user_selected`. Replace the former
readiness booleans with SourceFact verification dimensions and EvidenceCard
`evidence_status`. No-information criteria are represented in
`criterion_reviews` rather than empty EvidenceCards.

The eight public ACMG MCP tool names are unchanged, and
`ACMG_overlay_gate_assess_variant` remains a thin collector alias.
