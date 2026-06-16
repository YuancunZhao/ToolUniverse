---
name: tooluniverse-variant-interpretation
description: Clinical variant interpretation from raw variant calls to ACMG-classified recommendations with structural impact analysis. Use for VUS classification, pathogenicity assessment with cited criteria, structure-based variant impact (AlphaFold/PDB), and producing clinical-grade variant reports for return of results or molecular tumor boards.
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
Phase 2: CLINICAL DATABASES       → ClinVar, gnomAD, OMIM, ClinGen, GeneReviews/MedGen, COSMIC, SpliceAI
Phase 2.5: REGULATORY CONTEXT     → ChIPAtlas, ENCODE (non-coding variants only)
Phase 3: COMPUTATIONAL PREDICTIONS → CADD, AlphaMissense, EVE, SIFT/PolyPhen
Phase 4: STRUCTURAL ANALYSIS      → PDB/AlphaFold2, domains, functional sites (VUS/novel)
Phase 4.5: EXPRESSION CONTEXT     → CELLxGENE, GTEx tissue expression
Phase 5: LITERATURE EVIDENCE      → PubMed, EuropePMC, BioRxiv, MedRxiv
Phase 6: ACMG CLASSIFICATION      → Evidence codes, classification, recommendations
```

---

## Phase 1: Variant Identity

Tools: `MyVariant_query_variants`, `EnsemblVar_get_variant_consequences`, `NCBIGene_search`, `VariantValidator_gene2transcripts`, `VariantValidator_validate_variant`

**VariantValidator_gene2transcripts**: Look up MANE Select and MANE Plus Clinical transcripts for a gene. Use this to identify the correct canonical transcript before variant annotation.
- Parameters: `gene_symbol` (e.g. "TP53"), `transcript_set` ("mane" | "refseq" | "ensembl" | "all"), `genome_build` ("GRCh38" default)
- Returns: Array of `{current_symbol, transcripts: [{reference, annotations: {mane_select, mane_plus_clinical}}]}`
- Aliases: `gene` and `gene_name` also accepted for `gene_symbol`

**VariantValidator_validate_variant**: Validate HGVS variant descriptions and get normalized notation with genomic/transcript/protein consequences.
- Parameters: `genome_build` ("GRCh37" | "GRCh38"), `variant_description` (HGVS, e.g. "NM_007294.4:c.5266dup"), `select_transcripts` (transcript or "all")
- Returns: Validated HGVS, protein consequence, genomic coordinates, gene IDs

Capture: HGVS notation (c. and p.), gene symbol, canonical transcript (MANE Select via VariantValidator), consequence type, amino acid change, exon/intron location.

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

Before full ACMG classification, check if the variant already has an expert panel classification in ClinVar. Use `MyVariant_query_variants` with the rsID or HGVS notation — the `clinvar` field in the response includes clinical significance, review status, and RCV records. If an expert panel has already classified the variant as Pathogenic or Benign, note this prominently and focus on confirming/contextualizing rather than de novo classification.

## Phase 3: Computational Predictions

**Primary approach:** `MyVariant_query_variants` with `fields=dbnsfp,clinvar,cadd,gnomad_genome` retrieves 15+ predictor scores (SIFT, PolyPhen, CADD, REVEL, AlphaMissense, MetaRNN, FATHMM, GERP, PhyloP, etc.) in a single call. This is usually sufficient.

**REVEL/AlphaMissense fallback**: If `MyVariant_query_variants` returns no `dbnsfp` block, use the dedicated tool:
1. **`MyVariant_get_pathogenicity_scores`** (PREFERRED FALLBACK) — returns REVEL, AlphaMissense, SIFT, PolyPhen2, MetaRNN, GERP, PhyloP, and more in a single call with pre-configured dbnsfp fields. Input: `variant_id` (rsID or HGVS genomic).
2. `CADD_get_variant_score` (PHRED 0-99) — works for most variants
3. `AlphaMissense_get_variant_score` (0-1, needs UniProt ID) — missense only
4. `EVE_get_variant_score` (0-1) — missense only
5. `EnsemblVEP_annotate_hgvs` (VEP with colocated variants) — includes SIFT/PolyPhen
6. If REVEL is still unavailable, note this as a limitation and rely on CADD + SIFT + PolyPhen consensus. REVEL absence does not prevent classification.

Do not assign PP3/BP4 by local predictor voting. For missense variants, route predictor evidence through `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement`, which follows Pejaver et al. 2022 calibrated thresholds and selects one calibrated predictor before inspecting scores. CADD, AlphaMissense, EVE, SIFT, PolyPhen, REVEL, and other scores can still be retrieved here, but the evidence strength is assigned by the PP3/BP4 overlay or by a current VCEP rule.

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
- `catalytic` / `ligand-binding` / `ptm` lost → mechanistic support for PP3
- `secondary-structure` / `structural-stability` gained on a stable WT region → mechanistic basis for "destabilizing" claim
- No interpretable change at top-K → does not weaken AlphaMissense alone, but flag for caution

**When you have a saturation question** (e.g. "score all 19 substitutions at residue 600 to find the most disruptive"): use `ESM_score_variant_sae_batch` — 1 Forge call for the reference + 1 per variant, instead of 2 per variant.

**When the region is what matters** (e.g. "what's the SAE signature of the kinase activation loop, residues 754-771"): use `ESM_get_region_sae_features` then `ESM_describe_sae_feature` on the top hits.

**Requires**: `ESM_API_KEY` env var (free non-commercial token at https://forge.evolutionaryscale.ai) and `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` (SAE support is on an unmerged feature branch — PyPI esm 3.2.x does NOT include SAEConfig). License: EvolutionaryScale Cambrian Inference License — non-commercial use only.

## Phase 4.5: Expression Context

Tools: `CELLxGENE_get_expression_data`, `CELLxGENE_get_cell_metadata`, `GTEx_get_median_gene_expression`

Confirms gene expression in disease-relevant tissues. This can contextualize disease relevance, but it does not by itself satisfy PP4. PP4 and other phenotype-dependent criteria require patient phenotype or affected-status information; use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when phenotype specificity, diagnostic yield, tested/excluded loci, segregation, case enrichment, PM3 affected-proband context, BP5, BS2, or PS2/PM6 phenotype consistency is being considered. When PP4 interacts with PP1/BS4, route to `tooluniverse-acmg-pp1-segregation-refinement` for ClinGen 2024 combined PP1/BS4/PP4 points and the +5.0 cap. Use `tooluniverse-acmg-ba1-exception-list-refinement` before applying BA1 from AF >0.05. Use `tooluniverse-acmg-benign-context-refinement` when BA1/BS1/BS2/BP2/BP5 depends on disease threshold, unaffected status, phase, or alternate-diagnosis context.

## Phase 5: Literature Evidence

Tools: `PubMed_search_articles`, `EuropePMC_search_articles`, `BioRxiv_list_recent_preprints`, `MedRxiv_get_preprint`, `openalex_search_works`, `SemanticScholar_search_papers`

Always flag preprints as NOT peer-reviewed.

## Phase 6: ACMG Classification

Apply all relevant evidence codes (PVS1, PS1, PS3, PS4, PM1, PM2, PM4, PM5, PP3 for pathogenic; BA1, BS1, BS2, BS3, BP2, BP3, BP4, BP5, BP7 for benign). Use `tooluniverse-acmg-variant-classification` as the primary ACMG workflow and `tooluniverse-acmg-overlay-routing-core` to coordinate context overlays before evidence-specific overlays. The routing core standardizes the order: multiple-disorder context, mechanism context, clinical-context intake, source/literature intake, then criterion-specific scoring. Use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` when a secondary source assertion is encountered; PP5/BP6 are not counted by default. See `ACMG_CLASSIFICATION.md` for the complete algorithm.

