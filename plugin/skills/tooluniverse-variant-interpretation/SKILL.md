---
name: tooluniverse-variant-interpretation
description: Clinical variant interpretation from raw variant calls to ACMG-classified recommendations with structural impact analysis. Use for VUS classification, pathogenicity assessment with cited criteria, structure-based variant impact (AlphaFold/PDB), non-coding/regulatory variant effect prediction with sequence deep-learning models (AlphaGenome, Enformer, Borzoi, ChromBPNet, Evo 2), and producing clinical-grade variant reports for return of results or molecular tumor boards. Use this whenever a user asks about a variant's significance, an intronic/promoter/enhancer/UTR non-coding variant's functional impact, or needs ACMG classification — even if they don't say "ACMG".
disable-model-invocation: true
---

# Clinical Variant Interpreter

Systematic variant interpretation using ToolUniverse - from raw variant calls to ACMG-classified clinical recommendations with structural impact analysis.

## Triggers

Use this skill when users:
- Ask about variant interpretation, classification, or pathogenicity
- Have VCF data needing clinical annotation
- Need ACMG classification for variants
- Want structural impact analysis for missense variants

## Key Principles

1. **ACMG-Guided** - Follow ACMG/AMP 2015 guidelines with explicit evidence codes
2. **Structural Evidence** - Use AlphaFold2 for novel structural impact analysis
3. **Population Context** - gnomAD frequencies with ancestry-specific data
4. **Actionable Output** - Clear recommendations, not just classifications
5. **English-first queries** - Always use English terms in tool calls; respond in user's language

---

## LOOK UP, DON'T GUESS

When asked about a variant's significance, query ClinVar/gnomAD/CIViC FIRST. Never classify a variant without checking databases. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## Workflow Overview

```
Phase 1: VARIANT IDENTITY        → Normalize HGVS, map gene/transcript/consequence
Phase 2: CLINICAL DATABASES       → ClinVar, gnomAD, OMIM, ClinGen, COSMIC, SpliceAI
Phase 2.5: REGULATORY CONTEXT     → ChIPAtlas/ENCODE annotation + DL variant-effect (AlphaGenome/Enformer/Borzoi/ChromBPNet/Evo2) (non-coding only)
Phase 3: COMPUTATIONAL PREDICTIONS → CADD, AlphaMissense, EVE, SIFT/PolyPhen
Phase 4: STRUCTURAL ANALYSIS      → PDB/AlphaFold2, domains, functional sites (VUS/novel)
Phase 4.5: EXPRESSION CONTEXT     → CELLxGENE, GTEx tissue expression
Phase 5: LITERATURE EVIDENCE      → PubMed, EuropePMC, BioRxiv, MedRxiv
Phase 6: ACMG CLASSIFICATION      → Evidence codes, classification, recommendations
```

---

## Phase 1: Variant Identity

Tools: `MyVariant_query_variants`, `EnsemblVar_get_variant_consequences`, `NCBIGene_search`, `VariantValidator_gene2transcripts`, `VariantValidator_validate_variant`, `Tark_get_mane_transcripts`, `Tark_get_transcript`

**VariantValidator_gene2transcripts**: Look up MANE Select and MANE Plus Clinical transcripts for a gene. Use this to identify the correct canonical transcript before variant annotation.
- Parameters: `gene_symbol` (e.g. "TP53"), `transcript_set` ("mane" | "refseq" | "ensembl" | "all"), `genome_build` ("GRCh38" default)
- Returns: Array of `{current_symbol, transcripts: [{reference, annotations: {mane_select, mane_plus_clinical}}]}`
- Aliases: `gene` and `gene_name` also accepted for `gene_symbol`

**Tark_get_mane_transcripts**: Lightweight MANE Select / MANE Plus Clinical lookup from Ensembl Tark with the ENST↔RefSeq pairing (e.g. `gene="BRCA2"` → ENST00000380152.8 / NM_000059.4). Use as a quick cross-check of the canonical transcript namespace alongside VariantValidator, or to translate an ENST↔NM accession. `Tark_get_transcript` (param `stable_id`, e.g. "ENST00000380152") returns the archived transcript record (assembly, biotype, coordinates, per-release versions) when you need to resolve a specific transcript version.

