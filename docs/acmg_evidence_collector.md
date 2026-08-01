# ACMG Evidence Collector

`ACMG_evidence_collector` is an evidence-collection and review tool. It does
not produce Pathogenic, Likely Pathogenic, VUS, Likely Benign, or Benign
classifications.

## Runtime

The workbench path is:

`ToolUniverse provider or full text -> verified identity -> selected-transcript ConsequenceProfile -> SourceFact -> SVI/CSpec or LLM proposal -> EvidenceCard -> compatibility/conflict -> system preview -> user decisions -> user-selected Bayesian estimate`

`SourceFact` records what was observed. `EvidenceCard` records a suggested
criterion and strength plus its rule basis, caveats, missing requirements, and
review state. Neither is a final clinical adoption.

## Input scope and genome assembly

The collector is limited to germline small variants. It classifies the input
before calling identity, consequence, population, or literature providers and
returns a top-level `variant_scope` with the input kind, affected span,
normalized build, build-resolution source, support status, and recommended
route.

- `hg19` and `GRCh37` normalize to `GRCh37`; `hg38` and `GRCh38` normalize to
  `GRCh38`.
- An interval of at most 50 bp remains eligible for the small-variant route.
  Intervals over 50 bp, symbolic ALT or breakend notation, and
  DEL/DUP/INV/BND/CPX/CNV representations route to
  `tooluniverse-structural-variant-analysis`.
- A coordinate input without an explicit build that also cannot be inferred
  from a versioned RefSeq genomic accession returns
  `workflow_status=input_correction_required`. It is never silently treated as
  GRCh38.
- Transcript HGVS and rsID inputs without coordinates retain the historical
  GRCh38 default, recorded as `build_resolution_source=default_noncoordinate`.
- A structural variant returns `status=not_applicable` and
  `workflow_status=unsupported_variant_class`. No small-variant identity,
  consequence, PVS1, PM2, EvidenceCard, or Bayesian computation is attempted.

The structural-variant workflow preserves the original assembly and may call
`EnsemblMap_convert_coordinates` before a GRCh38-only provider. It must obtain
one verified contiguous mapping on the same chromosome; zero, multiple, or
discontinuous mappings fail closed. Approximate coordinate offsets and
cross-build regional comparisons are prohibited.

Runtime data-source notes:

- ClinGen CSpec discovery uses the JSON-LD registry
  (`https://cspec.genome.network/cspec/api/svis`). Its disease entries are
  MONDO identifiers. A `disease` given as a MONDO ID (e.g. `"MONDO:0700268"`)
  is used directly; a free-text disease name is resolved through
  `ols_search_terms` (exact match, MONDO only) and must resolve to exactly one
  MONDO ID, otherwise the collector falls back to the general ClinGen/SVI
  policy without blocking review.
- ClinVar assertions use an ordered identity-bound chain: a verified numeric
  Variation ID, rsID, selected-transcript coding/protein HGVS through
  `variant_name`, then a bounded gene/disease search only after a successful
  empty result. Every non-empty result must contain one unique gene/HGVS allele
  match; ambiguity or contradiction stops the chain. The adapter accepts the
  raw search envelope and the canonical ClinVar 1.4 `data.raw_data` envelope.
  All ClinVar labels remain quarantined source assertions.
- MyVariant pathogenicity scores are queried with the chr-prefixed genomic
  identifier (`chr17:g.7579472G>C`) derived from the GRCh37 projection;
  RefSeq accessions are not indexed by MyVariant. The tool-specific schema
  supplies the requested dbNSFP fields, and the SourceFact retains REVEL, CADD,
  AlphaMissense, SIFT, PolyPhen-2, MetaRNN, GERP, phyloP, phastCons, VEST4, and
  MutationTaster values plus available versions.
