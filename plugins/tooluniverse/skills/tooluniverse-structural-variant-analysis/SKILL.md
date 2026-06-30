---
name: tooluniverse-structural-variant-analysis
description: Structural variant (SV/CNV) evidence intake for deletions, duplications, inversions, translocations, and complex rearrangements. Retrieves coordinates, gene content, dosage sensitivity, population SV frequency, breakpoint, overlap, inheritance, and literature evidence, then routes germline pathogenicity assessment through ToolUniverse ACMG overlays rather than producing a standalone final ACMG classification.
disable-model-invocation: true
---

# Structural Variant Analysis Workflow

This skill collects and organizes SV/CNV evidence. It does not by itself assign final germline ACMG/AMP classification.

For germline pathogenicity assessment, pass the SV evidence summary to `tooluniverse-acmg-variant-classification` through `tooluniverse-acmg-overlay-routing-core`, especially the `cnv_sv_bundle`, `consequence_lof_bundle`, `population_frequency_bundle`, `clinical_observation_bundle`, `literature_functional_bundle`, and `final_combine_bundle`.

**LOOK UP, DON'T GUESS**: retrieve ClinGen dosage sensitivity, gene validity, population SV frequency, ClinVar/dbVar/DGVa overlap, and literature evidence with tools. Do not infer dosage sensitivity from gene function alone.

## Key Boundaries

- This skill outputs `sv_evidence_summary`, `candidate_acmg_routes`, `coverage_audit`, and `missing_inputs`.
- It must not output final germline ACMG classification, Tavtigian posterior, or counted ACMG evidence without the ACMG overlay route audit and Evidence Compatibility Resolution.
- ClinVar, DECIPHER, dbVar, DGVa, or literature labels are source leads until primary evidence is routed through the relevant overlay.
- A heuristic SV impact summary may be reported for orientation, but label it `not_final_acmg_classification`.

## Triggers

Use this skill when users provide or ask about:

- Copy-number variants from array, WGS, exome CNV, or sequencing.
- Deletions, duplications, inversions, translocations, breakends, or complex rearrangements.
- Exon-level or whole-gene deletion/duplication events.
- Breakpoint disruption, gene fusion, regulatory separation, or dosage sensitivity.

## Workflow Overview

```text
Phase 1: SV identity and normalization
Phase 2: Gene content and breakpoint impact
Phase 3: Dosage sensitivity and gene-disease validity
Phase 4: Population SV and overlap evidence
Phase 5: Literature, phenotype, and clinical observation intake
Phase 6: ACMG route candidate generation
Phase 7: Hand off to ACMG overlays and final compatibility/combination
```

## Phase 1: SV Identity and Normalization

Capture chromosome(s), coordinates, genome build, SV type, size, breakpoint precision, zygosity/copy number, assay type, and inheritance status if available.

Normalize hg19/hg38 coordinates when needed and state uncertainty around imprecise breakpoints.

## Phase 2: Gene Content and Breakpoint Impact

Classify affected genes as:

- `fully_contained`: entire gene lies inside deletion/duplication.
- `partially_disrupted`: breakpoint interrupts a transcript, exon, or regulatory region.
- `flanking`: within a plausible position-effect window.
- `fusion_candidate`: rearrangement may create or disrupt a fusion transcript.

Record transcript, exon, coding-frame, domain, and regulatory context when available. Breakpoint disruption may later route to PVS1, PM4/BP3, PS3/BS3, or other overlays depending on consequence and mechanism.

## Phase 3: Dosage Sensitivity and Gene-Disease Validity

Required retrieval:

- `ClinGen_search_dosage_sensitivity` for HI/TS scores.
- `ClinGen_search_gene_validity` for gene-disease validity and disease context.
- OMIM/MedGen/GeneReviews or similar disease resources when inheritance or mechanism is ambiguous.

Interpretation for intake:

- HI/TS score 3 is strong dosage-context evidence for route planning, not a standalone final classification.
- HI/TS score 2 is emerging dosage-context evidence and should trigger careful context review.
- pLI/LOEUF can support LoF intolerance context but does not replace ClinGen dosage or disease-specific mechanism review.

## Phase 4: Population SV and Overlap Evidence

Query population and clinical SV resources when available:

- gnomAD SV / population SV frequency.
- ClinVar/dbVar/DGVa or equivalent known SV records.
- DECIPHER or case databases when legally and technically available.

Use reciprocal overlap to compare SVs. Record the threshold used, typically at least 70% reciprocal overlap for candidate same-event comparison, but let disease-specific or VCEP guidance override.

Population and overlap evidence routes to ACMG overlays:

- High frequency: BA1/BS1/benign-context overlays.
- Absence or rarity: PM2 overlay; default PM2 strength remains controlled by ClinGen SVI PM2 guidance.
- ClinVar/dbVar labels: PP5/BP6 source-review overlay first, then source fan-out only when primary evidence is visible.

## Phase 5: Literature, Phenotype, and Clinical Observation Intake

Use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when evidence depends on papers, supplements, pedigrees, breakpoint figures, dosage plots, functional assays, or cohort tables.

Route clinical observations as follows:

- De novo SV: `tooluniverse-acmg-de-novo-evidence-refinement`.
- Segregation or non-segregation: `tooluniverse-acmg-pp1-segregation-refinement`.
- Case-control, cohort, recurrence, or enrichment evidence: `tooluniverse-acmg-ps4-case-enrichment-refinement`.
- Biallelic recessive affected-proband evidence: `tooluniverse-acmg-pm3-in-trans-refinement`.
- Functional assay evidence: `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.

Do not reuse the same individual or family across incompatible clinical-observation criteria; final reuse/cap decisions are handled by Evidence Compatibility Resolution.

## Phase 6: ACMG Route Candidate Generation

Generate route candidates instead of final evidence codes:

| SV evidence found | Candidate bundle / overlay route |
| --- | --- |
| Whole-gene or exon deletion in LoF/HI disease context | `consequence_lof_bundle` -> `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` |
| In-frame exon or protein-length change | `protein_length_bundle` -> `tooluniverse-acmg-pm4-bp3-protein-length-refinement` |
| High population SV frequency | `population_frequency_bundle` -> BA1 exception / benign-context overlays |
| Absent or rare population SV | `population_frequency_bundle` -> `tooluniverse-acmg-pm2-absence-rarity-refinement` |
| Same or overlapping source assertion | `literature_functional_bundle` / source review -> `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` before fan-out |
| De novo status | `clinical_observation_bundle` -> `tooluniverse-acmg-de-novo-evidence-refinement` |
| Segregation or affected relatives | `clinical_observation_bundle` -> `tooluniverse-acmg-pp1-segregation-refinement` |
| Case enrichment | `literature_functional_bundle` -> `tooluniverse-acmg-ps4-case-enrichment-refinement` |
| Functional dosage or breakpoint assay | `literature_functional_bundle` -> `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` |

## Phase 7: Hand Off to ACMG Overlays

For final germline interpretation:

1. Call `tooluniverse-acmg-variant-classification`.
2. Include the SV evidence summary under `cnv_sv_bundle`.
3. Expand candidate routes using `tooluniverse-acmg-overlay-routing-core`.
4. Apply evidence-specific overlays or VCEP-specific rules.
5. Run Evidence Compatibility Resolution.
6. Combine only `current_counted_evidence_resolved`.

## Output

Use `REPORT_TEMPLATE.md`. Required sections:

- SV identity and normalization.
- Gene content and breakpoint impact.
- Dosage sensitivity and gene-disease context.
- Population/overlap evidence.
- Literature and clinical observation intake.
- Candidate ACMG route plan.
- Missing inputs and limitations.
- Hand-off status to ACMG overlays.

Do not present a final germline ACMG verdict from this skill alone.

## Required Tools Reference

- `ClinGen_search_dosage_sensitivity`: HI/TS scores.
- `ClinGen_search_gene_validity`: gene-disease validity.
- `ClinVar_search_variants`: known source assertions and overlapping records.
- `ensembl_lookup_gene`: gene coordinates and transcript structure.
- `OMIM_search`, `OMIM_get_entry`, `MedGen_search_conditions`: disease context.
- `gnomad_search_variants` or SV-specific gnomAD tools: population frequency.
- `PubMed_search_articles`, `EuropePMC_search_articles`: literature evidence.
- `DisGeNET_search_gene`, `GO_get_term_details`: background context only.
