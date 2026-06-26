---
name: tooluniverse-acmg-bayesian-classification-framework
description: Convert already-routed and validator-passing ACMG/AMP evidence strengths into Tavtigian et al. 2018 Bayesian points, OddsPath, posterior probability, and a structured final classification report. Use only after evidence-specific overlays or VCEP rules have assigned counted evidence, compatibility resolution has completed, and the ACMG assessment bundle validator returns PASS.
disable-model-invocation: true
---

# ACMG Bayesian Classification Framework

This skill is the final evidence-combination layer for ToolUniverse ACMG/AMP variant classification. It follows Tavtigian et al. 2018, "Modeling the ACMG/AMP Variant Classification Guidelines as a Bayesian Classification Framework", PMID: 29300386, PMCID: PMC6336098, DOI: 10.1038/gim.2017.210.

Use this skill only after the base ACMG workflow, `tooluniverse-acmg-overlay-routing-core`, evidence-specific overlays, evidence compatibility resolution, any applicable VCEP specification, and `tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py` have completed successfully. This skill does not retrieve primary evidence, does not decide whether a criterion is met, and does not change any evidence-specific threshold.

Final-output hard gate: a final Bayesian tier requires a machine-checkable `acmg_assessment_bundle` and a validator summary block equivalent to:

```json
{"validator_status":"PASS","violations":[]}
```

Without validator `PASS`, this skill may show a Bayesian calculation draft for review, but the report must keep `classification_status: draft classification` and must not present `Pathogenic`, `Likely Pathogenic`, `VUS`, `Likely Benign`, or `Benign` as final.

---

## When to Use This Skill

Use this skill when:

- The report has a completed overlay route audit.
- Every counted evidence item has route outcome `overlay_applied` or `overlay_deferred_to_vcep`.
- Evidence compatibility resolution has produced `current_counted_evidence_resolved`.
- `unresolved_conflicts` is empty.
- The `acmg_assessment_bundle` validates with `validator_status: PASS`.
- The user needs a posterior probability, Bayesian points, or a more readable final combination summary.
- Pathogenic and benign evidence conflict and the qualitative ACMG/AMP 2015 table would otherwise leave the result as VUS without showing the quantitative balance.
- A final report should use the standardized phase structure defined below.

Do not use this skill when:

- BA1 is valid as stand-alone benign evidence. BA1 is a pre-Bayesian gate and should short-circuit to Benign.
- Any counted evidence item lacks an overlay or VCEP route outcome.
- Evidence compatibility resolution has not been run.
- Evidence compatibility resolution reports unresolved conflicts.
- The `acmg_assessment_bundle` is absent, invalid, or has validator status `DRAFT_ONLY` or `FAIL`.
- A VCEP or disease-specific specification provides a required alternate combining framework.
- The evidence table contains only source assertions, abstract-only evidence, inaccessible full text, unread supplements, or low-confidence visual extraction without primary-evidence routing.

---

## Evidence Inputs

Input must be `current_counted_evidence_resolved` after overlay review and evidence compatibility resolution. Each row should include:

- `criterion`: ACMG code, such as `PVS1`, `PM2`, `PP3`, `BS1`, or `BP4`.
- `strength`: `VeryStrong`, `Strong`, `Moderate`, or `Supporting`.
- `direction`: `pathogenic` or `benign`.
- `route_outcome`: `overlay_applied` or `overlay_deferred_to_vcep`.
- `guidance_authority`: `ClinGen/SVI primary`, `ACMG/AMP baseline`, `VCEP-specific`, or `practice/local refinement`.
- `source`: primary source or VCEP specification supporting the routed evidence.

If a row is a source assertion only, a lead, an unreviewed literature claim, or an unrouted candidate criterion, put it in `Source Assertions / Leads` or `Missing Evidence / Not Assessed`; do not include it in Bayesian points.

If compatibility resolution identifies evidence in `not_used_due_to_overlap`, `caps_applied`, `context_splits`, or `unresolved_conflicts`, report that block before Bayesian calculation. Use only the retained, resolved evidence. If `unresolved_conflicts` is not empty, do not compute final posterior probability.

