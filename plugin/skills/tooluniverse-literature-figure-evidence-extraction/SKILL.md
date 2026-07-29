---
name: tooluniverse-literature-figure-evidence-extraction
description: Extract structured evidence from literature figures, pedigrees, gels, blots, Sanger traces, RNA-splicing assay figures, and functional assay plots for downstream ToolUniverse ACMG/AMP evidence-rule overlays. Use when visual evidence from papers or supplements must be interpreted before PM3, PP1, BS4, PS2/PM6, PS3/BS3, PVS1/RNA, or related variant-classification rules are applied.
---

# Literature Figure Evidence Extraction

This skill is a lightweight ToolUniverse overlay for converting visual evidence in biomedical papers into structured, auditable evidence snippets. It is designed for figures and supplements that contain information needed by downstream ACMG/AMP rule-refinement skills.

This skill does not assign ACMG evidence codes. It extracts facts from figures, captions, OCR text, and surrounding article text. Evidence-specific skills such as `ACMG_clinical_evidence`, `ACMG_clinical_evidence`, `ACMG_functional_evidence`, and `ACMG_computational_evidence` decide whether and how the evidence affects classification.

Use existing `tooluniverse-image-analysis` for microscopy-derived measurements, segmentation, fluorescence intensity, colony morphology, image-derived statistics, or quantitative analysis from ImageJ/CellProfiler/QuPath outputs. Use this skill for literature figure semantics: pedigree interpretation, lane/trace labels, assay-panel meaning, genotype provenance, and structured extraction from published figures.

---

## When to Use This Skill

Use this skill when ACMG evidence depends on visual material such as:

- Pedigrees, family diagrams, parental genotyping figures, or segregation figures.
- RT-PCR, minigene, cDNA, RNA gel, transcript schematics, or Sanger traces used for splicing interpretation.
- Western blots, gels, enzyme assays, reporter assays, rescue assays, localization images, or functional plots.
- Variant maps, domain maps, protein schematics, or clinically important residue/domain figures.
- Supplementary figures or image-heavy tables that contain genotype, phase, functional, or transcript evidence.
- A figure must be reconciled with figure legend, OCR text, article body text, or supplementary captions before an ACMG overlay can use it.

Do not use this skill to:

- Directly apply ACMG criteria.
- Reanalyze raw microscopy images when `tooluniverse-image-analysis` is the better fit.
- Infer unseen genotypes, phase, or assay outcomes from incomplete diagrams.
- Treat low-quality OCR as proof when the visual evidence is unreadable.

---

## Core Principle

Extract only auditable facts and conservative interpretations. Every extracted conclusion must include source location, visual basis, text/caption basis when available, confidence, and ambiguity notes.

If the figure is unclear, cropped, too low resolution, missing labels, or contradicted by caption/body text, return `not_interpretable` or `low confidence` rather than guessing. Low-confidence or `not_interpretable` extraction is a downstream lead only; it must not upgrade ACMG evidence strength without corroborating text, readable source material, or a higher-confidence extraction.

---

## Evidence Extraction Workflow

1. **Retrieve and localize the source**
   - Use `tooluniverse-literature-deep-research`, `PubMed_search_articles`, `EuropePMC_search_articles`, `PMC_search_papers`, and full-text/supplement retrieval routes to identify the article and figure.
   - Record PMID, DOI, PMCID, article title, figure number, supplementary file, page number, and caption.

2. **Prepare visual evidence**
   - For local PDFs, use page rendering or image extraction tools when available, such as `pdftoppm`, `pdfimages`, and OCR tools.
   - For scanned PDFs or image-only supplements, OCR the page first when feasible.
   - Preserve the figure panel label and surrounding caption/body text.

3. **Classify the figure type**
   - Assign one or more figure types: `pedigree`, `segregation_family`, `functional_assay`, `rna_splicing_assay`, `sanger_trace`, `gel_or_western_blot`, `protein_domain_or_variant_map`, `clinical_imaging_or_phenotype`, or `unclear_or_mixed`.

4. **Perform LLM-assisted visual reading**
   - Read symbols, labels, legends, arrows, sample IDs, lane names, proband indicators, affected/unaffected states, genotypes, parental labels, control labels, and quantitative axes.
   - Cross-check visual observations against caption/body text and OCR output.
   - Distinguish what is explicitly visible from what is inferred.

5. **Emit structured evidence**
   - Use the general output format below and the figure-type schema in `references/figure_evidence_schema.md`.
   - Include downstream ACMG overlays that may consume the extracted evidence.
   - Do not apply the evidence code here.
   - For PP1, PS4, PS3/BS3, PM3, or PS2/PM6 downstream use, include source/panel, sample ID, genotype, phenotype or assay readout, confidence, and ambiguity fields. Missing critical fields should be reported as `not_interpretable`.

---

## General Output Format

```markdown
Figure evidence extraction:
- Source: [PMID/DOI/file], [figure/table/supplement/page/panel]
- Figure type: [pedigree / segregation_family / functional_assay / rna_splicing_assay / sanger_trace / gel_or_western_blot / protein_domain_or_variant_map / clinical_imaging_or_phenotype / unclear_or_mixed]
- Variant(s): [HGVS or source notation]
- Gene/disease context: [if available]
- Visual observations: [short factual observations visible in the figure]
- Text/caption context: [caption/body/OCR facts used to interpret the figure]
- Structured interpretation: [schema-specific result]
- Relevant ACMG overlays: [PM3 / PP1 / BS4 / PS2_PM6 / PS3_BS3 / PVS1_RNA / PS1_splicing / PM1 / other]
- Confidence: [high / medium / low / not_interpretable]
- Ambiguities: [missing labels, unclear phase, unreadable axis, cropped panel, inconsistent caption, etc.]
- Downstream-use limit: [countable facts / lead only due to low confidence / not_interpretable]
- ACMG assignment: Not assigned by this figure-extraction skill.
```

