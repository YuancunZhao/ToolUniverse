---
name: tooluniverse-acmg-ps4-case-enrichment-refinement
description: Refine ACMG/AMP PS4 case-enrichment evidence for rare-disease variant classification using ACGS 2024 practice guidance, case-control evidence, affected case counts, ancestry matching, gnomAD control caveats, recessive PM3 routing, literature extraction, and duplicate-report checks.
disable-model-invocation: true
---

# ACMG PS4 Case-Enrichment Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: `PS4`, the increased prevalence of a variant in affected individuals compared with controls.

It uses ACGS 2024 rare-disease practice guidance to refine how PS4 is considered when formal case-control studies are unavailable. It does not replace VCEP specifications, disease-specific case-count rules, or formal statistical enrichment analysis when those are available.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PS4-specific logic.

---

## When to Use This Skill

Use this skill when:

- A variant is reported in affected individuals or case series.
- A case-control study, cohort, meta-analysis, or odds ratio is available.
- The main ACMG workflow is considering PS4 for a rare disease.
- Literature reports one or more unrelated affected probands with the same variant.
- The same evidence could instead be PM3 for a recessive biallelic observation.
- The source is a paper table, supplement, case report, ClinVar assertion, DECIPHER entry, or database record that may duplicate another report.

Do not use this skill to count de novo evidence; use `tooluniverse-acmg-de-novo-evidence-refinement`. Do not use this skill for recessive biallelic case counting when genotype/phase information supports PM3.

---

## Core Principle

PS4 requires affected-case enrichment, not just a variant mention.

Prefer formal case-control or cohort evidence with an odds ratio, confidence interval, and matched controls. In rare-disease practice, where such data are often unavailable, PS4 may be applied cautiously from unrelated affected-case observations when the phenotype is rare and specific and the variant is absent or sufficiently rare in population databases.

---

## Evidence Retrieval Workflow

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant`, `ClinGenAR_lookup_allele`, `EnsemblVEP_annotate_hgvs`, or `MyVariant_query_variants`.
   - Record transcript, genomic allele, rsID/CA ID, protein consequence, disease, inheritance, and variant class.

2. **Retrieve population-control context**
   - Use `gnomad_search_variants`, `gnomad_get_variant`, `EnsemblVar_get_population_frequencies`, `dbsnp_get_frequencies`, or `MyVariant_query_variants`.
   - Record maximum ancestry AF, allele count, homozygote/hemizygote count, population representation, and quality/coverage concerns.
   - Treat gnomAD as an imperfect control source when the disease population may be included in gnomAD or ancestry matching is poor.

3. **Retrieve case evidence**
   - Use `ClinVar_search_variants`, `ClinVar_get_variant`, ClinGen ERepo tools, `PubMed_search_articles`, and `EuropePMC_search_articles`.
   - Use `tooluniverse-literature-deep-research` for publications, case tables, supplements, and multi-paper de-duplication.
   - Use `tooluniverse-literature-figure-evidence-extraction` if affected cases or segregation/case status are shown in pedigrees, tables rendered as images, or figure panels.

4. **Assess phenotype and unrelatedness**
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` to confirm that affected individuals have a phenotype matching the gene-disease context.
   - Count only unrelated affected probands unless a VCEP specifies otherwise.
   - De-duplicate the same individual reported across ClinVar, literature, DECIPHER, or database records.

5. **Choose PS4 versus another criterion**
   - For rare recessive biallelic observations with genotype and phase data, route to `tooluniverse-acmg-pm3-in-trans-refinement` instead of PS4.
   - For de novo observations, route to `tooluniverse-acmg-de-novo-evidence-refinement`.
   - For segregation within families, route to `tooluniverse-acmg-pp1-segregation-refinement`.

---

## Evidence Assignment

### Formal Case-Control Evidence

Apply PS4 based on formal enrichment when:

- Cases and controls are defined clearly.
- Case phenotype matches the disease being classified.
- Controls are ancestry-matched or population stratification is addressed.
- The variant is significantly enriched in cases compared with controls.
- Confidence intervals and sample sizes support the claimed strength.

Use VCEP thresholds when available. Without a VCEP, report odds ratio, confidence interval, p value, case/control counts, and any ancestry mismatch before assigning strength.

### Rare-Disease Affected-Case Evidence

When formal case-control data are unavailable, ACGS 2024 supports cautious rare-disease use:

| Evidence | Default PS4 assignment |
| --- | --- |
| One unrelated affected individual with a rare and specific phenotype, variant absent from gnomAD/population controls, and no better criterion captures the evidence | `PS4_Supporting` |
| Two or more unrelated affected individuals with rare and specific phenotype, variant absent from gnomAD/population controls, and duplicate reports excluded | `PS4_Moderate` |
| Recessive affected biallelic cases with genotype/phase suitable for PM3 | Route to PM3, do not count as PS4 |
| Common, late-onset, low-penetrance, or broad phenotype without formal enrichment analysis | Usually no PS4 or PS4 not assessable |

Do not use PS4 merely because a database states "Pathogenic" or because a variant appears in a disease database without case details.

---

## Ancestry and gnomAD Caveats

Before using gnomAD as a control population:

- Check whether the case ancestry is represented in gnomAD.
- Use maximum ancestry AF, not just global AF.
- Be cautious when the disorder may be present in gnomAD participants, especially adult-onset, cardiovascular, low-penetrance, or incompletely ascertained disease.
- Do not use population absence if coverage, mapping, build, or allele representation is unclear.

If ancestry matching is poor, report `PS4 not assessable` or downgrade the evidence unless a disease-specific rule supports use.

---

## Double Counting

Avoid double counting the same affected observation:

- Do not count the same proband as PS4 and PM3 for a recessive biallelic case.
- Do not count the same proband as PS4 and PS2/PM6 if the key evidence is de novo status rather than case enrichment.
- Do not use family members as independent PS4 cases when the evidence is segregation; use PP1/BS4.
- Do not count the same case from both a publication and ClinVar unless independence is confirmed.
- Do not use PP4 separately for the same case-count evidence if a VCEP or local rule merges phenotype specificity into PS4.

---

## Missing-Information Behavior

If case-enrichment evidence is mentioned but incomplete, mark PS4 as `Not Assessed - case enrichment data required` and ask for targeted fields.

```text
PS4 requires affected-case enrichment or unrelated affected-case evidence. Please provide the number of unrelated affected carriers, phenotype/disease used for ascertainment, ancestry or cohort details, population-control comparison, whether cases are duplicate reports, and whether biallelic recessive cases should instead be scored under PM3.
```

---

## Output Format

```markdown
PS4 case-enrichment refinement:
- Variant: [HGVS/genomic allele]
- Disease context: [disease, inheritance, gene validity]
- Evidence type: [case-control / cohort / rare-disease case count / database-only / not assessable]
- Affected carriers: [count, unrelatedness, phenotype specificity]
- Control source: [gnomAD/case-control cohort/other], ancestry match: [adequate/uncertain/poor]
- Population frequency: [global AF, max ancestry AF, AC/AN, homozygotes]
- Duplicate-report check: [none found / concern / not assessable]
- Recessive PM3 routing: [not applicable / route to PM3]
- De novo or segregation routing: [not applicable / route to PS2-PM6 / route to PP1]
- Applied evidence: [PS4 / PS4_Moderate / PS4_Supporting / No PS4 / Not Assessed]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [case-control / affected-case count / none]
```

---

## Tool Parameter Reference

| Tool or skill | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Normalize variant and transcript. |
| `ClinGenAR_lookup_allele` | Resolve canonical allele and external records. |
| `ClinVar_search_variants` / `ClinVar_get_variant` | Identify case assertions and cited reports. |
| `gnomad_search_variants` / `gnomad_get_variant` | Population-control allele count and ancestry AF. |
| `EnsemblVar_get_population_frequencies` / `MyVariant_query_variants` | Population fallback and aggregated annotation. |
| `MedGen_search_conditions`, HPO/MONDO/Monarch tools | Disease and phenotype matching. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Literature case evidence. |
| `tooluniverse-literature-deep-research` | Structured publication, table, supplement, and duplicate-report review. |
| `tooluniverse-literature-figure-evidence-extraction` | Visual case evidence, pedigree, and figure extraction. |
| `tooluniverse-acmg-pm3-in-trans-refinement` | Recessive biallelic case scoring. |

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868.
- ACGS Best Practice Guidelines for Variant Classification in Rare Disease 2024, v1.2, sections on PS4 and integration of clinical and scientific data.
- Current ClinGen VCEP specifications for disease-specific case-count and PS4 rules.
