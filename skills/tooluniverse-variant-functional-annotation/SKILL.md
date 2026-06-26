---
name: tooluniverse-variant-functional-annotation
description: Functional annotation of protein variants — ProtVar structural/functional context, ClinVar clinical classifications, gnomAD population frequencies, CADD deleteriousness, ClinGen gene-disease validity. Use for variant annotation pipelines, missense effect prediction, and protein-level variant interpretation with functional context.
disable-model-invocation: true
---

# Protein Variant Functional Annotation

Comprehensive functional annotation of protein variants by combining ProtVar structural/functional
context, ClinVar clinical classifications, gnomAD population frequencies, CADD deleteriousness
scoring, and ClinGen gene-disease validity.

**Differentiation from ACMG classification**: This skill focuses specifically on
**protein-level functional evidence** — structural mapping, residue context, protein domain impact,
and population allele frequencies. It does NOT produce full ACMG classifications or treatment
recommendations. Use `tooluniverse-acmg-variant-classification` for final germline ACMG/pathogenicity classification.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

**Triggers**:
- "Annotate variant [GENE]:[protein_change]" (e.g., "TP53:p.R175H")
- "What is the functional impact of [variant]?"
- "ProtVar annotation for [HGVS or rsID]"
- "Population frequency of [variant]"
- "Is [variant] in a conserved domain?"
- "Structural context of [amino acid change]"

---

## Functional Annotation Context

This skill retrieves and summarizes biological context for a protein variant. It does not assign ACMG/AMP evidence strength, does not produce final germline pathogenicity classification, and does not replace `tooluniverse-acmg-variant-classification`.

Use its output as `retrieval_context`, `prediction_context`, `protein_region_context`, or `source_assertion` input for the ACMG overlay workflow.

**1. Conservation: Is the position evolutionarily constrained?**
If the residue has been maintained across vertebrates or all eukaryotes, mutation may be more likely to affect protein function. ProtVar's conservation score and GERP/PhastCons from OpenCRAVAT quantify this. Report the values and route any computational evidence to the PP3/BP4 overlay or a current VCEP rule.

**2. Location: Is it in a functionally critical region?**
A variant in an annotated active site, binding site, PTM site, or constrained domain can provide protein-region context. Do not convert broad domain membership into PM1 inside this skill. Route regional evidence to `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` or the relevant VCEP.

**3. Population frequency: Is it rare enough to be pathogenic?**
Report global AF, ancestry maximum AF, homozygote/hemizygote counts, and coverage caveats. Do not assign PM2, BA1, BS1, or BS2 here. Route frequency evidence to the ACMG population-frequency overlays.

