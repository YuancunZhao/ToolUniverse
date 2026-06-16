# ClinGen Multiple-Disorder Guidance Summary

## Sources

- ClinGen. Guidance Classifying Variants in Genes Associated with Multiple Disorders, Version 1. January 2024. User-provided PDF: `clingen_guidance_for_classifying_variants_in_genes_associated_with_multiple_disorders_v1.pdf`.
- Thaxton C, Good ME, DiStefano MT, Luo X, Andersen EF, Thorland E, Berg J, Martin CL, Rehm HL, Riggs ER; ClinGen Gene Curation Working Group; ClinGen Dosage Sensitivity Working Group. Utilizing ClinGen gene-disease validity and dosage sensitivity curations to inform variant classification. Human Mutation. 2022;43(8):1031-1040. PMID: 34694049. PMCID: PMC9035475. DOI: 10.1002/humu.24291.

ToolUniverse `PubMed_search_articles` confirmed the Thaxton et al. 2022 PMID, PMCID, DOI, journal, and abstract. The user supplied both PDFs. The January 2024 two-page guidance is treated as the primary operational rule source; Thaxton et al. 2022 is used for the gene-disease validity and dosage sensitivity rationale.

## Core Message

Variant pathogenicity must be assigned in the context of a disease entity and inheritance model. In genes associated with multiple disorders, evidence can be aggregated only when the conditions are sufficiently close and the disease mechanism is similar. Otherwise, evidence must be split and classifications should be condition-specific.

## Seven Categories

| Category | Example | Evidence handling |
| --- | --- | --- |
| Single condition with severity based on inheritance/dosage | `LDLR` familial hypercholesterolemia | Classify for one semidominant condition; aggregate monoallelic and biallelic observations. |
| Two distinct conditions with different inheritance but consistent mechanism | `ATM` dominant breast cancer and recessive ataxia-telangiectasia | Aggregate evidence; prefer separate condition records using the same evidence summary. |
| Single mechanism with phenotype spectrum or pleiotropy | `FBN1` Marfan spectrum | Aggregate evidence, but case-counting strength depends on phenotype specificity and frequency. |
| Multiple mutually exclusive conditions with distinct mechanisms | `RET` Hirschsprung disease and MEN2 | Do not aggregate; classify pathogenicity only for the supported condition/mechanism. |
| Multiple non-mutually exclusive conditions | `RYR1` malignant hyperthermia and myopathy | Do not aggregate; make separate classifications per condition. |
| Unclear disease distinction or mechanism | Variable | Use judgment; aggregate only if phenotypes are close and mechanism appears similar. |
| CNV encompassing multiple genes with distinct associations | Multi-gene CNV | Route to CNV/SV analysis; list associated diseases and genes with unknown associations. |

## Gene-Disease Validity and Dosage Interpretation

Thaxton et al. 2022 emphasizes that gene-disease validity and dosage sensitivity are distinct:

- Gene-disease validity evaluates whether pathogenic variants in a gene cause a disease by any mechanism.
- Dosage sensitivity evaluates whether heterozygous/hemizygous loss or gain is a disease mechanism.
- Definitive gene-disease validity does not automatically establish haploinsufficiency or triplosensitivity.
- A non-sufficient dosage score does not refute a disease caused by recessive, gain-of-function, dominant-negative, or other non-dosage mechanisms.
- Limited, Disputed, or Refuted gene-disease relationships should not support classifications above VUS for that disease.
- Moderate gene-disease validity usually should not support classifications above Likely Pathogenic without stronger disease-specific guidance.

## ACMG Overlay Translation

- Use this overlay before applying disease-dependent evidence criteria.
- Route mechanism uncertainty to `tooluniverse-acmg-dominant-negative-mechanism-refinement`.
- Route LoF-compatible conditions to `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`.
- Route CNV/SV contexts to `tooluniverse-structural-variant-analysis`.
- Route phenotype, PS4, PP1/BS4, PP4, and PM3 context to their existing overlays.
- Do not aggregate PS4 cases, PM3 in-trans observations, PP1 segregation, PP4 phenotype specificity, PS3/BS3 assays, or PS1/PM5 comparison variants across split disease mechanisms.

## Reporting Rule

Report classification as:

```text
[Variant] is [classification] for [disease entity] under [inheritance/mechanism].
```

When a gene has additional disorders:

```text
Evidence was not aggregated with [other disease] because [mechanism/inheritance/entity] differs.
```

or:

```text
Evidence was aggregated across [conditions] because ClinGen multiple-disorder guidance supports shared mechanism / semidominant severity spectrum / single disease spectrum.
```
