# Clinical Variant Interpreter - Material-Collection Examples

These are FIXED material-collection examples: the variant data, query
methods, raw scores, and attributed external database classifications
are illustrative and must not be read as current database query
results. They deliberately contain no evidence scoring tables,
combination rules, final classifications, star confidences, or
upgrade rules -- classification happens only through the unified ACMG
skill and its calculator.

## Example 1: BRCA1 c.5266dupC — Material Collection

### User Query
"Interpret the clinical significance of BRCA1 c.5266dupC"

### Expected Output

```markdown
# Variant Interpretation Report: BRCA1 c.5266dupC

**Generated**: 2026-02-04 | **Analyst**: ToolUniverse Variant Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_007294.4:c.5266dupC (p.Gln1756ProfsTer74) |
| **Gene** | BRCA1 |
| **External classifications (attributed)** | ClinVar/ENIGMA: Pathogenic (see section 3) |
| **Key Finding** | Frameshift variant in a LoF-established gene; collected material below |

(Management decisions follow the unified classification flow, not this example.)

---

## 1. Variant Identity

| Property | Value |
|----------|-------|
| Gene | BRCA1 |
| Chromosome | 17 |
| Position | 17:43057051 (GRCh38) |
| Transcript | NM_007294.4 (MANE Select) |
| cDNA change | c.5266dupC |
| Protein change | p.Gln1756ProfsTer74 |
| Consequence | Frameshift |
| Exon | 20 of 23 |

**Note**: Also known as 5382insC (legacy notation)

*Source: `EnsemblVar_get_variant_consequences`, `MyVariant_query_variants`*

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency | Allele Count |
|------------|------------------|--------------|
| **Overall** | 0.00006 | 45 |
| European (Non-Finnish) | 0.00012 | 38 |
| Ashkenazi Jewish | 0.011 | 89 |
| African/African American | 0.00001 | 2 |
| Latino/Admixed American | 0.00002 | 3 |
| East Asian | 0 | 0 |
| South Asian | 0 | 0 |

**Homozygotes**: 0
**Hemizygotes**: N/A (autosomal gene)

**Interpretation**: Elevated in Ashkenazi Jewish population (founder variant). Overall frequency consistent with disease prevalence when accounting for reduced penetrance and carrier frequency.

*Source: `gnomad_search_variants`, accessed 2026-02-04*

---

## 3. Clinical Database Evidence

### ClinVar

| Property | Value |
|----------|-------|
| VCV ID | VCV000017661 |
| Classification | Pathogenic |
| Review Status | ★★★★ (Expert panel reviewed) |
| Submitters | 47 |
| Last Evaluated | 2024-12-15 |
| Conditions | Hereditary breast/ovarian cancer syndrome |

**Expert Panel**: ENIGMA consortium - criteria met for Pathogenic

### OMIM

| Gene-Disease | Inheritance | MIM# |
|--------------|-------------|------|
| Breast-ovarian cancer, familial 1 | AD | 604370 |
| Fanconi anemia, complementation group S | AR | 617883 |

### ClinGen

| Assessment | Status |
|------------|--------|
| Gene-Disease Validity | DEFINITIVE for HBOC |
| Dosage Sensitivity | Haploinsufficient |
| LOF Mechanism | Established |

*Sources: ClinVar VCV000017661, OMIM #113705, ClinGen*

---

## 4. Computational Predictions

**Note**: Computational predictors not applicable to frameshift variants (by definition, these are loss-of-function).

| Predictor | Score | Not Applicable Reason |
|-----------|-------|----------------------|
| SIFT | N/A | Frameshift |
| PolyPhen-2 | N/A | Frameshift |
| CADD | 35 (Phred) | High deleteriousness |

**NMD Prediction**: Predicted to undergo nonsense-mediated decay (PTC at codon 1829, well before last exon junction)

*Source: `MyVariant_query_variants`*

---

## 5. Structural Analysis

**Structural impact assessment not required** for truncating variants where LOF is established mechanism.

**Protein Context**:
- Truncation at codon 1756 (of 1863)
- Removes C-terminal BRCT domains
- BRCT domains essential for DNA repair function
- Even if translated, protein would be non-functional

*Source: UniProt P38398, InterPro domain annotations*

---

## 6. Literature Evidence

### Functional Studies

| Study | Finding | PMID |
|-------|---------|------|
| Carvalho et al., 2007 | LOF in HDR assay | 17308087 |
| Moghadasi et al., 2018 | Absent protein | 29446198 |
| Multiple studies | Segregates with cancer | Multiple |

### Clinical Reports

- Founder variant in Ashkenazi Jewish population
- Extensive clinical documentation (>500 families)
- Co-segregation in >100 affected individuals

**PS3 Evidence**: assessed in the unified ACMG skill under the SVI functional framework (strength from assay validation, not the number of studies); multiple functional studies are the raw material

*Source: `PubMed_search_articles`*

---

## 7. Handoff to the Unified ACMG Skill

This example stops at material collection. Evidence evaluation (all 28
codes, strengths, exclusions) happens in the unified
`tooluniverse-acmg-variant-classification` skill against its
`SVI_REFERENCE.md`, and the final classification comes only from the
`ACMG_calculate_classification` calculator -- never from this file.

## Data Sources

| Tool | Purpose | Result |
|------|---------|--------|
| `ClinVar_search_variants` | Classification lookup | VCV000017661 |
| `gnomad_search_variants` | Population frequency | AF=0.00006 |
| `MyVariant_query_variants` | Aggregated annotations | Complete |
| `PubMed_search_articles` | Literature evidence | 47 relevant papers |
| `OMIM_search` | Gene-disease | HBOC confirmed |
```

