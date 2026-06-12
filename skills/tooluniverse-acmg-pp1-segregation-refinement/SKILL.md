---
name: tooluniverse-acmg-pp1-segregation-refinement
description: Refine ACMG/AMP PP1 co-segregation evidence assignment using ClinGen gene-disease validity principles from Strande et al. 2017. Use with ToolUniverse ACMG variant classification when family segregation, LOD score, informative meioses, pedigree evidence, penetrance, phenocopy, or BS4 non-segregation affects PP1 strength.
disable-model-invocation: true
---

# ACMG PP1 Segregation Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: PP1 co-segregation evidence and its strength levels. It adapts ClinGen gene-disease validity principles from Strande et al. 2017 to the ACMG/AMP variant-level PP1 workflow.

Strande et al. 2017 is a gene-disease clinical validity framework, not a variant-classification-only PP1 specification. Use it here as a structured evidence-quality overlay: qualify the variant, verify the gene-disease context, evaluate segregation statistically when possible, avoid double counting, and downgrade evidence when penetrance, phenocopy, or pedigree uncertainty weakens the inference.

---

## When to Use This Skill

Use this skill when any of the following are present:

- Published family segregation data for the variant.
- A reported or calculable LOD score for variant/disease co-segregation.
- Informative meioses, affected carriers, unaffected non-carriers, obligate carriers, or phase-resolved pedigree data.
- Apparent non-segregation, affected non-carriers, unaffected carriers, phenocopies, or reduced penetrance.
- Need to decide PP1, PP1_Moderate, PP1_Strong, no PP1, or BS4.
- Need to avoid double counting the same individuals as segregation evidence and case-control or proband-count evidence.

Do not use this skill to refine unrelated ACMG evidence criteria. De novo evidence belongs under PS2/PM6, population evidence under BA1/BS1/PM2, functional evidence under PS3/BS3, and phenotype specificity under PP4.

---

## Core Principle

PP1 is variant-level evidence that a variant co-segregates with disease in a family. It should be applied only when the observed segregation is consistent with the disease inheritance model, the variant is a plausible qualifying variant for the gene-disease mechanism, and the same evidence is not being counted elsewhere.

Use the most quantitative segregation evidence available:

1. Use a published LOD score when provided and methodologically credible.
2. If no LOD score is provided, use informative meioses or clearly reported segregation events.
3. If neither is available, record the pedigree observation but do not apply PP1.

---

## Evidence Retrieval Workflow

Use ToolUniverse retrieval tools before assigning PP1 strength.

