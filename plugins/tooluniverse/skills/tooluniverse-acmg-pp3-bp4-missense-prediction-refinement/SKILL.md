---
name: tooluniverse-acmg-pp3-bp4-missense-prediction-refinement
description: Refine ACMG/AMP PP3 and BP4 computational evidence for missense variants using Pejaver et al. 2022 ClinGen SVI calibrated predictor thresholds.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ToolUniverse ACMG PP3/BP4 Missense Prediction Refinement

Use this overlay when ACMG/AMP classification depends on computational missense prediction evidence for `PP3` or `BP4`. It refines the base `tooluniverse-acmg-variant-classification` workflow using Pejaver et al. 2022 ClinGen SVI recommendations.

This skill does not create a new MCP tool. It uses ToolUniverse evidence-retrieval tools first, then applies calibrated rule interpretation inside the ACMG evidence assignment workflow.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PP3/BP4-specific logic.

## Scope

Use this overlay for:

- Single-nucleotide or small coding variants whose relevant consequence is `missense_variant`.
- Missense predictor scores from calibrated tools such as REVEL, BayesDel without allele frequency, MutPred2, VEST4, CADD, SIFT, PolyPhen-2 HumVar, PrimateAI, PhyloP, GERP++, MPC, FATHMM, or Evolutionary Action.
- Cases where `PP3` or `BP4` strength may be supporting, moderate, or strong rather than only supporting.
- Cases where `BP4_Moderate` must be recorded even if the downstream ACMG combiner does not natively support moderate benign evidence.
- Cases where `PM1` and `PP3` are both met and their combined pathogenic contribution must be capped at Strong.

Do not use this overlay as the primary evidence path for:

- Splice prediction or RNA assay evidence. Use PVS1/RNA, PS1-splicing, or other splicing-specific overlays.
- Functional assay evidence, including MAVE/DMS calibrated as PS3/BS3.
- Non-missense consequences unless a current VCEP specification explicitly extends calibrated computational evidence to that consequence.
- AlphaMissense, EVE, or other tools not calibrated in Pejaver et al. 2022, unless a VCEP or separate validated calibration provides thresholds.
- Dominant-negative mechanism proof. Use `tooluniverse-acmg-dominant-negative-mechanism-refinement` for mechanism routing; this overlay only assigns calibrated missense prediction evidence.

## Core Principle

For missense `PP3/BP4`, do not use uncalibrated majority voting across many predictors. Select one calibrated tool before looking at the score, preferably before considering other evidence, and map that score to the Pejaver et al. calibrated evidence interval.

If no tool was pre-specified and multiple tools were inspected after seeing scores, do not cherry-pick the strongest result. Either use the laboratory or VCEP pre-specified hierarchy, or record the prediction evidence as non-applied context.

External-agent rule: phrases such as "all predictors agree", predictor-majority statements, "CADD high plus SIFT/PolyPhen damaging", or "conservation supports pathogenicity" are not valid PP3/BP4 assignments by themselves. They may be reported as prediction context, but the counted ACMG code must come from this calibrated overlay or a current VCEP rule.

If the selected calibrated score is unavailable and no VCEP or pre-specified local hierarchy applies, report `applied_evidence: none` with `status: not_assessed` or `no_evidence`. Do not use SIFT plus PolyPhen plus CADD, conservation, or any predictor voting pattern as a fallback for `PP3_Supporting`.

## Recommended Evidence Retrieval

Start with variant normalization and consequence confirmation:

- `VariantValidator_validate_variant`
- `EnsemblVEP_annotate_hgvs`
- `ensembl_vep_region`
- `OpenCRAVAT_annotate_variant`

Retrieve missense prediction scores:

- `MyVariant_get_pathogenicity_scores` for dbNSFP-derived REVEL, CADD, SIFT, PolyPhen-2, GERP, PhyloP, VEST4, and related scores.
- `MyVariant_query_variants` as a broader fallback when the focused pathogenicity-score tool is incomplete.
- `OpenCRAVAT_annotate_variant` with annotators such as `revel`, `cadd_exome`, `sift`, `polyphen2`, `vest`, `primateai`, `fathmm`, and conservation modules when available.
- `EnsemblVEP_annotate_hgvs` or `ensembl_vep_region` for consequence, transcript, SIFT, PolyPhen, CADD, and colocated-variant context.