- rsID inputs preserve every allele and transcript candidate. GRCh38 rsIDs are
  resolved primarily through `NCBIVariation_rsid_lookup` (dbSNP refsnp alleles
  plus per-allele VariantValidator coding projection); the Ensembl recoder is
  the fallback for indels, non-GRCh38 builds, or NCBI failure. The collector
  accepts only a unique caller-supplied or MANE-compatible RefSeq coding
  projection; ambiguous alleles or transcripts fail identity verification
  rather than selecting the first result. Multiple alleles on the SAME
  selected transcript (e.g. rs104894531 on NM_000303.3) stop the run with
  `ambiguous_rsid_allele` and keep the alternatives in
  `normalization.allele_alternatives`; zero downstream evidence calls are
  made. A caller-supplied transcript that still maps to several alleles fails
  the same way — supply the full HGVS instead.
- The Ensembl variant recoder is not a single point of failure: when it is
  unavailable, HGVS inputs use `EnsemblVEP_annotate_hgvs` against the
  VariantValidator-confirmed genomic HGVS as the independent second identity
  source (transcript-oriented alleles are normalized to the forward strand;
  indel representations link by genomic HGVS string rather than VCF
  coordinates), and protein inputs fall back to VEP protein annotation with
  the same forward-strand normalization. VEP requests include `mane=1` so
  consequence routing can bind Ensembl transcripts to the identity-selected
  RefSeq MANE transcript.
- After identity is fixed, consequence annotation uses conditional exhaustive
  collection rather than a VEP-only fallback chain. Applicable calls include
  selected-transcript/genomic/single-allele-rsID/region VEP,
  VariantValidator/VariantFormatter, FAVOR, OpenTargets transcript
  consequences, Mutalyzer, GRCh37 GenomeNexus, and protein-representable
  ProtVar. A failure or empty result from one provider never stops the other
  read-only calls.
- Every observation records build, allele, gene, transcript/MANE mapping,
  HGVS c./p., SO terms, impact, biotype, exon/protein position, provider
  version, query representation, identity status, and whether its method is
  independent, VEP-derived, or an aggregation. The deterministic resolver
  selects exact RefSeq, unique MANE, then version-compatible transcript
  observations. It does not vote. Contradictory build, allele, gene,
  transcript, consequence, or protein results fail closed.
- `consequence_profile` reports all observations, selected and corroborating
  SourceFacts, failures, conflicts, mapping reason, and missing requirements.
  PVS1 may consume a uniquely resolved non-VEP observation, but consequence or
  HIGH impact alone cannot supply exon structure, PTC/NMD, or disease
  mechanism.

## Conditional exhaustive provider collection

After variant and gene identity are verified, the collector queries ClinGen
gene validity, dosage sensitivity, adult actionability, pediatric
actionability, variant classifications, and gnomAD constraint concurrently.
ClinGen classifications, dosage, actionability, and all database labels remain
`source_lead` or `review_only` facts and never become EvidenceCards by
themselves.

Literature discovery combines LitVar, PubMed (abstracts requested, up to 50),
Europe PMC, and paginated PubTator. It builds exact, equivalent, historical,
protein, rsID, and coordinate aliases into provider-specific combined queries.
Results are merged as a PMID/PMCID/DOI identifier graph while preserving every
provider hit and query representation; conflicting identifiers are reported
rather than merged.

Full-text state is explicit:
`full_text_verified_available`, `full_text_unavailable`, `abstract_only`,
`index_record_only`, or `availability_unknown`. `inEPMC`, snippets, and
text-mining hits do not prove full-text availability. Exact/equivalent papers
produce executable `literature_review.review_requests` and `next_actions`.
The host tries each listed legal full-text source once, reads the complete
accessible article, and submits a reading manifest plus structured proposals.

When a verified protein accession is available, the collector requests the
complete UniProt entry together with EBI Proteins variation/features and
InterPro annotations. The normalized UniProt fact retains entry status,
recommended or submission name, function, disease notes, catalytic activity,
cofactors, PTMs, domains, sequence length, cross-references, and publications.
Inactive or deleted entries remain visible with their reason.

For missense variants, the protein-wide EBI variation response is reduced to
germline-compatible variants at the exact selected residue. These are returned
as `prior_variant_candidates` and trigger `prior_variant` full-text requests.
ClinVar/EBI labels remain leads: PS1 or PM5 requires an independently anchored
paper fact that verifies the prior variant and its pathogenic evidence.

