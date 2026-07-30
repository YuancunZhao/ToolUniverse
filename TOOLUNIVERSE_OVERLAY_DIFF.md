# ToolUniverse ACMG Overlay Diff

Comparison baseline:
`upstream/main@089eb8e6308fc64ae5af3de4bfbec32b5cf07b61` to
`codex/acmg-on-tooluniverse-1.4`.

The package version is `1.4.0+acmg.1`. Files unrelated to the ACMG runtime,
its four missing provider operations, directly supporting Skills, generated
registration surface, and fork installation metadata remain on the fixed
upstream 1.4.0 base.

## Current Overlay Surface

The fork adds an evidence-only ClinGen/SVI extension around upstream
ToolUniverse variant providers. The public runtime is intentionally limited to:

- `ACMG_evidence_collector`
- `ACMG_overlay_gate_assess_variant` (backward-compatible alias)
- `ACMG_population_evidence`
- `ACMG_computational_evidence`
- `ACMG_clinical_evidence`
- `ACMG_functional_evidence`
- `ACMG_literature_evidence`
- `ACMG_guard_final_answer`

Internal evidence contracts now live in `acmg/models.py`; population rules live
in `acmg/population.py`. The generated `tools/` modules remain client wrappers,
while registered runtime classes live in `acmg_runtime_tools.py` so wrapper
regeneration cannot overwrite the collector implementation.

Provider outputs keep their upstream shape during ordinary ToolUniverse calls.
The collector-owned `ACMGScopedExecutor` quarantines high-risk source labels
and predictions only after single or batched provider execution, including
cache hits. No ACMG policy parameter is injected into ordinary ToolUniverse
execution, async, or cache paths. Search metadata recommends the collector but
does not claim to authorize evidence or prevent model reasoning outside
ToolUniverse.

The supporting code is deliberately thin: `acmg/search.py` only detects ACMG
search intent and ranks the collector, `acmg/policy.py` owns the scoped
source-lead boundary, `acmg/source_adapters.py` owns provider field parsing,
`acmg/consequence_sources.py` resolves auditable multi-provider observations,
and `acmg/consequence.py` normalizes criterion applicability.
The retired `acmg_gate_search.py` mixed these responsibilities and has been
removed.

The upstream runtime gains one general-purpose Python API,
`ToolUniverse.run_many_functions`, which is a policy-free wrapper around the
existing batch executor. Four general provider operations required for complete
ACMG fact collection are added without embedding ACMG decisions:
`ClinGen_search_cspec`, `MyVariant_get_metadata`,
`gnomad_get_site_callability`, and `gnomad_get_region_variants`.

Variant identity normalization reuses upstream VariantValidator and Ensembl VEP
tools. Complete HGVS is validated directly; gene plus c. shorthand is resolved
through `VariantValidator_gene2transcripts`, genomic input uses
`VariantValidator_format_genomic_to_transcripts`, and rsIDs use the VEP recoder
before validation. Gene;transcript:c. input is validated directly, while gene
plus p. input uses `EnsemblVEP_annotate_hgvs` for genomic identity and then the
MANE projection path. Ambiguous transcript or protein-to-genomic resolution
fails closed and never creates ACMG evidence.

Scientific changes include provider-verified identity-bound SourceFacts, a
dedicated gnomAD per-locus callability provider, Pejaver missense calibration,
the independent Walker 2023 SpliceAI policy, ClinGen v1.1 de novo proband
points, Brnich OddsPath assay strengths, and a PM1 protein-context route using
upstream EBI Proteins and InterPro tools. Ordinary domain overlap is displayed
but is not sufficient for PM1; an exact CSpec protein-region contract must bind
to the current online document. `ClinGen_search_cspec` runs immediately after
gene identity is verified. A released specification applies only after a
unique gene, MONDO disease, and inheritance match. Explicit structured
applicability and strength fields are normalized directly; natural-language
conditions become `cspec_review_requests` for host-LLM interpretation.
`cspec_proposals` are revalidated against the online specification ID, version,
content hash, criterion, and excerpt. Local compiled contracts are optional
exact-hash caches or fixtures, not a whitelist. Missing context, ambiguity, or
network failure remains visible and falls back without blocking evidence.
Under that fallback, AC=0 with auditable callability may suggest
PM2_Supporting; when no versioned coverage-adequacy policy is available the
suggestion is explicitly `requires_user_review`. BS1, BA1 exceptions, and PS4
use applicable disease-specific contracts when available. Without a CSpec,
anchored PS4 case-control or independent case-series facts still produce a
general-SVI review proposal. PM3 is now a formal proposal when its structured
source facts pass validation. Document-backed host-LLM proposals can enter the
system preview after ToolUniverse full-text identity, locator, field-excerpt,
and semantic checks; unresolved semantics remain review-required while
explicit contradictions are retained but excluded. The fixed literature fact
mapping also covers PP1/BS4, PP4, BS2, BP2, BP5, PS1/PM5, mechanism context,
PM1, and PM4/BP3. Criterion-specific PS2/PM6, PM3, and PS3/BS3 engines retain
the LLM explanation on one rule card rather than emitting a duplicate generic
card.