When OpenCRAVAT returns convenience fields such as `pp3_pathogenic` or `bp4_benign`, treat them as non-authoritative hints. For this overlay, assign ACMG evidence from the raw score, score scale, transcript/build context, and the Pejaver et al. calibrated threshold table. Do not rely on an aggregator's precomputed PP3/BP4 label unless its version and threshold logic are verified to match this overlay.

Check whether a VCEP rule supersedes the genome-wide calibration:

- `ClinGen_search_gene_validity`
- `PubMed_search_articles`
- `EuropePMC_search_articles`
- `EuropePMC_get_fulltext`

## Tool Selection Policy

Use the current disease-specific VCEP rule first if it gives a PP3/BP4 tool and threshold.

If no VCEP rule exists and a local policy has not already selected a tool, use a fixed default hierarchy before reading scores:

1. REVEL, because it reaches `PP3_Strong` and `BP4_VeryStrong/Strong/Moderate/Supporting` in the Pejaver calibration and is commonly available.
2. BayesDel without allele frequency, MutPred2, or VEST4 when REVEL is unavailable and the score source/version is clear.
3. Other Pejaver-calibrated tools only at their calibrated thresholds and maximal supported strength.

Do not use developer-default thresholds as ACMG evidence. In particular, SIFT 0.05, PolyPhen-2 0.902, and CADD 20 do not justify `PP3` under Pejaver et al.; CADD 20 falls inside the `BP4_Moderate` interval.

## Calibrated Evidence Thresholds

Intervals use standard mathematical notation: `[` or `]` includes the endpoint; `(` or `)` excludes it. A dash means the tool did not reach that evidence strength in the calibration.

| Tool | BP4_VeryStrong | BP4_Strong | BP4_Moderate | BP4_Supporting | PP3_Supporting | PP3_Moderate | PP3_Strong | PP3_VeryStrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BayesDel noAF | - | - | <= -0.36 | (-0.36, -0.18] | [0.13, 0.27) | [0.27, 0.50) | >= 0.50 | - |
| CADD | - | <= 0.15 | (0.15, 17.3] | (17.3, 22.7] | [25.3, 28.1) | >= 28.1 | - | - |
| Evolutionary Action | - | - | <= 0.069 | (0.069, 0.262] | [0.685, 0.821) | >= 0.821 | - | - |
| FATHMM | - | - | >= 4.69 | [3.32, 4.69) | (-5.04, -4.14] | <= -5.04 | - | - |
| GERP++ | - | - | <= -4.54 | (-4.54, 2.70] | - | - | - | - |
| MPC | - | - | - | - | [1.360, 1.828) | >= 1.828 | - | - |
| MutPred2 | - | <= 0.010 | (0.010, 0.197] | (0.197, 0.391] | [0.737, 0.829) | [0.829, 0.932) | >= 0.932 | - |
| PhyloP | - | - | <= 0.021 | (0.021, 1.879] | [7.367, 9.741) | >= 9.741 | - | - |
| PolyPhen-2 HumVar | - | - | <= 0.009 | (0.009, 0.113] | [0.978, 0.999) | >= 0.999 | - | - |
| PrimateAI | - | - | <= 0.362 | (0.362, 0.483] | [0.790, 0.867) | >= 0.867 | - | - |
| REVEL | <= 0.003 | (0.003, 0.016] | (0.016, 0.183] | (0.183, 0.290] | [0.644, 0.773) | [0.773, 0.932) | >= 0.932 | - |
| SIFT | - | - | >= 0.327 | [0.080, 0.327) | (0, 0.001] | 0 | - | - |
| VEST4 | - | - | <= 0.302 | (0.302, 0.449] | [0.764, 0.861) | [0.861, 0.965) | >= 0.965 | - |

## Assignment Workflow

