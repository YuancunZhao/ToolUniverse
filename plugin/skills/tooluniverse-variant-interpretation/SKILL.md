---
name: tooluniverse-variant-interpretation
description: Variant evidence intake and draft interpretation support from raw variant calls, with structural, population, clinical-database, computational, and literature annotation. Germline ACMG requests must be handed to the evidence-only ACMG collector, which does not permit a five-tier final verdict.
---

# Clinical Variant Interpreter

Systematic variant evidence intake using ToolUniverse - from raw variant calls to source, population, computational, structural, and literature context for downstream ACMG evidence assessment.

## Triggers

Use this skill when users:
- Ask about variant interpretation or evidence intake before classification
- Have VCF data needing clinical annotation
- Need source, population, computational, structural, or literature evidence gathered for variants
- Want structural impact analysis for missense variants

If the user asks whether a germline variant is pathogenic, asks for ACMG classification, clinical significance, or any final five-tier verdict, hand off to the evidence-only ACMG runtime through `ACMG_evidence_collector`. The current runtime may report validated criteria, conflicts, limitations, and a Bayesian review estimate, but it must explicitly decline an automated five-tier verdict.

## Key Principles

1. **ACMG-Guided Intake** - Gather evidence and candidate routes for ACMG/AMP 2015 criteria without final local scoring
2. **Structural Evidence** - Use AlphaFold2 for novel structural impact analysis
3. **Population Context** - gnomAD frequencies with ancestry-specific data
4. **Draft Output** - Clear evidence gaps and route candidates, not final clinical classification
5. **English-first queries** - Always use English terms in tool calls; respond in user's language
6. **Confidentiality and Human Review** - De-identify patient-level inputs, separate public from restricted evidence, disclose AI-assisted drafting when used for notes or curation drafts, and require qualified human review before clinical use

---

## LOOK UP, DON'T GUESS

When asked about a variant's significance, call `ACMG_evidence_collector`; use ClinVar/gnomAD/CIViC results as visible intake facts and leads. Never present a source label or free-form model inference as a final germline ACMG classification. Distinguish observed facts, suggested criteria, compatibility exclusions, system-preview inclusion, and user-selected inclusion.

---

## Confidentiality and AI-Assisted Drafting

Before processing patient-level phenotype, family, segregation, de novo, phase, or unpublished curation evidence:

- Ask the user to provide de-identified data only; do not request or retain names, dates of birth, medical record numbers, direct contact information, or other patient-identifiable data.
- Treat unpublished VCEP drafts, meeting notes, internal deliberations, and confidential case-level data as restricted evidence. Do not present them as public ClinGen guidance.
- If AI-assisted output will be used as meeting notes, curation notes, or a clinical interpretation draft, include an explicit statement that AI tools assisted drafting/evidence retrieval and that a designated human reviewer must verify and finalize the content.
- Do not automatically publish, distribute, or finalize variant classifications, evidence tables, or meeting notes without human review.

These safeguards follow the governance principles in ClinGen's AI note-taking
policy v1.0 and complement the
`tooluniverse-acmg-variant-classification` safeguards; they do not change ACMG
evidence criteria.

---

## Workflow Overview

```
Phase 1: VARIANT IDENTITY        → Normalize HGVS, map gene/transcript/consequence
Phase 2: CLINICAL DATABASES       → ClinVar, gnomAD, OMIM, ClinGen, GeneReviews/MedGen, COSMIC, SpliceAI
Phase 2.5: REGULATORY CONTEXT     → ChIPAtlas, ENCODE (non-coding variants only)
Phase 3: COMPUTATIONAL PREDICTIONS → CADD, AlphaMissense, EVE, SIFT/PolyPhen
Phase 4: STRUCTURAL ANALYSIS      → PDB/AlphaFold2, domains, functional sites (VUS/novel)
Phase 4.5: EXPRESSION CONTEXT     → CELLxGENE, GTEx tissue expression
Phase 5: LITERATURE EVIDENCE      → PubMed, EuropePMC, BioRxiv, MedRxiv
Phase 6: ACMG EVIDENCE REVIEW     → Candidate cards, compatibility, and Bayesian review; no final verdict
```

---

## Phase 1: Variant Identity

Tools: `MyVariant_query_variants`, `EnsemblVar_get_variant_consequences`, `NCBIGene_search`, `VariantValidator_gene2transcripts`, `VariantValidator_format_genomic_to_transcripts`, `VariantValidator_validate_variant`, `EnsemblVEP_annotate_hgvs`, `EnsemblVEP_variant_recoder`