The Walker fallback applies its calibrated thresholds at Supporting weight
(`>=0.2` PP3_Supporting; `<=0.1` BP4_Supporting), not Moderate. Candidate use
fails closed unless SpliceAI 1.3.1 and an annotation version are established
with provenance, the MANE Select context is verified, raw unmasked
distance-500 settings are proven, and one identity-bound score row is
present. Score rows bind across provider schemas (`gene`/`g_name`;
`transcript`/`t_id`/`t_refseq_ids`) with string-serialized DS/DP values
accepted. The four `DS_*` values are treated as provider delta scores and are
never recomputed from REF/ALT raw scores. PP3/BP4 uses their maximum and
reports all tied trigger channels; canonical PVS1 uses `DS_DL` for donor loss
or `DS_AL` for acceptor loss together with the paired `DP_*`. Functional
native-site loss uses >=0.5, except canonical `+2T>C` uses >=0.8; the Loss
event must map exactly to the selected transcript's Ensembl exon boundary. Gain
events >=0.5 are retained as alternative-site context only inside that window,
with genomic-coordinate DP signs left unchanged on minus-strand transcripts.
A scalar maximum without the four DS/DP channels is insufficient; the ACMG
interface uses `spliceai_scores`, `spliceai_profile`, and
`spliceai_max_delta`. Because the public SpliceAI Lookup API
does not report versions,
they are established by an operator-reviewed, provenance-bearing pin in the
reviewed tool config (model 1.3.1; annotation gencode.v49 with
`version_verified_at`); strict deployments should self-host
`docker.io/weisburd/spliceai-38` with a pinned annotation build. When a
SpliceAI call succeeds but the contract is incomplete, the collector surfaces
an explicit `spliceai_walker_contract_incomplete` limitation. Direct
RNA-splicing assays are excluded from the Brnich PS3/BS3 contract and remain
review-only until a separate RNA evidence contract is implemented.
BP7_Supporting is available only after strict BP4 for synonymous variants or
intronic variants outside the conservative +7/-21 region.

The PTEN Expert Panel Specifications v3.2 (GN003) PM1 contract remains an
exact-hash cache/fixture example for catalytic motifs 90-94, 123-130, and
166-168 on NP_000305.3, with protein mapping preferring the reviewed canonical
UniProt accession over TrEMBL/isoform entries. Other genes can use online
structured CSpec rules or re-anchored CSpec proposals without being
pre-registered in the local catalog.

PVS1 is assessed by a deterministic ClinGen SVI decision tree in
`acmg/pvs1.py` (Abou Tayoun 2018, PMID:30192042) instead of the former
`not_assessed` placeholders. The tree consumes only machine-verifiable facts,
never caller booleans: LoF disease mechanism (CSpec contract or
document-verified `gene_disease_mechanism`), VEP `biotype` and `exon` position
for the identity-selected transcript (the upstream VEP tool and adapter now
retain `exon`/`intron`/`biotype`/`canonical`/`distance`), and Walker 2023
SpliceAI deltas for canonical splice routes. Predicted-NMD nonsense/frameshift
variants reach PVS1; NMD-escape outcomes follow the official critical-region /
>10% / <10% fraction path with the protein length from the verified EBI
Proteins `sequence_length`; critical regions come from a CSpec contract or a
curated UniProt ACT_SITE/BINDING/METAL/SITE overlap (broader domains stay
review context). The frequent-population-LoF gate is automated with
`ensembl_lookup_gene` exon coordinates (GRCh38) and the new
`gnomad_get_region_variants` per-exon query (AF >= 0.001 or any homozygous
LoF carrier, CSpec-overridable). Splice routes follow the official frame
branches with a conservative PVS1_Strong default when the frame outcome is
unverifiable. Canonical duplications and insertions no longer stop before
SpliceAI: a selected-transcript, threshold-passing native Loss DS/DP bound to
the exact exon boundary enters the same frame/NMD tree. They remain
`not_assessed` when functional native-site
loss cannot be established; verified RNA or an exact-hash operation-specific
CSpec frame contract may still resolve the outcome. Initiation-codon variants
require a CSpec alternative-start
contract. CSpec-documented rescue transcripts, biologically irrelevant exons,
or exons with frequent population LoF make PVS1 `not_applicable` per the
flowchart, and missing mechanism/biotype/exon facts keep PVS1 `not_assessed`.
Promoted PVS1 cards are eligible for Tavtigian odds in the review estimate
only.

