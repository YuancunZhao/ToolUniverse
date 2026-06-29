# Variant Interpretation Examples

These examples demonstrate retrieval, route planning, and reporting. Final germline ACMG classification must be produced by `tooluniverse-acmg-variant-classification` after overlay route audit and Evidence Compatibility Resolution.

## Example 1: Known Source Assertion for a Truncating Variant

### Input

```text
BRCA1 NM_007294.4:c.68_69del
```

### Retrieval Summary

| Evidence source | Finding | Interpretation role |
| --- | --- | --- |
| VariantValidator / VEP | Frameshift or LoF-like consequence | Route trigger |
| ClinVar | Source assertion may exist | Source lead only until primary evidence is reviewed |
| gnomAD | Frequency and coverage required | Population-frequency bundle |
| ClinGen / GenCC / GeneReviews | LoF/HI mechanism context | Baseline context bundle |

### Bundle Route Plan

| Bundle | Trigger found? | Required overlays/checks |
| --- | --- | --- |
| baseline_context_bundle | yes | disease/mechanism context |
| population_frequency_bundle | yes | BA1/BS1/PM2/benign-context overlays |
| consequence_lof_bundle | yes | PVS1 LoF decision-tree overlay |
| literature_functional_bundle | if source/literature evidence appears | PP5/BP6 source review and primary-evidence fan-out |
| final_combine_bundle | after overlays | compatibility and final combine |

### Report Behavior

Do not count a ClinVar or paper label directly. Report final status only after the ACMG overlay workflow produces `current_counted_evidence_resolved`.

## Example 2: Missense VUS With Predictors and Same-Residue Leads

### Input

```text
TP53 NM_000546.6:c.524G>A (p.Arg175His)
```

### Retrieval Summary

| Evidence source | Finding | Interpretation role |
| --- | --- | --- |
| VEP / MyVariant | Missense consequence and predictor context | Prediction context |
| ClinVar / literature | Possible same-residue or same-amino-acid comparison records | Source leads |
| UniProt / InterPro | Functional region context | Regional evidence lead |
| MaveDB / functional databases | Structured functional score may exist | Functional discovery trigger |

### Bundle Route Plan

| Bundle | Trigger found? | Required overlays/checks |
| --- | --- | --- |
| baseline_context_bundle | yes | disease/mechanism context |
| population_frequency_bundle | yes | frequency and PM2/benign-context review |
| missense_bundle | yes | PP3/BP4, PS1/PM5, PM1/PP2/BP1, structured functional discovery |
| literature_functional_bundle | if assay/source evidence appears | PS3/BS3 or source-review route |
| final_combine_bundle | after overlays | compatibility and final combine |

### Report Behavior

Do not use predictor voting. Do not treat comparison-variant labels as PS1/PM5 until primary evidence, independence, mechanism, and splicing confounding are reviewed by the overlay.

## Example 3: Deep Intronic Splice Candidate

### Input

```text
NM_000059.4:c.7977+100A>G
```

### Retrieval Summary

| Evidence source | Finding | Interpretation role |
| --- | --- | --- |
| VEP / transcript annotation | Intronic position and transcript context | Splice bundle trigger |
| Splice prediction | Prediction context | PP3/BP4 or splicing-comparison route only |
| RNA assay or RT-PCR paper | Observed transcript consequence if available | RNA/splicing PVS1 or RNA no-impact route |
| ClinVar / literature | Source assertions and comparison variants | Source leads |

### Bundle Route Plan

| Bundle | Trigger found? | Required overlays/checks |
| --- | --- | --- |
| baseline_context_bundle | yes | disease/mechanism context |
| population_frequency_bundle | yes | frequency context |
| splice_bundle | yes | prediction/comparison path; RNA refinement only if RNA evidence exists |
| literature_functional_bundle | if RNA paper or figure exists | deep literature and figure extraction |
| final_combine_bundle | after overlays | compatibility and final combine |

### Report Behavior

Prediction-only splice evidence is not RNA-assay evidence. Direct RNA observations, if available, supersede prediction-only assumptions for the same splicing event and must be checked for double counting with PS3/BS3 and PP3/BP4.
