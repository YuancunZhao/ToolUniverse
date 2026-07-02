---
name: tooluniverse-acmg-pm3-in-trans-refinement
description: Refine ACMG/AMP PM3 evidence strength for recessive disorders using ClinGen SVI Recommendation for in trans Criterion PM3 Version 1.0. Use with ToolUniverse ACMG variant classification when compound heterozygous, in trans, phase-unknown, one-parent-tested, homozygous, or biallelic proband evidence affects PM3 scoring.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG PM3 In-Trans Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: PM3 evidence in recessive disorders. It follows the ClinGen Sequence Variant Interpretation recommendation for the in trans criterion, PM3, version 1.0, approved May 2, 2019.

PM3 is clinical/genotype evidence and should not be applied automatically without proband-level context. Use ToolUniverse tools to validate variants, check allele frequencies, retrieve prior classifications, and search literature, then apply the point-based PM3 framework when the user or source provides biallelic genotype and phase information.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PM3 point model.

---

## When to Use This Skill

Use this skill when all of the following are relevant:

- The disease is autosomal recessive or otherwise recessive-compatible.
- The patient/proband is affected.
- The variant being interpreted is observed with another variant on the other allele, or appears as a rare homozygous occurrence.
- Phase is confirmed in trans, presumed in trans, or unknown.
- The other variant has a pathogenicity classification that can be evaluated independently.

Do not use this skill for:

- Dominant disorders.
- Dominant-negative or antimorphic disease mechanisms, unless a separate recessive disease context is being evaluated.
- Unaffected individuals.
- Carrier screening without affected-proband evidence.
- A second variant that is too common for the disorder.
- Cases where the other variant's pathogenicity depends circularly on the variant being interpreted.

---

## Core Principle

For recessive disorders, PM3 applies when the variant being interpreted is detected in trans with a pathogenic or likely pathogenic variant in an affected patient. The SVI framework assigns points per proband based on:

1. Phase: confirmed in trans versus phase unknown.
2. Classification of the other allele: P/LP versus VUS.
3. Homozygous occurrence.
4. Rarity of both variants.

Sum points across eligible independent probands, then map total points to PM3 strength.

---

## Evidence Retrieval Workflow

1. **Normalize both variants**
   - Use `VariantValidator_validate_variant` or `Mutalyzer_normalize_variant` for the variant being interpreted and the other allele.
   - Use `EnsemblVEP_annotate_hgvs` to confirm transcript consequence.
   - Record HGVS, transcript, genomic coordinates, zygosity, and the affected individual's phenotype.