**4. Computational prediction: Do algorithms agree?**
CADD, REVEL, AlphaMissense, SIFT, PolyPhen, EVE, conservation, and similar scores are prediction context only. Do not assign PP3/BP4 by local predictor voting or raw thresholds in this skill. Route missense prediction evidence to `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or a current VCEP.

**Synthesis boundary**: Summarize whether annotations are concordant, discordant, or incomplete. Keep ClinVar, HGMD, LOVD, lab reports, and paper labels as `source_assertion` leads until primary evidence is retrieved and routed. Final ACMG evidence strength must come from `tooluniverse-acmg-variant-classification`.

---

## KEY PRINCIPLES

1. **ProtVar-first** — ProtVar provides the richest protein-level context; always start here
2. **Notation flexibility** — Accept HGVS (c./p.), genomic (chr:pos:ref:alt), rsID, or gene+AA change
3. **Population frequency mandatory** — Always report gnomAD AF and note ancestry-specific values
4. **Structural context required for missense** — Domain, active site, conservation
5. **Report-first approach** — Create report file FIRST, update progressively
6. **Route-aware reporting mandatory** — report candidate ACMG routes, not evidence strengths

---

## Retrieval Confidence

- **High**: direct database record or curated source retrieved with stable identifier, version, and no conflict.
- **Moderate**: multiple retrieved sources agree, but one or more details need ACMG overlay review.
- **Low**: prediction-only, broad domain annotation, single-source assertion, or incomplete mapping.
- **Lead only**: ClinVar/HGMD/LOVD/lab/paper label without primary-evidence extraction.

Do not translate retrieval confidence into ACMG evidence strength.

---

## Workflow Overview

```
Variant Input (HGVS / genomic / rsID / gene+protein_change)
|
+-- PHASE 0: Variant Notation Normalization
|   Resolve to canonical HGVS and UniProt position; confirm gene/transcript
|
+-- PHASE 1: ProtVar Protein-Level Annotation
|   map_variant -> structural coordinates, residue info, domain, active site
|   get_function -> conservation, functional impact prediction
|   get_population -> minor allele frequencies per ancestry
|
+-- PHASE 2: Population Frequency (gnomAD)
|   gnomad_get_variant -> AF global + ancestry-specific; homozygote count
|
+-- PHASE 3: Deleteriousness Scores (CADD)
|   CADD_get_variant_score -> PHRED score; raw C-score
|
+-- PHASE 3b: Multi-Source Annotation (OpenCRAVAT)
|   OpenCRAVAT_annotate_variant -> 182+ annotators in one call
|   (ClinVar, gnomAD, SIFT, PolyPhen-2, REVEL, AlphaMissense, SpliceAI, etc.)
|
+-- PHASE 4: Clinical Classification (ClinVar)
|   ClinVar_search_variants -> pathogenicity, review status, submitter count
|   ClinVar_get_variant_details -> full submission breakdown
|
+-- PHASE 5: Gene-Disease Validity (ClinGen)
|   ClinGen_search_gene_validity -> evidence classification for gene-disease pair
|
+-- SYNTHESIS: Integrated Annotation Report
    Structural context + population + deleteriousness + clinical + gene-disease
```

---

## Phase 0: Variant Notation Normalization

Accepted input forms: HGVS coding (`NM_000546.6:c.524G>A`), HGVS protein (`NP_000537.3:p.Arg175His`), gene + protein change (`TP53 R175H`), genomic (`chr17:7674220:G:A` hg38), or rsID. Expand shorthand to full three-letter notation for ProtVar (e.g., "TP53 R175H" → "TP53 Arg175His").

---

## Phase 1: ProtVar Protein-Level Annotation

`ProtVar_map_variant` takes `hgvs`, `genomic` (chr:pos:ref:alt), or `protein_variant` (GENE pAA#AA) — at least one is required. Extract `accession` (UniProt ID) and `position` from the result.

`ProtVar_get_function(accession, position)` returns conservation scores, domain membership, PTM sites, and functional impact annotations.

`ProtVar_get_population(accession, position)` returns gnomAD allele frequencies per ancestry from ProtVar's aggregation.

**Key fields to reason over**: `active_site` / `binding_site` flags are high-priority signals; `conservation_score` quantifies evolutionary constraint at this position; `domain` membership places the variant in biological context; `secondary_structure` (loop variants are typically less constrained than helix/sheet).

---

## Phase 2: Population Frequency (gnomAD)

`gnomad_get_variant` takes `variant_id` in the format `chrom-pos-ref-alt` (hg38, no "chr" prefix). Always report the global AF, the maximum population-specific AF, and the homozygote count. Use `gnomad_search_variants` as fallback when the exact variant ID is not known.

Absence from gnomAD is noteworthy but does not independently establish pathogenicity.

---

## Phase 3: Deleteriousness Scores (CADD)

`CADD_get_variant_score` takes `chrom` (without "chr" prefix), `pos`, `ref`, `alt`, `genome` (default "GRCh38"). CADD PHRED ≥ 30 is top 0.1% most deleterious; ≥ 20 is top 1-10%. Use `OpenCRAVAT_annotate_variant` with `annotators="cadd_exome"` as fallback if CADD is unavailable.

---

## Phase 3b: Multi-Source Annotation (OpenCRAVAT)

`OpenCRAVAT_annotate_variant` takes `chrom`, `pos` (1-based GRCh38), `ref_base`, `alt_base`, and an optional comma-separated `annotators` string. The `chrom` parameter auto-adds the "chr" prefix if missing.

For missense variants, use annotators `"clinvar,gnomad3,sift,polyphen2,revel,alphamissense,cadd_exome"`. For splice-region variants, add `"spliceai,dbscsnv"`. For non-coding variants, add `"gerp,phastcons,dann"`.

**When scores disagree**: document the concordance pattern and route the prediction context to `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or a current VCEP. Do not resolve PP3/BP4 locally.

