# ACMG Classification Quick Index

This file is a quick index for retrieval and reporting. It is not a standalone ACMG classifier. Use `tooluniverse-acmg-variant-classification` for final evidence-code assignment and classification, with `tooluniverse-acmg-overlay-routing-core` coordinating disease context, mechanism, phenotype/source/literature intake, and evidence-specific overlays.

## Evidence Route Index

Do not assign ACMG evidence strength from this quick index. Use
`tooluniverse-acmg-variant-classification` with the routing core, evidence
specific overlays, route audit, and Evidence Compatibility Resolution.

### Pathogenic/Context Candidate Routes

| Candidate | Evidence lead | Required route |
|------|----------|-------------|
| PVS1 | Null, canonical splice, start-loss, exon deletion/duplication, whole-gene deletion | `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`; RNA refinement only with RNA assay or observed transcript evidence |
| PS1/PM5 | Same amino-acid or same-residue comparison variant | `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement`; comparison source labels are leads only |
| PS3/BS3 | Functional assay evidence | `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` |
| PS4 | Case-control, cohort, meta-analysis, or affected-case enrichment | `tooluniverse-acmg-ps4-case-enrichment-refinement` |
| PM1/PP2/BP1 | Hotspot, functional domain, regional missense constraint, or missense mechanism context | `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` |
| PM2 | Absent/rare from controls after coverage and population checks | `tooluniverse-acmg-pm2-absence-rarity-refinement`; PM2 defaults to Supporting if applied |
| PM3 | Recessive biallelic, in-trans, phase-unknown, or homozygous observations | `tooluniverse-acmg-pm3-in-trans-refinement` |
| PM4/BP3 | Protein length change, in-frame indel, stop-loss, repeat/low-complexity region | `tooluniverse-acmg-pm4-bp3-protein-length-refinement` |
| PP1/BS4/PP4 | Segregation, non-segregation, phenotype-locus evidence | `tooluniverse-acmg-pp1-segregation-refinement` and phenotype-dependent intake when needed |
| PP3/BP4 | Calibrated computational prediction evidence | `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or VCEP; no local predictor voting |
| PP5/BP6 | Reputable-source assertion | `tooluniverse-acmg-pp5-bp6-reputable-source-refinement`; not counted by default |

### Benign/Frequency Candidate Routes

| Candidate | Evidence lead | Required route |
|------|----------|-------------|
| BA1 | AF >0.05 candidate | `tooluniverse-acmg-ba1-exception-list-refinement` before stand-alone benign classification |
| BS1/BS2/BP2/BP5 | High disease-specific frequency, healthy carriers, phase context, alternate diagnosis | `tooluniverse-acmg-benign-context-refinement` |
| RNA no-splicing-impact candidate | Synonymous/intronic no-splicing-impact evidence | `tooluniverse-acmg-pvs1-splicing-refinement`; prediction-only low splice scores remain prediction context |

## Classification Algorithm

Do not use this reference as an independent classification algorithm. The final classification must be produced through `tooluniverse-acmg-variant-classification`, which applies the overlay routing core, VCEP precedence, source-evidence rules, duplicate-evidence guards, and criterion-specific strength refinements.

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

Use `tooluniverse-acmg-pm2-absence-rarity-refinement` for PM2. PM2 remains ClinGen SVI-style `PM2_Supporting` by default. Use `tooluniverse-acmg-ba1-exception-list-refinement` before applying BA1. Use `tooluniverse-acmg-benign-context-refinement` for BA1/BS1/BS2/BP2/BP5 when disease prevalence, penetrance, inheritance, unaffected status, phase, or alternate diagnosis affects benign evidence.

| Frequency context | Route | Interpretation |
|-----------|-----------|----------------|
| Absent or rare after coverage review | PM2 overlay | Use `tooluniverse-acmg-pm2-absence-rarity-refinement`; PM2 defaults to Supporting strength |
| >0.05 candidate | BA1 exception-list overlay | BA1 only after Ghosh 2018 exception-list and dataset-adequacy review |
| High for disease but BA1 not valid | Benign-context overlay | Route BS1 assessment through disease-specific prevalence, penetrance, heterogeneity, inheritance, and ancestry AF review |

## COSMIC Somatic Context

COSMIC recurrence is somatic cancer context and a literature or cancer-interpretation lead. Do not map COSMIC recurrence directly to germline functional evidence. For tumor-specific interpretation, route to the cancer variant interpretation workflow; for germline ACMG, use COSMIC only to guide literature review, mechanism review, or hotspot/domain context that is then assessed by the appropriate overlay.

## DisGeNET Score Interpretation

| GDA Score | Evidence Level | ACMG use |
|-----------|----------------|--------------|
| >0.7 | Strong | Gene-disease context only; PP4 still requires patient phenotype |
| 0.4-0.7 | Moderate | Supporting |
| <0.4 | Weak | Insufficient |

## ClinGen Validity Levels (for ACMG PM1/PP4)

Gene-disease validity and disease association scores do not substitute for patient-level phenotype evidence. Use `tooluniverse-acmg-overlay-routing-core` before disease- or mechanism-sensitive evidence assignment. The routing core sends multiple-disorder questions to `tooluniverse-acmg-multiple-disorder-context-refinement`, clinical-context intake to `tooluniverse-acmg-phenotype-dependent-evidence-refinement`, and PP1/BS4/PP4 combined scoring to `tooluniverse-acmg-pp1-segregation-refinement`.

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

| Impact Level | Description | ACMG use |
|--------------|-------------|--------------|
| **Critical** | Active site, catalytic residue | PM1 candidate route |
| **High** | Buried residue, disulfide, structural core | PM1/structural context lead |
| **Moderate** | Domain interface, binding site | PM1/structural context lead |
| **Low** | Surface, flexible region | No support |

Use `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` before assigning PM1 from regional missense constraint, DECIPHER/CCR/MetaDome/paralog evidence, hotspots, domains, or critical residues. Use `tooluniverse-acmg-pm4-bp3-protein-length-refinement` for in-frame insertions/deletions, repeat-region indels, stop-loss variants, and last-exon altered-product contexts.

## Structural Impact Confidence (AlphaFold pLDDT)

| pLDDT Range | Interpretation |
|-------------|----------------|
| >90 | Very high confidence in position |
| 70-90 | High confidence |
| 50-70 | Moderate (often loops) |
| <50 | Low confidence (disorder) |

## Prediction Thresholds

For ACMG PP3/BP4, do not use this table as evidence-strength thresholds. Use `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement`, which follows Pejaver et al. 2022 calibrated missense prediction thresholds and VCEP overrides. The table below is only a retrieval/orientation aid.

| Predictor | Damaging | Benign |
|-----------|----------|--------|
| **AlphaMissense** | >0.564 | <0.34 |
| **CADD PHRED** | >=20 (top 1%) | <15 |
| **EVE** | >0.5 | <=0.5 |
| SIFT | <0.05 | >=0.05 |
| PolyPhen2 | >0.85 (probably) | <0.15 (benign) |

## PP3/BP4 Application Notes

- **PP3/BP4**: Assign only through calibrated predictor thresholds from `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or a current VCEP rule.
- **Avoid local predictor combining**: Multiple concordant uncalibrated predictors do not automatically create PP3/BP4 evidence.
- **Tool availability**: If a required calibrated score is unavailable through ToolUniverse, record the gap and do not substitute developer-default SIFT/PolyPhen/CADD thresholds as ACMG evidence.