**VariantValidator_gene2transcripts**: Look up MANE Select and MANE Plus Clinical transcripts for a gene. Use this to identify the correct canonical transcript before variant annotation.
- Parameters: `gene_symbol` (e.g. "TP53"), `transcript_set` ("mane" | "refseq" | "ensembl" | "all"), `genome_build` ("GRCh38" default)
- Returns: Array of `{current_symbol, transcripts: [{reference, annotations: {mane_select, mane_plus_clinical}}]}`
- Aliases: `gene` and `gene_name` also accepted for `gene_symbol`

**Input routing**:
- Complete transcript HGVS (for example `NM_000059.4:c.5946delT`) goes directly to `VariantValidator_validate_variant` and is cross-checked with `EnsemblVEP_variant_recoder`.
- Gene plus transcript HGVS (for example `BRCA2;NM_000059.4:c.5946delT`) is parsed into its gene and transcript components, then validated directly; the embedded gene and transcript must agree with provider output.
- Gene plus coding shorthand (for example `BRCA2 c.5946delT`) is resolved through `VariantValidator_gene2transcripts` first; use the unique MANE Select transcript, or a unique MANE Plus Clinical transcript only when no MANE Select exists, before constructing the full HGVS.
- Gene plus protein shorthand (for example `BRCA2 p.Ser1982ArgfsTer22`) is sent to `EnsemblVEP_annotate_hgvs` to obtain genomic identity, then projected through `VariantValidator_format_genomic_to_transcripts`; continue only when the gene and MANE projection are unique and cross-validated.
- Genomic HGVS or VCF-like input goes through `VariantValidator_format_genomic_to_transcripts` so the MANE Select transcript projection is selected before validation.
- An rsID is recoded with `EnsemblVEP_variant_recoder` before transcript/HGVS validation.
- If transcript resolution is ambiguous or provider identity cannot be cross-validated, stop identity processing and report the normalization limitation; do not infer a transcript or continue ACMG evidence collection.

**VariantValidator_validate_variant**: Validate HGVS variant descriptions and get normalized notation with genomic/transcript/protein consequences.
- Parameters: `genome_build` ("GRCh37" | "GRCh38"), `variant_description` (HGVS, e.g. "NM_007294.4:c.5266dup"), `select_transcripts` (transcript or "all")
- Returns: Validated HGVS, protein consequence, genomic coordinates, gene IDs

Capture: HGVS notation (c. and p.), gene symbol, canonical transcript (MANE Select via VariantValidator), consequence type, amino acid change, exon/intron location. The collector builds consequence applicability only from the identity-selected transcript; VEP `most_severe_consequence` is audit context and cannot route a criterion by itself.

## Phase 2: Clinical Databases

