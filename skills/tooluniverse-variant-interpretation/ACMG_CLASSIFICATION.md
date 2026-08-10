# ACMG Evidence Routing Reference

This file is a quick index for evidence retrieval and routing. It is not an ACMG classifier. Use `ACMG_evidence_collector` for evidence collection and the five deterministic group tools for criterion assessment. The current runtime does not produce a five-tier classification.

## Evidence Route Index

Do not assign ACMG evidence strength from this quick index. Use
`ACMG_evidence_collector` and the shared deterministic group rules; unsupported
inputs remain review-only and no five-tier classification is emitted.

### Pathogenic/Context Candidate Routes

| Candidate | Evidence lead | Required route |
|------|----------|-------------|
| PVS1 | Null, canonical splice, start-loss, exon deletion/duplication, whole-gene deletion | `ACMG_evidence_collector` runs the deterministic ClinGen/SVI tree; complete facts may create a card, while missing decision facts remain listed in `criterion_reviews` |
| PS1/PM5 | Same amino-acid or same-residue comparison variant | `ACMG_evidence_collector`; comparison source labels are leads only |
| PS3/BS3 | Functional assay evidence | `ACMG_functional_evidence` |
| PS4 | Case-control, cohort, meta-analysis, or affected-case enrichment | `ACMG_literature_evidence` |
| PM1 | Hotspot or critical functional-domain context | Collector maps genomic HGVS to UniProt/EBI/InterPro and separates source-backed candidates from verified CSpec or literature applications |
| PP2/BP1 | Regional missense constraint or missense mechanism context | Collector can produce source-backed candidates; verified use requires an applicable VCEP/CSpec or strictly anchored mechanism evidence |
| PM2 | Absent/rare from controls after coverage and population checks | General SVI suggests PM2_Supporting for AC=0 with auditable callability; an applicable CSpec takes precedence |
| PM3 | Recessive biallelic, in-trans, phase-unknown, or homozygous observations | `ACMG_clinical_evidence` |
| PM4/BP3 | Protein length change, in-frame indel, stop-loss, repeat/low-complexity region | Collector can produce source-backed candidates from unique protein mapping and feature overlap; verified use requires the strict rule facts |
| PP1/BS4/PP4 | Segregation, non-segregation, phenotype-locus evidence | `ACMG_clinical_evidence` and phenotype-dependent intake when needed |
| PP3/BP4 | Calibrated computational prediction evidence | `ACMG_computational_evidence` or VCEP; no local predictor voting |
| PP5/BP6 | Reputable-source assertion | `ACMG_evidence_collector`; deprecated and excluded from all calculations |

### Benign/Frequency Candidate Routes

| Candidate | Evidence lead | Required route |
|------|----------|-------------|
| BA1 | AF >0.05 candidate | `ACMG_population_evidence` before stand-alone benign classification |
| BS1/BS2/BP2/BP5 | High disease-specific frequency, healthy carriers, phase context, alternate diagnosis | `ACMG_population_evidence` |
| RNA no-splicing-impact candidate | Synonymous/intronic no-splicing-impact evidence | `ACMG_computational_evidence`; prediction-only low splice scores remain prediction context |

## Evidence Assessment Contract

Do not use this reference as an independent classifier. The current runtime
ends after source-backed and verified EvidenceCards, compatibility/conflict
handling, and Bayesian review estimates. A qualified human reviewer remains
responsible for any final classification.

## Source Assertions

ClinVar review status and submitted classifications are displayed as source
assertions with their provenance. They do not establish an EvidenceCard,
criterion strength, confidence level, or final classification.

## Population Evidence

Use `ACMG_population_evidence` or the collector for PM2 and benign-frequency
assessment. The normative SVI/CSpec rules, coverage requirements, exceptions,
and current strengths live in the `tooluniverse-acmg-variant-classification`
Skill and machine-readable rule catalog; this routing index does not duplicate
them.

## COSMIC Somatic Context

COSMIC recurrence is somatic cancer context and a literature or cancer-interpretation lead. Do not map COSMIC recurrence directly to germline functional evidence. For tumor-specific interpretation, route to the cancer variant interpretation workflow; for germline ACMG, use COSMIC only to guide literature review, mechanism review, or hotspot/domain context that is then assessed by the appropriate overlay.

## DisGeNET Context

Preserve the returned association score and provenance as gene-disease context.
Do not map score bands to ACMG strength or use them as patient-level PP4
evidence.

## ClinGen Validity Levels

