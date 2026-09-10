# ACMG Classification Reference

## Where the algorithm lives

Germline small-variant classification follows the unified flow in the
`tooluniverse-acmg-variant-classification` skill: evaluate all 28 criteria
(see its `SVI_REFERENCE.md` for per-code facts, strengths, exclusions, and
double-counting rules), then call `ACMG_calculate_classification` — the
deterministic Tavtigian 2020 point system (Supporting/Moderate/Strong/
VeryStrong = +/-1/2/4/8; >=10 Pathogenic, 6-9 Likely Pathogenic, 0-5 VUS,
-6 to -1 Likely Benign, <=-7 Benign; BA1 is a stand-alone benign path).
Do not combine criteria with the 2015 rule-counting table here — the
calculator is the single source of the final classification.

PP5 and BP6 are retired (ClinGen SVI) and are never scored; ClinVar/VCEP
conclusions are attributed separately in reports.

The tables below remain useful for evidence-gathering context (labels,
databases, thresholds used during assessment).

## Classification Confidence

| Symbol | Classification | Evidence Level |
|--------|----------------|----------------|
| 3 stars | High confidence | Multiple independent lines |
| 2 stars | Moderate confidence | Some supporting evidence |
| 1 star | Limited confidence | Minimal evidence |
| VUS | Uncertain | Insufficient data |

## ClinVar Classification Map

| ClinVar | Interpretation |
|---------|----------------|
| Pathogenic | Disease-causing |
| Likely pathogenic | 90%+ confidence pathogenic |
| VUS | Uncertain significance |
| Likely benign | 90%+ confidence benign |
| Benign | Not disease-causing |
| Conflicting | Multiple interpretations |

## gnomAD Frequency Thresholds (Rare Disease)

| Frequency | Interpretation |
|-----------|----------------|
| Absent | Absent from population databases |
| <0.00001 | Extremely rare |
| <0.0001 | Rare (use with caution) |
| >0.01 | Too common for a rare disease |

(Code assignment -- PM2/BA1/BS1 and strengths -- happens in the unified ACMG
skill against disease-aware maximum-credibility thresholds.)

## COSMIC Somatic Evidence

| COSMIC Finding | Interpretation |
|----------------|----------------|
| Recurrent hotspot (>100 samples) | Known oncogenic driver |
| Moderate frequency (10-100) | Likely oncogenic |
| Rare somatic (<10) | Unknown significance |

## DisGeNET Score Interpretation

| GDA Score | Evidence Level |
|-----------|----------------|
| >0.7 | Strong |
| 0.4-0.7 | Moderate |
| <0.4 | Weak |

## ClinGen Validity Levels (gene-disease context)

| Classification | Meaning | ACMG Impact |
|----------------|---------|-------------|
| **Definitive** | Multiple concordant studies | Strong gene-disease support |
| **Strong** | Extensive evidence | Moderate-strong support |
| **Moderate** | Some evidence | Moderate support |
| **Limited** | Minimal evidence | Weak support, use caution |
| **Disputed** | Conflicting evidence | Do not use for classification |
| **Refuted** | Evidence against | Gene NOT associated |

## ClinGen Dosage Sensitivity Scores (for CNV interpretation)

| Score | Meaning | Interpretation |
|-------|---------|----------------|
| **3** | Sufficient evidence | Haploinsufficiency/triplosensitivity established |
| **2** | Emerging evidence | Some support, not definitive |
| **1** | Little evidence | Minimal support |
| **0** | No evidence | Unknown |

## Structural Impact Categories

| Impact Level | Description |
|--------------|-------------|
| **Critical** | Active site, catalytic residue |
| **High** | Buried residue, disulfide, structural core |
| **Moderate** | Domain interface, binding site |
| **Low** | Surface, flexible region |

## Structural Impact Confidence (AlphaFold pLDDT)

| pLDDT Range | Interpretation |
|-------------|----------------|
| >90 | Very high confidence in position |
| 70-90 | High confidence |
| 50-70 | Moderate (often loops) |
| <50 | Low confidence (disorder) |

## Prediction Thresholds

| Predictor | Damaging | Benign |
|-----------|----------|--------|
| **AlphaMissense** | >0.564 | <0.34 |
| **CADD PHRED** | >=20 (top 1%) | <15 |
| **EVE** | >0.5 | <=0.5 |
| SIFT | <0.05 | >=0.05 |
| PolyPhen2 | >0.85 (probably) | <0.15 (benign) |

## PP3/BP4 Application Notes

- PP3/BP4 come from a single calibrated predictor meeting its pre-set
  threshold (per the ClinGen SVI in-silico calibration; see the ACMG skill's
  SVI_REFERENCE.md), not from counting votes across predictors
- Concordance of uncalibrated predictors is not PP3; discordant calibrated
  predictors -> neither code applies

## SpliceAI Thresholds (raw score context)

| Max Delta Score | Interpretation |
|-----------------|----------------|
| >=0.8 | High predicted splice impact |
| 0.5-0.8 | Moderate predicted splice impact |
| 0.2-0.5 | Low predicted splice impact |
| <0.2 | No predicted splice impact |

(Splicing code assignment follows the unified ACMG skill's calibrated
rules: canonical +/-1,2 -> PVS1 tree; non-canonical SpliceAI >=0.2 -> PP3
and <=0.1 -> BP4 conservatively at Supporting; BP7 position rules apply.)

## Literature Evidence

Collected literature findings are raw material for the unified ACMG skill.
Functional studies are assessed there under the SVI validation framework
(strength from validation, not study type); segregation under the
co-segregation point system; co-occurrence under BP2's phase rules. No
fixed code/strength mapping is applied at collection time.

## Regulatory Impact Categories

| Category | Criteria |
|----------|----------|
| **High impact** | Disrupts known TF binding motif |
| **Moderate impact** | In active regulatory region |
| **Low impact** | No regulatory annotation |

(Regulatory annotations are collection context; non-coding evidence codes
are decided in the unified ACMG skill.)

## PVS1 Application for Truncating Variants

PVS1 strength is decided ONLY by the SVI decision tree in the unified ACMG
skill's `SVI_REFERENCE.md` -- it depends on NMD prediction, whether the
removed C-terminal region is critical, the fraction of protein removed
(>10% vs <10%), transcript relevance, and population LoF frequency. NMD
escape alone does NOT imply Strong; without critical-region evidence and
with <10% of the protein removed the tree gives Moderate. Never assign PVS1
at any strength when LoF is not an established disease mechanism.
