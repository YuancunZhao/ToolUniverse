# SV/CNV Evidence Intake Report Template

Use this template when generating an SV/CNV evidence summary. This report is not a final germline ACMG classification.

## File Naming Convention

```text
SV_evidence_intake_[TYPE]_chr[CHR]_[START]_[END]_[GENES].md
```

## Report Template

```markdown
# Structural Variant Evidence Intake Report: [SV_IDENTIFIER]

**Generated**: [Date] | **Analyst**: ToolUniverse SV/CNV Evidence Intake

## Executive Summary

| Field | Value |
| --- | --- |
| SV type | Deletion / Duplication / Inversion / Translocation / Complex |
| Coordinates | chr_:________-________ ([build]) |
| Size | ___ kb |
| Gene content | X fully contained, Y partially disrupted, Z flanking |
| Intake status | evidence summary only |
| Final ACMG status | not computed here; route to `tooluniverse-acmg-variant-classification` |
| Key route candidates | [cnv_sv_bundle, consequence_lof_bundle, population_frequency_bundle, ...] |

## 1. SV Identity and Normalization

- Genome build:
- SV type:
- Coordinates:
- Copy number / zygosity:
- Breakpoint precision:
- Inheritance status:
- Assay/source:

## 2. Gene Content and Breakpoint Impact

### Fully Contained Genes

| Gene | Transcript | Disease association | Inheritance | Dosage context | Evidence source |
| --- | --- | --- | --- | --- | --- |

### Partially Disrupted Genes

| Gene | Breakpoint location | Predicted molecular effect | Critical region/domain | Evidence source |
| --- | --- | --- | --- | --- |

### Flanking / Regulatory Candidates

| Gene/element | Distance | Regulatory or position-effect rationale | Evidence source |
| --- | ---: | --- | --- |

## 3. Dosage Sensitivity and Gene-Disease Context

| Gene | ClinGen HI | ClinGen TS | Gene-disease validity | Disease context | Route implication |
| --- | --- | --- | --- | --- | --- |

## 4. Population and Source Overlap Evidence

| Source | Query result | Reciprocal overlap | Frequency / assertion | Interpretation as lead | Candidate route |
| --- | --- | ---: | --- | --- | --- |

## 5. Literature, Clinical, and Figure Evidence

| Source | Full text / supplement / figure status | Evidence type | Extracted facts | Candidate route |
| --- | --- | --- | --- | --- |

## 6. Candidate ACMG Route Plan

| Bundle | Trigger found? | Required overlays/checks | Coverage required | Status | Reason |
| --- | --- | --- | --- | --- | --- |
| cnv_sv_bundle | yes | SV/CNV evidence intake | coordinates, gene content, dosage, frequency, source overlap | completed | SV/CNV input |

## 7. Handoff to ACMG Overlays

- Required next skill: `tooluniverse-acmg-variant-classification`
- Required routing core: `tooluniverse-acmg-overlay-routing-core`
- Evidence compatibility required: yes
- Bayesian combine allowed now: no, only after `current_counted_evidence_resolved`

## 8. Missing Inputs / Limitations

| Missing input | Affected route | Impact |
| --- | --- | --- |

## Data Sources

List ToolUniverse tools, database versions, literature sources, and unavailable sources.
```