### Gene-Specific Population Frequency Thresholds

BA1 stand-alone benign evidence requires Ghosh 2018 exception-list review before use. BS1 (allele frequency too high for disorder) requires disease-specific calibration, not a universal cutoff. Use `tooluniverse-acmg-benign-context-refinement` when prevalence, penetrance, allelic/genetic heterogeneity, inheritance, or ancestry-specific max AF affects BA1/BS1:
- **High-penetrance genes** (BRCA1, TP53): BS1 threshold ~0.0001
- **Moderate-penetrance genes** (PALB2, ATM, CHEK2): BS1 threshold ~0.001
- **Low-penetrance/common disease genes**: BS1 threshold higher, depends on disease prevalence
- **Formula**: BS1 threshold = (disease prevalence × max allelic contribution × max genetic contribution) / penetrance
- When in doubt, compare the variant's AF to the highest AF of any known pathogenic variant in the same gene — if it exceeds that, BS1 is likely applicable.

### Handling Conflicting Evidence: Functional vs Epidemiological

This is one of the most challenging scenarios in variant interpretation. When a biochemical assay shows damage but population/epidemiological data shows no disease association:

1. **Epidemiological data generally trumps in-vitro assays** for clinical classification. A variant found at ~0.1% frequency with no disease association in 40K+ cases is unlikely to be clinically significant, even if it reduces protein function in a tube.
2. **Apply PS3/BS3 carefully**: ClinGen's SVI recommends that PS3 (functional evidence for pathogenicity) requires the assay to be validated against known pathogenic AND known benign controls. A single biochemical study without such validation is PS3_Supporting at best.
3. **Hypomorphic variants**: Some variants genuinely reduce protein function (detectable in sensitive assays) but not enough to cause disease. This is biologically real and does not make them pathogenic.
4. **Document the conflict explicitly** in the report. State: "Biochemical assay X shows [result], but case-control study Y with N cases found no significant disease association. Per ACMG guidelines, the epidemiological evidence is weighted more heavily for clinical classification."

