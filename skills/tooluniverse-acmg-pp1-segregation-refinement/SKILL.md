---
name: tooluniverse-acmg-pp1-segregation-refinement
description: Refine ACMG/AMP PP1 co-segregation and BS4 non-segregation evidence using ClinGen guidance, including Biesecker et al. 2024 combined PP1/BS4/PP4 points. Use with ToolUniverse ACMG variant classification when family segregation, LOD score, informative meioses, pedigree evidence, penetrance, phenocopy, diagnostic yield, locus heterogeneity, phenotype specificity, or BS4 non-segregation affects PP1/PP4 strength.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG PP1 Segregation Refinement

This skill extends `tooluniverse-acmg-variant-classification` for PP1 co-segregation evidence, BS4 non-segregation evidence, and their boundary with PP4 phenotype-specificity evidence.

Use Biesecker et al. 2024 ClinGen SVI combined guidance as the current primary overlay when PP1, BS4, and PP4 interact. Use Strande et al. 2017 as background for gene-disease validity and evidence-quality review. This update does not replace disease-specific VCEP rules; current VCEP specifications supersede these default rules.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions. This overlay owns PP1/BS4 scoring and PP1/BS4/PP4 combined scoring; phenotype-dependent refinement only collects clinical context before routing here.

---

## When to Use This Skill

Use this skill when any of the following are present:

- Published family segregation data for the variant.
- A reported or calculable LOD score for variant/disease co-segregation.
- Informative meioses, affected carriers, unaffected non-carriers, obligate carriers, or phase-resolved pedigree data.
- Apparent non-segregation, affected non-carriers, unaffected carriers, phenocopies, or reduced penetrance.
- Need to decide PP1, PP1_Moderate, PP1_Strong, no PP1, or BS4.
- Need to avoid double counting the same individuals as segregation evidence and case-control or proband-count evidence.
- PP4 phenotype specificity, diagnostic yield, locus homogeneity/heterogeneity, or exclusion of other loci affects how segregation evidence should be scored.
- Multiple plausible candidate variants are present on the same allele or across linked loci, requiring evidence apportionment.

Do not use this skill to refine unrelated ACMG evidence criteria. De novo evidence belongs under PS2/PM6, population evidence under BA1/BS1/PM2, and functional evidence under PS3/BS3. Phenotype intake and generic PP4 routing belong under `tooluniverse-acmg-phenotype-dependent-evidence-refinement`, but the PP1/BS4/PP4 combined points cap and double-counting rules are handled here when segregation evidence is present.

---

## Core Principle

PP1 is variant-level evidence that a variant co-segregates with disease in a family. It should be applied only when the observed segregation is consistent with the disease inheritance model, the variant is a plausible qualifying variant for the gene-disease mechanism, and the same evidence is not being counted elsewhere.

Use the most quantitative segregation evidence available:

1. If a disease-specific VCEP rule exists, use it.
2. If Biesecker et al. 2024 combined PP1/BS4/PP4 logic applies, score diagnostic-yield PP4 and segregation points together, cap combined locus evidence, and apportion evidence across candidate variants when needed.
3. Use a published likelihood/LOD score when provided and methodologically credible, especially for complex pedigrees.
4. If no likelihood/LOD score is provided and the combined-guidance inputs are incomplete, use informative meioses or clearly reported segregation events as a conservative fallback.
5. If neither is available, record the pedigree observation but do not apply PP1.

Do not mix scoring frameworks to obtain a higher strength. Use the Biesecker 2024 combined PP1/BS4/PP4 points approach when its required inputs are available. Use the informative-meioses/LOD fallback only when combined-guidance inputs are incomplete, and state why the fallback was used.

---

## Evidence Retrieval Workflow

Use ToolUniverse retrieval tools before assigning PP1 strength.

