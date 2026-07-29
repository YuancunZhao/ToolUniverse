# Clinical Variant Interpreter - Tool Reference

## Core Annotation Tools

### MyVariant.info - Aggregated Annotations

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `MyVariant_query_variants` | Query variant annotations | `variant_id`, `fields` |

**Example - Query variant**:
```python
result = tu.tools.MyVariant_query_variants(
    variant_id="chr17:g.7674220C>T",
    fields="clinvar,gnomad,cadd,dbnsfp"
)
# Returns: ClinVar, gnomAD, CADD, dbNSFP predictions
```

**Key Fields**:
| Field | Contains |
|-------|----------|
| `clinvar` | Classification, review status |
| `gnomad` | Allele frequencies |
| `cadd` | CADD scores |
| `dbnsfp` | SIFT, PolyPhen, REVEL, etc. |

---

### ClinVar - Clinical Classifications

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinVar_search_variants` | Search by variant | `variant`, `gene` |
| `ClinVar_get_variant_details` | Get by VCV ID | `variation_id` |

**Example - Search ClinVar**:
```python
result = tu.tools.ClinVar_search_variants(
    variant="NM_007294.4:c.5266dupC"
)
# Returns: VCV ID, classification, review status, submitters
```

Preserve review status, submitter count, dates, conditions, and the submitted
classification as source assertions. Do not map stars or labels to an ACMG
criterion.

---

### VariantValidator - MANE Transcript Lookup & Variant Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `VariantValidator_gene2transcripts` | Get MANE Select/Plus Clinical transcripts for a gene | `gene_symbol`, `transcript_set`, `genome_build` |
| `VariantValidator_validate_variant` | Validate and normalize HGVS variant descriptions | `genome_build`, `variant_description`, `select_transcripts` |

**Example - Get MANE transcript**:
```python
result = tu.tools.VariantValidator_gene2transcripts(
    gene_symbol="TP53", transcript_set="mane", genome_build="GRCh38"
)
# Returns: [{current_symbol: "TP53", transcripts: [{reference: "NM_000546.6",
#   annotations: {mane_select: true, mane_plus_clinical: false}}]}]
```

**Example - Validate variant**:
```python
result = tu.tools.VariantValidator_validate_variant(
    genome_build="GRCh38",
    variant_description="NM_007294.4:c.5266dup",
    select_transcripts="NM_007294.4"
)
# Returns: validated HGVS, protein consequence, genomic coordinates, gene IDs
```

**When to use**:
- Phase 1: Always use `gene2transcripts` to identify the MANE Select transcript before annotating variants
- Phase 1: Use `validate_variant` to normalize user-provided HGVS notation and get cross-genome-build coordinates
- Prefer MANE Select transcript for canonical annotation; fall back to MANE Plus Clinical if relevant

---

### gnomAD - Population Frequencies

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `gnomad_search_variants` | Get allele frequencies | `variant`, `dataset` |

**Example - Query gnomAD**:
```python
result = tu.tools.gnomad_search_variants(
    variant="17-7674220-C-T"
)
# Returns: AF, ancestry-specific AFs, AC, AN, homozygotes
```

Report AC, AN, AF, homozygotes, ancestry frequencies, dataset, build, and
callset. Obtain callability separately with `gnomad_get_site_callability` and
send both facts to `ACMG_population_evidence`; do not apply frequency cutoffs in
the agent.

**Ancestry-Specific Populations**:
| Code | Population |
|------|------------|
| nfe | European (Non-Finnish) |
| fin | Finnish |
| afr | African/African American |
| amr | Latino/Admixed American |
| eas | East Asian |
| sas | South Asian |
| asj | Ashkenazi Jewish |

---

## ClinGen - Gene Validity & Dosage Sensitivity (NEW)

Authoritative curation of gene-disease relationships from ClinGen.

When disease context, mechanism, clinical context, source assertions, or literature extraction affects ACMG evidence assignment, use `ACMG_evidence_collector` for the current evidence-only workflow. Gene-disease validity and dosage sensitivity are separate evidence types: definitive gene-disease validity does not automatically establish haploinsufficiency/triplosensitivity, and a non-sufficient dosage score does not refute recessive, gain-of-function, dominant-negative, or other non-dosage disease mechanisms.

### Gene Validity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_gene_validity` | Search validity by gene | `gene` |
| `ClinGen_get_gene_validity` | Get all validity curations | `gene` (optional filter) |