Gene-disease validity and disease association scores do not substitute for patient-level phenotype evidence. Use `ACMG_evidence_collector` for evidence-only intake. Disease, phenotype, segregation, and mechanism-sensitive criteria remain review rows unless their deterministic group rule produces a source-backed candidate EvidenceCard.

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

Do not assign PM1, PP2, BP1, PM4, or BP3 from this index alone. Preserve regional, domain, paralog, protein-length, and altered-product observations as collector context. Generic UniProt/InterPro overlap is insufficient for PM1 because it does not establish a critical region or depletion of benign variation. `ACMG_functional_evidence` can suggest PM1 only when the collector supplies verified protein SourceFacts and an exact online-bound CSpec PM1 contract; anchored literature facts may separately produce review-required PP2/BP1 or PM4/BP3 proposals. Direct group calls remain review-only.

## Structural Impact Confidence (AlphaFold pLDDT)

| pLDDT Range | Interpretation |
|-------------|----------------|
| >90 | Very high confidence in position |
| 70-90 | High confidence |
| 50-70 | Moderate (often loops) |
| <50 | Low confidence (disorder) |

## Prediction Scores

List all available prediction scores, their versions, transcripts, and input
coordinates. Do not reproduce provider-default cutoffs as ACMG thresholds.
Only the versioned computational rule catalog may suggest PP3/BP4.

## PP3/BP4 Application Notes

- **PP3/BP4**: Assign only through calibrated predictor thresholds from `ACMG_computational_evidence` or a current VCEP rule.
- **Avoid local predictor combining**: Multiple concordant uncalibrated predictors do not automatically create PP3/BP4 evidence.
- **Tool availability**: If a required calibrated score is unavailable through ToolUniverse, record the gap and do not substitute developer-default SIFT/PolyPhen/CADD thresholds as ACMG evidence.

## PS4 and Phenotype-Dependent Evidence

Use `ACMG_evidence_collector` for case-control evidence, odds ratio/confidence
interval interpretation, unrelated affected case counts, ancestry matching,
gnomAD control caveats, and PS4 processing. The collector applies an exact
online CSpec first; without one, case-control facts use the general SVI route
and case-series facts may form versioned source-backed candidates. Recessive
biallelic affected-proband observations route to PM3 rather than PS4.

Use `clinical_observations` on `ACMG_evidence_collector` for structured PP4,
PS4, PP1/BS4, PM3, BP5, BS2, or PS2/PM6 inputs. Source-backed but unverified
records may enter `automatic_bayesian`; only strictly anchored records enter
`verified_bayesian`.

## SpliceAI Prediction Context

The collector preserves all four delta channels, positions, run metadata, and
selected-transcript binding. Use the
`tooluniverse-acmg-variant-classification` Skill as the single normative source
for current Walker PP3/BP4/BP7 and canonical PVS1 splice interpretation. Do
not infer a splice criterion from this index.

## Literature Evidence Weights

| Evidence | Route | Use |
|----------|-----------|--------|
| Functional study (null) | PS3/BS3 route | Assay strength requires the structured functional-assay contract |
| Functional study (reduced) | PS3/BS3 route | Assay strength requires the structured functional-assay contract |
| Case reports with segregation | PP1/PP4 route | Target-linked facts may create source-backed candidates; verified inclusion requires the strict family/phenotype contract and deduplication |
| Co-occurrence with pathogenic | Benign-context overlay | BP2 requires inheritance and cis/trans context |

## Regulatory Impact Categories

| Category | Criteria | ACMG use |
|----------|----------|--------------|
| **High impact** | Disrupts known TF binding motif | Regulatory prediction context; route to the appropriate regulatory or ACMG overlay before assigning evidence |
| **Moderate impact** | In active regulatory region | Consider context |
| **Low impact** | No regulatory annotation | No support |

## PVS1 Application for Truncating Variants

Call `ACMG_evidence_collector`. It runs the versioned ClinGen/SVI PVS1 decision
tree using provider-verified mechanism, selected-transcript consequence,
biotype, exon/frame/NMD, rescue-transcript, critical-region, population-LoF,
protein-length, SpliceAI, RNA, and exact CSpec facts as applicable. A complete
fact path may generate a PVS1 EvidenceCard eligible for automatic and, when
strictly verified, verified estimates. Missing or unverifiable decision points
remain listed in `criterion_reviews` without creating a positive placeholder
card. The `tooluniverse-acmg-variant-classification` Skill is the normative
description of this behavior.