Every attempted provider produces a SourceFact even for an empty, incomplete,
unversioned, or failed response. Conditions that cannot apply are represented
as `not_applicable` coverage rather than synthetic negative evidence. Summary
mode exposes all normalized clinical fields and entry indexes; full mode adds
the complete normalized audit structures and raw-result hashes, without
embedding provider raw payloads.

## Output detail and clinical context

- `response_detail` selects the output shape. `"summary"` (the default)
  returns complete compact indexes: source facts retain clinically relevant
  normalized values, dataset/callset/version metadata, predictor scores, and
  literature anchors;
  evidence cards keep a unified index (`criterion`, `strength`, `source`,
  `route`, proposal status/origin, system-preview state, user-decision state,
  `decision_basis`, `rule_id`, `rule_version`, `source_fact_ids`), while bulky
  raw provider payloads and full CSpec documents are omitted. Clinically
  relevant lists are not truncated. The
  compatibility report contains only compatible card IDs and exclusion
  decisions (`card_id`, `criterion`, `reason`); the Bayesian report keeps the
  calculation summary plus included/excluded card IDs; criterion reviews omit
  repeated observed facts and keep status, consequence applicability, card
  IDs, and missing requirements. Representative compact UTF-8 JSON is held
  below 50 KB. The
  REVEL missense route (`missense_revel`) and the SpliceAI splice route
  (`spliceai_splice`) are labelled separately so distinct channels are not
  merged into "multiple supporting evidence". `"full"` returns the complete
  payloads for audit.
- `clinical_context` accepts review-only context (`zygosity`,
  `parental_origin`, `phase`, `phenotype`, `second_allele_status`,
  `hpo_terms`). Explicit HPO identifiers accept `HP:0001250`, `HP_0001250`,
  or bare numeric forms and trigger term, gene-association, and
  disease-association lookups. Free text triggers term search without
  selecting among multiple candidates. The context is echoed with
  `review_only`/`not_evidence` markers and never generates PS2, PM3, PP4, or
  any classification; unknown fields are dropped and reported in
  `ignored_fields`.

`criterion_reviews` covers all 28 criteria and derives its route from the
versioned use matrix. Each row has one `route_status`: `assessed`,
`proposal_validated`, `candidate_available`, `review_pending`,
`insufficient_information`, `not_applicable`, or `deprecated`, plus compact
candidate SourceFact IDs, pending request IDs, card IDs, and missing
requirements. `not_assessed` and `insufficient_information` mean evidence was
not established; neither is benign evidence.

The top-level `review_readiness` describes workflow completion, not clinical
classification. `ready_for_evidence_review` means all currently executable
provider, consequence, CSpec, and full-text actions have finished;
`incomplete` means actions or inaccessible mandatory content remain;
`blocked` means identity/build is unresolved; `not_applicable` means the event
is outside germline-small-variant scope. Missing optional evidence for one or
more criteria does not prevent review readiness. Conflicts remain listed and
continue to control compatibility and Bayesian inclusion.

Each system-preview card has a valid ACMG strength, has
`overlay_validated=true`, references identity-bound `source_fact_ids`, and
passes compatibility checks. It may be a versioned deterministic suggestion or
a `requires_user_review` proposal. Public population, computational, clinical,
functional, and literature group tools remain review-only; only the collector
can bind their facts to source provenance. `system_preview_included` records
review-estimate inclusion and does not mean clinical approval.

Provider labels, classifications, criteria, and scores from ClinVar, GeneBe,
InterVar, and similar sources are source leads. They are never adopted as ACMG
evidence. Population evidence uses gnomAD facts only; the generic Ensembl
population response is not a countable source.

## Current automated scope

The collector can include the following verified contracts in the system
preview:

- ClinGen CSpec discovery runs as soon as the identity-verified gene is known.
  A released specification is applied only after a unique gene, MONDO disease,
  and inheritance match. Explicit structured applicability and strength fields
  are normalized directly from the online Registry document. Natural-language
  thresholds and conditions are returned in
  `rule_context.cspec_review_requests`; they are never converted into
  deterministic rules by regular expressions. The host LLM may submit
  `cspec_proposals`, which are accepted only after the collector re-fetches the
  specification and verifies its ID, version, content hash, criterion, and
  excerpt. Local compiled contracts are optional caches or fixtures and may add
  details only when bound to the exact online content hash. Ambiguity, missing
  disease/inheritance, or network failure falls back to general ClinGen/SVI
  while preserving all candidates and limitations.
- gnomAD frequency and `gnomad_get_site_callability` facts are collected as
  separate, build/dataset/callset-bound SourceFacts. Under the general SVI
  fallback, AC=0 with auditable site callability suggests PM2_Supporting. BS1
  still requires a disease-specific maximum credible allele frequency.
  Gene-level mechanism context uses only `gnomad_get_constraint` and retains
  pLI, LOEUF, observed/expected LoF bounds, missense/synonymous Z-scores, and
  observed/expected counts. Failure or incomplete version metadata remains a
  visible SourceFact and never triggers a second ACMG constraint path.
  Constraint remains context only and is never proof of a LoF disease
  mechanism.
- Missense PP3 or BP4 from the versioned Pejaver REVEL policy. Non-canonical
  splice PP3/BP4 uses the separate Walker 2023 SpliceAI policy. The calibrated
  likelihood-ratio bins reach a Moderate range, but the general predictive code
  is conservatively applied only as PP3_Supporting or BP4_Supporting. Canonical
  donor/acceptor +/-1/2 variants are routed to the PVS1 decision tree (below).
  Other predictors, including CADD and AlphaMissense, are retained for audit
  and conflict review only.
- PVS1 from the deterministic ClinGen SVI decision tree (Abou Tayoun 2018,
  PMID:30192042) in `acmg/pvs1.py`. The tree consumes only machine-verifiable
  facts and never caller booleans: the LoF disease mechanism (a verified
  online or exact-hash CSpec contract, or a semantically verified
  document-backed
  `gene_disease_mechanism` fact), the selected transcript's VEP `biotype`
  and `exon` position, and — for canonical +/-1/2 splice routes — the verified
  selected-transcript SpliceAI native-site Loss score and delta position
  (donor `DS_DL`/`DP_DL`, acceptor `DS_AL`/`DP_AL`). Functional native-site
  loss uses a 0.5 interpretation threshold, with 0.8 for canonical `+2T>C`;
  the Loss event coordinate must match the selected transcript's Ensembl exon
  boundary.
  `DS_AG`/`DP_AG` and `DS_DG`/`DP_DG` are retained as alternative-site
  context when score >=0.5 and position is within +/-20 bp.
  Nonsense/frameshift variants in a predicted-NMD region reach
  PVS1; the unverifiable final-50nt penultimate-exon boundary downgrades to
  PVS1_Strong; NMD-escape outcomes follow the official role/fraction path
  (critical region or >10% removed -> PVS1_Strong, <10% -> PVS1_Moderate)
  with the protein length taken from the verified `EBIProteins_get_features`
  `sequence_length`. Critical regions come from a CSpec contract or from an
  overlap of the truncated region with curated UniProt ACT_SITE/BINDING/
  METAL/SITE features (broader DOMAIN/MOTIF overlap stays review context).
  The "LoF variants frequent in the general population" gate is automated via
  `ensembl_lookup_gene` exon coordinates (GRCh38 only) plus the
  `gnomad_get_region_variants` per-exon query: any LoF-consequence variant in
  the variant's exon with AF >= 0.001 or a homozygous carrier makes PVS1
  `not_applicable` (CSpec `exon_lof_frequent_af_threshold` may override).
  Splice routes follow the official frame branches: a CSpec
  `predicted_frame_outcome` of `disrupts_reading_frame` with predicted NMD
  reaches PVS1, while unknown frame outcomes stay at a conservative
  PVS1_Strong default adjusted by selected-transcript native-site Loss DS/DP.
  Canonical duplications and insertions are structurally marked as potentially
  motif-preserving, but are no longer stopped before computational review:
  a threshold-passing native Loss event bound exactly to that exon boundary
  enters the same PVS1 frame/NMD tree. If native Loss is not supported or its
  DP cannot be bound exactly, the route remains `not_assessed`; verified RNA or an
  exact-hash operation-specific CSpec can still resolve the outcome.
  Substitutions, deletions, and delins that alter the canonical motif continue
  through the decision tree. Initiation-codon variants require
  a CSpec contract (`alternative_in_frame_start`,
  `pathogenic_upstream_of_alternative_start`) and otherwise stay
  `not_assessed`. ClinGen validity and gnomAD pLI/LOEUF remain visible mechanism
  context but cannot establish a LoF disease mechanism by themselves. Facts
  that cannot be verified at all (mechanism, biotype,
  exon position) keep PVS1 `not_assessed`, and CSpec-documented rescue
  transcripts, exons absent from biologically relevant transcripts, or exons
  whose LoF variants are frequent in the general population make PVS1
  `not_applicable` per the official flowchart. Promoted PVS1 cards are
  countable at Tavtigian odds (350 / 18.7 / 4.3 / 2.08) in the review
  estimate only.