**Example - Check gene-disease validity**:
```python
result = tu.tools.ClinGen_search_gene_validity(gene="BRCA1")
# Returns: Classification (Definitive/Strong/Moderate/Limited), disease, inheritance
```

Preserve the validity classification, disease, inheritance, curation date, and
provenance as gene-disease context. It does not establish PP4 or imply that a
VCEP/CSpec exists.

### Dosage Sensitivity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_dosage_sensitivity` | HI/TS scores by gene | `gene` |
| `ClinGen_get_dosage_sensitivity` | All dosage curations | `gene`, `include_regions` |

**Example - Check haploinsufficiency**:
```python
result = tu.tools.ClinGen_search_dosage_sensitivity(gene="MECP2")
# Returns: Haploinsufficiency Score (0-3), Triplosensitivity Score (0-3)
```

**Dosage Score Interpretation** (for CNVs):
| Score | Meaning | Usage |
|-------|---------|-------|
| **3** | Sufficient evidence | HI/TS established - PVS1 for LOF CNVs |
| **2** | Emerging evidence | Some support |
| **1** | Little evidence | Minimal support |
| **0/40** | No evidence / Dosage unlikely | Unknown or unlikely dosage effect |

### Clinical Actionability

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_actionability` | Actionability by gene (both contexts) | `gene` |
| `ClinGen_get_actionability_adult` | Adult actionability | `gene` (optional) |
| `ClinGen_get_actionability_pediatric` | Pediatric actionability | `gene` (optional) |

Gene validity, dosage sensitivity, and actionability are distinct context
records. Preserve their own curation labels and provenance; none directly
creates a germline EvidenceCard in this skill.

---

## SpliceAI - Splice Variant Prediction (NEW)

Deep learning model for predicting splice-altering effects.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SpliceAI_predict_splice` | Full splice prediction | `variant`, `genome`, `distance`, `mask` |
| `SpliceAI_get_max_delta` | Quick max score | `variant`, `genome` |
| `SpliceAI_predict_pangolin` | Pangolin model (alternative) | `variant`, `genome` |

**Example - Predict splice effect**:
```python
# Full prediction
result = tu.tools.SpliceAI_predict_splice(
    variant="chr17-41276045-A-G",
    genome="38"
)
# Returns: DS_AG, DS_AL, DS_DG, DS_DL scores, max_delta_score, interpretation

# Quick triage
quick = tu.tools.SpliceAI_get_max_delta(
    variant="chr17-41276045-A-G"
)
# Returns: max_delta_score, interpretation
```

**Variant Format**: `chr{chrom}-{pos}-{ref}-{alt}` or `{chrom}:{pos}:{ref}:{alt}`

**Delta Score Types**:
| Score | Meaning |
|-------|---------|
| DS_AG | Acceptor Gain (creates new acceptor) |
| DS_AL | Acceptor Loss (disrupts existing) |
| DS_DG | Donor Gain (creates new donor) |
| DS_DL | Donor Loss (disrupts existing) |

Preserve all four delta scores and positions, model/annotation versions,
transcript, gene, run settings, and input coordinates. The collector explicitly
uses raw, unmasked distance-500 scores and binds one row to the verified MANE
Select context. Under the general Walker rule, max delta >=0.2 is
PP3_Supporting and <=0.1 is BP4_Supporting; missing run provenance is
`not_assessed`. After strict BP4, synonymous variants or intronic variants
outside +7/-21 may also suggest BP7_Supporting. Direct RNA-splicing readouts do
not enter PS3/BS3.

**When to Use**:
- Intronic variants within ±50bp of splice sites
- Synonymous/missense variants (may still affect splicing)
- Deep intronic variants creating cryptic splice sites
- Validation when functional studies suggest splice defect

---

## Pathogenicity Prediction Tools (NEW)

### CADD - Combined Annotation Dependent Depletion (NEW API)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CADD_get_variant_score` | Get PHRED score for variant | `chrom`, `pos`, `ref`, `alt`, `version` |
| `CADD_get_position_scores` | All substitutions at position | `chrom`, `pos` |
| `CADD_get_range_scores` | Scores in genomic range (max 100bp) | `chrom`, `start`, `end` |

**Example - Score a variant**:
```python
result = tu.tools.CADD_get_variant_score(
    chrom="17",
    pos=7674220,
    ref="G",
    alt="A",
    version="GRCh38-v1.7"  # Options: GRCh38-v1.7, GRCh37-v1.7
)
# Returns: phred_score, raw_score, interpretation
```

