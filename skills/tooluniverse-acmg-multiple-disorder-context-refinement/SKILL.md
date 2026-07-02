---
name: tooluniverse-acmg-multiple-disorder-context-refinement
description: Refine ACMG/AMP variant classification when one gene is associated with multiple disorders, inheritance patterns, dosage states, disease spectra, or mechanisms. Use before aggregating evidence across conditions, before assigning disease-specific evidence codes, and when ClinGen gene-disease validity, dosage sensitivity, lumping/splitting, or disease entity selection affects classification.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG Multiple-Disorder Context Refinement

This overlay extends `tooluniverse-acmg-variant-classification` by defining the disease entity, inheritance model, mechanism, and evidence-aggregation boundary before evidence codes are assigned.

It follows ClinGen's January 2024 "Guidance Classifying Variants in Genes Associated with Multiple Disorders, Version 1" and Thaxton et al. 2022. It does not create a new ACMG evidence code. It decides whether evidence may be aggregated across disorders or must be split into separate disease-specific classifications.

Use `tooluniverse-acmg-overlay-routing-core` for shared routing order and output-status conventions. This overlay is the disease-entity step in that shared routing order.

Use this overlay before mechanism-sensitive criteria such as PVS1, PS1/PM5, PS3/BS3, PM1/PP2/BP1, PS4, PP1/BS4, PM3, PP4, BA1/BS1, and de novo evidence when a gene has more than one associated disorder.

---

## When to Use This Skill

Invoke this overlay when any of the following are true:

- The gene has multiple disease associations, phenotypic spectra, inheritance patterns, or mechanism classes.
- The same gene has dominant and recessive conditions.
- The same gene has both sequence-variant and dosage/CNV disease contexts.
- A variant is being classified for one condition but evidence comes from another condition.
- A ClinVar or literature assertion names a broad disease while the current case has a narrower phenotype.
- The gene has both LoF/haploinsufficiency and gain-of-function, dominant-negative, antimorphic, or other altered-product mechanisms.
- The gene has semidominant disease where monoallelic and biallelic states have different severity.
- The user asks whether evidence can be aggregated across related phenotypes.
- CNVs include multiple genes with distinct disease associations.

Do not use this overlay as a substitute for disease-specific VCEP specifications. If a current VCEP defines disease-specific rules for the gene and condition, follow the VCEP and use this overlay only to document the disease-entity boundary.

---

## Core Principle

A variant is not simply "pathogenic" in the abstract. It is classified for:

- a disease entity or disease spectrum;
- a mode of inheritance;
- a molecular mechanism or qualifying variant class;
- and, where needed, a dosage state or zygosity state.

Evidence may be aggregated only when the disease entities are sufficiently close and the mechanism of pathogenicity is similar. When mechanisms, inheritance patterns, or clinical entities are distinct, evidence must be separated.

---

## Evidence Retrieval Workflow

Use ToolUniverse evidence retrieval before deciding whether to lump or split.

1. **Normalize variant and consequence**
   - Use `VariantValidator_validate_variant`, `VariantValidator_gene2transcripts`, and `EnsemblVEP_annotate_hgvs`.
   - Record variant type, transcript, protein effect, predicted LoF/NMD, in-frame/missense/splicing consequence, and zygosity.

2. **List gene-disease relationships**
   - Use `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity`.
   - Use `GenCC_search_gene`, `G2P_search`, OMIM/Orphanet-derived tools, MedGen, MONDO, and GeneReviews routes.
   - Record disease name, inheritance, molecular mechanism, validity level, curation date, and whether ClinGen lumped or split the disease entity.

3. **Check dosage sensitivity separately**
   - Use `ClinGen_search_dosage_sensitivity`.
   - Record HI and TS scores separately from gene-disease validity.
   - Do not treat a definitive gene-disease relationship as proof of haploinsufficiency or triplosensitivity.
   - Do not treat an HI score of 0, 30, or 40 as refuting a non-dosage disease mechanism such as gain-of-function, dominant-negative, or recessive biallelic disease.