---

## Tavtigian 2018 Default Model

Use these default parameters unless a VCEP or explicitly stated local policy changes them:

| Parameter | Default | Source |
| --- | ---: | --- |
| Prior probability (`Prior_P`) | `0.10` | Tavtigian et al. 2018 main text and Supplemental Table S1 |
| Very Strong odds of pathogenicity (`OPVSt`) | `350` | Tavtigian et al. 2018 main text and Supplemental Table S1 |
| Exponential progression (`X`) | `2.0` | Tavtigian et al. 2018 main text and Supplemental Table S1 |

Tavtigian et al. modeled the ACMG/AMP evidence strengths as exponentially scaled odds. With `X = 2`, this can be expressed as integer Bayesian points:

| Direction | Strength | Points |
| --- | --- | ---: |
| Pathogenic | `VeryStrong` | `+8` |
| Pathogenic | `Strong` | `+4` |
| Pathogenic | `Moderate` | `+2` |
| Pathogenic | `Supporting` | `+1` |
| Benign | `Strong` | `-4` |
| Benign | `Supporting` | `-1` |

BA1 is not assigned points. It is a stand-alone benign gate outside the Bayesian calculation.

---

## Formula

Calculate total points:

```text
total_points =
  8 * pathogenic_very_strong_count
+ 4 * pathogenic_strong_count
+ 2 * pathogenic_moderate_count
+ 1 * pathogenic_supporting_count
- 4 * benign_strong_count
- 1 * benign_supporting_count
```

Then calculate odds and posterior probability:

```text
OddsPath = 350^(total_points / 8)
Post_P = OddsPath * Prior_P / ((OddsPath - 1) * Prior_P + 1)
```

With the default `Prior_P = 0.10`, useful reference values are:

| Total points | OddsPath | Posterior probability | Typical range |
| ---: | ---: | ---: | --- |
| `+12` | `6547.90` | `0.99863` | Pathogenic |
| `+10` | `1513.86` | `0.99409` | Pathogenic |
| `+8` | `350.00` | `0.97493` | Likely pathogenic |
| `+6` | `80.92` | `0.89991` | Likely pathogenic boundary |
| `0` | `1.00` | `0.10000` | Prior baseline |
| `-2` | `0.2312` | `0.02505` | Likely benign |
| `-4` | `0.05345` | `0.00590` | Likely benign |
| `-8` | `0.00286` | `0.00032` | Benign |

---

## Classification Thresholds

Use Tavtigian et al. 2018 probability thresholds unless a VCEP or local policy specifies otherwise:

| Posterior probability | Bayesian tier |
| --- | --- |
| `> 0.99` | Pathogenic |
| `> 0.90` and `<= 0.99` | Likely Pathogenic |
| `>= 0.10` and `<= 0.90` | VUS |
| `>= 0.001` and `< 0.10` | Likely Benign |
| `< 0.001` | Benign |

When a value is exactly on a boundary, report the value and boundary explicitly. The Tavtigian/Supplemental Table S1 examples treat approximately `0.900` as the likely-pathogenic boundary and approximately `0.00032` as benign.

---

## Handling Later ClinGen or VCEP Strengths

Tavtigian et al. 2018 modeled the original ACMG/AMP categories: four pathogenic strengths and two benign strengths. Later ClinGen/VCEP/local frameworks may use benign strengths not present in the original 2015 table, such as `BP4_Moderate`, `BP4_Strong`, `BP4_VeryStrong`, or `BS3_Moderate`.

Handle those later strengths as follows:

1. If a VCEP defines the conversion, follow the VCEP and report `guidance_authority: VCEP-specific`.
2. If a ClinGen/SVI document explicitly defines a Bayesian or point-equivalent strength, use that conversion and label it as a later ClinGen/SVI extension, not as original Tavtigian 2018.
3. If local policy maps later benign strengths to points, label the row `practice/local refinement`.
4. If no conversion policy is available, do not silently downgrade or force the evidence into the 2018 model. Report `status: not_assessed` for Bayesian conversion while preserving the qualitative evidence table.

