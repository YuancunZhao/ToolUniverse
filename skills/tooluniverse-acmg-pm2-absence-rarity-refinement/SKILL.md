---
name: tooluniverse-acmg-pm2-absence-rarity-refinement
description: Refine ACMG/AMP PM2 absence/rarity evidence using ClinGen SVI PM2 Recommendation Version 1.0. Use with ToolUniverse ACMG variant classification when population absence, extreme rarity, database coverage, ancestry-specific allele frequency, or PVS1 plus PM2_Supporting combination affects classification.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG PM2 Absence/Rarity Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: PM2 evidence for absence or extreme rarity in population databases. It follows the ClinGen Sequence Variant Interpretation recommendation for PM2, version 1.0, approved September 4, 2020.

The SVI recommendation reduces PM2 from Moderate strength to Supporting strength (`PM2_Supporting`). Rarity is common in large reference datasets and should not be treated as moderate pathogenic evidence unless a current VCEP rule explicitly specifies otherwise.

Use ToolUniverse tools to retrieve population frequency, ancestry-specific allele counts, homozygote/hemizygote observations, and coverage context. Then apply this refinement in the ACMG evidence table.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PM2-specific logic.

---

## When to Use This Skill

Use this skill when:

- The variant is absent from, or extremely rare in, population databases.
- The main ACMG workflow is considering PM2, BA1, BS1, BS2, or PM3.
- A PVS1-qualifying variant needs the SVI `PVS1 + PM2_Supporting => Likely Pathogenic` combination rule.
- The case needs ancestry-specific frequency review rather than global AF only.
- The variant is not found in gnomAD and you need to decide whether this is true absence or a coverage/representation gap.
- A recessive PM3 assessment requires checking PM2-level rarity for the assessed variant and the other allele.

Do not use this skill to refine unrelated population criteria beyond their boundary with PM2. BA1, BS1, and BS2 still require their own disease-specific thresholds and clinical context. Use `tooluniverse-acmg-ba1-exception-list-refinement` before applying BA1 stand-alone benign evidence.

---

## Core Principle

Apply PM2 as `PM2_Supporting` when the variant is absent from population controls or present only at an extremely low frequency that remains compatible with the disease prevalence, penetrance, allelic heterogeneity, and inheritance model.

Do not apply PM2 when:

- The variant meets BA1, BS1, or BS2.
- The variant is absent only because the locus is poorly covered, hard to map, or unavailable in the queried dataset.
- Population data are missing or the variant could not be normalized to the same genomic allele.
- A VCEP defines a different population threshold and the variant fails that threshold.
- The available data are too ambiguous to distinguish true absence from ascertainment or database limitations.

---