1. Confirm that the variant has a relevant missense consequence on the transcript being classified.
2. Exclude cases where the key computational question is splicing, expression, or another non-missense mechanism.
3. Check for an applicable VCEP specification; if present, follow the VCEP.
4. Select one calibrated prediction tool or a pre-specified local hierarchy before looking at scores.
5. Retrieve the raw score and document the source, version if available, transcript/build context, and whether the selected score corresponds to the classified transcript/protein change. If the data source also returns a precomputed PP3/BP4 label, keep it as a cross-check only.
6. Map the score to the calibrated interval table.
7. Apply exactly one computational evidence code from the selected tool: `PP3_Strong`, `PP3_Moderate`, `PP3_Supporting`, `BP4_VeryStrong`, `BP4_Strong`, `BP4_Moderate`, `BP4_Supporting`, or no code.
8. If the selected score is missing, incompatible, outside evidence intervals, or conflicts with a VCEP rule, do not apply `PP3/BP4`.
9. If only developer-default labels or a mixed predictor summary are available, record them in prediction context and keep counted evidence as none.

## Double Counting and Conflicts

- Do not stack multiple missense predictors for extra strength.
- Do not downgrade this rule into a majority vote when the calibrated selected score is missing.
- Do not use mechanistic missense predictors, such as protein-stability predictors, in addition to the selected calibrated missense impact predictor unless a VCEP explicitly permits it.
- Do not treat a high missense predictor score as evidence that the variant acts through a dominant-negative mechanism.
- `PM2` and `BS1` may be combined with `PP3/BP4` when the selected predictor does not use allele frequency; use REVEL or BayesDel without allele frequency for this reason.
- When `PM1` and `PP3` are both retained, cap their combined pathogenic contribution at Strong. Use `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` for the PM1 side of this rule.
- Do not use the same DMS/MAVE data as both `PP3/BP4` and `PS3/BS3`.
- Do not use the same splicing prediction or RNA evidence as both splicing-specific evidence and missense `PP3/BP4`.

## Handling BP4_Moderate

`BP4_Moderate` is not part of the original 2015 ACMG/AMP combining table. Record it explicitly as calibrated benign computational evidence.

If the downstream combiner supports Tavtigian-style points, count `BP4_Moderate` as -2 points. If the combiner is limited to the original ACMG/AMP table, report `BP4_Moderate` with a policy note rather than silently downgrading it. Pejaver et al. describe pragmatic interim use where `BP4_Moderate` may satisfy a likely benign combination with one strong benign criterion, or may be sufficient alone or with another benign supporting criterion under a modified likely benign rule.

## Output Format

```markdown
PP3/BP4 missense-prediction refinement:
- Variant: [HGVS c./p.], transcript [ID]
- Consequence: [missense / other]
- Selected prediction tool: [REVEL / BayesDel noAF / MutPred2 / VEST4 / other]
- Raw score and source: [score, version/build if available]
- Calibrated interval: [Pejaver 2022 interval]
- Applied evidence: [PP3_Strong / PP3_Moderate / PP3_Supporting / BP4_VeryStrong / BP4_Strong / BP4_Moderate / BP4_Supporting / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [selected predictor score / none]
- Double-counting restriction: [PM1 plus PP3 cap / same assay not reused / none]
- Combiner note: [BP4_Moderate handling if relevant]
```

Example:

```text
PP3_Strong applied. REVEL was selected as the pre-specified missense predictor. REVEL score 0.95 falls in the Pejaver et al. 2022 PP3_Strong interval (>=0.932). No VCEP-specific threshold was identified. PM1 is also met, so the combined PM1+PP3 pathogenic contribution is capped at Strong.
```

## References

- Pejaver V, Byrne AB, Feng B, Pagel KA, Mooney SD, Karchin R, O'Donnell-Luria A, Harrison SM, Tavtigian SV, Greenblatt MS, Biesecker LG, Brenner SE, ClinGen Sequence Variant Interpretation Working Group. Calibration of computational tools for missense variant pathogenicity classification and ClinGen recommendations for PP3/BP4 criteria. American Journal of Human Genetics. 2022;109:2163-2177. PMID: 36413997. PMCID: PMC9748256. DOI: 10.1016/j.ajhg.2022.10.013.
- See `references/pejaver_2022_pp3_bp4_summary.md` for a concise rule summary and supplement relevance.
