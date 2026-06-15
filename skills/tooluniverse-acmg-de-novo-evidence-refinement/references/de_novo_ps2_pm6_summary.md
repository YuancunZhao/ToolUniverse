# SVI PS2/PM6 De Novo Evidence Summary

This reference summarizes ClinGen Sequence Variant Interpretation Recommendation for De Novo Criteria (PS2 and PM6), version 1.1.

## Core Rule

Use a point-based system. Each unrelated de novo occurrence receives points based on phenotype specificity and whether parental relationships are confirmed. Sum points across independent occurrences and map the total to PS2/PM6 evidence strength.

The v1.1 clarification is that confirmed versus assumed refers to parental relationships, not whether the variant itself is de novo.

## Points Per Proband

| Phenotypic consistency | Confirmed parental relationships | Unconfirmed parental relationships |
| --- | ---: | ---: |
| Phenotype highly specific for the gene | 2 | 1 |
| Phenotype consistent with the gene but not highly specific | 1 | 0.5 |
| Phenotype consistent but not highly specific and high genetic heterogeneity | 0.5 | 0.25 |
| Phenotype not consistent with the gene | 0 | 0 |

High-genetic-heterogeneity observations may contribute at most 1 point to the overall score.

No points are awarded if the parents have not been tested for parentage or for the variant.

## Strength Thresholds

| Total points | Evidence strength |
| ---: | --- |
| 0.5 | Supporting: `PS2_Supporting` or `PM6_Supporting` |
| 1 | Moderate: `PS2_Moderate` or `PM6` |
| 2 | Strong: `PS2` or `PM6_Strong` |
| 4 | Very Strong: `PS2_VeryStrong` or `PM6_VeryStrong` |

Use the highest threshold met. A total of 3 points is Strong, not Very Strong.

## PS2 Versus PM6 Label

- Use PS2 labels when at least one counted occurrence has confirmed parental relationships.
- Use PM6 labels when all counted occurrences have unconfirmed parental relationships.
- For mixed confirmed and unconfirmed observations, report each point source and use the PS2 label for the combined evidence.

## Do Not Apply PS2/PM6 When

- No parental genotype information is provided.
- Parents were not tested for the variant.
- Only one parent was tested, unless a current VCEP allows a reduced score.
- Only a "sporadic" statement is provided without variant-level parental testing.
- The proband phenotype is missing or mismatched.
- The variant is inherited.
- The observation is duplicate or circular.
- Parentage, sample identity, or mosaicism concerns make the evidence unreliable.

## Inheritance-Specific Considerations

- X-linked inheritance: a de novo variant in an unaffected carrier mother may count if family history is consistent and she has no other affected male relatives apart from affected son(s).
- Autosomal recessive inheritance: if no additional pathogenic or likely pathogenic variant is identified, decrease final evidence strength by one level.
- Apparent germline mosaicism: for multiple affected siblings with both parents negative, parental relationships must be confirmed for de novo criteria to apply.

## Missing Information

When de novo evidence is considered but incomplete, request:

- Proband phenotype/HPO terms and suspected disease.
- Mother and father genotypes.
- Parentage confirmation status.
- Testing method/sample type.
- Parental mosaicism assessment.
- Source of the de novo claim.
- Number of unrelated de novo observations and duplicate-report status.