4. **Determine mechanism and variant-class compatibility**
   - If mechanisms differ or are unclear, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` and the relevant evidence-specific overlays.
   - Compare whether the variant class under assessment fits the target disease mechanism.

5. **Map patient phenotype, literature case definition, or target indication**
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when patient phenotype, affected status, diagnostic yield, tested/excluded loci, family data, de novo data, healthy-carrier context, or alternate diagnosis affects PP4, rare-disease PS4 case counting, PP1/BS4, PM3, PS2/PM6, BS2, BP2, or BP5.
   - For formal PS4 case-control, cohort, or meta-analysis evidence, retrieve the study's case definition and disease ascertainment through the PS4 overlay; do not request patient phenotype unless the study definition is missing or ambiguous.
   - If the user has not supplied the target disease/entity for classification, mark disease-context routing as `status: not_assessed` with reason `disease context required` and ask for the disease being classified. A target disease/entity is not the same as a full patient phenotype.

6. **Choose aggregation category**
   - Apply one of the seven categories below.
   - Document whether evidence is aggregated, split, or conditionally split.

---

## Seven ClinGen Multiple-Disorder Categories

### 1. Single Condition With Severity Based on Inheritance and Gene Dosage

Example: `LDLR` familial hypercholesterolemia, where biallelic pathogenic variants cause more severe disease than monoallelic pathogenic variants.

Handling:

- Classify variants for the single semidominant condition.
- Evidence can be aggregated across monoallelic and biallelic observations.
- Record severity, zygosity, and dosage state in the evidence summary.
- Do not create separate pathogenicity claims solely because severity differs by zygosity.

### 2. Two Distinct Conditions With Different Inheritance Based on Gene Dosage, Same Mechanism

Example: `ATM` dominant breast cancer and recessive ataxia-telangiectasia, where the pathogenic mechanism is consistent across conditions.

Handling:

- Evidence for pathogenicity can be aggregated across both conditions.
- The final pathogenicity classification is expected to be the same for both conditions.
- Prefer storing two classifications, one for each condition, using the same evidence summary.
- If only one classification can be submitted, use the best-established condition and note the relationship to the other condition.

### 3. Single Mutational Mechanism With Phenotypic Spectrum or Pleiotropy

Example: `FBN1` Marfan syndrome spectrum, including full Marfan phenotype and milder or isolated features such as aortic dissection.

Handling:

- Evidence can generally be aggregated across observations.
- Case-counting strength must account for phenotype specificity and frequency.
- Fewer cases may be needed when the full, specific phenotype is present; more cases are needed for isolated or common features.
- Route PP4, rare-disease PS4 case-counting, and PP1 questions through phenotype-dependent and case-enrichment overlays. Formal PS4 case-control/cohort evidence routes directly to the PS4 overlay unless the study disease definition is unclear.

### 4. Multiple Conditions With Distinct, Mutually Exclusive Mechanisms

Example: `RET` Hirschsprung disease and multiple endocrine neoplasia type 2, usually LoF versus GoF.

Handling:

- Do not aggregate evidence across conditions.
- Classify pathogenic variants only for the condition and mechanism they support.
- The variant does not need to be classified for mutually exclusive conditions, though a comment about lack of association can be added when clinically useful.
- Apply benign/likely benign only if that benign classification is relevant for all conditions being represented, or classify benign separately per condition.
- For VUS, classify toward the condition with relevant evidence; if no evidence exists for either condition, use both conditions or a broader disease name only if appropriate.

### 5. Multiple Conditions That Are Not Mutually Exclusive

Example: `RYR1` malignant hyperthermia plus dominant and recessive myopathy.

Handling:

- Do not aggregate evidence across conditions.
- Make separate classifications for each condition.
- A variant may be pathogenic for more than one condition, but each classification needs its own evidence summary.
- If pathogenic for one condition and uncertain/not associated with another, add a note to the pathogenic classification rather than creating misleading conflicts.

### 6. Multiple Possible Conditions With Unclear Distinction or Mechanism

Handling:

- Use clinical judgment and document uncertainty.
- Aggregate evidence only if phenotypes are close and the mechanism appears similar, such as similar pLoF mechanisms.
- If mechanisms may differ, split evidence until current curated sources or VCEP rules support lumping.
- Do not transfer evidence between conditions just because the gene is the same.

### 7. CNVs Encompassing Multiple Genes With Distinct Disease Associations

Handling:

- Route CNV/SV evidence through `tooluniverse-structural-variant-analysis`.
- The CNV can be associated with a list of diseases linked to genes in the interval.
- Note genes with unknown disease association separately.
- Do not convert a multi-gene CNV disease list into a sequence-variant classification for one gene without gene-level and mechanism-specific evidence.

---

## Gene-Disease Validity and Dosage Rules

Use ClinGen gene-disease validity and dosage sensitivity as distinct evidence types:

- Gene-disease validity asks whether pathogenic variants in a gene cause a disease by any mechanism.
- Dosage sensitivity asks whether haploinsufficiency or triplosensitivity specifically causes disease.
- A definitive gene-disease validity curation does not automatically permit PVS1 or CNV deletion pathogenicity.
- A non-sufficient HI/TS score does not negate a definitive disease mechanism if the disease is recessive, gain-of-function, dominant-negative, or otherwise non-dosage.
- A ClinGen HI score of 3 can support using PVS1/CNV deletion logic, but final PVS1 strength still depends on the PVS1 decision tree and the exact variant.
- For gene-disease pairs with Limited, Disputed, or Refuted validity, do not classify variants above VUS using that disease association.
- For Moderate gene-disease validity, do not typically classify above Likely Pathogenic unless a current VCEP or strong disease-specific rationale supports it.

---

## Evidence Aggregation Rules by ACMG Criterion

### PVS1

Use PVS1 only for the disease entity where LoF/haploinsufficiency is established. If a gene has both LoF and GoF/DN diseases, split the diseases and route PVS1 through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` only for the LoF-compatible condition.