## Evidence Retrieval Workflow

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant`, `Mutalyzer_normalize_variant`, or `ClinGenAR_lookup_allele`.
   - Record transcript, genomic coordinates, genome build, reference/alternate allele, rsID, and ClinGen Allele Registry CA ID if available.
   - Make sure all population queries refer to the same allele and genome build.

2. **Retrieve population frequencies**
   - Use `gnomad_search_variants` and `gnomad_get_variant` when a gnomAD variant ID or rsID is available.
   - Use `EnsemblVEP_annotate_hgvs` for colocated variants and gnomAD/1000 Genomes context.
   - Use `EnsemblVar_get_population_frequencies`, `dbsnp_get_frequencies`, `OpenTargets_get_variant_info`, and `MyVariant_query_variants` as complementary or fallback sources.
   - For structural variants, use `gnomad_get_sv_detail`, `gnomad_get_sv_by_gene`, or `gnomad_get_sv_by_region` and defer to SV-specific interpretation when needed.

3. **Use ancestry-specific data**
   - Record global AF and the maximum ancestry/subpopulation AF.
   - Record allele count, allele number, homozygote count, and hemizygote count when available.
   - Do not let a low global AF hide a high ancestry-specific AF.

4. **Check database adequacy**
   - Confirm that the variant's genomic region is represented well enough in the queried database.
   - Treat no returned record as "not observed in this source" only after coordinate, allele, build, and representation have been checked.
   - If coverage or representation is unclear, report `status: not_assessed` with reason `PM2 coverage or representation unclear` rather than applying PM2.

5. **Apply disease-specific context**
   - Check disease prevalence, penetrance, inheritance model, allelic heterogeneity, and VCEP thresholds when available.
   - For dominant fully penetrant rare disorders, even very low AF may be too high.
   - For recessive disorders, carrier frequency can be higher, but the variant should still be rare enough for the disease model.

6. **Resolve conflict with benign frequency criteria**
   - If BA1 applies after BA1 exception-list review, classification should follow BA1 and PM2 is not applied.
   - If BS1 applies, PM2 is not applied.
   - If BS2 applies because the variant is observed in healthy individuals incompatible with disease penetrance/inheritance, PM2 is not applied.
   - If population data are compatible with rarity but not absence, apply only `PM2_Supporting` unless a VCEP says otherwise.

---

## PM2 Strength

| Population observation | Default evidence |
|------------------------|------------------|
| Absent from adequately covered and ancestry-relevant population datasets | `PM2_Supporting` |
| Present at extremely low frequency compatible with disease model and VCEP threshold | `PM2_Supporting` |
| Present above disease-specific BA1/BS1 threshold | No PM2; consider BA1 after exception-list review or BS1 |
| Present in healthy individuals incompatible with disease model | No PM2; consider BS2 |
| No reliable population data or poor coverage | `status: not_assessed`; no PM2 |

Do not apply PM2 at Moderate strength under the generic ACMG framework. Use Moderate or other non-supporting PM2 strength only when a current VCEP specification explicitly defines it.

---

## SVI Combination Rule

Because PM2 is reduced to Supporting, the SVI recommendation adds a combination not listed in the original 2015 ACMG/AMP combining rules:

| Evidence combination | Classification impact |
|----------------------|-----------------------|
| `PVS1 + PM2_Supporting` | Meets Likely Pathogenic under the SVI PM2 recommendation, assuming no conflicting benign evidence and PVS1 is valid at Very Strong strength. |

Use this combination only when:

- PVS1 is valid and not downgraded below Very Strong.
- PM2_Supporting is based on reliable absence/rarity data.
- No BA1, BS1, BS2, or strong contradictory evidence is present.
- Current VCEP rules do not specify a different combination framework.

If PVS1 is downgraded to `PVS1_Strong`, `PVS1_Moderate`, or `PVS1_Supporting`, use the standard or VCEP-specified combining rules rather than assuming this special combination.

---

## PM2 and PM3

For recessive PM3 assessment, PM2-level rarity is usually required for both:

- The variant being interpreted.
- The other variant observed in trans or phase unknown.

Use `tooluniverse-acmg-pm3-in-trans-refinement` for PM3 scoring. This PM2 overlay determines whether each variant is rare enough to be eligible for PM3 consideration. Do not use the other allele's rarity as independent pathogenic evidence for the assessed variant outside PM3.

---

## VCEP and Disease-Specific Rules

Current VCEP specifications supersede this generic SVI overlay. Follow VCEP rules when they define:

- Disease-specific BA1, BS1, or PM2 frequency thresholds.
- Whether PM2 may be used at Supporting only or another strength.
- Minimum allele number or coverage requirements.
- Treatment of founder variants, reduced penetrance, late-onset disease, or ancestry-specific enrichment.
- How PM2 combines with PVS1, PM3, PP3, PS3, or other evidence codes.

Always cite the VCEP if it changes the default SVI PM2 assignment.

---

## Output Format

Report PM2 refinement transparently:

```markdown
PM2 absence/rarity refinement:
- Variant: [HGVS/genomic allele], build [GRCh37/GRCh38], normalized ID [rsID/CA ID/gnomAD ID]
- Population sources checked: [gnomAD / Ensembl / dbSNP / OpenTargets / MyVariant / other]
- Global AF: [value or absent], maximum ancestry AF: [value and ancestry]
- Allele count/number: [AC/AN], homozygotes/hemizygotes: [counts]
- Coverage/representation: [adequate / uncertain / poor / not checked]
- Disease model: [dominant/recessive/X-linked], prevalence/penetrance context: [summary]
- Benign frequency conflict: [none / BA1 / BS1 / BS2]
- Applied evidence: [PM2_Supporting / No PM2 / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [population frequency / coverage / none]
- Combination note: [e.g., PVS1 + PM2_Supporting supports Likely Pathogenic under ClinGen SVI PM2 v1.0]
```

Example evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PM2 | Supporting | Variant absent from adequately covered gnomAD populations and no ancestry-specific frequency conflict was found; PM2 applied at Supporting strength per ClinGen SVI PM2 v1.0. | ClinGen SVI PM2 v1.0; gnomAD [version/source] |
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize HGVS, transcript, and genomic coordinates. |
| `Mutalyzer_normalize_variant` | Alternative HGVS normalization and allele representation. |
| `ClinGenAR_lookup_allele` | Resolve ClinGen Allele Registry CA ID and cross-references. |
| `gnomad_search_variants` / `gnomad_get_variant` | Primary gnomAD variant frequency, AC/AN, ancestry-specific AF, homozygotes. |
| `EnsemblVEP_annotate_hgvs` | Consequence and colocated population annotations. |
| `EnsemblVar_get_population_frequencies` | Population frequencies for rsID-resolved variants. |
| `dbsnp_get_frequencies` | dbSNP population frequency fallback. |
| `OpenTargets_get_variant_info` | Variant coordinates, rsID, consequence, and population frequency context. |
| `MyVariant_query_variants` | Aggregated ClinVar, gnomAD, dbNSFP, and annotation fallback. |
| `gnomad_get_sv_detail` / `gnomad_get_sv_by_gene` / `gnomad_get_sv_by_region` | Structural-variant frequency and homozygote context. |
| `ClinGen_search_gene_validity` / `GenCC_search_gene` | Gene-disease validity, inheritance, and disease-model context. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Disease prevalence, penetrance, founder effect, or VCEP/publication context when frequency thresholds need support. |

---

## Limitations

- This skill is a rule-refinement layer, not a deterministic population-frequency calculator.
- PM2 requires disease-specific interpretation; no universal AF cutoff is safe across all disorders.
- Absence from one database is not proof of absence from all relevant populations.
- Underrepresented ancestries, low coverage, paralogous regions, complex alleles, and genome-build mismatches can make PM2 unreliable.
- Newer VCEP or ClinGen specifications should supersede this generic PM2 overlay when available.

---

## Primary References

- ClinGen Sequence Variant Interpretation Working Group. SVI Recommendation for Absence/Rarity (PM2) - Version 1.0. Approved September 4, 2020.
- Tavtigian SV, Greenblatt MS, Harrison SM, et al. Modeling the ACMG/AMP variant classification guidelines as a Bayesian classification framework. Genet Med. 2018;20(9):1054-1060. PMID: 29300386. DOI: 10.1038/gim.2017.210.
- Lek M, Karczewski KJ, Minikel EV, et al. Analysis of protein-coding genetic variation in 60,706 humans. Nature. 2016;536(7616):285-291. PMID: 27535533. DOI: 10.1038/nature19057.