## PS4 and Phenotype-Dependent Evidence

Use `tooluniverse-acmg-ps4-case-enrichment-refinement` for case-control evidence, odds ratio/confidence interval interpretation, unrelated affected case counts, ancestry matching, gnomAD control caveats, and rare-disease ACGS-style PS4 case counting. Recessive biallelic affected-proband observations should route to PM3 rather than PS4.

Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when PP4, PS4, PP1/BS4, PM3, BP5, BS2, or PS2/PM6 phenotype consistency requires patient phenotype, affected status, disease specificity, diagnostic yield, or tested/excluded loci. Use `tooluniverse-acmg-pp1-segregation-refinement` when PP4 and PP1/BS4 must be combined rather than counted independently.

## SpliceAI Prediction Context

Use SpliceAI scores as prediction context, not direct evidence strength. Route prediction-only splice evidence through the relevant PP3/BP4 or splicing-prediction pathway, apply `tooluniverse-acmg-ps1-splicing-similarity-refinement` only for independent same-event comparison-variant evidence, and apply `tooluniverse-acmg-pvs1-splicing-refinement` only when RNA assay or detailed RNA/splicing evidence affects PVS1 or RNA no-impact evidence.

## Literature Evidence Weights

| Evidence | Route | Use |
|----------|-----------|--------|
| Functional study (null) | PS3/BS3 overlay | Assay strength requires functional-assay refinement |
| Functional study (reduced) | PS3/BS3 overlay | Assay strength requires functional-assay refinement |
| Case reports with segregation | PP1/PP4 route | Use ClinGen 2024 combined PP1/BS4/PP4 overlay; avoid PP4/PS4/PP1 double counting |
| Co-occurrence with pathogenic | Benign-context overlay | BP2 requires inheritance and cis/trans context |

## Regulatory Impact Categories

| Category | Criteria | ACMG use |
|----------|----------|--------------|
| **High impact** | Disrupts known TF binding motif | Regulatory prediction context; route to the appropriate regulatory or ACMG overlay before assigning evidence |
| **Moderate impact** | In active regulatory region | Consider context |
| **Low impact** | No regulatory annotation | No support |

## PVS1 Application for Truncating Variants

Before using this table, run `tooluniverse-acmg-overlay-routing-core`, then `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`, and verify that LoF/haploinsufficiency is an established mechanism for the exact gene-disease context.

Use `tooluniverse-acmg-pvs1-splicing-refinement` only after the baseline PVS1 decision-tree branch is identified and RNA assay or Walker 2023 splicing-specific evidence is present.

| Scenario | PVS1 Strength |
|----------|---------------|
| Canonical LOF gene, NMD predicted and no transcript-structure NMD escape or rescue transcript evidence | Very Strong |
| LOF gene, PTC in the 3' most exon or within the 3' most 50 nucleotides of the penultimate exon under the Abou Tayoun 2018 baseline tree | Reduce strength through the truncated-protein branch; often Strong or Moderate depending critical-region loss, protein fraction removed, exon relevance, and population LoF context |
| Start-loss, exon deletion/duplication, whole-gene deletion, or in-frame exon loss | Use the PVS1 LoF decision-tree overlay; route CNV/SV event definition to structural-variant analysis |
| Non-LOF gene | Not applicable |