### PS1/PM5

Same amino-acid, same-residue, or same-codon evidence must match the disease mechanism. Do not transfer PS1/PM5 from a GoF or DN disorder to a LoF disorder, or vice versa, unless the comparison variant is known to support the same condition and mechanism.

### PS3/BS3

Functional evidence must test the mechanism relevant to the target condition. A LoF assay, GoF assay, DN assay, channel-gating assay, or splicing assay should not be applied to a different disease mechanism without a mechanistic bridge.

### PM1/PP2/BP1/PP3/BP4

Regional constraint, missense mechanism, and computational predictions should be interpreted within the target disease mechanism. BP1 is unsafe when a different disease of the same gene is caused by pathogenic missense/in-frame variants.

### PS4

Case enrichment must match the target disease or a valid lumped disease spectrum. Do not aggregate cases from mutually exclusive disorders or different mechanisms. For spectrum disorders, phenotype specificity affects case-counting strength.

### PP1/BS4 and PP4

Segregation, non-segregation, and phenotype specificity require the same disease entity. If PP4 and PP1/BS4 interact through phenotype specificity, diagnostic yield, or locus evidence, use `tooluniverse-acmg-pp1-segregation-refinement` for combined PP1/BS4/PP4 guidance.

### PM3

PM3 is condition-specific recessive in-trans evidence. Do not use a variant that is pathogenic for a dominant disorder as the "other allele" for a recessive disorder unless it is also a qualifying pathogenic allele for that recessive condition.

### BA1/BS1/PM2

Frequency thresholds depend on the disease entity, inheritance, penetrance, and allelic/genetic heterogeneity. A benign classification across multiple disorders should be used only when benignity is relevant for all represented conditions, or it should be assigned separately by condition.

---

## Output Format

```markdown
Multiple-disorder context refinement:
- Gene: [symbol]
- Target disease/entity: [disease], [inheritance], [MONDO/MedGen/OMIM if available]
- Other gene-associated disorders: [list with inheritance/mechanism/validity]
- ClinGen gene-disease validity: [target dyad and other dyads]
- ClinGen dosage sensitivity: [HI/TS scores and interpretation]
- Lumping/splitting category: [1-7]
- Evidence aggregation decision: [aggregate / split / aggregate with phenotype-specific case-counting / not_assessed]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Variant class fit: [target disease mechanism fit]
- Evidence codes affected: [PVS1, PS1/PM5, PS3/BS3, PS4, PP1/BS4, PP4, PM3, BA1/BS1/PM2, etc.]
- Final disease-specific classification plan: [one shared classification / separate classifications / target-condition-only / VUS by disease]
- Missing information: [target disease, phenotype, inheritance, mechanism, zygosity, etc.]
```

---

## Tool Parameter Reference

| Tool | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Normalize variant and transcript. |
| `VariantValidator_gene2transcripts` | Retrieve MANE transcript context. |
| `EnsemblVEP_annotate_hgvs` | Consequence and variant class. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Disease-specific gene validity and inheritance. |
| `ClinGen_search_dosage_sensitivity` | HI/TS dosage context. |
| `GenCC_search_gene` | Cross-check gene-disease validity and inheritance. |
| `G2P_search` / `G2P_get_record` | Curated disease, consequence, and mechanism terms. |
| `MedGen_search_conditions` | Disease synonyms, GeneReviews discovery, and phenotype context. |
| `Mondo_get_disease` / `Mondo_get_disease_phenotypes` | Normalize disease entities and phenotype associations. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Literature evidence for disease spectrum and mechanism. |
| `tooluniverse-literature-deep-research` | Extract disease-specific evidence from publications. |
| `tooluniverse-literature-figure-evidence-extraction` | Extract pedigree, phenotype, and mechanism figures when needed. |

---

## Limitations

- This overlay does not decide final pathogenicity by itself.
- Disease-specific VCEP rules override this generic guidance.
- If the target disease is not provided and the gene has multiple associations, do not silently choose one disease; ask the user.
- ClinGen, GenCC, G2P, and dosage curations are updated over time. Use current database retrieval when applying the overlay.
- Do not use gene-level curation to replace variant-level evidence.

---

## References

- ClinGen. Guidance Classifying Variants in Genes Associated with Multiple Disorders, Version 1. January 2024. User-provided PDF: `clingen_guidance_for_classifying_variants_in_genes_associated_with_multiple_disorders_v1.pdf`.
- Thaxton C, Good ME, DiStefano MT, Luo X, Andersen EF, Thorland E, Berg J, Martin CL, Rehm HL, Riggs ER; ClinGen Gene Curation Working Group; ClinGen Dosage Sensitivity Working Group. Utilizing ClinGen gene-disease validity and dosage sensitivity curations to inform variant classification. Human Mutation. 2022;43(8):1031-1040. PMID: 34694049. PMCID: PMC9035475. DOI: 10.1002/humu.24291.
