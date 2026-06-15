# Phenotype-Dependent ACMG Criteria Summary

This reference lists ACMG/AMP evidence criteria that should not be applied without patient phenotype, affected status, unaffected status, or disease-match context.

## Criteria Commonly Requiring Phenotype Context

| Criterion | Phenotype-dependent requirement |
| --- | --- |
| `PP4` | Patient phenotype or family history must be highly specific for the disease/gene context. |
| `PS4` | Case enrichment requires affected-case definition and phenotype/disease ascertainment. |
| `PP1` | Segregation requires affected relatives to have the relevant phenotype. |
| `BS4` | Non-segregation requires reliable affected status and phenocopy/penetrance review. |
| `PM3` | In-trans evidence requires the proband to be affected with the relevant recessive disease. |
| `PS2` / `PM6` | De novo observations require phenotype consistency with the gene-disease relationship. |
| `BP5` | Alternate molecular basis must explain the patient's phenotype. |
| `BS2` | Healthy observation requires reliable unaffected status, age, penetrance, and disease ascertainment. |

## ACGS 2024 PP4 Practice Guidance

ACGS 2024 is used here as practice guidance, not as a separate selectable classification profile.

PP4 can be considered when the patient's phenotype is specific for:

- a single gene-disease entity;
- a rare recognizable syndrome with a narrow genetic differential;
- a rare combination of features where appropriate testing has excluded common alternatives;
- a validated disease-specific biomarker pattern, including biochemical, imaging, methylation, pathology, or treatment-response evidence.

Default PP4 handling:

| Context | Handling |
| --- | --- |
| Broad or nonspecific features only | No PP4 |
| Compatible phenotype but broad differential remains | Usually no PP4; VCEP-only supporting use |
| Rare and recognizable phenotype with narrow differential and appropriate testing | `PP4_Supporting` |
| Highly specific biomarker/clinical pattern with strong gene-disease fit | Consider `PP4_Moderate` |
| Near-pathognomonic phenotype or validated disease-defining biomarker profile | Consider `PP4_Strong` only with VCEP, MDT, or guideline-level support |

Double-counting guard:

- If phenotype specificity increases PS2/PM6 de novo strength, do not also apply PP4 from the same specificity.
- If a VCEP embeds phenotype specificity in PS4 case-counting or another criterion, do not add PP4 separately unless the VCEP permits it.
- Do not apply PP4 from disease background alone when the patient's actual phenotype is missing.

## Default Behavior When Phenotype Is Missing

- Do not apply the criterion.
- Mark it as `Not Assessed - phenotype required`.
- Ask the user for the minimal missing information.
- Continue assessing evidence criteria that do not require phenotype.

## Minimum Useful Phenotype Intake

- Proband clinical summary or HPO terms.
- Suspected disease.
- Age at onset and current age.
- Key positive and negative features.
- Family history and affected/unaffected relative status when relevant.
- Alternate molecular diagnosis when BP5 is considered.
- Penetrance, sex limitation, and age-dependent onset context when BS2 or segregation is considered.
