---
name: tooluniverse-acmg-ps4-case-enrichment-refinement
description: Refine ACMG/AMP PS4 case-enrichment evidence for rare-disease variant classification using formal case-control/cohort evidence, VCEP-specific rules, practice/local rare-disease affected-case refinements, ancestry matching, gnomAD control caveats, recessive PM3 routing, literature extraction, and duplicate-report checks.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG PS4 Case-Enrichment Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: `PS4`, the increased prevalence of a variant in affected individuals compared with controls.

Formal case-control or cohort enrichment and current VCEP specifications are the primary PS4 paths. ACGS 2024 rare-disease affected-case guidance is used only as `practice/local refinement` when formal enrichment data are unavailable and local policy accepts that approach. It does not replace VCEP specifications, disease-specific case-count rules, or formal statistical enrichment analysis when those are available.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PS4-specific logic. Formal case-control or cohort PS4 evidence is literature/cohort evidence; it does not require user-supplied patient phenotype when the source defines the affected cohort and disease context sufficiently.

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

Guidance authority:

- Formal case-control/cohort enrichment follows `ACMG/AMP baseline` PS4 language unless a current VCEP supplies `VCEP-specific` thresholds.
- ACGS rare-disease affected-case counting is `practice/local refinement`, not a generic ClinGen/SVI primary PS4 rule.
- Database or publication assertions that PS4 was applied are `source lead only` until the case evidence is extracted and routed.

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

4. **Assess disease context, phenotype, and unrelatedness**
   - For formal case-control, cohort, or meta-analysis evidence, extract the study's disease/case definition, affected-cohort ascertainment, controls, ancestry handling, and statistics from the publication or cohort metadata. User-supplied patient phenotype is not required if the study definition is sufficient.
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when affected-case phenotype specificity, patient-level disease match, or rare-disease case-count context is unclear.
   - For rare-disease affected-case counting, count only unrelated affected probands unless a VCEP specifies otherwise.
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
- The affected cohort or case definition matches the disease being classified.
- Controls are ancestry-matched or population stratification is addressed.
- The variant is significantly enriched in cases compared with controls.
- Confidence intervals and sample sizes support the claimed strength.

Use VCEP thresholds when available. Without a VCEP, report odds ratio, confidence interval, p value, case/control counts, and any ancestry mismatch before assigning strength.

Do not require a separate user-supplied proband phenotype for this evidence type. The required clinical context is the study's case definition and disease ascertainment, which should be retrieved from the article, supplement, cohort description, or database record.

### Rare-Disease Affected-Case Evidence

When formal case-control data are unavailable, ACGS 2024 may be used as `practice/local refinement` only if local policy accepts rare-disease affected-case counting:

| Evidence | Practice/local PS4 assignment |
| --- | --- |
| One unrelated affected individual with a rare and specific phenotype, variant absent from gnomAD/population controls, and no better criterion captures the evidence | `PS4_Supporting` |
| Two or more unrelated affected individuals with rare and specific phenotype, variant absent from gnomAD/population controls, and duplicate reports excluded | `PS4_Moderate` |
| Recessive affected biallelic cases with genotype/phase suitable for PM3 | Route to PM3, do not count as PS4 |
| Common, late-onset, low-penetrance, or broad phenotype without formal enrichment analysis | Usually no PS4, or `status: not_assessed` if enrichment context is missing |

Do not use PS4 merely because a database states "Pathogenic" or because a variant appears in a disease database without case details.

Unlike formal case-control evidence, rare-disease affected-case counting requires case-level disease/phenotype specificity and unrelatedness. If those facts are absent from the report or database, mark PS4 as `not_assessed` rather than assuming them.

### Founder, Haplotype, and Mutation-Positive Cohort Evidence

Founder haplotypes, shared ancestry, repeated case-series recurrence, and mutation-positive cohort summaries require extra caution:

- A shared founder haplotype can show recurrence but may reduce independence between cases.
- A cohort denominator such as "gene mutation-positive probands" is not the same as all affected disease cases and must not be used as a formal case-control denominator unless the study design supports that comparison.
- gnomAD can be used as population-control context only after ancestry match, disease ascertainment, and possible inclusion of affected individuals are considered.
- Founder recurrence should usually be routed to rare-disease affected-case counting, downgraded, or marked `status: not_assessed` unless formal cohort/case-control statistics or a VCEP rule support stronger PS4 use.
- Do not calculate an OR against gnomAD from a founder or mutation-positive cohort without reporting case ascertainment, control suitability, ancestry match, and duplicate/relatedness review.

---

## Ancestry and gnomAD Caveats

Before using gnomAD as a control population:

- Check whether the case ancestry is represented in gnomAD.
- Use maximum ancestry AF, not just global AF.
- Be cautious when the disorder may be present in gnomAD participants, especially adult-onset, cardiovascular, low-penetrance, or incompletely ascertained disease.
- Do not use population absence if coverage, mapping, build, or allele representation is unclear.

If ancestry matching is poor, report `status: not_assessed` with reason `PS4 ancestry/control comparison inadequate`, or downgrade the evidence unless a disease-specific rule supports use.

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

If case-enrichment evidence is mentioned but incomplete, mark PS4 as `status: not_assessed` with reason `case enrichment data required` and ask only for the fields missing from the evidence type being used.

```text
PS4 requires affected-case enrichment or unrelated affected-case evidence. For formal case-control/cohort evidence, please provide the disease/case definition, case and control counts, ancestry handling, odds ratio or enrichment statistics, confidence interval or p value, and cohort source. For rare-disease affected-case counting, please provide the number of unrelated affected carriers, phenotype/disease used for ascertainment, ancestry or cohort details, population-control comparison, whether cases are duplicate reports, and whether biallelic recessive cases should instead be scored under PM3.
```

---

## Output Format

```markdown
PS4 case-enrichment refinement:
- Variant: [HGVS/genomic allele]
- Disease context: [disease, inheritance, gene validity]
- Evidence type: [case-control / cohort / rare-disease case count / database-only / unclear]
- Affected carriers: [count, unrelatedness, phenotype specificity]
- Control source: [gnomAD/case-control cohort/other], ancestry match: [adequate/uncertain/poor]
- Population frequency: [global AF, max ancestry AF, AC/AN, homozygotes]
- Founder/haplotype context: [none / founder suspected / shared haplotype / mutation-positive cohort], independence impact [summary]
- Duplicate-report check: [none found / concern / not_assessed]
- Recessive PM3 routing: [not applicable / route to PM3]
- De novo or segregation routing: [not applicable / route to PS2-PM6 / route to PP1]
- Applied evidence: [PS4 / PS4_Moderate / PS4_Supporting / No PS4 / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Guidance authority: [ACMG/AMP baseline / VCEP-specific / practice/local refinement / source lead only]
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