### Classification Combiner

Do not calculate the final ACMG classification inside this variant-interpretation skill. After Phases 1-5 retrieve and summarize the evidence, route final evidence assignment and classification to `tooluniverse-acmg-variant-classification`. That workflow applies the routing core, evidence-specific overlays, VCEP precedence, source-assertion handling, double-counting safeguards, and final classification logic.

### Gene-Specific VCEP Criteria

ClinGen Variant Curation Expert Panels (VCEPs) publish gene-specific ACMG modifications. Before classifying, check if a VCEP exists:
- `ClinGen_search_gene_validity(gene="<gene_symbol>")` — if validity is "Definitive" or "Strong", a VCEP likely exists
- Common VCEPs: BRCA1/2 (Enigma), TP53, PTEN, CDH1, PALB2, RASopathies, Lynch syndrome genes
- VCEP criteria override generic ACMG criteria (e.g., PALB2 VCEP has specific PM1 hotspot regions)

### Predictor Weighting

Not all computational predictors are equal. For missense variants:
- **REVEL** (AUC ~0.95) — best single meta-predictor; weight highest
- **AlphaMissense** (AUC ~0.94) — strong, structure-aware
- **CADD** (AUC ~0.85) — good for all variant types, but less specific for missense
- **SIFT/PolyPhen** (AUC ~0.80) — legacy tools; useful for consensus but not individually decisive

When predictors disagree, record the discordance and route the predictor set to `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or a current VCEP rule. Do not create PP3/BP4 from uncalibrated predictor consensus inside this skill.

### Tool Failure Fallbacks

If a primary tool fails, use these alternatives:
- **ClinVar_search_variants returns 0 results**: Use `MyVariant_query_variants` with rsID or HGVS — the `clinvar` field in MyVariant is more reliable for variant lookup than NCBI Entrez search
- **gnomad_search_variants fails**: Use `EnsemblVEP_annotate_hgvs` which includes gnomAD frequency via colocated variants
- **CADD_get_variant_score fails**: CADD PHRED is also available in the `dbnsfp` block from MyVariant
- **AlphaFold prediction unavailable** (large proteins >2700aa): Use `PDBe_get_uniprot_mappings` for experimental structures

---

## Special Scenarios

**Novel Missense VUS**: Check PM5 (other pathogenic at same residue), get AlphaFold2 structure, apply PM1/PP3 as appropriate.

**Truncating Variant**: Use `tooluniverse-acmg-overlay-routing-core` first when disease boundary or mechanism is unclear. Then route PVS1 through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` before assigning strength. If RNA assay or Walker 2023 splicing-specific evidence is present, apply `tooluniverse-acmg-pvs1-splicing-refinement` after the baseline LoF branch is identified.

**Splice Variant**: Run SpliceAI, assess canonical splice distance, in-frame skipping potential, and route the result to the relevant splicing overlay. Prediction-only evidence remains separate from RNA assay evidence; use `tooluniverse-acmg-pvs1-splicing-refinement` only when RNA/splicing evidence affects PVS1 or BP7, and use `tooluniverse-acmg-ps1-splicing-similarity-refinement` only for independent comparison-variant evidence.

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