Preserve PHRED/raw scores, version, and input coordinates as audit context.
CADD does not substitute for the executable computational rule contract.

---

### AlphaMissense - DeepMind Pathogenicity Prediction (NEW)

State-of-the-art deep learning model for missense pathogenicity prediction.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `AlphaMissense_get_variant_score` | Score specific variant | `uniprot_id`, `variant` |
| `AlphaMissense_get_residue_scores` | All substitutions at position | `uniprot_id`, `position` |

**Example - Get pathogenicity score**:
```python
result = tu.tools.AlphaMissense_get_variant_score(
    uniprot_id="P00533",  # EGFR
    variant="L858R"  # or "p.L858R"
)
# Returns: pathogenicity_score, classification
```

Preserve the score, provider classification, model version, protein accession,
and amino-acid input as audit context. AlphaMissense does not substitute for
the executable computational rule contract.

---

### ESMC-6B SAE - Mechanism of Effect (for VUS missense)

AlphaMissense and ESMC-6B outputs are prediction and mechanism context. Preserve
their raw outputs to investigate a variant, but do not convert them directly to
an ACMG criterion.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ESM_explain_variant_mechanism` | One-call mechanism (disruption + feature labels + summary) | `sequence`, `position`, `ref_aa`, `alt_aa`, `top_k_features` |
| `ESM_score_variant_sae_disruption` | Single variant — top features lost/gained, no labels | `sequence`, `position`, `ref_aa`, `alt_aa` |
| `ESM_score_variant_sae_batch` | Multiple variants on same protein, N+1 Forge calls instead of 2N | `sequence`, `variants` (list) |
| `ESM_get_region_sae_features` | Aggregate features over a residue range (domain, motif) | `sequence`, `start_position`, `end_position` |
| `ESM_describe_sae_feature` | Label a feature_id by biological category | `feature_id` |

**Example — One-call mechanism for a VUS**:
```python
result = tu.tools.ESM_explain_variant_mechanism(
    sequence=wt_aa_sequence,
    position=600, ref_aa="V", alt_aa="E",
    top_k_features=5,
)
# result["data"]["mechanism_summary"] e.g.:
#   "Disrupted feature categories (lost): catalytic=2, ligand-binding=1"
```

**Example — Saturation at one position (all 19 alternates)**:
```python
from itertools import product
alts = "ACDEFGHIKLMNPQRSTVWY".replace(wt_residue, "")
variants = [{"position": 600, "ref_aa": "V", "alt_aa": a} for a in alts]
result = tu.tools.ESM_score_variant_sae_batch(
    sequence=wt_aa_sequence, variants=variants, top_k_features=5,
)
# Forge cost: 20 calls (1 ref + 19 mut), not 38 (2 per variant)
```

**Mapping SAE categories to mechanism narrative**:
| SAE category lost | Mechanistic claim | Evidence use |
|---|---|---|
| `catalytic` | Active-site disruption | Mechanism narrative; route any evidence-code use to the relevant overlay |
| `ligand-binding` | Substrate/cofactor binding loss | Mechanism narrative only |
| `ptm` | Post-translational modification site | Mechanism narrative only |
| `domain` / `motif` | Domain integrity loss | Mechanism narrative only |
| `structural-stability` | Disulfide / coiled-coil disruption | Mechanism narrative only |
| `transmembrane` / `signal-peptide` | Targeting / membrane integration | Mechanism narrative only |
| (no interpretable change) | No mechanistic signal | Do not change predictor evidence strength |

**Requires**: `ESM_API_KEY` (free non-commercial token at https://forge.evolutionaryscale.ai) and `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` (PyPI esm 3.2.x lacks SAEConfig). Outputs governed by EvolutionaryScale Cambrian Inference License — non-commercial use only.

---

### EVE - Evolutionary Variant Effect (NEW)

Unsupervised deep learning model using evolutionary data (Harvard/Oxford).

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EVE_get_variant_score` | Get EVE score via VEP | `chrom`, `pos`, `ref`, `alt` OR `variant` (HGVS) |
| `EVE_get_gene_info` | Check if gene has EVE coverage | `gene_symbol` |