---

## Phase 4: Clinical Classification (ClinVar)

`ClinVar_search_variants(query="GENE protein_change")` returns pathogenicity classifications and review status. `ClinVar_get_variant_details(variant_id)` provides the full submission breakdown.

ClinVar review status (star ratings): 4 stars = practice guideline; 3 = expert panel reviewed; 2 = multiple submitters without conflict; 1 = single submitter; 0 = conflicting or not reviewed. Treat ClinVar classifications as source assertions. Expert-panel or practice-guideline labels are high-value leads, but they do not by themselves become ACMG counted evidence unless primary evidence is routed or a VCEP specification explicitly applies.

If ClinVar is unavailable, use `OpenCRAVAT_annotate_variant` with `annotators="clinvar"` as a fallback.

---

## Phase 5: Gene-Disease Validity (ClinGen)

`ClinGen_search_gene_validity(gene_symbol, disease_label)` returns curated gene-disease evidence classifications. ClinGen classifications from strongest to weakest: Definitive → Strong → Moderate → Limited → Disputed → Refuted.

**Critical reasoning step**: If the gene-disease relationship is Disputed or Refuted, any pathogenic ClinVar variant in this gene must be interpreted with extreme caution — the clinical relevance is uncertain independent of variant-level evidence. Always report ClinGen classification before interpreting variant pathogenicity.

---

## Synthesis: Integrated Annotation Report

```
# Variant Functional Annotation: [GENE] [VARIANT]
**Generated**: YYYY-MM-DD
**Input**: [original user input]
**Canonical notation**: [HGVS c. and p.]

## Executive Summary
(2-3 sentences: structural context, population frequency, and candidate ACMG routes)

## 1. Variant Identity
(Canonical HGVS, gene, transcript, consequence type, amino acid change)

## 2. Protein Structural Context
(From ProtVar: domain, secondary structure, active/binding site, 3D coordinates)

## 3. Functional Annotations
(Conservation, predicted impact, PTM proximity, domain function)

## 4. Population Frequency
(gnomAD global AF, max population AF, homozygote count)

## 5. Prediction Context
(CADD PHRED, REVEL, AlphaMissense — note concordance or discordance)

## 6. Source Assertions
(ClinVar significance, review stars, submitter count)

## 7. Gene-Disease Validity
(ClinGen classification for relevant disease)

## 8. Candidate ACMG Routes
(Route population, prediction, protein-region, source assertion, or functional-study leads to the ACMG overlay workflow)

## Data Gaps
(Any phase with no data; confidence caveats)
```

---

## Fallback Chains

- `ProtVar_map_variant` fails → try with genomic notation or `protein_variant` format
- `gnomad_get_variant` fails → use `gnomad_search_variants` by gene, or OpenCRAVAT `gnomad3` annotator
- `CADD_get_variant_score` unavailable → use OpenCRAVAT `cadd_exome` annotator
- `ClinVar_search_variants` returns empty → use OpenCRAVAT `clinvar` annotator
- `ClinGen_search_gene_validity` returns no data → note gene-disease relationship not curated by ClinGen

---

## Limitations

- **ProtVar**: Covers UniProt canonical isoforms only; alternative isoforms not mapped
- **gnomAD**: Based on gnomAD v4 (exomes + genomes); mitochondrial variants have separate AF
- **CADD**: Computational prediction only [T3]; does not replace experimental evidence
- **ClinVar**: Reflects submitter interpretations; star rating reflects concordance not accuracy
- **ProtVar structural coordinates**: Derived from AlphaFold2 where no experimental structure exists