- Consequence routing uses the VEP consequence for the identity-selected MANE
  transcript, not `most_severe_consequence` across all transcripts. It controls
  criterion applicability only and never creates evidence strength. Population,
  clinical, functional-assay, and literature facts remain visible regardless of
  consequence.
- For PM1-eligible variants, the collector maps the verified genomic HGVS to a
  unique UniProt residue with `EBIProteins_get_variation_by_hgvs` (the reviewed
  canonical accession is preferred over TrEMBL/isoform entries), obtains exact
  feature ranges with `EBIProteins_get_features`, and records the InterPro domain
  inventory. A domain/site overlap is reviewable context and remains
  `indeterminate`. An exact region contract may come from structured online
  CSpec fields, a re-anchored `cspec_proposals` interpretation, or an
  exact-content-hash compiled cache. The PTEN GN003 v3.2 contract remains an
  offline fixture/cache example for catalytic motifs 90-94, 123-130, and
  166-168 on NP_000305.3 (P60484 / NM_000314.8); it is not a whitelist for
  other online CSpecs.
- PS2/PM6 and PS3/BS3 from document-backed structured facts whose quoted fields,
  locators, and variant/gene/disease bindings are verified against ToolUniverse
  full text. Host-curator verification is retained when supplied but is not the
  only possible machine-verification path. Functional records must declare
  `assay_scope`; direct RNA-splicing readouts never enter PS3/BS3 and remain on
  the Walker RNA review route.
- PM3 becomes a formal proposal when the other allele, phase, zygosity,
  classification, and frequency-eligibility facts pass the structured source
  contract. It may enter the system preview after compatibility checks; final
  adoption remains the user's decision.
- PS4 uses one document-backed path. A uniquely applicable online CSpec rule
  takes precedence. Without a disease-specific rule, anchored case-control or
  independent case-series facts still produce a general-SVI
  `requires_user_review` proposal; no empty local policy catalog can suppress
  them and no universal case-count threshold is invented.
- Other anchored literature facts can produce review proposals through a fixed
  fact-type mapping: segregation (`PP1`/`BS4`), phenotype specificity (`PP4`),
  healthy adult observations (`BS2`), phase/co-occurrence (`BP2`), alternative
  cause (`BP5`), prior same-amino-acid/residue variants (`PS1`/`PM5`),
  mechanism context (`PVS1`/`PP2`/`BP1`), critical regions (`PM1`), and
  protein-length/repeat context (`PM4`/`BP3`). RNA-splicing experiments remain
  review facts and cannot bypass the PVS1 decision tree. An LLM-suggested
  criterion outside the allowed fact-type mapping is preserved as `unmapped`
  and excluded from the system preview.
- Provider-resolved in-frame or stop-loss consequences can produce a
  review-required PM4 proposal when the unique protein mapping is outside a
  repeat, or BP3 when it overlaps a repeat/low-complexity region without a
  known functional feature. Ambiguous mappings or unresolved feature context
  remain candidates only.