**Example - Score variant**:
```python
# Via genomic coordinates
result = tu.tools.EVE_get_variant_score(
    chrom="17",
    pos=7674220,
    ref="C",
    alt="T"
)

# Or via HGVS
result = tu.tools.EVE_get_variant_score(
    variant="ENST00000269305.4:c.100G>A"
)
# Returns: eve_score, classification, gene, polyphen/sift from VEP
```

Record the score, model version, transcript, input coordinates, and provider
classification exactly as returned. EVE does not have a rule contract in the
current collector and cannot substitute for REVEL or SpliceAI evidence.

---

### Integrating Prediction Tools

**Best Practice for VUS Prediction Retrieval**:

```python
def get_predictor_audit_context(tu, variant_info):
    """
    Retrieve multiple predictors for orientation.
    Do not assign PP3/BP4 here; route to the calibrated overlay or VCEP.
    """
    scores = []

    # 1. CADD (all variants)
    cadd = tu.tools.CADD_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt']
    )
    if cadd.get('status') == 'success':
        scores.append({
            'tool': 'CADD',
            'score': cadd['data']['phred_score'],
            'provider_result': cadd['data']
        })

    # 2. AlphaMissense (missense only)
    if variant_info.get('uniprot_id') and variant_info.get('aa_change'):
        am = tu.tools.AlphaMissense_get_variant_score(
            uniprot_id=variant_info['uniprot_id'],
            variant=variant_info['aa_change']
        )
        if am.get('status') == 'success' and am.get('data'):
            scores.append({
                'tool': 'AlphaMissense',
                'score': am['data'].get('pathogenicity_score'),
                'provider_classification': am['data'].get('classification'),
                'provider_result': am['data']
            })

    # 3. EVE (via VEP)
    eve = tu.tools.EVE_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt']
    )
    if eve.get('status') == 'success':
        eve_scores = eve['data'].get('eve_scores', [])
        if eve_scores:
            scores.append({
                'tool': 'EVE',
                'score': eve_scores[0].get('eve_score'),
                'provider_result': eve_scores[0]
            })

    return {
        'prediction_context': scores,
        'candidate_route': 'ACMG_computational_evidence',
        'route_status': 'audit_only_no_predictor_voting'
    }
```

---

## Somatic & Disease Association Tools (NEW)

### COSMIC - Somatic Cancer Mutations

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `COSMIC_search_mutations` | Search mutations | `operation="search"`, `terms`, `max_results` |
| `COSMIC_get_mutations_by_gene` | Gene mutations | `operation="get_by_gene"`, `gene`, `genome_build` |

**Example - Check if variant is somatic hotspot**:
```python
# Search for specific mutation
result = tu.tools.COSMIC_search_mutations(
    operation="search",
    terms="BRAF V600E",
    max_results=20
)
# Returns: mutation_id, cancer types, frequency

# Get all mutations for gene (hotspot analysis)
gene_muts = tu.tools.COSMIC_get_mutations_by_gene(
    operation="get_by_gene",
    gene="BRAF",
    max_results=200
)
# Returns: All mutations with cancer type distribution
```

**COSMIC Context for Variant Interpretation**:
| Finding | Use | Application |
|---------|-----|-------------|
| Recurrent somatic hotspot | Cancer-context lead | Route tumor-specific interpretation to the cancer variant workflow; do not treat as germline PS3 |
| Frequent in COSMIC | Literature/domain lead | Use to guide literature review or PM1/domain context, then assess through the relevant overlay |
| Rare in COSMIC | Context only | Consider other evidence |

### OMIM - Mendelian Disease Context

**⚠️ Requires**: `OMIM_API_KEY` environment variable

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OMIM_search` | Search genes/diseases | `operation="search"`, `query`, `limit` |
| `OMIM_get_entry` | Detailed entry | `operation="get_entry"`, `mim_number` |
| `OMIM_get_clinical_synopsis` | Clinical features | `operation="get_clinical_synopsis"`, `mim_number` |
| `OMIM_get_gene_map` | Gene-disease map | `operation="get_gene_map"`, `mim_number` |

**Example - Get gene-disease context**:
```python
# Search for gene in OMIM
search = tu.tools.OMIM_search(
    operation="search",
    query="BRCA1",
    limit=5
)

# Get detailed entry with clinical info
entry = tu.tools.OMIM_get_entry(
    operation="get_entry",
    mim_number="113705"  # BRCA1
)