Tools: `ClinVar_search_variants`, `gnomad_search_variants`, `gnomad_get_variant`, `OMIM_search`, `OMIM_get_entry`, `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`, `MedGen_search_conditions`, `COSMIC_search_mutations`, `COSMIC_get_mutations_by_gene`, `DisGeNET_search_gene`, `DisGeNET_get_vda`, `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, `civic_get_variants_by_gene`, `civic_search_evidence_items`, `civic_search_assertions`

> **gnomAD two-step workflow**: `gnomad_search_variants` only accepts rsIDs or variant IDs (not gene names). Search by rsID first, then use the returned `variant_id` with `gnomad_get_variant` to get population allele frequencies.
>
> **CIViC**: Use `civic_search_genes(query="<gene_symbol>")` to find the CIViC gene ID dynamically (do NOT rely on a hardcoded lookup table). Then use `civic_get_variants_by_gene(gene_id=<id>)` and `civic_search_evidence_items` for actionability details. If `civic_search_genes` returns no results, the gene may not be curated in CIViC — note this gap.
>
> **OncoKB note**: Demo mode only supports BRAF, TP53, ROS1. For other genes, set `ONCOKB_API_TOKEN` environment variable.

Use SpliceAI for: intronic variants near splice sites, synonymous variants, exonic variants near splice junctions.

Use GeneReviews/NCBI Bookshelf disease chapters when disease spectrum, inheritance, or mechanism affects ACMG evidence routing. Start with `MedGen_search_conditions(query="<gene or disease> GeneReviews")`; if the chapter is not exposed in ToolUniverse results, use PubMed/EuropePMC or direct NCBI Bookshelf lookup. GeneReviews supports mechanism and clinical-context interpretation, but it is not a VCEP specification and should not be used alone as primary variant-level evidence.

See `CODE_PATTERNS.md` for implementation details.

## Phase 2.5: Regulatory Context (Non-Coding Only)

Apply for intronic (non-splice), promoter, UTR, or intergenic variants near disease genes.

Tools: `ChIPAtlas_enrichment_analysis`, `ChIPAtlas_get_peak_data`, `ENCODE_search_experiments`, `ENCODE_get_experiment`

## Phase 2.9: Short-Circuit Check

Before evidence review, let `ACMG_evidence_collector` query ClinVar and related sources from the verified identity. Treat expert-panel and practice-guideline entries as source assertions and high-value leads; retrieve primary evidence and route criterion review through the collector's deterministic rules. Do not adopt the source label as evidence.

## Phase 3: Computational Predictions

**Primary approach:** Let `ACMG_evidence_collector` query MyVariant with the
VariantValidator-verified GRCh37 absolute genomic HGVS. It preserves available
dbNSFP predictor scores and metadata while binding them back to the normalized
variant.

**REVEL/AlphaMissense fallback**: If `MyVariant_query_variants` returns no `dbnsfp` block, use the dedicated tool:
1. **`MyVariant_get_pathogenicity_scores`** (collector provider) — returns REVEL, AlphaMissense, SIFT, PolyPhen2, MetaRNN, GERP, PhyloP, and more in a single call with pre-configured dbnsfp fields. Input must be the verified GRCh37 absolute genomic HGVS; do not substitute rsID, protein HGVS, or an unverified coordinate.
2. `CADD_get_variant_score` (PHRED 0-99) — works for most variants
3. `AlphaMissense_get_variant_score` (0-1, needs UniProt ID) — missense only
4. `EVE_get_variant_score` (0-1) — missense only
5. `EnsemblVEP_annotate_hgvs` (VEP with colocated variants) — includes SIFT/PolyPhen
6. If REVEL is unavailable, record PP3/BP4 as `not_assessed`; do not substitute CADD, AlphaMissense, or an unregistered predictor.

Do not assign PP3/BP4 by local predictor voting. For missense variants, route predictor evidence through `ACMG_computational_evidence`, which currently applies the versioned REVEL thresholds from Pejaver et al. 2022. CADD, AlphaMissense, EVE, SIFT, and PolyPhen may be retained as audit context, but cannot replace REVEL or vote toward a criterion.

See `ACMG_CLASSIFICATION.md` for evidence routes and missing-contract guidance.

## Phase 4: Structural Analysis (VUS/Novel Missense)

Tools: `PDBe_get_uniprot_mappings`, `NvidiaNIM_alphafold2` *(requires NVIDIA_API_KEY env var; free key at build.nvidia.com)*, `alphafold_get_prediction` (param: `qualifier`, e.g., UniProt accession), `InterPro_get_protein_domains`, `UniProt_get_function_by_accession`

Workflow: Get structure -> map residue -> assess domain/functional site -> predict destabilization.

> **AlphaFold size limitation**: Very large proteins (>2,700 aa, e.g., BRCA2 at 3,418 aa) may not have AlphaFold predictions via the standard API. Fall back to published structural studies or `PDBe_get_uniprot_mappings` for experimental structures.

## Phase 4.2: Mechanism of Effect (VUS missense, ESMC-6B SAE)

AlphaMissense / REVEL / CADD give a pathogenicity score but no mechanism. When you need to answer "**how** does this variant disrupt protein function" - for example, for VUS write-ups, clinical reports, or to investigate discordant predictor outputs - use the ESMC-6B Sparse Autoencoder to identify which interpretable protein-language-model features the mutation disrupts.

**One-call mechanism summary** (recommended starting point):
```python
mech = tu.tools.ESM_explain_variant_mechanism(
    sequence=wt_aa_sequence,   # full reference protein sequence
    position=600,              # 1-indexed
    ref_aa="V",
    alt_aa="E",
    top_k_features=5,          # describe top 5 lost + top 5 gained
)
# mech["data"]["mechanism_summary"] e.g.:
#   "Disrupted feature categories (lost): catalytic=2, ligand-binding=1;
#    Induced feature categories (gained): structural-stability=1"
```

Returns `mechanism_summary`, per-feature lost/gained tables, and category aggregates. Use the category aggregate as mechanism context for downstream evidence review:
- `catalytic` / `ligand-binding` / `ptm` lost → mechanism context only; route prediction evidence to the collector and do not count PP3 locally
- `secondary-structure` / `structural-stability` gained on a stable WT region → mechanistic basis for "destabilizing" claim
- No interpretable change at top-K → does not weaken AlphaMissense alone, but flag for caution

**When you have a saturation question** (e.g. "score all 19 substitutions at residue 600 to find the most disruptive"): use `ESM_score_variant_sae_batch` — 1 Forge call for the reference + 1 per variant, instead of 2 per variant.

**When the region is what matters** (e.g. "what's the SAE signature of the kinase activation loop, residues 754-771"): use `ESM_get_region_sae_features` then `ESM_describe_sae_feature` on the top hits.

**Requires**: `ESM_API_KEY` env var (free non-commercial token at https://forge.evolutionaryscale.ai) and `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` (SAE support is on an unmerged feature branch — PyPI esm 3.2.x does NOT include SAEConfig). License: EvolutionaryScale Cambrian Inference License — non-commercial use only.

## Phase 4.5: Expression Context

Tools: `CELLxGENE_get_expression_data`, `CELLxGENE_get_cell_metadata`, `GTEx_get_median_gene_expression`

Confirms gene expression in disease-relevant tissues. This can contextualize disease relevance, but it does not satisfy PP4. The current clinical group tool keeps PP4, segregation, and benign-context routes review-only until a complete disease-specific contract is available.

## Phase 5: Literature Evidence

Tools: `PubMed_search_articles`, `EuropePMC_search_articles`, `BioRxiv_list_recent_preprints`, `MedRxiv_get_preprint`, `openalex_search_works`, `SemanticScholar_search_papers`

Always flag preprints as NOT peer-reviewed.

## Phase 6: ACMG Intake Only

This phase is evidence collection and review only. Do not emit a five-tier classification from this skill. Use `ACMG_evidence_collector`; it delegates to the five deterministic evidence group tools and returns observed facts, criterion suggestions, exclusions, and a system-preview Bayesian estimate. Secondary source assertions remain leads, and PP5/BP6 are deprecated.

Any interpretation report remains evidence-only. Criterion wording requires a matching overlay-validated EvidenceCard and `ACMG_guard_final_answer`; five-tier labels are blocked.

### Gene-Specific Population Frequency Thresholds

BA1 stand-alone benign evidence requires a registered exception-list review before use. BS1 requires a disease-specific maximum credible AF contract incorporating prevalence, penetrance, allelic and genetic heterogeneity, inheritance, and ancestry. The current collector does not automatically count BA1 or BS1; missing that contract must remain a review limitation. Do not substitute gene-group thresholds or compare against the highest AF of a known pathogenic variant.

### Handling Conflicting Evidence: Functional vs Epidemiological

This is one of the most challenging scenarios in variant interpretation. When a biochemical assay shows damage but population/epidemiological data shows no disease association:

1. **Do not impose an undocumented precedence rule.** Preserve population, case-control, and functional facts independently and let compatibility/conflict review show their directions and calibration.
2. **Route PS3/BS3 carefully**: ClinGen's SVI functional-assay guidance requires assay validity, controls, replicates, calibration, and variant-specific results. Do not assign PS3/BS3 inside this variant-interpretation skill; route assay evidence to `ACMG_functional_evidence`.
3. **Hypomorphic variants**: Some variants genuinely reduce protein function (detectable in sensitive assays) but not enough to cause disease. This is biologically real and does not make them pathogenic.
4. **Document the conflict explicitly** with each source, assay or cohort, rule basis, and compatibility decision. Do not automatically select the favorable direction.

### Evidence-only Summary

Do not calculate the final ACMG classification inside this variant-interpretation skill. After Phases 1-5 retrieve and summarize the evidence, call `ACMG_evidence_collector` for the supported evidence-only workflow. The collector returns review estimates and never emits a five-tier label.

### Gene-Specific VCEP Criteria

ClinGen Variant Curation Expert Panels (VCEPs) publish gene- and disease-specific ACMG modifications. The collector calls `ClinGen_search_cspec` immediately after gene identity is verified, then requires a unique released gene, MONDO disease, and inheritance match. Gene Validity does not imply that a VCEP specification exists. Explicit structured applicability and strength fields are normalized from the online document. Natural-language conditions are returned as `cspec_review_requests`; a host-LLM `cspec_proposals` interpretation is used only after the collector re-fetches and verifies the specification ID, version, content hash, criterion, and excerpt. Local contracts are exact-hash caches or fixtures, not a whitelist. Missing context, no match, ambiguity, or network failure falls back to general SVI without blocking evidence collection.

### Predictor Weighting

Report every available predictor score and version. For missense variants, use
an applicable CSpec predictor policy first; otherwise use the versioned
Pejaver-2022 REVEL calibration. CADD, AlphaMissense, SIFT, PolyPhen, and other
scores remain audit and disagreement context and never vote. For supported
small variants, retain all SpliceAI delta scores and positions; compatibility
review handles overlap with PVS1 or RNA evidence. The general Walker rule uses
PP3_Supporting at raw max delta >=0.2 and BP4_Supporting at <=0.1; the Moderate
label describes calibration performance, not the applied code weight. Missing
1.3.1/MANE/raw/unmasked/distance-500 provenance remains `not_assessed`. After
strict BP4, synonymous variants and intronic variants outside +7/-21 may also
suggest BP7_Supporting.

### Tool Failure Fallbacks

If a primary tool fails, use these alternatives:
- **ClinVar_search_variants returns 0 results**: Preserve the no-hit result. A MyVariant ClinVar block may be shown as a separate source assertion, never as criterion evidence.
- **gnomAD frequency or callability fails**: Preserve the provider failure and population data gap. VEP colocated variants are not a substitute for the gnomAD frequency/callability SourceFact contract.
- **CADD_get_variant_score fails**: CADD PHRED is also available in the `dbnsfp` block from MyVariant
- **AlphaFold prediction unavailable** (large proteins >2700aa): Use `PDBe_get_uniprot_mappings` for experimental structures

---

## Special Scenarios

**Novel Missense Variant**: Check comparison variants and protein-region context as review leads. PP3/BP4 uses the versioned REVEL policy. PM1 protein mapping and domain/site overlap are collected through EBI Proteins and InterPro, but ordinary overlap remains `indeterminate`; only an exact online-bound CSpec PM1 region contract may become a candidate. Anchored literature facts may produce review-required PS1/PM5 and PP2/BP1 proposals through the fixed fact-type mapping.

**Truncating Variant**: Collect transcript and loss-of-function context, but keep PVS1 `not_assessed` until the complete ClinGen decision-tree facts are available.

**Splice Variant**: Run SpliceAI for supported normalized small variants. The versioned Walker rule may suggest Supporting PP3/BP4 only when its strict run and selected-row contract is verified; canonical +/-1/2 variants remain PVS1 route context. Prediction, PVS1, and RNA facts remain separate. Direct RNA-splicing readouts are not PS3/BS3 evidence.

---

## Output Structure

```markdown
# Variant Interpretation Report: {GENE} {VARIANT}
## Executive Summary
## 1. Variant Identity
## 2. Population Data
## 3. Clinical Database Evidence
## 4. Computational Predictions
## 5. Structural Analysis
## 6. Literature Evidence
## 7. ACMG Evidence Review
## 8. Human Review Boundary
## 9. Limitations & Uncertainties
## Data Sources
```

File naming: `{GENE}_{VARIANT}_interpretation_report.md`

---

## Human Review Notes

This section records review boundaries and evidence gaps, not patient-management recommendations.

- If source assertions or candidate rules point in one direction, state the supporting facts, exclusions, unresolved conflicts, and need for qualified review rather than a final clinical action.

- If evidence remains uncertain, state that the variant evidence is draft-only and should not guide medical decisions without qualified review.

- If benign-oriented evidence appears, preserve the facts and compatibility decision; do not recommend cascade-testing decisions from this skill alone.

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Population frequency | gnomAD overall + at least 3 ancestry groups |
| Predictions | REVEL when available; other predictors are audit-only |
| Literature search | At least 2 search strategies |
| ACMG codes | Only supported, source-backed criteria are listed; unsupported criteria remain route candidates |

---

## Cross-Skill References

For amino acid properties at variant position, run: `python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code X`

---

## References

- `ACMG_CLASSIFICATION.md` - Evidence routes, rule context, limitations, and prediction audit fields
- `CODE_PATTERNS.md` - Reusable code patterns for each workflow phase
- `CHECKLIST.md` - Pre-delivery verification
- `EXAMPLES.md` - Sample interpretations
- `TOOLS_REFERENCE.md` - Tool parameters and fallbacks