For general Walker PP3/BP4, the collector explicitly requests raw, unmasked
SpliceAI output at distance 500. `DS_AG`, `DS_AL`, `DS_DG`, and `DS_DL` are
already delta scores; ToolUniverse never subtracts REF/ALT raw scores. PP3/BP4
uses the maximum of those four deltas and reports every tied trigger channel.
Canonical PVS1 instead uses the site-specific loss channel described above.
A scalar maximum alone is insufficient: use `spliceai_scores`,
`spliceai_profile`, and `spliceai_max_delta`, preserving all four channels and
their trigger direction.
A SourceFact is assessment-ready only when
SpliceAI 1.3.1 and an annotation version are established, the selected
transcript is verified as MANE Select, and exactly one returned score row binds
to the selected gene/transcript with all DS/DP values present. Score rows are
bound across provider schemas (`gene`/`g_name`; `transcript`/`t_id`/
`t_refseq_ids`) and string-serialized DS/DP values are accepted. The public
SpliceAI Lookup API does not report versions in its responses, so the version
is established by an operator-reviewed pin in the reviewed tool config
(`model_version=1.3.1` — the only public SpliceAI model release;
`annotation_version=gencode.v49` — the GENCODE_VERSION in the provider's
published server.py), each with a provenance URL and `version_verified_at`
date that is echoed in the run metadata for audit. Re-verify the annotation
pin against the linked server.py before relying on a redeployed service, or
self-host `docker.io/weisburd/spliceai-38` with a pinned annotation build for
strict deployments. Missing metadata, zero or ambiguous row matches, and
unverifiable responses remain visible but are `not_assessed` and excluded from
the candidate Bayesian estimate; when a SpliceAI call succeeded but this
contract is incomplete, the collector reports an explicit
`spliceai_walker_contract_incomplete` limitation instead of an ambiguous
absence of evidence. After a strict BP4_Supporting result, synonymous variants
and intronic variants outside the conservative donor +7 / acceptor -21 region
may additionally suggest BP7_Supporting. BP7 is never generated from an
incomplete or review-only SpliceAI result.

Every summary and full response retains a normalized `spliceai_profile` with
all four DS values, all four DP positions, `max_delta_score`,
`max_delta_channels`, `max_delta_events`, and—when the selected consequence is
canonical—native Loss channel, score, DP, threshold, genomic event coordinate,
position status, and all threshold-passing Gain events inside or outside the
canonical +/-20 bp window. DP signs are genomic-coordinate relative and are
not inverted for minus-strand transcripts. Provider-reported
maximum values are checked against the four deltas; mismatches, missing
channels, non-finite values, and out-of-range scores fail closed while the
original row remains visible for audit.

## LLM literature proposals

The host LLM interprets papers; ToolUniverse does not invoke a second embedded
model. Submit the result through `literature_proposals`. `criterion` and
`suggested_strength` are optional LLM suggestions: the collector independently
maps each `fact_type` through its allowed SVI/CSpec route. For each case,
family, mechanism, functional-assay, or case-control proposal, the collector
fetches the cited EuropePMC full text and verifies:

- PMID or PMCID, section/table/figure locator, and quoted excerpt.
- Variant and gene binding.
- Extractor name and version.
- A matching excerpt for every consumed structured field.
- A reading manifest recording `complete`, `partial`, `abstract_only`, or
  `unavailable` status; sections, tables, figures, and supplements reviewed;
  variant-match locations; document hash when available; and missing-content
  limitations.
- A machine-anchored quote and locator match, or stronger host-curator
  verification, before the fact can support a candidate card.
- A stable fact ID used for duplicate detection.

The result separates `anchor_status` (`verified`, `unavailable`, `mismatch`)
from `semantic_status` (`verified`, `unresolved`, `contradicted`). Numeric and
enumerated submitted values are checked against their per-field excerpts.
Explicit contradictions and failed anchors remain visible but are excluded
from the system preview. A verified anchor whose semantics cannot be reliably
machine parsed remains `requires_user_review`, with the LLM interpretation,
confidence, extractor version, excerpt, and unresolved questions preserved.
Literature mechanism facts may feed the deterministic PVS1 tree only when the
mechanism is a controlled value and `semantic_status=verified`; unresolved
mechanism text remains visible background. Deterministic PS2/PM6, PM3, and
PS3/BS3 engines consume their structured facts and retain the LLM explanation
on that one rule card rather than creating a second generic card.

