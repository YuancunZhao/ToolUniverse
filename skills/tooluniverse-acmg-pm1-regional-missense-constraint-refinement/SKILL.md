---
name: tooluniverse-acmg-pm1-regional-missense-constraint-refinement
description: Refine ACMG/AMP PM1 evidence assignment for missense variants using regional missense mutational intolerance and missense-depleted region guidance from PMID 38645134. Use with ToolUniverse ACMG variant classification when a missense variant falls in a constrained protein region, hotspot, functional domain, or author-provided MDR/MPC regional constraint dataset.
disable-model-invocation: true
---

# ACMG PM1 Regional Missense Constraint Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: PM1 evidence for missense variants in constrained, hotspot, or functionally important protein regions.

It uses the regional missense mutational intolerance framework described in PMID:38645134 as a non-ClinGen regional evidence refinement overlay. The paper identifies missense-depleted regions (MDRs) by comparing observed rare missense variation against expected missense variation and may support PM1 when local policy, a VCEP, or a disease-specific rule accepts the dataset and threshold. Do not describe PMID:38645134 as a generic ClinGen/SVI PM1 recommendation.

This skill does not replace gene-specific VCEP rules and does not create a new ToolUniverse MCP tool. Use ToolUniverse tools to retrieve variant, protein, clinical, population, and domain evidence, then apply this refinement when PM1 is under-specified.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PM1-specific logic.

Guidance authority: baseline PM1 comes from `ACMG/AMP baseline`. Current VCEP hotspot/domain rules are `VCEP-specific`. PMID:38645134 MDR membership and ACGS regional resources are `practice/local refinement` unless adopted by a VCEP.

---

## When to Use This Skill

Use this skill when any of the following are present:

- A missense variant lies in a known disease hotspot, active site, binding site, catalytic residue, or critical protein domain.
- A variant lies in an author-provided missense-depleted region (MDR) or regional missense constraint interval.
- PM1 needs refinement beyond broad InterPro/Pfam domain membership.
- A protein region has pathogenic missense enrichment and low benign/population missense variation.
- The user provides a local MDR/MPC table, regional constraint file, or residue interval derived from PMID:38645134 or a later validated release.

Do not use this skill for:

- Loss-of-function variants. Use PVS1.
- Splice-impact evidence. Use PVS1/PP3/BP4 splicing workflows.
- Population absence alone. Use PM2.
- General computational deleteriousness alone. Use PP3.
- Somatic cancer hotspot interpretation unless the germline ACMG disease context is also appropriate.

---

## Core Principle

PM1 supports pathogenicity when a variant is located in a mutational hotspot or well-established functional domain without benign variation. The PMID:38645134 framework refines this by identifying regions depleted for rare missense variation in gnomAD relative to expectation. A missense variant in a strongly missense-depleted region can support PM1 when the gene-disease mechanism and variant class are appropriate.

Use regional missense constraint as **regional evidence**, not as a generic computational predictor:

- MDR membership may support PM1.
- MPC or other missense deleteriousness scores may support PP3 only if used as prediction evidence and not already counted as the regional PM1 basis.
- Do not apply both PM1 and PP3 from the same regional constraint feature unless the PP3 evidence comes from independent calibrated predictors.

---

## Evidence Retrieval Workflow

Use ToolUniverse retrieval tools before assigning PM1.

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant` or `Mutalyzer_normalize_variant` to confirm HGVS notation.
   - Use `EnsemblVEP_annotate_hgvs` to confirm the variant is missense and to identify transcript/protein consequence.
   - Map to UniProt coordinates with `ProtVar_map_variant` when protein-level tools are needed.

2. **Confirm disease mechanism and variant class**
   - Use `ClinGen_search_gene_validity`, `ClinGen_get_gene_validity`, GenCC, OMIM/Orphanet-derived evidence, and disease literature.
   - PM1 from regional missense constraint is most appropriate for diseases where pathogenic missense variation is an established mechanism.
   - If pathogenic missense variants may act through a dominant-negative or antimorphic mechanism, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` to confirm that the region, hotspot, domain, or interface is relevant to that mechanism.
   - Do not apply regional PM1 when LoF is the only established mechanism and missense pathogenicity is unsupported.

3. **Check population and clinical context**
   - Use `gnomad_get_gene_constraints`, `gnomad_get_region`, `MyVariant_query_variants`, `ProtVar_get_population`, and ClinVar tools.
   - Confirm that the queried region is not enriched with benign or high-frequency missense variants.
   - Confirm that ClinVar pathogenic variants, if used, are relevant to the same disease mechanism and not dominated by low-confidence assertions.
   - Treat ClinVar, HGMD, LOVD, and published ACMG labels as source leads, not as PM1 evidence by themselves. If they are used to support regional pathogenic enrichment, retrieve the primary evidence where feasible and avoid reusing the same assertions for PS1/PM5.

