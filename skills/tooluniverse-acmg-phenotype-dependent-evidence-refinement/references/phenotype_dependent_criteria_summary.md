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
