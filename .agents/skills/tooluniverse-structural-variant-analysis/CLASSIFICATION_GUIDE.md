# SV/CNV Evidence Routing Guide

This guide supports structural-variant evidence intake. It does not define a standalone germline ACMG classifier.

Final germline pathogenicity assessment must be performed by `tooluniverse-acmg-variant-classification` after overlay route audit, Evidence Compatibility Resolution, and final combine.

## SV Types

| Type | Abbreviation | Main evidence question |
| --- | --- | --- |
| Deletion | DEL | Does the event remove a LoF/HI-relevant gene, exon, transcript region, regulatory element, or critical domain? |
| Duplication | DUP | Does the event increase dosage, disrupt a transcript, create altered product, or affect regulation? |
| Inversion | INV | Does either breakpoint disrupt coding sequence, a known regulatory element, or a disease-relevant fusion context? |
| Translocation / breakend | TRA / BND | Does the event disrupt a gene, create a fusion, or separate gene and regulatory element? |
| Complex rearrangement | CPX | Which component event creates the disease-relevant consequence? |

## Dosage Sensitivity Context

| ClinGen dosage score | Intake interpretation |
| --- | --- |
| HI/TS 3 | Strong dosage-context signal; route to mechanism/PVS1/CNV-relevant overlays as appropriate. |
| HI/TS 2 | Emerging dosage-context signal; route for context review and possible VCEP/disease-specific handling. |
| HI/TS 1 or 0 | Insufficient dosage sensitivity by itself; route cautiously and document missing or negative context. |
| Dosage sensitivity unlikely | Benign-context or no-evidence route may be appropriate depending on population and clinical context. |

pLI/LOEUF and constraint metrics can support context but do not replace ClinGen dosage, gene-disease validity, transcript consequence, or VCEP rules.

## Population and Overlap Intake

Use reciprocal overlap for population and source comparison. Record the reciprocal-overlap threshold, affected genes, breakpoint precision, genome build, and whether the matched SV is truly comparable.

| Evidence pattern | Route candidate |
| --- | --- |
| High population SV frequency | BA1 exception-list review, BS1/benign-context review |
| Rare or absent population SV | PM2 absence/rarity overlay; default strength remains controlled by ClinGen SVI PM2 guidance |
| ClinVar/dbVar/DGVa source label | PP5/BP6 source-review overlay first; fan out only with primary evidence |
| DECIPHER or case-database overlap | PS4, PP1, PS2/PM6, PM3, PP4, or source-lead route depending on extracted evidence type |

## Candidate ACMG Routes

| SV/CNV evidence | Required route before counting |
| --- | --- |
| Whole-gene deletion or exon deletion in LoF/HI context | `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` |
| Exon-level or in-frame protein-length change | `tooluniverse-acmg-pm4-bp3-protein-length-refinement` |
| High/too-high allele frequency | `tooluniverse-acmg-ba1-exception-list-refinement` and/or `tooluniverse-acmg-benign-context-refinement` |
| Absence/rarity in population SV databases | `tooluniverse-acmg-pm2-absence-rarity-refinement` |
| De novo SV | `tooluniverse-acmg-de-novo-evidence-refinement` |
| Segregation / non-segregation | `tooluniverse-acmg-pp1-segregation-refinement` |
| Case-control/cohort enrichment | `tooluniverse-acmg-ps4-case-enrichment-refinement` |
| Biallelic recessive affected-proband evidence | `tooluniverse-acmg-pm3-in-trans-refinement` |
| Functional dosage/breakpoint assay | `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` |
| Source label or external classification | `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` |

## Compatibility Notes

- A CNV/SV consequence cannot be counted twice as both PVS1 and PM4 for the same primary effect.
- Whole-gene deletion dosage evidence should not be counted as separate PVS1 plus separate CNV dosage evidence unless a recognized framework explicitly allows the split.
- The same proband or family member cannot simultaneously support PS4, PM3, PS2/PM6, PP1, and PP4.
- Source labels are leads, not counted evidence.
- Low-confidence figure or OCR extraction from pedigrees, traces, or CNV plots is a lead only.

Use `tooluniverse-acmg-overlay-routing-core` Evidence Compatibility Resolution before any final qualitative or Bayesian combine.