4. **Assess known functional/domain context**
   - Use `InterPro_get_protein_domains`, `UniProt_get_function_by_accession`, `EBIProteins_get_variation`, and structural tools such as AlphaFold/PDB when needed.
   - Broad domain membership alone is not sufficient for PM1 unless the domain or subregion is known to be critical and benign variation is low.
   - ACGS 2024 `practice/local refinement` regional/context sources include DECIPHER protein-view missense constraint tracks, constrained coding regions (CCR), MetaDome regional intolerance, paralogous residue evidence, curated active/binding/catalytic sites, and disease-specific hotspot/domain rules.

5. **Assess regional missense constraint**
   - Use the author-provided MDR/MPC regional constraint data when available.
   - Match the variant to the same transcript/protein coordinate system used by the MDR dataset.
   - Record region boundaries, observed/expected missense ratio, dataset version, and whether the region meets the calibrated threshold.
   - Do not infer MDR membership from gene-level missense constraint alone.
   - Prefer local or regional constraint over whole-gene intolerance. Whole-gene missense depletion can support PP2 context, but should not substitute for PM1 without residue-level or interval-level evidence.

---

## PM1 Assignment Rules

### Apply PM1

Apply `PM1` when all of the following are true:

- The variant is missense.
- The gene-disease relationship and disease mechanism support pathogenic missense variation.
- The variant lies in a well-defined constrained region, hotspot, or critical functional subregion.
- The region has low benign/population missense variation.
- The region evidence is independent of population rarity evidence used for PM2.

For the MDR framework from PMID:38645134:

- Use `PM1` at moderate strength when the variant lies in a validated missense-depleted region meeting the calibrated observed/expected missense threshold.
- Prefer the latest validated release of the MDR/MPC dataset. The bioRxiv API currently reports a 2026 version using 730,947 gnomAD v4.1.1 exomes and an abstract threshold of regions with less than 36% of expected missense variation.
- Older PubMed-linked abstract metadata may show the earlier 125,748-exome framing and a stricter less-than-20% threshold. If using the older release, record that version explicitly.

ACGS 2024 `practice/local refinement` additions:

- PM1 may be supported by one or more of these evidence types when they point to the same local region: enrichment of pathogenic missense variants with low benign variation, disease-relevant paralogous residue pathogenicity, an invariant or highly conserved residue in an established functional domain, and protein modelling showing deleterious alteration of a known functional region.
- `PM1_Strong` can be considered only for well-established critical residues or motif rules with guideline/VCEP-level support, such as cysteine disruption in FBN1 EGF-like calcium-binding domains, NOTCH3 EGF-repeat cysteine imbalance, glycine substitutions in collagen triple-helical domains, or Cys/His residues in C2H4 zinc-finger motifs when established for the disease.
- `PM1_Supporting` may be appropriate for functional non-coding loci or weak regional evidence when a disease-specific rule supports local functional importance but moderate evidence is not justified.
- Use DECIPHER regional constraint, CCR, MetaDome, paralog evidence, and structure/conservation only as PM1 context when the evidence is region-specific and independent of PP3 predictor scores.

### Reduce or Withhold PM1

Withhold or reduce PM1 when:

- The variant is outside the constrained subregion even if it is inside a broad domain.
- The region contains multiple benign or high-frequency missense variants.
- The disease mechanism is not missense-mediated.
- The region is not relevant to the asserted dominant-negative mechanism when the disease is dominant-negative or mixed-mechanism.
- The region is constrained only at the gene level, with no residue-level or interval-level evidence.
- The coordinate mapping between transcript, protein, and MDR interval is uncertain.
- The only evidence is a high MPC/AlphaMissense/REVEL score without regional membership or hotspot/domain evidence.
- The evidence is only whole-gene missense intolerance and the local region does not show constraint; in this situation PP2 may be considered instead of PM1 if other PP2 requirements are met.
- The same same-residue pathogenic comparison evidence is already being used for PM5 and no independent regional/domain evidence remains for PM1.
- The only support is that another publication, database, or expert panel already applied PM1, without reviewable hotspot, constrained-region, critical-residue, or low-benign-variation evidence.
- The evidence is only membership in a broad InterPro/Pfam/UniProt domain without a defined disease-relevant hotspot, critical residue, local constraint interval, pathogenic enrichment, or VCEP/gene-specific rule.

---

## Double-Counting Rules

- Do not count the same regional constraint feature as both PM1 and PP3.
- Do not use population absence or rarity from the same gnomAD data as the PM1 rationale; that belongs under PM2.
- Do not count ClinVar pathogenic clustering as PM1 if the same ClinVar assertions are already being used as PS1/PM5-style evidence without independence.
- If functional assays prove the same residue/domain impact, use PS3/BS3 for the assay and PM1 only for independent regional/domain location evidence.
- If a VCEP has a disease-specific PM1 hotspot/domain rule, use the VCEP rule first and cite the MDR evidence only as supporting context unless the VCEP allows it.

---

## PM1, PP2, and PP3 Evidence Selection

Use these priority rules after PM1 strength has been assigned and before combining ACMG evidence:

- **PM1 and PP2 both met**: retain `PM1` and do not also apply `PP2`, unless a current disease-specific VCEP rule explicitly permits both.
- **PM1_Supporting and PP2 both met**: retain `PP2` and do not also apply `PM1_Supporting`, unless a current disease-specific VCEP rule explicitly permits both.
- **VCEP override**: if a current gene/disease-specific VCEP specification gives a different PM1/PP2 rule, follow the VCEP rule and cite it.
- **PM1 and PP3 both used**: when PM1-region evidence and PP3 computational evidence are both retained for a missense variant, the combined regional/predictor evidence contribution must not exceed Strong. Do not stack PM1 plus PP3 into an effective Very Strong contribution.

Rationale: PM1 and PP2 can both describe missense intolerance. PM1 is local or regional; PP2 is gene-wide. When PM1 is moderate, it is the more specific evidence and should be retained over PP2. When PM1 is only supporting, PP2 is the stronger gene-level criterion and should be retained over PM1_Supporting. PP3 can remain when it is based on independent calibrated predictors, but it should not over-amplify the same missense-intolerance signal.

### BP1 Interaction

Use BP1 only when pathogenic missense variation is not an established mechanism for the disease context, such as a gene-disease pair where disease is caused by LoF/truncating variants and missense variation is tolerated or not disease-relevant.

Do not apply BP1 when the variant lies in a PM1-qualified hotspot, critical residue, or constrained subregion for the same disease mechanism. If the gene has both LoF-only and missense/dominant-negative disease contexts, resolve the disease context with `tooluniverse-acmg-dominant-negative-mechanism-refinement` before using PM1, PP2, or BP1.

---

## Output Format

Report the refined PM1 evidence as part of the ACMG evidence table:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PM1 | Moderate | Missense variant lies in [region/residues], a validated missense-depleted/critical region with [observed/expected missense ratio or dataset threshold], low benign variation, and disease-relevant missense mechanism. | PMID:38645134; [MDR dataset version]; [domain/hotspot source] |
```

If PM1 is withheld:

```markdown
PM1 not applied: variant is [inside broad domain/outside MDR/uncertain coordinate], and available evidence does not establish a disease-relevant constrained subregion without benign variation.
```

Always state whether MPC or other prediction scores were used separately under PP3 or excluded to avoid double counting.

Also include a routing-core summary:

```markdown
PM1 regional missense-constraint refinement:
- Applied evidence: [PM1 / PM1_Supporting / PP2 retained instead / No PM1]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Guidance authority: [ACMG/AMP baseline / VCEP-specific / practice/local refinement / source lead only]
- Consumed evidence: [regional constraint / hotspot / critical residue / none]
- Broad-domain check: [not used alone / supported by local evidence / insufficient]
- Double-counting restriction: [PM1 plus PP3 cap / PM1-PP2 selection / none]
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize HGVS and transcript/protein consequence. |
| `Mutalyzer_normalize_variant` | Alternative HGVS normalization and protein prediction. |
| `EnsemblVEP_annotate_hgvs` | Confirm missense consequence and transcript context. |
| `ProtVar_map_variant` | Map protein variant to UniProt/genomic context and retrieve predictions. |
| `ProtVar_get_population` | Inspect co-located protein variants and population/clinical annotations. |
| `gnomad_get_gene_constraints` | Gene-level constraint context; not sufficient alone for PM1. |
| `gnomad_get_region` | Regional population variation context. |
| `MyVariant_query_variants` | Aggregated variant annotations. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Gene-disease validity and mechanism context. |
| `InterPro_get_protein_domains` | Protein domain architecture. |
| `UniProt_get_function_by_accession` | Functional sites and curated protein features. |
| `EBIProteins_get_variation` | Known protein variants from ClinVar, gnomAD/ExAC, COSMIC, and UniProt. |
| `AlphaMissense_get_variant_score` | Prediction evidence for PP3; not PM1 by itself. |
| DECIPHER regional constraint, CCR, MetaDome resources when accessible | Regional constraint context; use only with coordinate/version documentation. |

---

## Limitations

- This skill is a rule-refinement layer, not a deterministic MDR lookup tool.
- The author-provided MDR/MPC interval dataset is required for reliable automated membership testing. Do not reconstruct MDRs from ad hoc local counts unless reproducing the published method.
- PMID:38645134 is indexed as a bioRxiv preprint. The bioRxiv API reports multiple versions; use and cite the specific version and dataset release.
- Full text and supplemental materials were not available through automated retrieval in this implementation pass because bioRxiv/PMC access returned challenge pages and Europe PMC fullTextXML returned 404.
- Current gene-specific VCEP specifications supersede this generic overlay.
- ACGS 2024 regional resources such as DECIPHER, CCR, MetaDome, and paralog evidence are `practice/local refinement`, require careful coordinate mapping, and should not be treated as deterministic without source/version documentation.

---

## Primary Reference

- Wang L, Chao KR, Panchal R, et al. The landscape of regional missense mutational intolerance quantified from 730,947 exomes. bioRxiv. DOI: 10.1101/2024.04.11.588920. PMID: 38645134.
- Ellard S, Baple EL, Berry I, et al. ACGS Best Practice Guidelines for Variant Classification 2024. Use only as `practice/local refinement` for DECIPHER/CCR/MetaDome/paralog regional context, critical-residue PM1 strengthening, and PM1/PP2/BP1 double-counting boundaries unless a VCEP adopts the rule.