2. **Confirm recessive gene-disease context**
   - Use `ClinGen_search_gene_validity`, `ClinGen_get_gene_validity`, `GenCC_search_gene`, OMIM/Orphanet-derived evidence, and disease literature.
   - PM3 should only be applied in a recessive disorder context.
   - If the same gene also has a dominant-negative or mixed-mechanism disease, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` to keep the recessive PM3 disease context separate from the dominant disease context.

3. **Check allele frequencies for both variants**
   - Check the variant being interpreted and the other allele with gnomAD/MyVariant/Ensembl/dbSNP/Open Targets frequency tools as available.
   - Usually both variants must satisfy PM2-level rarity for the disease context.
   - Do not apply PM3 if either variant is too common for the disorder unless a current VCEP rule explicitly permits a different threshold.

4. **Determine phase status**
   - Confirmed in trans: the source explicitly states "compound heterozygous" or "in trans", or family testing confirms each variant is inherited from a different parent.
   - Reads-based confirmation counts when the read evidence demonstrates compound heterozygosity or trans configuration for the two variants.
   - One-parent-tested/presumed in trans: if only one parent is tested and carries one of the variants, SVI allows the pair to be counted as in trans. Report this as presumed or one-parent-supported trans evidence.
   - Phase unknown: the report only lists "allele 1" and "allele 2", biallelic variants, or two variants in the same proband without family validation, read-based phase, or explicit compound-heterozygous/in-trans wording.

5. **Classify the other allele independently**
   - Determine whether the other allele is Pathogenic, Likely Pathogenic, VUS, or not usable.
   - Use ClinVar/ClinGen expert classifications, curated literature, or independent ACMG evidence.
   - Avoid circularity: the other variant's P/LP classification must not rely on PM3 evidence from the variant currently being interpreted. If variant A relies on variant B for PM3 to become LP/P, then variant A cannot be used as the PM3 basis for variant B.

6. **Score each eligible proband**
   - Apply the SVI point table below.
   - Count independent probands. Related individuals may not represent independent observations unless the curation source or VCEP allows it.

---

## Literature-Assisted Workflow

When PM3 evidence comes from papers, use `tooluniverse-literature-deep-research` or an equivalent ToolUniverse literature-reading skill first, then pass structured proband evidence into this PM3 refinement. The literature step should extract facts; this PM3 skill should assign points.

Recommended sequence:

1. Invoke `tooluniverse-literature-deep-research` for the gene, disease, assessed variant, and PM3 keywords such as "compound heterozygous", "in trans", "biallelic", "phase", "parental testing", and "reads".
2. If phase, parental origin, Sanger confirmation, or affected status is shown in a pedigree or figure, use `tooluniverse-literature-figure-evidence-extraction` to convert the visual evidence into structured proband and phase fields before PM3 scoring.
3. Use `PubMed_search_articles`, `EuropePMC_search_articles`, and full-text retrieval tools as direct fallback or supplemental tools when the literature skill needs targeted retrieval.
4. Extract proband-level evidence into the schema below.
5. Normalize every variant and verify frequencies/classifications with ToolUniverse tools.
6. Resolve phase status and circularity.
7. Score each eligible proband with the PM3 point table.
8. Sum independent proband points and assign PM3 strength.

Minimum proband evidence schema:

| Field | Required content |
|-------|------------------|
| `source` | PMID, DOI, ClinVar/ClinGen record, or report identifier. |
| `proband_id` | Proband label used in the source; use a stable local label if unnamed. |
| `affected_status` | Affected / unaffected / unclear. |
| `gene_disease_context` | Gene, disease, inheritance model, and source. |
| `assessed_variant` | HGVS/genomic/protein notation for the variant being interpreted. |
| `other_allele_variant` | HGVS/genomic/protein notation for the other allele. |
| `assessed_variant_frequency` | gnomAD/other AF and whether PM2-level rarity is met. |
| `other_allele_frequency` | gnomAD/other AF and whether PM2-level rarity is met. |
| `phase_evidence` | Exact text or evidence supporting compound heterozygous, in trans, one-parent-supported trans, reads-supported trans, phase unknown, or homozygous. |
| `other_allele_classification` | P / LP / VUS / unknown, with classification source. |
| `classification_independent` | Whether the other allele classification is independent of the assessed variant's PM3 evidence. |
| `duplicate_or_related_case` | Whether this proband duplicates another report or is a related non-independent case. |

If the literature step cannot fill these fields, return `No PM3` or `status: not_assessed` with reason `PM3 proband/phase fields incomplete` rather than guessing.

Literature extraction should preserve exact source wording for phase calls. For example, keep the sentence or table note containing "compound heterozygous", "in trans", parent genotypes, read-backed phasing, or allele 1/allele 2 wording so the PM3 scoring step can audit the phase category.

---

## PM3 Point Table

Award points per eligible affected proband:

| Other allele / zygosity | Confirmed or presumed in trans | Phase unknown |
|-------------------------|--------------------------------|---------------|
| Other variant Pathogenic | 1.0 | 0.5 |
| Other variant Likely Pathogenic | 1.0 | 0.25 |
| Homozygous occurrence | 0.5, maximum total 1.0 | N/A |
| Other variant VUS and rare | 0.25, maximum total 0.5 | 0.0 |

All variants should be sufficiently rare for the disease context, usually meeting PM2 specifications.

---

## PM3 Strength Mapping

After summing eligible proband points:

| Total points | Evidence strength |
|--------------|-------------------|
| 0.5 | PM3_Supporting |
| 1.0 | PM3 |
| 2.0 | PM3_Strong |
| 4.0 | PM3_VeryStrong |

Use the highest threshold met. For example, 2.0 total points supports `PM3_Strong`; 1.5 total points supports `PM3` unless a current VCEP specifies a different mapping.

---

## Circularity and Independence Rules

- The pathogenicity classification of the other allele must be established without using PM3 evidence from the variant currently being interpreted.
- If both variants in a compound heterozygous pair are VUS or depend on each other to reach LP/P, do not use either as P/LP support for the other.
- If the other allele is rare but only a VUS, score it using the VUS row, not the P/LP row.
- Do not count the same proband twice for the same assessed variant.
- Do not combine duplicated reports of the same proband from multiple papers.
- If related affected individuals share the same genotype, count conservatively unless independent segregation/proband rules are supplied by a VCEP.

---

## VCEP and Disease-Specific Rules

Current VCEP specifications supersede this generic SVI overlay. Follow VCEP rules when they define:

- Disease-specific PM2 frequency thresholds.
- Which variants count as P/LP for PM3.
- Whether phase-unknown observations are allowed.
- Whether homozygous occurrences can score above the SVI default cap.
- How related individuals or founder alleles should be counted.
- Different point thresholds for PM3 strength.

Always cite the VCEP if it changes the default SVI point assignment.

---

## Output Format

Report PM3 scoring transparently:

```markdown
PM3 refinement:
- Disease model: [recessive gene-disease context]
- Proband status: affected / not affected / unclear
- Assessed variant: [HGVS], frequency [source/result], PM2 rarity [met/not met]
- Other allele: [HGVS], classification [P/LP/VUS], classification source, frequency [source/result], PM2 rarity [met/not met]
- Phase: [confirmed in trans / presumed in trans from one-parent testing / reads-supported trans / phase unknown / homozygous]
- Circularity check: [other allele classification independent of assessed variant / not independent]
- Points: [per-proband points]
- Total PM3 points: [sum]
- Applied evidence: [PM3_Supporting / PM3 / PM3_Strong / PM3_VeryStrong / No PM3]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [proband IDs / phase evidence / other-allele classification / none]
```

Example evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PM3 | Strong | Two independent affected probands: assessed variant observed in trans with independently classified P/LP variants; total PM3 points = 2.0. | ClinGen SVI PM3 v1.0; [primary source] |
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize both variants and transcript consequences. |
| `Mutalyzer_normalize_variant` | Alternative HGVS normalization and protein consequence. |
| `EnsemblVEP_annotate_hgvs` | Consequence and transcript annotation. |
| `MyVariant_query_variants` | Aggregated ClinVar, gnomAD, and dbNSFP-style fields. |
| `gnomad_get_region` / gnomAD variant tools | Population frequency and homozygote context. |
| `EnsemblVar_get_population_frequencies` | Population frequencies for rsID-resolved variants. |
| `dbsnp_get_frequencies` | dbSNP population frequencies when rsID is available. |
| `OpenTargets_get_variant_info` | Variant frequency and coordinate context. |
| `ClinGen_get_variant_classifications` | Expert-curated variant classifications when available. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Recessive gene-disease validity and inheritance context. |
| `GenCC_search_gene` | Cross-check gene-disease validity and inheritance. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Literature with compound heterozygous, in trans, phase, or family validation evidence. |
| `GeneBe_classify_variant` / `InterVar_classify_variant` | External second-opinion ACMG classifications; do not use as opaque proof of independent P/LP without reviewing evidence when PM3 circularity is possible. |

---

## Limitations

- This skill is a rule-refinement layer, not a deterministic phase caller.
- PM3 requires proband-level genotype and phenotype context that many databases do not expose.
- Read-based phasing must be source-supported; do not infer trans configuration from short-read co-occurrence without adequate evidence.
- Frequency thresholds are disease-specific; PM2-level rarity is the default requirement but VCEP thresholds should supersede it.
- The SVI document is a versioned recommendation; use newer ClinGen/VCEP guidance when available.

---

## Primary Reference

- ClinGen Sequence Variant Interpretation Working Group. SVI Recommendation for in trans Criterion (PM3) - Version 1.0. Approved May 2, 2019.