**VariantValidator_validate_variant**: Validate HGVS variant descriptions and get normalized notation with genomic/transcript/protein consequences.
- Parameters: `genome_build` ("GRCh37" | "GRCh38"), `variant_description` (HGVS, e.g. "NM_007294.4:c.5266dup"), `select_transcripts` (transcript or "all")
- Returns: Validated HGVS, protein consequence, genomic coordinates, gene IDs

Capture: HGVS notation (c. and p.), gene symbol, canonical transcript (MANE Select via VariantValidator), consequence type, amino acid change, exon/intron location.

## Phase 2: Clinical Databases

Tools: `ClinVar_search_variants`, `gnomad_search_variants`, `gnomad_get_variant`, `OMIM_search`, `OMIM_get_entry`, `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`, `COSMIC_search_mutations`, `COSMIC_get_mutations_by_gene`, `DisGeNET_search_gene`, `DisGeNET_get_vda`, `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, `civic_get_variants_by_gene`, `civic_search_evidence_items`, `civic_search_assertions`

> **gnomAD two-step workflow**: `gnomad_search_variants` only accepts rsIDs or variant IDs (not gene names). Search by rsID first, then use the returned `variant_id` with `gnomad_get_variant` to get population allele frequencies.
>
> **CIViC**: Use `civic_search_genes(query="<gene_symbol>")` to find the CIViC gene ID dynamically (do NOT rely on a hardcoded lookup table). Then use `civic_get_variants_by_gene(gene_id=<id>)` and `civic_search_evidence_items` for actionability details. If `civic_search_genes` returns no results, the gene may not be curated in CIViC — note this gap.
>
> **OncoKB note**: Demo mode only supports BRAF, TP53, ROS1. For other genes, set `ONCOKB_API_TOKEN` environment variable.

Use SpliceAI for: intronic variants near splice sites, synonymous variants, exonic variants near splice junctions.

See `CODE_PATTERNS.md` for implementation details.

## Phase 2.5: Regulatory Context (Non-Coding Only)

Apply for intronic (non-splice), promoter, UTR, or intergenic variants near disease genes.

**Annotation — what regulatory element is here:** `ChIPAtlas_enrichment_analysis`, `ChIPAtlas_get_peak_data`, `ENCODE_search_experiments`, `ENCODE_get_experiment`. These tell you whether the variant falls in a known TF-binding peak, enhancer, or open-chromatin region.

**Prediction — what the variant *does* to regulation:** annotation says an element is present, not whether this specific allele disrupts it. Sequence-based deep-learning models answer that directly: they read the reference and alternate DNA windows and predict the change in regulatory signal. This is what turns "the variant is in an enhancer" into "the variant is predicted to reduce accessibility/expression in the relevant tissue" — the mechanistic evidence ACMG PS3/PP3 actually needs for a non-coding variant, where SIFT/PolyPhen/AlphaMissense do not apply.

| Tool | Predicts | Context | Access |
|---|---|---|---|
| `AlphaGenome_score_variant` | Δ across RNA-seq / ATAC / CAGE / splice tracks (frontier accuracy, single-base) | up to 1 Mb | hosted API — needs `ALPHA_GENOME_API_KEY` |
| `run_enformer_variant_effect` | Δ across 5,313 human tracks (expression, chromatin, TF binding) | 196 kb | remote MCP server |
| `run_borzoi_variant_effect` | Δ in RNA-seq coverage (expression / polyA / splicing emphasis) | 524 kb | remote MCP server |
| `run_chrombpnet_variant_effect` | Δ in chromatin accessibility (ATAC / DNase), base-resolution | ~2 kb | remote MCP server |
| `Evo2_score_variant` | Genome-foundation-model delta log-likelihood; covers coding **and** non-coding | up to 1 Mb | hosted NIM — needs `NVIDIA_API_KEY` |

**Reading the score:** these return Δ (alt − ref) effect sizes, *not* calibrated pathogenicity probabilities. Record the deltas per tissue-relevant track as raw facts; whether they support or oppose pathogenicity is decided in the unified ACMG skill -- no direct code mapping is applied here. Rank or calibrate against known regulatory variants rather than applying an absolute cutoff.

**Which to pick:** start with `AlphaGenome_score_variant` (broadest readout, longest context, frontier accuracy) when its key is set; `run_enformer_variant_effect` / `run_borzoi_variant_effect` are the named, self-hostable equivalents (Enformer for general regulation, Borzoi when expression/splicing is the question); `run_chrombpnet_variant_effect` when the hypothesis is specifically chromatin accessibility; `Evo2_score_variant` as a sequence-only check that also works on coding variants. If no key/server is provisioned, fall back to the ChIPAtlas/ENCODE annotation above and note the predictive gap rather than guessing.

**Inputs:** `AlphaGenome_score_variant` takes `chromosome` + `position` + `reference_bases`/`alternate_bases` (+ `output_type`, `sequence_length`); `Evo2_score_variant` takes a DNA window as `sequence` + `position` + `alternate` (point substitution) or `ref_sequence`/`alt_sequence`, plus optional `model` (`evo2-40b` default, `evo2-7b` faster); the Enformer/Borzoi/ChromBPNet remote tools take the variant locus and score the change over their output tracks.

## Phase 2.9: Short-Circuit Check

Before full ACMG classification, check if the variant already has an expert panel classification in ClinVar. Use `MyVariant_query_variants` with the rsID or HGVS notation — the `clinvar` field in the response includes clinical significance, review status, and RCV records. If an expert panel has already classified the variant as Pathogenic or Benign, note this prominently and focus on confirming/contextualizing rather than de novo classification.

## Phase 3: Computational Predictions

**Primary approach:** `MyVariant_query_variants` with `fields=dbnsfp,clinvar,cadd,gnomad_genome` retrieves 15+ predictor scores (SIFT, PolyPhen, CADD, REVEL, AlphaMissense, MetaRNN, FATHMM, GERP, PhyloP, etc.) in a single call. This is usually sufficient.

**REVEL/AlphaMissense fallback**: If `MyVariant_query_variants` returns no `dbnsfp` block, use the dedicated tool:
1. **`MyVariant_get_pathogenicity_scores`** (PREFERRED FALLBACK) — returns REVEL, AlphaMissense, SIFT, PolyPhen2, MetaRNN, GERP, PhyloP, and more in a single call with pre-configured dbnsfp fields. Input: `variant_id` (rsID or HGVS genomic).
2. `CADD_get_variant_score` (PHRED 0-99) — works for most variants
3. `AlphaMissense_get_variant_score` (0-1, needs UniProt ID) — missense only
4. `EVE_get_variant_score` (0-1) — missense only
5. `EnsemblVEP_annotate_hgvs` (VEP with colocated variants) — includes SIFT/PolyPhen
6. If REVEL is still unavailable, note this as a limitation and record the raw CADD / SIFT / PolyPhen scores as material. REVEL absence does not prevent evidence collection.

Code assignment: NEVER by predictor agreement. The ACMG code and strength come from a pre-specified calibrated tool under the unified ACMG skill's SVI_REFERENCE.md; concordance among uncalibrated predictors is context, not evidence.

See `ACMG_CLASSIFICATION.md` for thresholds.

## Phase 4: Structural Analysis (VUS/Novel Missense)

Tools: `PDBe_get_uniprot_mappings`, `NvidiaNIM_alphafold2` *(requires NVIDIA_API_KEY env var; free key at build.nvidia.com)*, `alphafold_get_prediction` (param: `qualifier`, e.g., UniProt accession), `InterPro_get_protein_domains`, `UniProt_get_function_by_accession`

Workflow: Get structure -> map residue -> assess domain/functional site -> predict destabilization.

> **AlphaFold size limitation**: Very large proteins (>2,700 aa, e.g., BRCA2 at 3,418 aa) may not have AlphaFold predictions via the standard API. Fall back to published structural studies or `PDBe_get_uniprot_mappings` for experimental structures.

## Phase 4.2: Mechanism of Effect (VUS missense, ESMC-6B SAE)

AlphaMissense / REVEL / CADD give a pathogenicity score but no mechanism. When you need to answer "**how** does this variant disrupt protein function" — e.g. for VUS write-ups, clinical reports, or to triangulate a discordant predictor consensus — use the ESMC-6B Sparse Autoencoder to identify which interpretable protein-language-model features the mutation disrupts.

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

Returns `mechanism_summary`, per-feature lost/gained tables, and category aggregates. Use the category aggregate to support or qualify the pathogenicity verdict in the report:
- `catalytic` / `ligand-binding` / `ptm` lost → record as mechanistic context for the unified assessment
- `secondary-structure` / `structural-stability` gained on a stable WT region → mechanistic basis for "destabilizing" claim
- No interpretable change at top-K → does not weaken AlphaMissense alone, but flag for caution

**When you have a saturation question** (e.g. "score all 19 substitutions at residue 600 to find the most disruptive"): use `ESM_score_variant_sae_batch` — 1 Forge call for the reference + 1 per variant, instead of 2 per variant.

**When the region is what matters** (e.g. "what's the SAE signature of the kinase activation loop, residues 754-771"): use `ESM_get_region_sae_features` then `ESM_describe_sae_feature` on the top hits.

**Requires**: `ESM_API_KEY` env var (free non-commercial token at https://forge.evolutionaryscale.ai) and `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` (SAE support is on an unmerged feature branch — PyPI esm 3.2.x does NOT include SAEConfig). License: EvolutionaryScale Cambrian Inference License — non-commercial use only.

## Phase 4.5: Expression Context

Tools: `CELLxGENE_get_expression_data`, `CELLxGENE_get_cell_metadata`, `GTEx_get_median_gene_expression`

Confirms gene expression in disease-relevant tissues; record expression breadth as raw context -- phenotype-specificity assessment (PP4) happens in the unified ACMG skill.

## Phase 5: Literature Evidence

Tools: `PubMed_search_articles`, `EuropePMC_search_articles`, `BioRxiv_list_recent_preprints`, `MedRxiv_get_preprint`, `openalex_search_works`, `SemanticScholar_search_papers`

Always flag preprints as NOT peer-reviewed.

## Phase 6: ACMG Classification (germline small variants -> single unified flow)

For any germline small variant, classification runs in the
`tooluniverse-acmg-variant-classification` skill -- one flow shared by every
entry point: confirm variant and scope -> query and confirm the applicable
ClinGen CSpec (`ClinGen_search_cspec`, then read the specification's official
page with `get_webpage_text_from_url`) -> collect facts -> evaluate all 28
criteria (per that skill's `SVI_REFERENCE.md`) -> check dependencies and
double counting -> call `ACMG_calculate_classification` -> present its output
verbatim. Do not compute classifications, point totals, or thresholds inline
here. PP5/BP6 are retired; ClinVar/VCEP conclusions are attributed separately
and never scored. When a specification pauses the calculator
(`needs_review`), report the reasons -- never silently fall back to generic
classification.

### Gene-Specific Population Frequency Thresholds

Record ancestry-specific allele frequencies and disease prevalence as raw
facts. BS1/BA1/PM2 thresholds are gene- and disease-specific and are
decided in the unified ACMG skill (disease-aware maximum credible
frequency, Whiffin 2017 framework) -- no fixed cutoff or heuristic is
applied at collection time.


### Handling Conflicting Evidence: Functional vs Epidemiological

This is one of the most challenging scenarios in variant interpretation. When a biochemical assay shows damage but population/epidemiological data shows no disease association:

1. **Epidemiological data generally trumps in-vitro assays** for clinical classification. A variant found at ~0.1% frequency with no disease association in 40K+ cases is unlikely to be clinically significant, even if it reduces protein function in a tube.
2. **Record functional-study quality as facts**: validation status (known pathogenic AND benign controls, replication) is raw material; PS3/BS3 strength assignment follows the SVI validation framework in the unified ACMG skill.
3. **Hypomorphic variants**: Some variants genuinely reduce protein function (detectable in sensitive assays) but not enough to cause disease. This is biologically real and does not make them pathogenic.
4. **Document the conflict explicitly** in the report. State: "Biochemical assay X shows [result], but case-control study Y with N cases found no significant disease association. Per ACMG guidelines, the epidemiological evidence is weighted more heavily for clinical classification."

### CSpec and VCEP Specifications Take Precedence

A Released ClinGen CSpec (VCEP specification) overrides generic rules for its
genes (PM1 hotspot regions, PM2 at Supporting, BA1 exceptions, combination
caps, ...). Before classifying:
- `ClinGen_search_cspec(gene="<symbol>")` -- Released specifications with
  criterion applicability, versions, and official page URLs
- Read the specification's official page -- the API JSON alone is not the
  full specification
- Combinations or thresholds the Tavtigian 2020 calculator cannot express
  pause the classification for expert review
- No Released specification -> generic ACMG/AMP 2015 + ClinGen SVI rules

### Predictor Weighting

Not all computational predictors are equal. For missense variants:
- **REVEL** (AUC ~0.95) — best single meta-predictor; weight highest
- **AlphaMissense** (AUC ~0.94) — strong, structure-aware
- **CADD** (AUC ~0.85) — good for all variant types, but less specific for missense
- **SIFT/PolyPhen** (AUC ~0.80) — legacy tools; raw-score context only, never the basis for PP3/BP4 strength

When predictors disagree: if REVEL says tolerated but SIFT/PolyPhen say damaging, lean toward REVEL. PP3/BP4 are applied from a single calibrated predictor meeting its pre-set threshold (see the ACMG skill's SVI_REFERENCE.md); when calibrated predictors disagree, neither code applies.

### Tool Failure Fallbacks

If a primary tool fails, use these alternatives:
- **ClinVar_search_variants returns 0 results**: Use `MyVariant_query_variants` with rsID or HGVS — the `clinvar` field in MyVariant is more reliable for variant lookup than NCBI Entrez search
- **gnomad_search_variants fails**: Use `EnsemblVEP_annotate_hgvs` which includes gnomAD frequency via colocated variants
- **CADD_get_variant_score fails**: CADD PHRED is also available in the `dbnsfp` block from MyVariant
- **AlphaFold prediction unavailable** (large proteins >2700aa): Use `PDBe_get_uniprot_mappings` for experimental structures

---

## Special Scenarios

**Novel Missense VUS**: collect same-residue variants, structure, and domain context as raw facts; PM5/PM1/PP3 are assessed in the unified ACMG skill.

**Truncating Variant**: collect LoF mechanism evidence, NMD expectation, and isoform context; PVS1 strength comes from the SVI decision tree in the unified ACMG skill.

**Splice Variant**: run SpliceAI and record canonical-splice distance and in-frame skipping potential as facts; PP3/BP7/PVS1 assignment follows the calibrated splicing rules in the unified ACMG skill.

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
## 7. ACMG Classification
## 8. Clinical Recommendations
## 9. Limitations & Uncertainties
## Data Sources
```

File naming: `{GENE}_{VARIANT}_interpretation_report.md`

---

## Clinical Recommendations

**Pathogenic/Likely Pathogenic**: Enhanced screening, risk-reducing options, drug dosing adjustment, reproductive counseling, family cascade screening.

**VUS**: Do not use for medical decisions. Reinterpret in 1-2 years. Pursue functional studies and segregation data.

**Benign/Likely Benign**: Not expected to cause disease. No cascade testing needed.

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Population frequency | gnomAD overall + at least 3 ancestry groups |
| Predictions | At least 3 computational predictors |
| Literature search | At least 2 search strategies |
| ACMG codes | All applicable codes listed |

---

## Cross-Skill References

For amino acid properties at variant position, run: `python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code X`

---

## References

- `ACMG_CLASSIFICATION.md` - Evidence codes, classification algorithm, prediction thresholds, structural/regulatory impact tables
- `CODE_PATTERNS.md` - Reusable code patterns for each workflow phase
- `CHECKLIST.md` - Pre-delivery verification
- `EXAMPLES.md` - Sample interpretations
- `TOOLS_REFERENCE.md` - Tool parameters and fallbacks
