# SV/CNV Evidence Intake Examples

These examples show how to summarize structural-variant evidence and route it to ACMG overlays. They are not standalone final ACMG classifications.

## Example 1: Whole-Gene Deletion in a Dosage-Sensitive Gene

### Input

```text
Deletion chr17:31,000,000-31,300,000, GRCh38, heterozygous, overlaps all exons of GENE1.
```

### Evidence Intake

| Evidence category | Finding | Source type | Route implication |
| --- | --- | --- | --- |
| SV identity | Heterozygous deletion, precise breakpoints | user / VCF | `cnv_sv_bundle` |
| Gene content | Whole-gene deletion of GENE1 | coordinate overlap | `consequence_lof_bundle` candidate |
| Dosage context | ClinGen HI score should be retrieved | ClinGen dosage | mechanism/PVS1 gate |
| Population context | gnomAD SV frequency should be queried | population SV | `population_frequency_bundle` |
| Source assertions | ClinVar/dbVar overlap should be reviewed | source lead | PP5/BP6 source-review before fan-out |

### Candidate Route Plan

| Bundle | Trigger found? | Required overlays/checks | Status |
| --- | --- | --- | --- |
| cnv_sv_bundle | yes | SV evidence intake | completed |
| baseline_context_bundle | yes | multiple-disorder and mechanism context | planned |
| consequence_lof_bundle | yes | PVS1 LoF decision tree | planned |
| population_frequency_bundle | yes | BA1/BS1/PM2/benign-context overlays | planned |
| final_combine_bundle | later | route audit, compatibility, Bayesian combine | blocked until overlays finish |

### Handoff

Send the evidence summary to `tooluniverse-acmg-variant-classification`. Count no final ACMG evidence until the relevant overlays produce route outcomes and Evidence Compatibility Resolution returns `current_counted_evidence_resolved`.

## Example 2: Duplication With Unclear Triplosensitivity

### Input

```text
Duplication chrX:150,000,000-150,120,000, includes part of GENE2.
```

### Evidence Intake

| Evidence category | Finding | Route implication |
| --- | --- | --- |
| SV type | Partial-gene duplication | `cnv_sv_bundle` |
| Molecular consequence | Breakpoint may disrupt transcript or create altered product | `protein_length_bundle` or PVS1 branch only after transcript review |
| Dosage context | TS score missing or uncertain | `baseline_context_bundle`, `not_assessed` until retrieved |
| Population | Frequency must be checked by reciprocal overlap | `population_frequency_bundle` |

### Handoff

Do not infer pathogenicity from duplication size alone. Route altered-product or dosage evidence through ACMG overlays and mark missing dosage/transcript information explicitly.

## Example 3: Recurrent CNV With Literature Cases

### Input

```text
Deletion in a recurrent microdeletion region; paper reports several affected cases and a shared interval.
```

### Evidence Intake

| Evidence category | Required extraction | Route implication |
| --- | --- | --- |
| Case evidence | Case definition, unrelatedness, denominator, ancestry, controls, duplicate reports | `tooluniverse-acmg-ps4-case-enrichment-refinement` |
| Pedigree evidence | Affected/unaffected relatives, genotypes, informative meioses | `tooluniverse-acmg-pp1-segregation-refinement` |
| De novo evidence | Parental testing and parentage confirmation | `tooluniverse-acmg-de-novo-evidence-refinement` |
| Figure/table evidence | Supplement and figure readability, sample IDs, genotype/readout confidence | literature figure extraction before scoring |

### Handoff

The same proband cannot be reused across PS4, PP1, PM3, or PS2/PM6. Final reuse decisions belong to Evidence Compatibility Resolution in `tooluniverse-acmg-overlay-routing-core`.
