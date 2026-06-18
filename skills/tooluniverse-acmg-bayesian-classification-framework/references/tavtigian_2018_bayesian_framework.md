# Tavtigian 2018 Bayesian ACMG/AMP Framework Summary

## Source

- Tavtigian SV, Greenblatt MS, Harrison SM, Nussbaum RL, Prabhu SA, Boucher KM, Biesecker LG; ClinGen Sequence Variant Interpretation Working Group. Modeling the ACMG/AMP variant classification guidelines as a Bayesian classification framework. Genetics in Medicine. 2018;20(9):1054-1060.
- PMID: 29300386.
- PMCID: PMC6336098.
- DOI: 10.1038/gim.2017.210.
- Supplement: Supplemental Table S1, `NIHMS915467-supplement-Supplemental_Table_S1.xlsx`.

## Provenance

- `full_text_read`: yes. Full text was retrieved from PubMed Central / Europe PMC JATS for PMCID PMC6336098.
- `supplement_read`: yes. Supplemental Table S1 was retrieved from PMC article instance `6336098` after PMC proof-of-work validation and read as an Excel workbook.
- Supplement workbook sheet: `ACMG_.10`.
- Supplement workbook purpose: an Excel calculator encoding ACMG/AMP 2015 combining criteria and a custom two-rule calculator using the Tavtigian Bayesian parameters.

## Main Modeling Assumptions

Tavtigian et al. modeled the ACMG/AMP 2015 combining criteria as a naive Bayesian classifier:

- Evidence types are treated as independent for multiplication of odds.
- BA1 is excluded because it is stand-alone benign evidence and acts as a pre-Bayesian filter.
- Pathogenic evidence strengths are exponentially scaled.
- Benign evidence strengths use reciprocal odds.
- The model uses a prior probability, odds of pathogenicity for Very Strong evidence, and an exponential progression factor.

Supplemental Table S1 states that the three editable yellow cells are:

- Prior probability in cell C10, starting value `0.10`.
- OddsPath for Very Strong in cell C11, starting value `350`.
- Exponent controlling Supporting / Moderate / Strong relative to Very Strong in cell C12, starting value `2.0`.

## Default Parameters

| Parameter | Default |
| --- | ---: |
| Prior probability (`Prior_P`) | `0.10` |
| Very Strong odds of pathogenicity (`OPVSt`) | `350` |
| Exponential progression (`X`) | `2.0` |

With these defaults:

| Evidence strength | OddsPath |
| --- | ---: |
| Pathogenic Supporting | `2.0797` |
| Pathogenic Moderate | `4.3253` |
| Pathogenic Strong | `18.7083` |
| Pathogenic Very Strong | `350` |
| Benign Supporting | `0.4808` |
| Benign Strong | `0.05345` |

## Points Representation

The same model can be expressed as integer points:

| Direction | Strength | Points |
| --- | --- | ---: |
| Pathogenic | VeryStrong | `+8` |
| Pathogenic | Strong | `+4` |
| Pathogenic | Moderate | `+2` |
| Pathogenic | Supporting | `+1` |
| Benign | Strong | `-4` |
| Benign | Supporting | `-1` |

These points are a reporting and calculation representation of the Tavtigian exponential model. They are not evidence-assignment rules.

## Formula

For default `OPVSt = 350` and `X = 2.0`:

```text
OddsPath = 350^(total_points / 8)
Post_P = OddsPath * Prior_P / ((OddsPath - 1) * Prior_P + 1)
```

Equivalent count formula:

```text
OP = OPVSt^(
  N_PSu / 8
+ N_PM / 4
+ N_PSt / 2
+ N_PVSt
- N_BSu / 8
- N_BSt / 2
)
```

The original ACMG/AMP framework did not include benign Moderate, benign VeryStrong, or benign StandAlone in the Bayesian equation. BA1 is excluded from the equation.

## Classification Thresholds

Tavtigian et al. used probability thresholds consistent with the ACMG/AMP five-tier framework:

| Posterior probability | Tier |
| --- | --- |
| `> 0.99` | Pathogenic |
| `> 0.90` to `<= 0.99` | Likely Pathogenic |
| `0.10` to `0.90` | VUS |
| `>= 0.001` to `< 0.10` | Likely Benign |
| `< 0.001` | Benign |

Boundary values should be reported explicitly because Supplemental Table S1 produces values such as `0.899910` for some combinations near the likely-pathogenic boundary.

## Key Supplemental Table S1 Results

With Prior_P `0.10`, OPVSt `350`, and X `2.0`:

| Evidence combination | Points | OddsPath | Posterior |
| --- | ---: | ---: | ---: |
| PVS1 alone | `+8` | `350.00` | `0.97493` |
| PVS1 + one Moderate | `+10` | `1513.86` | `0.99409` |
| PVS1 + one Strong | `+12` | `6547.90` | `0.99863` |
| Two Strong pathogenic criteria | `+8` | `350.00` | `0.97493` |
| Two Strong + one Supporting benign | `+7` | `168.29` | about `0.949` |
| Two Strong + two Supporting benign | `+6` | `80.92` | `0.89991` |
| Two Strong + one Strong benign | `+4` | `18.71` | `0.67519` |
| Two Supporting benign criteria | `-2` | `0.2312` | `0.02505` |
| Strong benign + Supporting benign | `-5` | `0.02570` | `0.00285` |
| Two Strong benign criteria | `-8` | `0.00286` | `0.00032` |

## Internal Consistency Observations

Tavtigian et al. identified two internal consistency issues in the ACMG/AMP 2015 qualitative table:

- Likely Pathogenic rule `PVS1 + one Moderate` reaches posterior probability about `0.994`, comparable to several Pathogenic combinations.
- Pathogenic rule `two Strong` reaches posterior probability about `0.975`, below the Pathogenic threshold and in the Likely Pathogenic range.

These are combination-framework observations. They should not be used to alter whether PVS1, PS, PM, PP, BS, or BP evidence applies.

## Implementation Boundaries

- Use this framework only after evidence-specific overlays or VCEP rules have assigned strengths.
- Do not derive evidence strengths from points.
- Do not include BA1 in points.
- Do not count source assertions, unread full text, unread supplements, or unreviewed figures.
- Later ClinGen or VCEP benign strength levels require explicit conversion policy before entering Tavtigian-style points.