# Get clinical synopsis for phenotype matching
synopsis = tu.tools.OMIM_get_clinical_synopsis(
    operation="get_clinical_synopsis",
    mim_number="114480"  # Breast-ovarian cancer
)
```

**OMIM Entry Types**:
| Prefix | Type | Example |
|--------|------|---------|
| * | Gene | *113705 (BRCA1) |
| # | Phenotype with known gene | #114480 (BRCA1 cancer) |
| % | Phenotype, unknown molecular basis | Mapped locus only |
| + | Gene and phenotype combined | Historical entries |

### DisGeNET - Gene-Disease Associations

**⚠️ Requires**: `DISGENET_API_KEY` environment variable

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DisGeNET_search_gene` | Diseases for gene | `operation="search_gene"`, `gene`, `limit` |
| `DisGeNET_search_disease` | Genes for disease | `operation="search_disease"`, `disease` |
| `DisGeNET_get_gda` | Curated associations | `operation="get_gda"`, `gene`, `source`, `min_score` |
| `DisGeNET_get_vda` | Variant-disease | `operation="get_vda"`, `variant` or `gene` |

**Example - Get gene-disease evidence**:
```python
# Gene-disease associations
gda = tu.tools.DisGeNET_search_gene(
    operation="search_gene",
    gene="BRCA1",
    limit=20
)
# Returns: Associated diseases with scores

# High-confidence curated associations
curated = tu.tools.DisGeNET_get_gda(
    operation="get_gda",
    gene="BRCA1",
    source="CURATED",
    min_score=0.5
)

# Variant-disease associations
vda = tu.tools.DisGeNET_get_vda(
    operation="get_vda",
    gene="BRCA1",
    limit=30
)
```

**DisGeNET Score for Gene-Disease Background**:
| Score | Background context | ACMG route note |
|-------|--------------------|-----------------|
| >0.7 | Strong gene-disease context | Background only; PP4 still requires supplied phenotype and, when applicable, combined PP1/BS4/PP4 review |
| 0.4-0.7 | Moderate gene-disease context | Background only; do not count as ACMG evidence |
| <0.4 | Weak or literature-only context | Insufficient for variant-level ACMG evidence |

---

## Regulatory Context Tools (NEW)

### ChIPAtlas - Transcription Factor Binding

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChIPAtlas_enrichment_analysis` | TF binding enrichment | `gene`, `cell_type` |
| `ChIPAtlas_get_peak_data` | ChIP-seq peaks | `gene`, `experiment_type` |
| `ChIPAtlas_search_datasets` | Find experiments | `antigen`, `cell_type` |

**Example - Check TF binding at variant**:
```python
# Get TF binding near gene
tf_binding = tu.tools.ChIPAtlas_enrichment_analysis(
    gene="BRCA1",
    cell_type="all"
)
# Returns: TFs with binding peaks near gene

# Get specific peaks
peaks = tu.tools.ChIPAtlas_get_peak_data(
    gene="BRCA1",
    experiment_type="TF"
)
```

**Use for**: Non-coding variants that may disrupt TF binding sites

### ENCODE - Regulatory Elements

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ENCODE_search_experiments` | Find regulatory data | `assay_title`, `biosample` |
| `ENCODE_get_experiment` | Experiment details | `accession` |
| `ENCODE_get_biosample` | Sample annotations | `accession` |

**Example - Get regulatory annotations**:
```python
# Search for regulatory data near variant
experiments = tu.tools.ENCODE_search_experiments(
    assay_title="ATAC-seq",
    biosample="heart"
)
# Returns: Open chromatin experiments
```

**Key ENCODE Assays**:
| Assay | Purpose | Relevance |
|-------|---------|-----------|
| ATAC-seq | Open chromatin | Accessible regions |
| H3K27ac | Active enhancers | Regulatory activity |
| H3K4me3 | Active promoters | Promoter regions |
| CTCF | Insulator binding | Chromatin structure |

---

## Expression Context Tools (NEW)

### CELLxGENE - Single-Cell Expression

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CELLxGENE_get_expression_data` | Cell-type expression | `gene`, `tissue` |
| `CELLxGENE_get_cell_metadata` | Cell annotations | `gene` |

**Example - Validate tissue expression**:
```python
# Get expression in disease-relevant tissue
expression = tu.tools.CELLxGENE_get_expression_data(
    gene="FBN1",
    tissue="heart"
)
# Returns: Expression per cell type (cardiomyocytes, fibroblasts, etc.)
```

**Why use it**: Confirms gene is expressed in phenotype-relevant cells

---

## Literature Tools (ENHANCED)

### BioRxiv/MedRxiv - Preprints

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv/medRxiv) | `query`, `source='PPR'`, `pageSize` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi` |

