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

| Frequency | ACMG Code | Interpretation |
|-----------|-----------|----------------|
| Absent | PM2_Supporting | Absent from controls |
| <0.00001 | PM2_Supporting | Extremely rare |
| <0.0001 | - | Rare (use with caution) |
| >0.01 | BS1/BA1 | Too common for rare disease |

## COSMIC Somatic Evidence

| COSMIC Finding | Interpretation | ACMG Support |
|----------------|----------------|--------------|
| Recurrent hotspot (>100 samples) | Known oncogenic driver | PS3 (functional) |
| Moderate frequency (10-100) | Likely oncogenic | PM1 (hotspot) |
| Rare somatic (<10) | Unknown significance | No support |

## DisGeNET Score Interpretation

| GDA Score | Evidence Level | ACMG Support |
|-----------|----------------|--------------|
| >0.7 | Strong | PP4 (phenotype) |
| 0.4-0.7 | Moderate | Supporting |
| <0.4 | Weak | Insufficient |

## ClinGen Validity Levels (for ACMG PM1/PP4)

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

| Impact Level | Description | ACMG Support |
|--------------|-------------|--------------|
| **Critical** | Active site, catalytic residue | PM1 (strong) |
| **High** | Buried residue, disulfide, structural core | PM1 (moderate) |
| **Moderate** | Domain interface, binding site | PM1 (supporting) |
| **Low** | Surface, flexible region | No support |

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

## SpliceAI Thresholds

| Max Delta Score | Interpretation | ACMG Support |
|-----------------|----------------|--------------|
| >=0.8 | High pathogenicity | PP3 (strong) for splice-altering |
| 0.5-0.8 | Moderate | PP3 (supporting) |
| 0.2-0.5 | Low | Weak evidence |
| <0.2 | Likely benign | BP7 (if synonymous) |

## Literature Evidence Weights

| Evidence | ACMG Code | Weight |
|----------|-----------|--------|
| Functional study (null) | PS3 | Strong |
| Functional study (reduced) | PS3_Moderate | Moderate |
| Case reports with segregation | PP1 | Supporting to Moderate |
| Co-occurrence with pathogenic | BP2 | Supporting against |

## Regulatory Impact Categories

| Category | Criteria | ACMG Support |
|----------|----------|--------------|
| **High impact** | Disrupts known TF binding motif | PP3 (supporting) |
| **Moderate impact** | In active regulatory region | Consider context |
| **Low impact** | No regulatory annotation | No support |

## PVS1 Application for Truncating Variants

| Scenario | PVS1 Strength |
|----------|---------------|
| Canonical LOF gene, NMD predicted | Very Strong |
| NMD escape (last exon, last ~50 bp of penultimate exon) | Strong |
| In-frame exon skipping / rescue transcript possible | Moderate/Supporting |
| LoF not an established disease mechanism | Not applicable |

Full decision tree, transcript and splice caveats: the ACMG skill's
`SVI_REFERENCE.md`.