## Dynamic CSpec and literature automatic cycle

1. Call the collector and inspect `workflow_status`, `recoverable_gaps`,
   `next_actions`, literature requests, and CSpec requests.
2. The collector completes applicable consequence recovery internally. The
   host automatically executes pending CSpec/full-text actions without asking
   whether to continue.
3. The host reads complete accessible papers section by section, including
   relevant tables, figures, captions, and supplements, and prepares
   `literature_proposals`/`cspec_proposals` with exact anchors, structured
   facts, reading manifests, confidence, questions, and extractor version.
4. Call the collector again automatically. It re-fetches sources, verifies
   anchors and hashes, maps facts to rules, emits one EvidenceCard per semantic
   unit, checks conflicts, and computes the system preview.
5. Process only newly discovered request IDs on at most one incremental pass.
   Stable full-text failure ends as `blocked_external_full_text`, not an
   infinite loop.
6. User `evidence_decisions` are a separate optional round used only to
   calculate the user-selected estimate.

## System preview and user-selected estimate

`system_preview_bayesian` includes compatible deterministic suggestions and
qualified review-required LLM proposals. Exact versioned rules use catalogued odds; other
legal strengths use generic Tavtigian odds with `odds_source` recorded. BA1 and
other non-multiplicative special criteria appear in `special_criteria`.

To record review decisions, call the collector again with
`evidence_decisions`. A decision has `card_id`, `decision=accept|reject`, and
optional `strength_override`; every override requires a reason and must retain
the criterion's direction. The collector recollects current data and applies
only decisions whose stable card IDs still match. Stale IDs appear in
`decision_report.unmatched_decisions`. `user_selected_bayesian` includes only
accepted, compatible cards. Neither estimate maps to a five-tier
classification.

## Interface migration

The ACMG runtime has one current representation for each concept and does not
dual-write removed fields:

| Removed interface | Current interface |
|---|---|
| `literature_facts` | `literature_proposals` |
| `spliceai_dl` | `spliceai_scores` + `spliceai_profile` + `spliceai_max_delta` |
| overlay `mode` | Call `ACMG_overlay_gate_assess_variant` with collector parameters |
| ClinVar search `variant` | ClinVar search `variant_name` |
| `counted`, `included_in_candidate_bayesian` | `system_preview_included` |
| `counted_criteria`, `bayesian_estimate` | Evidence-card states + `system_preview_bayesian` |
| legacy gnomAD constraint fallback | `gnomad_get_constraint` |
| ClinVar `formatted_data` | canonical `data` envelope with `data.raw_data` |

## Agent boundary

The policy/search layer places the collector ahead of high-risk direct sources.
The collector-owned scoped executor quarantines high-risk provider results as
source leads after single or batched execution, including cache hits. Ordinary
ToolUniverse execution has no ACMG policy parameter and preserves upstream
provider output. This constrains calls that enter the collector, not a
general-purpose LLM operating outside it.

Deployments that must prevent final-label bypasses must invoke the collector in
a host pre-answer hook and `ACMG_guard_final_answer` in a post-answer hook. The
guard allows evidence-card-backed criterion discussion and blocks all
five-tier ACMG labels. Responses must distinguish observed facts, system
suggestions, and user-selected evidence.

## Install verification

`scripts/verify_acmg_install_smoke.py` builds an isolated install and verifies
the installed artifact rather than the source tree. Its default `--source
local` mode is offline; `--source git-ref --git-ref <commit-sha>` installs an
explicit remote revision and then reuses the same offline assertions: tool
discovery for all eight ACMG tools, wrapper/schema consistency, guard blocking,
version consistency, and the PMM2 rs104894531 multi-allele regression. Git-ref
mode uses the network only for the requested installation and should be run
with the pushed exact commit SHA, never a floating branch name.
