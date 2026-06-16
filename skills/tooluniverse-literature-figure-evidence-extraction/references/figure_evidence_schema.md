# Figure Evidence Extraction Schema

This reference defines structured fields for visual evidence extracted from literature figures. Use the smallest schema that fits the figure. If required fields are unreadable or absent, return `not_interpretable` for that interpretation.

---

## General Fields

| Field | Required content |
|-------|------------------|
| `source` | PMID, DOI, PMCID, file name, figure/table/supplement/page/panel. |
| `figure_type` | `pedigree`, `segregation_family`, `functional_assay`, `rna_splicing_assay`, `sanger_trace`, `gel_or_western_blot`, `protein_domain_or_variant_map`, `clinical_imaging_or_phenotype`, or `unclear_or_mixed`. |
| `variant_context` | Variant notation exactly as shown plus normalized notation if available. |
| `gene_disease_context` | Gene, disease, inheritance, and source context if available. |
| `visual_observations` | Factual observations visible in the figure. |
| `text_context` | Caption, body text, OCR, or supplement text used to interpret the visual. |
| `confidence` | `high`, `medium`, `low`, or `not_interpretable`. |
| `ambiguities` | Missing labels, low resolution, cropped panel, conflict, or unclear inference. |

---

## PM3 Pedigree / Phase Schema

| Field | Required content |
|-------|------------------|
| `proband_id` | Proband label and figure basis. |
| `proband_affected_status` | Affected, unaffected, unclear. |
| `assessed_variant` | Variant being interpreted. |
| `other_allele_variant` | Other variant in the proband, if present. |
| `mother_genotype` | Carrier of assessed variant, carrier of other allele, negative, not tested, unclear. |
| `father_genotype` | Carrier of assessed variant, carrier of other allele, negative, not tested, unclear. |
| `phase_evidence_basis` | Pedigree, Sanger trace, caption text, explicit in-trans wording, reads, or unknown. |
| `phase_conclusion` | Confirmed in trans, presumed in trans from one-parent testing, phase unknown, homozygous, not_interpretable. |
| `pm3_ready` | Whether enough fields are present for PM3 overlay scoring. |

---

## PP1 / BS4 Segregation Schema

| Field | Required content |
|-------|------------------|
| `family_id` | Family or pedigree identifier. |
| `inheritance_model` | AD, AR, X-linked, mitochondrial, unclear. |
| `affected_carriers` | Count/list. |
| `unaffected_carriers` | Count/list and whether age/penetrance makes them informative. |
| `affected_non_carriers` | Count/list and possible phenocopy explanation. |
| `unaffected_non_carriers` | Count/list. |
| `informative_meioses` | Count if readable or stated. |
| `lod_score` | Published/calculated LOD if shown. |
| `segregation_conclusion` | Supports segregation, possible non-segregation, uninformative, not_interpretable. |
| `pp1_ready` | Whether enough fields are present for PP1/BS4 overlay review. |

---

## PS2 / PM6 De Novo Schema

| Field | Required content |
|-------|------------------|
| `proband_id` | Proband label. |
| `proband_affected_status` | Affected, unaffected, unclear. |
| `variant` | Variant shown or stated. |
| `mother_tested` | Yes/no/unclear. |
| `father_tested` | Yes/no/unclear. |
| `maternal_result` | Negative, carrier, unclear, not tested. |
| `paternal_result` | Negative, carrier, unclear, not tested. |
| `parentage_confirmed` | Confirmed, not confirmed, not stated. |
| `de_novo_conclusion` | Confirmed de novo, assumed de novo, inherited, not_interpretable. |

---

## Functional Assay Schema

| Field | Required content |
|-------|------------------|
| `assay_class` | Enzyme, reporter, rescue, localization, abundance, binding, electrophysiology, model organism, MAVE/DMS, other. |
| `model_system` | Patient-derived, cell line, cDNA, endogenous edit, organism, in vitro, unclear. |
| `readout` | Measurement, units, direction of abnormality. |
| `controls` | Wild-type/normal, abnormal/null, benign/pathogenic variant controls if shown. |
| `replicates_or_error_bars` | Replicates, SD/SEM/CI, not shown, unclear. |
| `variant_result` | Normal, abnormal, intermediate, conflicting, not_interpretable. |
| `quantitative_values` | Values if visible or extracted; otherwise qualitative trend. |
| `statistics` | p-values, significance markers, thresholds, or not shown. |
| `ps3_bs3_ready` | Whether enough fields are present for PS3/BS3 overlay review. |

---

## RNA / Splicing Figure Schema

| Field | Required content |
|-------|------------------|
| `assay_type` | RT-PCR, minigene, cDNA sequencing, RNA-seq, Sanger of transcript, gel, schematic, other. |
| `sample_source` | Patient tissue/cell, blood, fibroblast, minigene, cell line, unclear. |
| `normal_transcript` | Present/absent/unclear. |
| `aberrant_transcript` | Exon skipping, intron retention, pseudoexon inclusion, cryptic site, complex, none, unclear. |
| `sequence_confirmation` | Sanger/RNA-seq/caption confirmation, not shown, unclear. |
| `abundance_or_ratio` | Quantified, qualitative, not shown. |
| `predicted_protein_effect` | Out-of-frame/NMD, in-frame, unknown, not shown. |
| `pvs1_rna_ready` | Whether enough fields are present for PVS1/RNA overlay review. |

---

## Sanger / Gel / Blot Schema

| Field | Required content |
|-------|------------------|
| `panel_type` | Sanger, gel, western blot, northern blot, other. |
| `sample_labels` | Proband, parents, controls, lanes, or unclear. |
| `variant_or_target` | Variant, amplicon, protein, transcript, or target. |
| `observed_signal` | Peak, band, product size, intensity trend, absent/present signal. |
| `control_signal` | WT/control/null/marker lane if shown. |
| `interpretation_supported` | Genotype confirmation, parental origin, transcript product, protein abundance, functional trend, not_interpretable. |
| `limitations` | Cropped lanes, unreadable peaks, overexposure, missing marker, missing labels, low resolution. |

---

## Protein Domain / Variant Map Schema

| Field | Required content |
|-------|------------------|
| `protein_reference` | UniProt/transcript/protein isoform if shown. |
| `variant_position` | Residue or region. |
| `domain_or_region` | Domain, motif, active site, hotspot, constrained region, unclear. |
| `comparison_variants` | Known P/LP/B/LB variants shown in same region. |
| `map_interpretation` | Region supports PM1/PS1/PM5 context, uninformative, not_interpretable. |
| `recommended_overlay` | PM1, PS1, PM5, or other downstream overlay. |