EvidenceCards separate observed facts, proposal origin/status, suggested
criterion/strength, rule verification, caveats, system-preview inclusion, and
user decision state. `system_preview_included` does not mean clinical
approval. The
collector returns `system_preview_bayesian` plus a separate
`user_selected_bayesian` after stable-card `evidence_decisions`.

Collector output defaults to a compact `summary` shape (unified card index,
clinically relevant normalized fact values, complete lead indexes, compatibility exclusions
as `{card_id, criterion, reason}`, Bayesian included/excluded card IDs, and
criterion-review decision fields without repeated observed facts). The
representative compact UTF-8 JSON regression ceiling is 50 KB;
`response_detail="full"` restores complete payloads. A review-only
`clinical_context` (zygosity,
parental origin, phase, phenotype, second-allele status) is echoed for human
review and never generates criteria. Multi-allele rsIDs on one transcript fail
closed as `ambiguous_rsid_allele` with alternatives preserved.
`scripts/verify_acmg_install_smoke.py` verifies the installed package from
either the local checkout (offline) or an explicit Git ref, reusing the same
eight-tool, schema, guard, version, and PMM2 multi-allele assertions. Remote
verification uses a pushed exact commit SHA rather than a floating branch.
Git-ref verification now requires a full 40-character commit SHA, disables pip
cache reuse, isolates user site packages and the working directory, verifies
the installed `direct_url.json` VCS revision, and reports the schema
fingerprint and actual import path. The Guard smoke uses a complete
`collector_result`, covering serialized known-SourceFact binding.

Collector results include a compact `runtime_manifest` with ToolUniverse
version, evidence-only runtime version, collector schema version, a stable
hash over the deterministic criterion/PVS1/SpliceAI/Bayesian ruleset, optional
installed VCS revision, and applicable online CSpec identities. The Bayesian
prior remains fixed at 0.1.

An offline BRCA2 `NM_000059.4:c.5946delT` golden fixture now exercises initial
collection, anchored literature interpretation, deterministic PVS1, stable
user decisions, dual Bayesian estimates, Guard PASS/BLOCK behavior, and an
actual compact-MCP `execute_tool` call. Reviewer attribution remains optional
and has no effect on inclusion or scoring.

Identity resolution no longer treats the Ensembl variant recoder as a single
point of failure. GRCh38 rsIDs resolve primarily through
`NCBIVariation_rsid_lookup` plus per-allele VariantValidator projection
(recoder only for indels, GRCh37, or NCBI failure); HGVS inputs fall back to
`EnsemblVEP_annotate_hgvs` on the VariantValidator-confirmed genomic HGVS with
forward-strand allele normalization; protein inputs fall back to VEP with the
same normalization. VEP requests carry `mane=1` so consequence routing binds
Ensembl transcripts to the identity-selected RefSeq MANE transcript.
Once identity is fixed, the collector runs every applicable read-only
consequence source rather than stopping at VEP: selected/genomic/single-allele
rsID/region VEP, VariantValidator/VariantFormatter, FAVOR, OpenTargets,
Mutalyzer, GRCh37 GenomeNexus, and protein-representable ProtVar. The resolver
uses exact RefSeq, unique MANE, then version-compatible observations without
majority voting; build, allele, gene, transcript, consequence, or protein
conflicts fail closed. The profile exposes observations, method dependence,
selected/corroborating SourceFacts, failures, conflicts, resolution reason, and
missing requirements. PVS1 can consume a uniquely resolved non-VEP
consequence, but exon structure, PTC/NMD, and disease mechanism must still come
from provider/document facts. All available provider and predictor values
remain visible even when excluded from the system preview.