---

## Figure-Type Guidance

### Pedigrees and Phase Evidence

Use for PM3, PP1, BS4, PS2/PM6, and BP2-style phase evidence.

Extract:

- Proband ID and affected status.
- Assessed variant and other allele when present.
- Maternal and paternal genotypes, if visible or stated.
- Whether variants are confirmed in trans, presumed in trans from one-parent testing, phase unknown, homozygous, or not_interpretable from the figure.
- Whether a de novo claim is supported by tested parents.
- Which family members are informative for co-segregation or non-segregation.

Do not infer trans phase from a pedigree unless the figure/caption/body shows parental origin, explicit "compound heterozygous" or "in trans" wording, reads-backed phase, or equivalent evidence.

### Functional Assay Figures

Use for PS3/BS3 extraction, then pass to `ACMG_functional_evidence`.

Extract:

- Assay class, model system, readout, controls, replicates, and variant result.
- Axis labels, units, direction of abnormality, thresholds, statistical markers, and number of tested controls when visible.
- Whether the figure provides raw quantitative values, only qualitative trend, or insufficient numeric detail.

Use `tooluniverse-image-analysis` when the task requires image-derived measurement statistics, segmentation, fluorescence quantification, or formal reanalysis of image-derived CSV/TSV data.

### RNA/Splicing Figures

Use for PVS1/RNA, BP7/RNA, PS1-splicing, or PS3/BS3 boundary review.

Extract:

- Assay type: RT-PCR, minigene, cDNA sequencing, RNA-seq, Sanger of transcript product, gel, or transcript schematic.
- Observed transcript products: exon skipping, intron retention, pseudoexon inclusion, cryptic donor/acceptor, normal transcript, or complex profile.
- Whether transcript abundance, NMD prediction, in-frame/out-of-frame consequence, or rescue transcript evidence is visible or stated.
- Whether the result supports no splicing impact, partial effect, or LoF transcript evidence.

Do not convert RNA figure extraction directly into `PVS1_Strength (RNA)`; pass the structured result to `ACMG_computational_evidence`.

### Gels, Blots, and Sanger Traces

Extract:

- Lane/sample labels, controls, genotype labels, band sizes/intensity trends, peak labels, and whether the figure supports genotype confirmation or functional readout.
- Whether a lane/trace identifies a parent, proband, control, or variant carrier.
- Whether low resolution, overexposure, cropped lanes, missing molecular weight labels, or unclear peak labels weaken interpretation.

Use only as supporting extracted facts unless downstream ACMG overlays can evaluate assay validity.

---

## Confidence Levels

| Confidence | Use when |
|------------|----------|
| High | Figure labels, caption/body text, and visual evidence agree; key fields are legible and source location is clear. |
| Medium | Main conclusion is supported, but one non-critical label, count, or context detail is missing or inferred from caption/body text. |
| Low | Figure is partially legible, caption is incomplete, labels are ambiguous, or interpretation depends on weak OCR. |
| Not interpretable | Critical labels, genotype, phase, assay result, or source context cannot be read or verified. |

Low-confidence or not-interpretable extractions should not be used to activate or upgrade ACMG criteria without independent corroboration.

---

## Double-Counting Boundary

This skill extracts figure facts only. Downstream overlays must still avoid double counting:

- RNA-splicing figure evidence used for `PVS1_Strength (RNA)` should not also be counted as PS3.
- A pedigree used for PM3 phase evidence should not also be counted as independent PP1 evidence unless the individuals and inference are truly distinct.
- Functional assay figures used for PS3/BS3 should not also be treated as PP3/BP4 prediction evidence.
- Sanger traces that confirm genotype are not themselves functional evidence.

---

## Tool Parameter Reference

| Tool or skill | Use |
|---------------|-----|
| `tooluniverse-literature-deep-research` | Retrieve article, supplements, captions, and figure context before visual extraction. |
| `tooluniverse-image-analysis` | Quantitative image-derived measurements, segmentation, fluorescence/cell-count statistics, and assay plots when numeric reanalysis is needed. |
| `PubMed_search_articles` / `EuropePMC_search_articles` / `PMC_search_papers` | Locate article and full-text routes. |
| `EuropePMC_get_fulltext_snippets` or full-text retrieval tools | Extract caption/body context around figure mentions when available. |
| Local PDF tools such as `pdftotext`, `pdftoppm`, `pdfimages`, `ocrmypdf`, and `tesseract` | Optional helpers for local PDFs, page rendering, image extraction, and OCR. |
| Vision-capable LLM inspection | Read figure semantics, labels, pedigree symbols, lanes, traces, and visual relationships. |

---

## Limitations

- This skill is not a deterministic computer-vision system.
- LLM visual extraction must be treated as evidence curation, not as automatic classification.
- Low-resolution, cropped, or compressed figures may not support reliable extraction.
- Figure captions and article text can contradict or clarify the image; always reconcile them.
- Gene- or disease-specific VCEP rules determine how extracted evidence is used for ACMG evidence assignment.

---

## Related Skills

- `tooluniverse-literature-deep-research`
- `tooluniverse-image-analysis`
- `ACMG_clinical_evidence`
- `ACMG_clinical_evidence`
- `ACMG_functional_evidence`
- `ACMG_computational_evidence`
- `ACMG_evidence_collector`