---

## Internal Consistency Notes from Tavtigian 2018

Tavtigian et al. found two notable inconsistencies in the ACMG/AMP 2015 qualitative combining criteria under the default Bayesian model:

- `PVS1 + one Moderate` reaches posterior probability about `0.994`, equivalent to several Pathogenic combinations.
- `two Strong` reaches posterior probability about `0.975`, which is below the Pathogenic threshold and falls in the Likely Pathogenic range.

Do not use these observations to change evidence-specific strengths. Report them as Bayesian-combination notes when those combinations occur.

---

## Required Report Structure

Use this structure for final ACMG reports when this skill is active:

```markdown
# ACMG Variant Classification Report

## Variant Normalization
- Variant:
- Gene:
- Transcript:
- Genome build:
- Consequence:

## Disease / Mechanism Context
- Disease context:
- Inheritance:
- Mechanism:
- Multiple-disorder boundary:

## Evidence Retrieval
- Population:
- Computational:
- Clinical databases and source assertions:
- Literature and supplements:
- Functional / segregation / case evidence:

## Overlay Route Audit
| Criterion | Proposed evidence | Route outcome | Guidance authority | Overlay or VCEP source | Counted? | Reason |
| --- | --- | --- | --- | --- | --- | --- |

## Current Counted Evidence
| Criterion | Direction | Strength | Points | Source | Consumed evidence |
| --- | --- | --- | ---: | --- | --- |

## Evidence Compatibility Resolution
- current_counted_evidence_resolved:
- not_used_due_to_overlap:
- caps_applied:
- context_splits:
- unresolved_conflicts:

## ACMG Assessment Bundle Validator
```json
{"validator_status":"PASS","violations":[]}
```

## Bayesian Calculation
- Model: Tavtigian et al. 2018 Bayesian ACMG/AMP framework
- Prior probability: 0.10
- Very Strong OddsPath: 350
- Exponential progression: 2.0
- Total points:
- OddsPath:
- Posterior probability:
- Boundary note:

## Final Classification
- Classification status: [final classification / draft classification]
- Bayesian tier:
- ACMG/AMP qualitative table comparison:
- VCEP override, if any:

## Source Assertions / Leads
| Source | Assertion | Why not counted directly | Routed primary evidence |
| --- | --- | --- | --- |

## Missing Evidence / Not Assessed
| Criterion | Missing field or unavailable source | Impact |
| --- | --- | --- |
```

---

## Guardrails

- Do not count ClinVar, HGMD, LOVD, VCEP, laboratory report, or paper classification labels as points.
- Do not count abstract-only or inaccessible literature as points when the criterion depends on full-text details.
- Do not count unread supplements or low-confidence figure extraction as points.
- Do not count the same primary evidence twice.
- Do not accept unresolved conflicts from evidence compatibility resolution.
- Do not present a final Bayesian tier without a validator-passing `acmg_assessment_bundle`.
- Do not compute posterior probability from evidence outside `current_counted_evidence_resolved`.
- Do not use Bayesian points to justify assigning a criterion that an evidence-specific overlay did not support.
- Do not use this skill to override current VCEP specifications.

---

## Primary References

- Tavtigian SV, Greenblatt MS, Harrison SM, Nussbaum RL, Prabhu SA, Boucher KM, Biesecker LG; ClinGen Sequence Variant Interpretation Working Group. Modeling the ACMG/AMP variant classification guidelines as a Bayesian classification framework. Genetics in Medicine. 2018;20(9):1054-1060. PMID: 29300386. PMCID: PMC6336098. DOI: 10.1038/gim.2017.210.
- Tavtigian et al. 2018 Supplemental Table S1: `NIHMS915467-supplement-Supplemental_Table_S1.xlsx`.
- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genetics in Medicine. 2015;17(5):405-424. PMID: 25741868.