**Example - Search preprints** (bioRxiv/medRxiv don't have search APIs, use EuropePMC):
```python
# Search for recent findings
preprints = tu.tools.EuropePMC_search_articles(
    query="BRCA1 variant functional",
    source="PPR",  # PPR = Preprints only
    pageSize=10
)
```

**⚠️ Important**: Always flag preprints as NOT peer-reviewed

### OpenAlex - Citation Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search with citations | `query`, `limit` |

**Example - Get citation counts**:
```python
# Get citation metrics for key paper
work = tu.tools.openalex_search_works(
    query="BRCA1 functional study pathogenic",
    limit=5
)
# Returns: Papers with cited_by_count, is_oa, etc.
```

### Semantic Scholar - AI-Ranked Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SemanticScholar_search_papers` | AI-ranked search | `query`, `limit` |

**Example**:
```python
papers = tu.tools.SemanticScholar_search_papers(
    query="BRCA1 c.5266dupC pathogenic",
    limit=15
)
```

---

### Ensembl - Variant Effect Predictor

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EnsemblVar_get_variant_consequences` | VEP annotations | `variant_id` |
| `ensembl_lookup_gene` | Gene details | `gene_id` |

**Example - Get VEP data**:
```python
result = tu.tools.EnsemblVar_get_variant_consequences(
    variant_id="rs28934576"
)
# Returns: Consequence, transcript, SIFT, PolyPhen
```

---

## Disease Association Tools

### OMIM - Gene-Disease Relationships

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OMIM_search` | Search by gene/disease | `query` |
| `OMIM_get_entry` | Get MIM entry | `mim_number` |

**Example - Get OMIM associations**:
```python
result = tu.tools.OMIM_search(query="BRCA1")
# Returns: MIM#, gene-phenotype relationships, inheritance
```

---

### ClinGen - Gene Validity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_gene_validity` | Get curation status | `gene` |
| `ClinGen_dosage` | Dosage sensitivity | `gene` |

**Gene Validity Levels**:
| Level | Meaning |
|-------|---------|
| Definitive | Strong evidence, replicated |
| Strong | Considerable evidence |
| Moderate | Some evidence |
| Limited | Minimal evidence |
| Disputed | Conflicting evidence |
| Refuted | Evidence against |

---

## Structural Analysis Tools

### PDB - Experimental Structures

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PDBe_get_uniprot_mappings` | Find structures | `uniprot_id` |
| `RCSBData_get_entry` | Download PDB | `pdb_id` |

**Example - Get structure**:
```python
# Find PDB structures for TP53
hits = tu.tools.PDBe_get_uniprot_mappings(uniprot_id="P04637")
if hits:
    structure = tu.tools.PDB_get_structure(pdb_id=hits[0]['pdb_id'])
```

### AlphaFold - Predicted Structures

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `alphafold_get_prediction` | Get AF DB prediction | `accession` |
| `NvidiaNIM_alphafold2` | Predict de novo | `sequence`, `algorithm` |

**Example - Get AlphaFold structure**:
```python
# From AlphaFold DB
structure = tu.tools.alphafold_get_prediction(accession="P04637")

# Or predict de novo
structure = tu.tools.NvidiaNIM_alphafold2(
    sequence=protein_sequence,
    algorithm="mmseqs2"
)
```

**pLDDT Interpretation**:
| Score | Confidence | Use for Variant |
|-------|------------|-----------------|
| >90 | Very high | Reliable position assessment |
| 70-90 | High | Reliable |
| 50-70 | Moderate | Use with caution |
| <50 | Low | Likely disordered |

---

### Domain/Function Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `InterPro_get_protein_domains` | Domain annotations | `accession` |
| `UniProt_get_function_by_accession` | Functional sites | `accession` |

**Example - Get domains**:
```python
domains = tu.tools.InterPro_get_protein_domains(accession="P04637")
# Returns: Domain boundaries, types, functions
```

---

## Literature Tools

### PubMed - Literature Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `max_results` |
| `PubMed_get_article` | Get abstract | `pmid` |

**Example - Search for functional studies**:
```python
# Gene + variant search
result = tu.tools.PubMed_search_articles(
    query="BRCA1 AND c.5266dupC",
    max_results=10
)

# Functional studies
result = tu.tools.PubMed_search_articles(
    query="BRCA1 AND functional study",
    max_results=20
)
```

**Search Strategies**:
| Strategy | Query Pattern |
|----------|---------------|
| Specific variant | `"{GENE} AND ({HGVS} OR {legacy})"` |
| Functional | `"{GENE} AND (functional study OR mutagenesis)"` |
| Clinical | `"{GENE} AND case report AND {phenotype}"` |
| Review | `"{GENE} AND review[pt]"` |

---

## Workflow Code Examples

### Example 1: Complete Variant Annotation

```python
def annotate_variant(tu, variant_hgvs, gene):
    """Complete variant annotation workflow."""

    # Phase 1: Get aggregated annotations
    annotations = tu.tools.MyVariant_query_variants(
        variant_id=variant_hgvs,
        fields="clinvar,gnomad,cadd,dbnsfp"
    )

    # Phase 2: ClinVar detail
    clinvar = tu.tools.ClinVar_search_variants(variant=variant_hgvs)

    # Phase 3: Population frequency
    gnomad = tu.tools.gnomad_search_variants(variant=variant_hgvs)

    # Phase 4: Gene context
    omim = tu.tools.OMIM_search(query=gene)

    # Phase 5: Literature
    literature = tu.tools.PubMed_search_articles(
        query=f"{gene} AND {variant_hgvs}",
        max_results=20
    )

    return {
        'annotations': annotations,
        'clinvar': clinvar,
        'gnomad': gnomad,
        'omim': omim,
        'literature': literature
    }
```

### Example 2: Structural Analysis for VUS

```python
def structural_analysis_for_vus(tu, gene, genomic_hgvs, uniprot_id, residue_position):
    """Structural analysis for VUS missense variants."""

    # Try PDB first
    pdb_structures = tu.tools.PDBe_get_uniprot_mappings(uniprot_id=uniprot_id)

    if pdb_structures:
        # Use best resolution experimental structure
        best_pdb = sorted(pdb_structures, key=lambda x: x.get('resolution', 10))[0]
        structure = tu.tools.PDB_get_structure(pdb_id=best_pdb['pdb_id'])
        structure_source = f"PDB {best_pdb['pdb_id']}"
    else:
        # Fallback to AlphaFold
        structure = tu.tools.alphafold_get_prediction(accession=uniprot_id)
        structure_source = "AlphaFold DB"

    # Verify genomic-HGVS to protein mapping before using a caller-provided accession.
    protein_mapping = tu.tools.EBIProteins_get_variation_by_hgvs(hgvs=genomic_hgvs)

    # EBI features carry exact ranges; InterPro is a coordinate-free inventory here.
    domains = tu.tools.EBIProteins_get_features(
        accession=uniprot_id, category="DOMAINS_AND_SITES"
    )
    interpro_inventory = tu.tools.InterPro_get_entries_for_protein(
        accession=uniprot_id
    )

    # Get functional sites
    functions = tu.tools.UniProt_get_function_by_accession(accession=uniprot_id)

    # Analyze residue context
    analysis = {
        'structure_source': structure_source,
        'domains': identify_domain(domains, residue_position),
        'protein_mapping': protein_mapping,
        'interpro_inventory': interpro_inventory,
        'functional_sites': find_nearby_sites(functions, residue_position),
        # Generic domain context remains indeterminate. Only the collector can
        # match it to an exact online-bound CSpec PM1 region contract.
        'pm1_domain_context_only': True
    }

    return analysis
```

### Example 3: ACMG Classification

Do not use a local helper function to calculate a final ACMG classification from evidence-code counts. Route evidence intake and deterministic criterion review through `ACMG_evidence_collector`; the current runtime reports compatibility and Bayesian review estimates but does not emit a five-tier classification.

---

## Fallback Chains

### Variant Annotations
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `MyVariant_query_variants` | `ClinVar_search_variants` + `gnomad_search_variants` | Direct database queries |

### Structure
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PDBe_get_uniprot_mappings` | `alphafold_get_prediction` | `NvidiaNIM_alphafold2` |

### Gene Information
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `OMIM_search` | `NCBIGene_search` | `ensembl_lookup_gene` |

### Literature
| Primary | Fallback 1 |
|---------|------------|
| `PubMed_search_articles` | `EuropePMC_search_articles` |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `MyVariant_query_variants` | `id="rs123"` | `variant_id="rs123"` |
| `ClinVar_search_variants` | `gene="BRCA1:c.123"` | `variant="NM_007294.4:c.123A>G"` |
| `gnomad_search_variants` | `variant="c.123A>G"` | `variant="17-41245466-A-G"` |
| `alphafold_get_prediction` | `uniprot="P04637"` | `accession="P04637"` |

---

## ACMG Route Quick Reference

This is a route index, not an evidence-strength table. Use
`ACMG_evidence_collector` for evidence intake, compatibility review, route
audit, Evidence Compatibility Resolution, and Bayesian review estimation.

### Pathogenic/Context Candidate Routes
| Candidate | Trigger | Required route |
|------|----------|---------|
| PVS1 | Predicted LoF, canonical splice, start-loss, exon deletion/duplication, or whole-gene deletion | Collector route context only; remains `not_assessed` until the complete ClinGen decision contract is available |
| PS1/PM5 | Same amino acid or same residue comparison variant | `ACMG_evidence_collector`; source labels are leads only |
| PS1-splicing | Same predicted splice event as an independent P/LP comparison variant | `ACMG_evidence_collector` |
| PS2/PM6 | De novo or trio evidence | `ACMG_clinical_evidence` |
| PS3/BS3 | Functional assay or structured functional database hit | `ACMG_functional_evidence` |
| PS4 | Case-control, cohort, meta-analysis, or affected-case enrichment evidence | `ACMG_literature_evidence` |
| PM1 | Hotspot or critical functional region | Collector uses `EBIProteins_get_variation_by_hgvs`, `EBIProteins_get_features`, and `InterPro_get_entries_for_protein`; generic overlap is `indeterminate`, exact reviewed CSpec contract may produce a candidate |
| PP2/BP1 | Regional missense constraint or missense mechanism context | Collector route context only; no current automatic count |
| PM2 | Absent or rare population frequency | `ACMG_population_evidence`; review-only without a validated coverage contract |
| PM3 | Recessive biallelic, in-trans, phase-unknown, or homozygous evidence | `ACMG_clinical_evidence` |
| PM4/BP3 | In-frame indel, stop-loss, altered product, repeat/low-complexity region | Collector route context only; no current automatic count |
| PP1/BS4/PP4 | Segregation, non-segregation, family, pedigree, phenotype-locus evidence | `ACMG_clinical_evidence` and phenotype-dependent intake when needed |
| PP3/BP4 | Computational prediction evidence | `ACMG_computational_evidence` or VCEP; no local predictor voting |
| PP5/BP6 | Reputable-source assertion | `ACMG_evidence_collector`; deprecated and excluded from system preview |

### Benign/Frequency Candidate Routes
| Candidate | Trigger | Required route |
|------|----------|---------|
| BA1 | AF >0.05 candidate or stand-alone benign frequency claim | `ACMG_population_evidence` before benign classification |
| BS1/BS2/BP2/BP5 | High disease-specific frequency, healthy carriers, cis/trans context, or alternate diagnosis | `ACMG_population_evidence`; route/review-only until the matching contract exists |
| RNA no-splicing-impact evidence | Synonymous/intronic variant with direct RNA or appropriate splicing no-impact evidence | Collector route context only; prediction-only scores remain non-countable context |
| Evidence compatibility | Counted EvidenceCards | Collector compatibility resolver removes duplicate and correlated evidence before Bayesian review; no final classifier is emitted |

---

## Computational Prediction Review

Preserve every available score, model version, transcript, coordinate, and
provider interpretation. `ACMG_computational_evidence` applies the versioned
Pejaver REVEL contract for missense variants and the separate Walker SpliceAI
contract for eligible non-canonical splice variants. Do not reproduce the
thresholds in agent instructions or infer evidence from another provider's
label. Other predictors remain transparent audit and disagreement context.

### Prediction Evidence Routing
| Prediction pattern | ACMG application |
|---------------------|------------------|
| Multiple provider outputs | Preserve every score and route to `ACMG_computational_evidence` |
| Provider disagreement | Record discordance; do not resolve by voting or selecting the favorable score |
| Required calibrated score absent | Return the data gap; do not substitute another predictor |

---

## Rate Limits

| Tool | Limit |
|------|-------|
| NVIDIA NIM tools | 40 RPM |
| PubMed | 3 requests/second |
| Ensembl | 15 requests/second |

Handle with appropriate delays between calls.