1. **Confirm variant identity and transcript consequence**
   - Use `VariantValidator_validate_variant` to normalize HGVS notation.
   - Use `EnsemblVEP_annotate_hgvs` and `MyVariant_query_variants` to confirm consequence, ClinVar context, and population annotations.
   - Confirm that the variant is plausible for the disease mechanism and is not contradicted by high population frequency or other strong benign evidence.
   - If the disease may be dominant-negative, antimorphic, or mixed by variant class, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` to document why the segregating variant is a qualifying variant for that mechanism.

2. **Confirm gene-disease validity, inheritance, and diagnostic-yield context**
   - Use `ClinGen_search_gene_validity` or `ClinGen_get_gene_validity` to establish the gene-disease relationship and asserted inheritance pattern.
   - Use GenCC, OMIM/Orphanet-derived tools, and disease literature when ClinGen is absent or incomplete.
   - Do not use PP1 to rescue a gene-disease relationship that is disputed, refuted, or unsupported for the disease being classified.
   - Retrieve disease-specific diagnostic yield and locus heterogeneity/homogeneity from VCEP specifications, GeneReviews, MedGen, curated disease reviews, or primary cohort studies. Record whether the testing method used in the case is comparable to the method underlying the diagnostic-yield estimate.

3. **Retrieve segregation evidence**
   - Use `PubMed_search_articles` and `EuropePMC_search_articles` with the gene, variant HGVS, disease name, "segregation", "pedigree", "family", "LOD", and "linkage".
   - Use `ClinVar_search_variants` or ClinVar-related tools to identify submitted segregation comments, but prefer primary literature or curated expert-panel evidence when available.
   - When segregation, affected status, carrier status, phase, or non-segregation is shown in a pedigree or figure, use `tooluniverse-literature-figure-evidence-extraction` to extract structured family evidence before applying PP1 or BS4 rules.

4. **Extract the pedigree evidence**
   - Record affected carriers, affected non-carriers, unaffected carriers, unaffected non-carriers, obligate carriers, number of independent families, phase, zygosity, and genotyping method.
   - Distinguish co-segregating individuals, informative meioses, families, affected carriers, and informative unaffected relatives. These are not interchangeable units.
   - The proband establishes the variant-case observation but is not an additional segregation event by itself. Count relatives or meioses only when they add informative transmission or non-transmission evidence beyond the proband.
   - Record whether the LOD score is variant-specific, locus-level, or gene-level.
   - Record disease age of onset, penetrance assumptions, phenocopy risk, phenotype certainty, and whether relatives are old enough to be informative.
   - When the observation comes from OCR, a cropped figure, a user correction, or inferred carrier status, record confidence and provenance before scoring.

5. **Choose the evidence code**
   - When PP4 phenotype specificity and PP1 segregation are based on the same phenotype/locus evidence, apply the Biesecker 2024 combined points cap and convert to allowable PP1/PP4 code combinations.
   - Apply PP1 strength only when the segregation is variant-specific or the implicated allele has been appropriately apportioned to the variant under assessment.
   - Apply BS4 when robust non-segregation cannot be explained by phenocopy, reduced penetrance, wrong phenotype, wrong disease model, or technical error.

---

## ClinGen Combined PP1/BS4/PP4 Rules

Biesecker et al. 2024 treats PP4 phenotype specificity and PP1 co-segregation as linked evidence, not independent evidence that can be freely stacked. The same phenotype/locus evidence must not be double counted as both unrestricted PP4 and unrestricted PP1.

### Scope Gate

Use the combined points approach only for Mendelian disorders with a definitive or strong gene-disease relationship and reasonably reliable phenotype, inheritance, and testing-yield information. Use caution or require formal segregation analysis when:

- gene-disease validity is lower than strong/definitive;
- penetrance is low, age dependent, or sex limited;
- phenocopy rate is high;
- the pedigree is large, consanguineous, or statistically complex;
- diagnostic yield is unknown or derived from a non-comparable testing method;
- locus heterogeneity is extensive and the contribution of the gene under assessment is below 20%.

### PP4 Diagnostic-Yield Points

When phenotype specificity is used as PP4 in the combined PP1/PP4 framework, estimate the diagnostic yield for the exact gene-phenotype dyad and comparable testing method. Round down to the nearest supported value.

| Diagnostic yield | PP4 points |
| --- | ---: |
| >=99.9% | 12 |
| >=99.8% | 11.5 |
| >=99.7% | 11 |
| >=99.6% | 10.5 |
| >=99.4% | 10 |
| >=99.2% | 9.5 |
| >=98.8% | 9 |
| >=98.3% | 8.5 |
| >=97.5% | 8 |
| >=96.5% | 7.5 |
| >=95.0% | 7 |
| >=93.0% | 6.5 |
| >=90.2% | 6 |
| >=86.4% | 5.5 |
| >=81.6% | 5 |
| >=75.4% | 4.5 |
| >=68.0% | 4 |
| >=59.6% | 3.5 |
| >=50.6% | 3 |
| >=41.5% | 2.5 |
| >=33.0% | 2 |
| >=25.4% | 1.5 |
| >=19.1% | 1 |

Do not use diagnostic-yield PP4 below approximately 20% unless a current VCEP rule explicitly permits it. For very heterogeneous disorders, use only co-segregation/non-segregation points unless diagnostic-yield data are robust.

### Co-Segregation Points

Use these points for simple pedigrees when a VCEP or formal segregation analysis is not available:

| Co-segregating individuals | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Autosomal recessive, affected | 2.0 | 4.0 | 6.0 | 8.0 | 10.0 |
| Autosomal recessive, unaffected | 0.4 | 0.8 | 1.2 | 1.6 | 2.0 |
| Autosomal dominant, affected and informative unaffected | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |
| X-linked recessive, affected males and informative unaffected males | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |

Only count unaffected individuals when the disease is fully penetrant for that person's age, sex, and clinical evaluation. Do not count unaffected parents used only to establish phase. For autosomal-recessive unaffected co-segregations, continue adding 0.4 points per informative meiosis above five.

Low-confidence or `not_interpretable` visual extraction can guide follow-up but cannot upgrade PP1 strength without corroborating text, genotype table, clear figure evidence, or user-supplied source material.

### Locus Homogeneity and PP1

When the phenotype points to one locus with high diagnostic yield, PP4 can carry the locus evidence and PP1 should not be added from expected perfect co-segregation. In this setting, co-segregation is not independent evidence; it follows from the phenotype/locus specificity.

When the trait has locus heterogeneity, or locus homogeneity with low diagnostic yield, add PP1/BS4 points only after:

- assigning PP4 points based on the relevant diagnostic yield;
- establishing phase where required;
- confirming the same family members are not also counted under PS4 or another case-counting criterion;
- reassessing PP4 if non-segregation or comprehensive testing excludes another plausible locus.

### Combined PP1/PP4 Cap and Code Conversion

Combined PP1 plus PP4 locus evidence is capped at +5.0 points per variant. Do not allow PP1/PP4 alone to reach likely pathogenic or pathogenic classification. Use independent variant-level evidence such as PVS1, PS3, PP3, PM1, or other appropriate criteria for higher classifications.

| Combined points | Maximum allowable code combination |
| --- | --- |
| 0-0.9 | Not applicable |
| 1-1.9 | `PP1` or `PP4_Supporting` |
| 2-2.9 | `PP1_Moderate`, `PP4_Moderate`, or `PP1` + `PP4_Supporting` |
| 3-3.9 | `PP1` + `PP4_Moderate`, or `PP1_Moderate` + `PP4_Supporting`, or `PP1_Moderate` |
| 4-4.9 | `PP1_Strong`, `PP4_Strong`, or `PP1_Moderate` + `PP4_Moderate` |
| >=5 | `PP1_Strong` + `PP4_Supporting`, or `PP4_Strong` + `PP1` |

The code split is a reporting choice. Prefer the split that most transparently reflects the evidence source: use more PP4 weight when phenotype/locus specificity is doing most of the work; use more PP1 weight when multiple informative segregations are doing most of the work.

### Multiple Variants on One Allele or Linked Loci

Co-segregation and phenotype-specificity evidence implicate an allele or locus, not automatically one nucleotide change. If more than one plausible candidate variant is present in cis on the implicated allele, distribute the posterior probability across plausible candidate variants before converting back to points. Do not simply divide points arithmetically.

Use Table S1 logic from Biesecker et al. 2024 when two plausible candidate variants need apportionment:

- sum non-PP1/PP4/BS4 evidence for each variant;
- convert each variant's non-segregation posterior to relative odds;
- combine those relative odds with the diagnostic yield;
- convert each adjusted posterior back to points;
- cap combined PP1/PP4 evidence at +5.0 per variant.

If one variant has much stronger independent pathogenic evidence and the other has substantial benign evidence, the combined allele evidence can be redistributed toward the more plausible pathogenic variant. If the variants remain similarly plausible, keep the evidence divided and state the uncertainty.

### BS4 Non-Segregation

Use `BS4` when non-segregation is robust and unexplained. In the points framework, Biesecker et al. 2024 retains BS4 as strong benign evidence, equivalent to approximately -4.0 points, for autosomal-dominant, autosomal-recessive homozygous, and X-linked settings where non-segregation distinguishes the variant or locus.

Do not apply BS4 automatically in autosomal-recessive compound heterozygous families when a relative has non-segregation at the locus. In a single family, such non-segregation may show that one of two alleles is not causative but may not identify which allele or variant is benign.

Negative evidence at one locus can increase support for another locus in a heterogeneous disorder, but only when testing has comprehensively assessed the plausible loci and the phenotype/test-yield assumptions are documented.

### PP4/PS4 Boundary

A previously observed affected individual can count as PP4 or PS4 evidence, but not both. If a published case is used to establish PP4 diagnostic-yield/phenotype-specificity support for the variant, do not count that same individual again as a PS4 case. Family members of that individual may still contribute additional PP1 segregation evidence if they are independently informative.

Do not let PP1/PP4 plus PS4 exceed a strength that would overstate case/locus evidence. If PS4 case-counting and combined PP1/PP4 both use overlapping individuals or ascertainment, choose the most defensible allocation and document it.

---

## Evidence Quality Rules

### Qualifying Variant Requirement

Count segregation evidence only when the variant is a plausible qualifying variant for the gene-disease pair:

- The molecular consequence fits the disease mechanism.
- For dominant-negative disease, the variant class plausibly produces the relevant altered product or has direct evidence for dominant interference.
- The inheritance model fits the family structure.
- The variant is not too common for the disease.
- The variant is not contradicted by strong benign evidence.
- The phenotype in the family fits the asserted disease.

If these are not met, do not apply PP1. Record the segregation observation as context only.

### LOD and Informative Meioses Fallback

Use a credible published LOD score when available, especially when the pedigree is complex or the disease has reduced penetrance or a high phenocopy rate. If the paper provides only raw pedigree observations and Biesecker combined-guidance inputs are not available, use informative meioses as the operational fallback. Do not fabricate a LOD score unless a validated disease-specific calculator or VCEP method is available.

Conservative fallback strength mapping when no gene-specific VCEP rule supersedes it and the combined PP1/PP4 points approach cannot be applied:

| Evidence | Default PP1 strength |
|----------|----------------------|
| LOD >= 3, or >= 7 informative meioses with no contradictory segregation | PP1_Strong |
| LOD 1.5 to < 3, or 5-6 informative meioses with no contradictory segregation | PP1_Moderate |
| LOD 0.5 to < 1.5, or 2-4 informative meioses with no contradictory segregation | PP1 |
| Single uninformative family observation, no LOD, or unclear phase/phenotype | Do not apply PP1 |

Prefer disease-specific ClinGen VCEP PP1 thresholds when available and current. When diagnostic yield and PP4 are being used, prefer the combined points table above over this fallback table.

### Penetrance and Phenocopy Handling

Reduced penetrance and phenocopies can weaken segregation inference. This is especially important for adult-onset disease, cancer predisposition, common phenotypes, low-penetrance alleles, and disorders with variable expressivity.

- Do not treat an unaffected carrier as contradictory if the person is too young, incompletely evaluated, or the disease is known to be incompletely penetrant.
- Do not treat an affected non-carrier as definitive non-segregation if the phenotype is common, weakly specific, or compatible with a phenocopy.
- Downgrade PP1 or withhold it when penetrance assumptions are not stated and the pedigree relies heavily on unaffected carriers or affected non-carriers.

### Double-Counting Boundary

Strande et al. separate case-level and case-control evidence and warn against counting the same evidence twice. Apply the same principle here:

- Do not count the same individuals both as PP1 segregation evidence and as independent proband observations for another case-level evidence summary.
- Do not count the proband as both a PS4 affected case and extra PP1 segregation evidence from the same family observation.
- Do not use the same family both as the sole basis for PP1 and as independent case-control enrichment evidence.
- If a publication includes both family segregation and case-control data, use each individual only once, selecting the most informative evidence path.
- Do not count the same affected individual as both PP4 diagnostic-yield evidence and PS4 case-count evidence.
- Do not stack PP1 and PP4 beyond the +5.0 combined cap when both are derived from locus/phenotype segregation evidence.
- Do not add Biesecker 2024 points and the informative-meioses fallback together for the same pedigree.

---

## Applying PP1

Apply PP1 only when:

- The variant is the same variant being classified.
- The gene-disease relationship and inheritance model are appropriate.
- Affected status is clinically credible.
- Segregation is observed in informative relatives.
- Contradictory segregation is absent or adequately explained.

Report PP1 evidence as:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PP1 | [Supporting/Moderate/Strong] | Variant co-segregates with [disease] in [family count/pedigree details]; [LOD or informative meioses]; no unexplained non-segregation. | Strande et al. 2017; PMID:28552198; [primary family source] |
```