1. **Confirm variant identity and transcript consequence**
   - Use `VariantValidator_validate_variant` to normalize HGVS notation.
   - Use `EnsemblVEP_annotate_hgvs` and `MyVariant_query_variants` to confirm consequence, ClinVar context, and population annotations.
   - Confirm that the variant is plausible for the disease mechanism and is not contradicted by high population frequency or other strong benign evidence.
   - If the disease may be dominant-negative, antimorphic, or mixed by variant class, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` to document why the segregating variant is a qualifying variant for that mechanism.

2. **Confirm gene-disease validity and inheritance**
   - Use `ClinGen_search_gene_validity` or `ClinGen_get_gene_validity` to establish the gene-disease relationship and asserted inheritance pattern.
   - Use GenCC, OMIM/Orphanet-derived tools, and disease literature when ClinGen is absent or incomplete.
   - Do not use PP1 to rescue a gene-disease relationship that is disputed, refuted, or unsupported for the disease being classified.

3. **Retrieve segregation evidence**
   - Use `PubMed_search_articles` and `EuropePMC_search_articles` with the gene, variant HGVS, disease name, "segregation", "pedigree", "family", "LOD", and "linkage".
   - Use `ClinVar_search_variants` or ClinVar-related tools to identify submitted segregation comments, but prefer primary literature or curated expert-panel evidence when available.
   - When segregation, affected status, carrier status, phase, or non-segregation is shown in a pedigree or figure, use `tooluniverse-literature-figure-evidence-extraction` to extract structured family evidence before applying PP1 or BS4 rules.

4. **Extract the pedigree evidence**
   - Record affected carriers, affected non-carriers, unaffected carriers, unaffected non-carriers, obligate carriers, number of independent families, phase, zygosity, and genotyping method.
   - Record whether the LOD score is variant-specific, locus-level, or gene-level.
   - Record disease age of onset, penetrance assumptions, phenocopy risk, phenotype certainty, and whether relatives are old enough to be informative.

5. **Choose the evidence code**
   - Apply PP1 strength only when the segregation is variant-specific and disease-consistent.
   - Apply BS4 when robust non-segregation cannot be explained by phenocopy, reduced penetrance, wrong phenotype, wrong disease model, or technical error.

---

## Strande-Informed Evidence Quality Rules

### Qualifying Variant Requirement

Count segregation evidence only when the variant is a plausible qualifying variant for the gene-disease pair:

- The molecular consequence fits the disease mechanism.
- For dominant-negative disease, the variant class plausibly produces the relevant altered product or has direct evidence for dominant interference.
- The inheritance model fits the family structure.
- The variant is not too common for the disease.
- The variant is not contradicted by strong benign evidence.
- The phenotype in the family fits the asserted disease.

If these are not met, do not apply PP1. Record the segregation observation as context only.

### LOD and Informative Meioses

Use a credible published LOD score when available. If the paper provides only raw pedigree observations, use informative meioses as the operational fallback. Do not fabricate a LOD score unless a validated disease-specific calculator or VCEP method is available.

Default strength mapping when no gene-specific VCEP rule supersedes it:

| Evidence | Default PP1 strength |
|----------|----------------------|
| LOD >= 3, or >= 7 informative meioses with no contradictory segregation | PP1_Strong |
| LOD 1.5 to < 3, or 5-6 informative meioses with no contradictory segregation | PP1_Moderate |
| LOD 0.5 to < 1.5, or 2-4 informative meioses with no contradictory segregation | PP1 |
| Single uninformative family observation, no LOD, or unclear phase/phenotype | Do not apply PP1 |

Prefer disease-specific ClinGen VCEP PP1 thresholds when available and current.

### Penetrance and Phenocopy Handling

Reduced penetrance and phenocopies can weaken segregation inference. This is especially important for adult-onset disease, cancer predisposition, common phenotypes, low-penetrance alleles, and disorders with variable expressivity.

- Do not treat an unaffected carrier as contradictory if the person is too young, incompletely evaluated, or the disease is known to be incompletely penetrant.
- Do not treat an affected non-carrier as definitive non-segregation if the phenotype is common, weakly specific, or compatible with a phenocopy.
- Downgrade PP1 or withhold it when penetrance assumptions are not stated and the pedigree relies heavily on unaffected carriers or affected non-carriers.

### Double-Counting Boundary

Strande et al. separate case-level and case-control evidence and warn against counting the same evidence twice. Apply the same principle here:

- Do not count the same individuals both as PP1 segregation evidence and as independent proband observations for another case-level evidence summary.
- Do not use the same family both as the sole basis for PP1 and as independent case-control enrichment evidence.
- If a publication includes both family segregation and case-control data, use each individual only once, selecting the most informative evidence path.

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
- LOD score or informative meioses, if available.
- Affected carriers and any affected non-carriers.
- Unaffected carriers and whether they are informative.
- Penetrance, phenocopy, age-of-onset, and phenotype-certainty assumptions.
- Whether any related evidence was excluded to avoid double counting.
- Final evidence code: `PP1`, `PP1_Moderate`, `PP1_Strong`, `BS4`, or `No PP1`.

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize and verify HGVS variant identity. |
| `EnsemblVEP_annotate_hgvs` | Annotate transcript and molecular consequence. |
| `MyVariant_query_variants` | Retrieve aggregated variant annotations, ClinVar, and population fields. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Confirm gene-disease validity and inheritance. |
| `GenCC_search_gene` | Cross-check gene-disease assertions when ClinGen is incomplete. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Retrieve family, pedigree, linkage, and segregation literature. |
| `ClinVar_search_variants` | Find curated or submitted segregation comments; verify with primary sources when possible. |

---

## Limitations

- This skill is a rule-refinement layer, not a new deterministic MCP tool.
- Strande et al. 2017 is a gene-disease validity framework; it informs PP1 evidence quality but does not replace ACMG/AMP or gene-specific VCEP PP1 rules.
- Supplementary Document S1 contains Figure S1, which is the article's detailed segregation-by-LOD reference. If exact Figure S1 scoring is required, consult the supplement or current ClinGen Gene Curation SOP directly.
- Current gene-specific VCEP guidance should supersede the default thresholds in this skill.
- PP1 is rarely decisive alone; it should be combined with independent pathogenic evidence according to the ACMG/AMP classification combiner.

---

## Primary References

- Strande NT, Riggs ER, Buchanan AH, et al. Evaluating the Clinical Validity of Gene-Disease Associations: An Evidence-Based Framework Developed by the Clinical Genome Resource. Am J Hum Genet. 2017;100(6):895-906. PMID: 28552198. PMCID: PMC5473734. DOI: 10.1016/j.ajhg.2017.04.015.
- Supplemental information linked from PMC5473734: Document S1 (Figures S1-S65) and Document S2 (article plus Supplemental Data).
