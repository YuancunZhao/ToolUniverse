# SV/CNV Evidence Intake Reference

Use this reference when a VCF or regional query contains structural variants. It supports evidence retrieval and routing only. Final germline ACMG classification must be produced by `tooluniverse-acmg-variant-classification` after overlay route audit and Evidence Compatibility Resolution.

## Step 1: Parse SV Calls

Capture:

- `SVTYPE`
- chromosome, start, end, genome build
- size
- copy number / zygosity if available
- breakpoint precision
- inheritance field if present
- affected samples and genotype quality

## Step 2: Identify Gene and Transcript Impact

For each SV:

- fully contained genes
- partially disrupted genes
- affected exons/transcripts
- flanking/regulatory candidates
- possible fusion or position-effect mechanism

## Step 3: Retrieve Dosage and Disease Context

Query:

- ClinGen dosage sensitivity for HI/TS.
- ClinGen gene-disease validity.
- OMIM/MedGen/GeneReviews or equivalent disease context when inheritance or mechanism is unclear.

Dosage scores guide route planning. They are not standalone final ACMG evidence without the appropriate overlay route.

## Step 4: Retrieve Population and Source Overlap

Query:

- gnomAD SV or equivalent population SV frequency.
- ClinVar/dbVar/DGVa overlap.
- DECIPHER or case databases when available and appropriate.

Record reciprocal overlap, breakpoint precision, population ancestry, source assertion, and review status. Source labels are leads until primary evidence is routed.

## Step 5: Generate ACMG Route Candidates

| Evidence found | Candidate route |
| --- | --- |
| Whole-gene/exon deletion or LoF-like breakpoint | `cnv_sv_bundle` -> `consequence_lof_bundle` -> PVS1 LoF decision tree |
| In-frame exon or protein length change | `protein_length_bundle` -> PM4/BP3 overlay |
| High or disease-incompatible frequency | `population_frequency_bundle` -> BA1/BS1/benign-context overlays |
| Absence/rarity in population SV data | `population_frequency_bundle` -> PM2 overlay |
| De novo observation | `clinical_observation_bundle` -> PS2/PM6 overlay |
| Segregation / non-segregation | `clinical_observation_bundle` -> PP1/BS4/PP4 overlay |
| Case-control, cohort, recurrence, or enrichment evidence | `literature_functional_bundle` -> PS4 overlay |
| Functional assay | `literature_functional_bundle` -> PS3/BS3 overlay |
| ClinVar/dbVar/lab/paper assertion | PP5/BP6 source-review overlay before any fan-out |

## Step 6: Report SV Intake

Return:

```markdown
## SV/CNV Evidence Intake
- SV identity:
- Gene content:
- Dosage context:
- Population / overlap context:
- Literature / clinical observation context:
- Candidate ACMG route bundles:
- Missing inputs:
- Final germline ACMG status: not computed in this skill
```

## Example: Regional CNV Query

```python
sv_summary = {
    "sv_type": "DEL",
    "coordinates": "chr17:43044295-43070295",
    "genome_build": "GRCh38",
    "gene_content": ["BRCA1"],
    "dosage_context": "ClinGen dosage to be retrieved",
    "population_context": "gnomAD SV overlap to be retrieved",
    "candidate_routes": [
        "cnv_sv_bundle",
        "consequence_lof_bundle",
        "population_frequency_bundle",
        "final_combine_bundle"
    ],
    "final_germline_acmg_status": "not_computed_here"
}
```

Send the summary to `tooluniverse-structural-variant-analysis` for richer SV evidence intake or directly to `tooluniverse-acmg-variant-classification` for routed ACMG assessment.

## Guardrails

- Do not convert deletion + HI score + rarity into final ACMG classification inside this skill.
- Do not count source labels as ACMG evidence.
- Do not reuse the same proband/family across PS4, PM3, PS2/PM6, PP1, or PP4.
- Do not compute Bayesian posterior until `current_counted_evidence_resolved` is available.