Use `PP1` for supporting strength, `PP1_Moderate` for moderate strength, and `PP1_Strong` for strong strength.

---

## Applying BS4 or Withholding PP1

Apply BS4 when a variant clearly fails to segregate with disease in a family and the non-segregation is not plausibly explained by phenotype mismatch, phenocopy, reduced penetrance, incorrect inheritance model, sample mix-up, or technical genotyping error.

Withhold PP1 rather than applying BS4 when:

- The family is too small or the relatives are not informative.
- Phenotype status is uncertain.
- Disease penetrance is reduced and unaffected carriers are not old enough or adequately evaluated.
- Affected non-carriers may represent phenocopies.
- The reported variant is not clearly the same variant being classified.
- The publication does not provide enough pedigree detail to verify segregation.

---

## Output Requirements

For each PP1 decision, explicitly report:

- Gene-disease context and inheritance model.
- Variant identity and qualifying-variant rationale.
- Diagnostic yield, phenotype specificity, and locus heterogeneity/homogeneity assumptions when PP4 interacts with PP1.
- LOD score or informative meioses, if available.
- Counting units used: co-segregating individuals, informative meioses, families, affected carriers, or informative unaffected relatives.
- Whether the proband was used only as the index case and not as an extra segregation event.
- Affected carriers and any affected non-carriers.
- Unaffected carriers and whether they are informative.
- Combined PP1/PP4 point total, cap, and selected code split when applicable.
- Evidence apportionment across variants on the same allele or linked loci, if applicable.
- Penetrance, phenocopy, age-of-onset, and phenotype-certainty assumptions.
- Whether any related evidence was excluded to avoid double counting.
- Figure/provenance confidence when evidence comes from a pedigree image, OCR, user-supplied correction, or inferred carrier.
- Final evidence code: `PP1`, `PP1_Moderate`, `PP1_Strong`, `BS4`, or `No PP1`.
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [segregation / non-segregation / phenotype specificity / diagnostic yield / none]

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize and verify HGVS variant identity. |
| `EnsemblVEP_annotate_hgvs` | Annotate transcript and molecular consequence. |
| `MyVariant_query_variants` | Retrieve aggregated variant annotations, ClinVar, and population fields. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Confirm gene-disease validity and inheritance. |
| `GenCC_search_gene` | Cross-check gene-disease assertions when ClinGen is incomplete. |
| `MedGen_search_conditions` / GeneReviews routes | Retrieve disease definition, inheritance, testing yield, phenotype specificity, and locus heterogeneity. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Retrieve family, pedigree, linkage, and segregation literature. |
| `ClinVar_search_variants` | Find curated or submitted segregation comments; verify with primary sources when possible. |