---

## Example 2: TP53 p.R175C — Material Collection

### User Query
"Interpret TP53 p.R175C - it's reported as a VUS"

### Expected Output

```markdown
# Variant Interpretation Report: TP53 p.R175C

**Generated**: 2026-02-04 | **Analyst**: ToolUniverse Variant Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000546.6:c.523C>T (p.Arg175Cys) |
| **Gene** | TP53 |
| **External classifications (attributed)** | ClinVar: VUS for p.R175C itself; other R175 missense variants Pathogenic (see section 3) |
| **Key Finding** | Hotspot residue in the DNA-binding domain; collected material below |

(Any reclassification would come from the unified ACMG flow, not this example.)

---

## 1. Variant Identity

| Property | Value |
|----------|-------|
| Gene | TP53 |
| Chromosome | 17 |
| Position | 17:7674220 (GRCh38) |
| Transcript | NM_000546.6 (MANE Select) |
| cDNA change | c.523C>T |
| Protein change | p.Arg175Cys |
| Consequence | Missense |
| Exon | 5 of 11 |

*Source: `EnsemblVar_get_variant_consequences`, `MyVariant_query_variants`*

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency | Allele Count |
|------------|------------------|--------------|
| **Overall** | 0 | 0 |
| European (Non-Finnish) | 0 | 0 |
| African/African American | 0 | 0 |
| Latino/Admixed American | 0 | 0 |
| East Asian | 0 | 0 |
| South Asian | 0 | 0 |

**Homozygotes**: 0

**Interpretation**: Absent from gnomAD (>140,000 individuals). Supports PM2 (absent from controls).

*Source: `gnomad_search_variants`, accessed 2026-02-04*

---

## 3. Clinical Database Evidence

### ClinVar

| Property | Value |
|----------|-------|
| VCV ID | VCV000376642 |
| Classification | VUS (outdated) |
| Review Status | ★★ (criteria provided) |
| Submitters | 3 |
| Conditions | Li-Fraumeni syndrome |

(External classifications are recorded as attributed facts; updating them is out of scope here.)

### Critical Context: R175 Position

| Variant at R175 | ClinVar Classification |
|-----------------|------------------------|
| p.R175H | Pathogenic (★★★★) |
| p.R175G | Pathogenic |
| p.R175L | Pathogenic |
| p.R175S | Pathogenic |
| **p.R175C** | VUS (being reclassified) |

**PM5 material**: multiple different missense changes at R175 are externally classified pathogenic -- a PM5 fact candidate for the unified assessment.

### OMIM

| Gene-Disease | Inheritance |
|--------------|-------------|
| Li-Fraumeni syndrome | AD |
| Various cancers | Somatic |

*Sources: ClinVar, OMIM #191170*

---

## 4. Computational Predictions

| Predictor | Score | Interpretation |
|-----------|-------|----------------|
| SIFT | 0.00 | Damaging |
| PolyPhen-2 | 1.00 | Probably damaging |
| CADD | 29.5 (Phred) | Top 0.1% deleterious |
| REVEL | 0.92 | Pathogenic range |

**Concordance**: 4/4 predictors damaging (raw context only) → PP3 decided in the unified ACMG skill by the pre-specified calibrated tool's threshold, never by vote count

*Source: `MyVariant_query_variants`*

---

## 5. Structural Analysis

### Structure Information

| Property | Value |
|----------|-------|
| Structure used | PDB: 2OCJ (1.8 Å) |
| Domain | DNA-binding domain (DBD) |
| Position pLDDT | N/A (experimental structure) |
| Resolution | 1.8 Å |

### R175 Structural Context

| Feature | Assessment |
|---------|------------|
| **Location** | DNA-binding domain core |
| **Solvent accessibility** | Buried (RSA = 5%) |
| **Secondary structure** | Loop L2 (critical for zinc coordination) |
| **Zinc coordination** | 4.2 Å from Zn²⁺ binding site |
| **Conservation** | 100% in vertebrates |

### Structural Impact Analysis

| Factor | Wildtype (Arg) | Mutant (Cys) | Impact |
|--------|----------------|--------------|--------|
| Charge | +1 (basic) | 0 (neutral) | Charge loss in buried position |
| Side chain volume | Large | Small | Potential cavity |
| H-bonding | 5 H-bonds | 1 H-bond | Loss of stabilizing interactions |
| Zinc coordination | Proximal | Potential interference | May affect zinc binding |

### Structural Conclusion

**PM1 applies (moderate)**: 
- R175 is in a critical structural region
- Known mutational hotspot
- Zinc coordination region essential for DNA binding
- Structural analysis collected as mechanistic context

*Sources: PDB 2OCJ, structural analysis*

---

## 6. Literature Evidence

### Functional Studies (at R175 position)

| Study | Variant | Finding | PMID |
|-------|---------|---------|------|
| Kato et al., 2003 | R175H | Loss of transactivation | 12826609 |
| Bullock et al., 2000 | R175H | Destabilized, unfolded | 10788335 |
| Joerger et al., 2006 | R175 mutations | Disrupt zinc binding | 16630891 |

### R175C-Specific Evidence

- Limited direct functional data for R175C specifically
- Same position as extensively characterized R175H
- Mechanism (zinc coordination disruption) likely conserved

**PS3**: Not directly applicable (no R175C-specific functional study)
**PS1**: Not applicable (amino acid change differs from R175H)

*Source: `PubMed_search_articles`*

---

## 7. Handoff to the Unified ACMG Skill

This example stops at material collection. Evidence evaluation (all 28
codes, strengths, exclusions) happens in the unified
`tooluniverse-acmg-variant-classification` skill against its
`SVI_REFERENCE.md`, and the final classification comes only from the
`ACMG_calculate_classification` calculator -- never from this file.

## Data Sources

| Tool | Purpose | Result |
|------|---------|--------|
| `ClinVar_search_variants` | Classification | VCV000376642 (VUS) |
| `gnomad_search_variants` | Population freq | 0 (absent) |
| `MyVariant_query_variants` | Predictions | All damaging |
| `RCSBData_get_entry` | Structure | 2OCJ |
| `PubMed_search_articles` | Literature | R175 studies |
```