The collector exposes one source-assertion list and one criterion-review list.
Older duplicate `source_leads`, `route_candidates`, `candidate_criteria`, and
constant execution-mode fields were removed; search only recommends and ranks
tools, while deterministic criterion routing remains in the collector rules.

## Skill Changes

`skills/` is the canonical instruction source. The former
`tooluniverse-acmg-overlay-routing-core` is retired as a visible Skill; its
entry-point, CSpec/literature, SpliceAI/PVS1, compatibility, Bayesian, Guard,
and optional-reviewer contracts now live in
`tooluniverse-acmg-variant-classification`. Criterion-specific rule Skills
remain retired because scientific decisions live in shared pure rule functions
and the machine-readable rule catalog.

The consolidated Skill treats `workflow_status`, `recoverable_gaps`,
`next_actions`, literature review requests, and CSpec requests as a mandatory
automatic state machine. Read-only recovery and exact/equivalent full-text
review proceed without asking the user to continue; the optional user decision
round remains separate. Publication identifier-graph deduplication, verified
full-text states, reading manifests, proposal/document hashes, and processed
request IDs prevent duplicate counting and repeated review loops.

The branch installs the complete upstream user-facing ToolUniverse Skill
surface—not only ACMG Skills—and adds the consolidated ACMG workflow within
that biological research toolkit. `scripts/install_tooluniverse_skills.sh`
is an exact-SHA ACMG deployment extension: Claude and Codex profiles use the
same generated mirrors as their upstream plugins, while the generic profile
uses the same filtered canonical Skill set exposed to standalone clients.
Ordinary upstream users continue to use the marketplace plugins or
`npx skills add`; the branch installer preserves unrelated user Skills and
removes only retired ACMG directories. The packaged mirrors are rebuilt from
canonical `skills/` with the upstream `plugin/sync-skills.sh` rules; the mirror
verifier checks the complete published file set and documented host-specific
YAML frontmatter differences.

Upstream small-variant, rare-disease, and literature Skills route supported
germline small variants to the collector or one of the five evidence group
tools. Structural-variant Skills remain CNV/SV evidence-intake workflows and
explicitly do not submit CNV/SV events to the current small-variant collector.

## Removed Legacy Surface

- plan/collect/apply/finalize wrappers
- harness runner and keyword-based literature evidence extractor
- assessment bundle validator and semantic-combiner fixtures
- legacy session-finalization instructions
- public criterion dispatcher, route, and combine tool configs

The overlay does not produce a five-tier ACMG classification. Global prevention
of model-only pathogenicity reasoning still requires host pre-answer and
post-answer hooks; ToolUniverse enforcement begins inside its policy context.
`examples/acmg_host_hooks.py` provides a framework-neutral reference for those
two calls. Guard label matching normalizes Unicode width, underscores, hyphens,
and repeated whitespace before checking five-tier terminology.
Document-backed LLM facts require ToolUniverse full-text verification of their
identity, locator, excerpts, and extracted fields. An optional internal
`acmg_review_assertion_verifier` callback can add curator provenance but cannot
be self-declared through public tool arguments.

## Installation and MCP Surface

The upstream installation surface remains the default for non-ACMG use:
marketplace plugins for Codex and Claude Code, `npx skills add` for standalone
Skill clients, and `uvx tooluniverse` for the compact MCP runtime. The branch
setup adds only the exact-SHA path needed to bind the enhanced ACMG runtime and
Skill contract reproducibly. That path installs the complete user-facing
ToolUniverse Skill bundle, replaces current ToolUniverse Skill names, and
removes retired routing-core and criterion/refinement directories without
touching unrelated user Skills.
The fork's Claude and Codex `.mcp.json` manifests pin that same validated Git
SHA; this is the only intentional difference from the upstream plugins'
floating `uvx tooluniverse` package resolution.
The default `tooluniverse` entry runs compact mode and exposes
`find_tools`, `list_tools`, `grep_tools`, `get_tool_info`, and `execute_tool`;
approximately 2,600 scientific tools remain dynamically discoverable behind
that compact surface. When any discovery or execution tool is unavailable,
ACMG review stops rather than falling back to direct provider HTTP calls or
manual criterion scoring.
