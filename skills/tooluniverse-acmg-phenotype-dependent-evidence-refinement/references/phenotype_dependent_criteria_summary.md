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

Biesecker et al. 2024 / ClinGen SVI is used when PP4 phenotype specificity interacts with PP1 co-segregation or BS4 non-segregation. In that setting, PP4 and PP1 are coupled locus evidence, not fully independent criteria.

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
- If PP4 is combined with PP1 or BS4, route to `tooluniverse-acmg-pp1-segregation-refinement` and apply the ClinGen 2024 combined points cap.
- A published affected individual can count as PP4 or PS4, but not both.
- Do not apply PP4 from disease background alone when the patient's actual phenotype is missing.

## ClinGen 2024 PP1/BS4/PP4 Combined Guidance

When PP4 and PP1/BS4 use the same family, phenotype, locus, or diagnostic-yield evidence:

- collect the exact phenotype definition, diagnostic yield, comparable testing method, inheritance, locus homogeneity/heterogeneity, and family affected/genotype status;
- convert diagnostic yield to PP4 points only when yield is robust for the gene-phenotype dyad;
- add PP1/BS4 points only when segregation or non-segregation contributes information beyond phenotype/locus specificity;
- cap combined PP1 plus PP4 evidence at +5.0 points per variant;
- apportion evidence across multiple plausible variants on an implicated allele before assigning PP1/PP4 strength.

Do not use high PP4 strength for incomplete phenotyping, broad endophenotypes, or diagnostic yields below about 20% unless a VCEP permits it.

## Default Behavior When Phenotype Is Missing

- Do not apply the criterion.
- Use `applied_evidence: none` with `status: not_assessed` and `reason: phenotype required`.
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
- Diagnostic yield and tested/excluded loci when PP4 interacts with PP1/BS4.

## References

- Biesecker LG, Byrne AB, Harrison SM, Pesaran T, Schaffer AA, Shirts BH, Tavtigian SV, Rehm HL; ClinGen Sequence Variant Interpretation Working Group. ClinGen guidance for use of the PP1/BS4 co-segregation and PP4 phenotype specificity criteria for sequence variant pathogenicity classification. Am J Hum Genet. 2024;111(1):24-38. PMID: 38103548. PMCID: PMC10806742. DOI: 10.1016/j.ajhg.2023.11.009.