---

## Example 3: CFTR p.M470V — Material Collection

### User Query  
"What is the significance of the CFTR p.M470V variant?"

### Expected Output (Key Sections)

```markdown
# Variant Interpretation Report: CFTR p.M470V

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000492.4:c.1408A>G (p.Met470Val) |
| **Gene** | CFTR |
| **External classifications (attributed)** | ClinVar: Benign (see section 3) |
| **Key Finding** | Common variant (14% global AF); collected material below |

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency |
|------------|------------------|
| **Overall** | 0.14 (14%) |
| European | 0.22 |
| East Asian | 0.03 |
| African | 0.08 |

**Interpretation** (raw material): at 14% global AF the variant is far more frequent than CF prevalence (1/3,000) would allow -- recorded as a frequency fact for the unified assessment (BA1 decided there, with the SVI exception list).

---

## 7. Handoff to the Unified ACMG Skill

This example stops at material collection. Evidence evaluation (all 28
codes, strengths, exclusions) happens in the unified
`tooluniverse-acmg-variant-classification` skill against its
`SVI_REFERENCE.md`, and the final classification comes only from the
`ACMG_calculate_classification` calculator -- never from this file.
## Example 4: SCN5A c.4813+3A>G — Material Collection

### User Query
"Interpret SCN5A c.4813+3A>G - novel splice variant"

### Expected Output (Key Sections)

```markdown
# Variant Interpretation Report: SCN5A c.4813+3A>G

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000335.5:c.4813+3A>G |
| **Gene** | SCN5A |
| **External classifications (attributed)** | ClinVar: VUS (see section 3) |
| **Key Finding** | Near-splice variant in a cardiac arrhythmia gene; SpliceAI predicts donor loss (raw score below) |

(RNA studies would be the next collection step; any classification follows the unified flow.)

---

## 4. Computational Predictions

### Splice Predictions

| Tool | Score | Prediction |
|------|-------|------------|
| SpliceAI donor loss | 0.89 | High impact predicted |
| MaxEntScan (WT) | 8.2 | Strong donor site |
| MaxEntScan (Mut) | 4.1 | Weakened |

**Interpretation**: +3 position variants can affect splicing. SpliceAI score of 0.89 suggests high likelihood of splice disruption.

---

## 7. Handoff to the Unified ACMG Skill

This example stops at material collection. Evidence evaluation (all 28
codes, strengths, exclusions) happens in the unified
`tooluniverse-acmg-variant-classification` skill against its
`SVI_REFERENCE.md`, and the final classification comes only from the
`ACMG_calculate_classification` calculator -- never from this file.