---

## Limitations

- This skill is a rule-refinement layer, not a new deterministic MCP tool.
- Strande et al. 2017 is a gene-disease validity framework; it informs gene-disease validity and evidence quality but is no longer the most specific PP1/BS4/PP4 scoring source when Biesecker et al. 2024 applies.
- Biesecker et al. 2024 provides a practical heuristic for simple pedigrees. Formal maximum-likelihood segregation analysis is still needed for complex pedigrees, low penetrance, high phenocopy, consanguinity, or rich family datasets.
- Current gene-specific VCEP guidance should supersede the default thresholds in this skill.
- Combined PP1/PP4 locus evidence is capped at +5.0 points and should be combined with independent variant-level evidence according to the ACMG/AMP classification combiner.

---

## Primary References

- Strande NT, Riggs ER, Buchanan AH, et al. Evaluating the Clinical Validity of Gene-Disease Associations: An Evidence-Based Framework Developed by the Clinical Genome Resource. Am J Hum Genet. 2017;100(6):895-906. PMID: 28552198. PMCID: PMC5473734. DOI: 10.1016/j.ajhg.2017.04.015.
- Supplemental information linked from PMC5473734: Document S1 (Figures S1-S65) and Document S2 (article plus Supplemental Data).
- Biesecker LG, Byrne AB, Harrison SM, Pesaran T, Schaffer AA, Shirts BH, Tavtigian SV, Rehm HL; ClinGen Sequence Variant Interpretation Working Group. ClinGen guidance for use of the PP1/BS4 co-segregation and PP4 phenotype specificity criteria for sequence variant pathogenicity classification. Am J Hum Genet. 2024;111(1):24-38. PMID: 38103548. PMCID: PMC10806742. DOI: 10.1016/j.ajhg.2023.11.009.
