---
name: tooluniverse-acmg-benign-context-refinement
description: Refine ACMG/AMP benign-context evidence BA1, BS1, BS2, BP2, and BP5 using ClinGen/SVI BA1 exception-list routing, ACMG/AMP baseline criteria, VCEP-specific thresholds, and explicitly labeled practice/local refinements for disease-specific frequency, healthy-observation, alternate-diagnosis, cis/trans, penetrance, and phenotype context.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG Benign-Context Refinement

This skill extends `tooluniverse-acmg-variant-classification` for benign evidence that depends on disease context, phenotype context, or alternate molecular explanations:

- `BA1`: allele frequency is too high for disease.
- `BS1`: allele frequency is greater than expected for disease.
- `BS2`: variant observed in healthy individuals incompatible with disease penetrance/onset.
- `BP2`: observed in trans with a pathogenic variant for a fully penetrant dominant disorder, or in cis with a pathogenic variant in any inheritance pattern.
- `BP5`: variant found in a case with an alternate molecular basis for disease.

This overlay does not change the PM2 overlay. Population rarity/absence still follows `tooluniverse-acmg-pm2-absence-rarity-refinement`. Before applying BA1 stand-alone benign evidence, use `tooluniverse-acmg-ba1-exception-list-refinement`.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions. In this overlay, BA1 exception-list review is a prerequisite for BA1 only; BS1/BS2/BP2/BP5 remain here.

BP1 cross-route stub: BP1 is a benign criterion, but this overlay does not assess it. If BP1 is proposed or the agent searches benign criteria for a missense variant in a gene where missense variation is not an established disease mechanism, route BP1 to `tooluniverse-acmg-pm1-regional-missense-constraint-refinement`. Keep BP1 out of this overlay's covered criteria unless a current in-scope VCEP explicitly moves it.

Guidance authority:

- BA1 exception-list and generic stand-alone BA1 review follow Ghosh et al. 2018 as `ClinGen/SVI primary`.
- BS1, BS2, BP2, and BP5 start from `ACMG/AMP baseline` unless a current VCEP supplies `VCEP-specific` thresholds or rules.
- ACGS 2024 operational details for BS1/BS2/BP2/BP5 are `practice/local refinement`, not generic ClinGen/SVI primary guidance.

---

## When to Use This Skill

Use this skill when:

- BA1 or BS1 may apply from population frequency.
- A variant has AF >0.05 and BA1 may be applied after exception-list review.
- BS2 may apply from healthy adult observations, homozygotes, hemizygotes, or curated unaffected carriers.
- BP2 may apply because another pathogenic variant explains a fully penetrant dominant disease or because the variant is in cis with a pathogenic variant.
- BP5 may apply because another molecular diagnosis explains the patient's phenotype.
- Disease prevalence, penetrance, age of onset, inheritance, ancestry, or phenotype affects benign evidence.

Do not apply benign-context evidence when the required context is missing. Separate disease-context-only inputs from patient-level phenotype inputs: BA1 and BS1 need disease prevalence, inheritance, penetrance, heterogeneity, ancestry, and frequency-threshold context, but not the current patient's phenotype. BS2, BP2, and BP5 may need patient or healthy-carrier clinical context depending on the evidence source.

---

## Evidence Retrieval Workflow

1. **Normalize the variant and disease context**
   - Use `VariantValidator_validate_variant`, `ClinGenAR_lookup_allele`, `EnsemblVEP_annotate_hgvs`, and `MyVariant_query_variants`.
   - Record disease, inheritance, penetrance, age of onset, disease prevalence, and relevant transcript.

2. **Retrieve population data**
   - Use `gnomad_search_variants`, `gnomad_get_variant`, `EnsemblVar_get_population_frequencies`, `dbsnp_get_frequencies`, and `MyVariant_query_variants`.
   - Record global AF, maximum ancestry AF, AC/AN, homozygote/hemizygote count, data quality flags, and coverage concerns.

3. **Assess disease-specific thresholds**
   - Before applying BA1, use `tooluniverse-acmg-ba1-exception-list-refinement` to check the Ghosh 2018 updated BA1 definition, 2,000 observed-allele requirement, general continental population status, exception list, founder-population caveats, and gene/variant-specific BA1 modifications.
   - Use VCEP thresholds when available.
   - Use disease prevalence, penetrance, allelic heterogeneity, genetic heterogeneity, and inheritance model to evaluate maximum credible frequency.
   - Use conservative assumptions when precise prevalence or penetrance data are unavailable.

4. **Assess phenotype and alternate diagnosis**
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when patient phenotype, healthy status, or alternate molecular diagnosis affects BS2, BP2, or BP5.
   - Do not request patient phenotype for BA1/BS1 frequency review unless a VCEP explicitly requires phenotype-specific threshold selection beyond disease context.
   - Use MedGen/HPO/MONDO/Monarch tools and literature only to contextualize supplied phenotype, not to invent patient phenotype.

5. **Assess phase and genotype context**
   - For BP2, document whether the variant is in cis or trans with another pathogenic variant and whether the inheritance model supports benign evidence.
   - For BP5, document whether the alternate P/LP variant or diagnosis explains all or most of the phenotype.

---

## BA1 and BS1

Apply BA1 only after `tooluniverse-acmg-ba1-exception-list-refinement` confirms that stand-alone BA1 is valid. Under Ghosh et al. 2018, generic BA1 requires AF >0.05 in a qualifying general continental population dataset with at least 2,000 observed alleles at the site, and no gene-specific or variant-specific BA1 modification.

Do not apply BA1 when the variant is on the ClinGen BA1 exception list, when high frequency is only supported by an inadequate/founder dataset, or when a VCEP/gene-specific rule supersedes the generic 0.05 threshold.

Apply BS1 when allele frequency is greater than expected for the disorder but does not meet BA1.

ACGS 2024 `practice/local refinement` points:

- For high-penetrance autosomal dominant disorders, `BS1_Strong` can be stand-alone evidence for likely benign when the disease-specific threshold is exceeded.
- Use maximum ancestry AF, not global AF alone.
- Use current gnomAD data and check quality flags, paralogous regions, low read depth, and poor genotyping regions.
- Do not apply PM2 if BA1 or BS1 applies.

---

## BS2

Apply BS2 only when healthy observations are incompatible with pathogenicity for the disease context.

ACGS 2024 `practice/local refinement` examples:

- For a highly penetrant dominant disease, BS2 can be supported by at least two heterozygous healthy appropriately phenotyped individuals.
- For severe pediatric-onset recessive disease, at least two healthy homozygotes or phenotype-incompatible homozygotes in population data may support BS2.
- For recessive disorders, at least two appropriately phenotyped healthy homozygotes can support BS2.
- For late-onset or reduced-penetrance disorders, require more healthy observations and more detailed phenotyping.

If unaffected status, age, penetrance, or clinical evaluation is unclear, mark BS2 as `status: not_assessed` and ask for those fields.

---

## BP2

Apply BP2 when:

- The patient has a pathogenic variant in a fully penetrant dominant gene/disorder that explains the clinical phenotype, and the variant under assessment is observed in trans.
- The variant under assessment is observed in cis with a pathogenic variant in any inheritance pattern and the cis context supports benign interpretation.

Do not apply BP2 when:

- Biallelic variants in the gene cause a different phenotype that has not been excluded.
- The patient is too young for the relevant biallelic phenotype to be penetrant.
- Phase is unknown.
- The alternate pathogenic variant does not explain the clinical presentation.

---

## BP5

Apply BP5 only when another molecular diagnosis explains the patient's disease.

ACGS 2024 `practice/local refinement` cautions:

- Do not apply BP5 if the alternate P/LP variant does not explain all or most clinical features.
- Do not apply BP5 when a blended phenotype is plausible.
- Use caution in genes where co-occurrence of pathogenic variants has little or no effect on phenotype, such as some BRCA1/BRCA2 contexts.
- If phenotype or alternate diagnosis details are missing, request them instead of applying BP5.

---

## Output Format

```markdown
Benign-context refinement:
- Variant: [HGVS/genomic allele]
- Disease context: [disease, inheritance, penetrance, age of onset]
- Population data: [global AF, max ancestry AF, AC/AN, homozygotes/hemizygotes, quality]
- Frequency threshold: [BA1/BS1 threshold source or not_assessed]
- Healthy-observation evidence: [individuals, age, phenotype, genotype]
- Phase/alternate diagnosis: [cis/trans, other P/LP variant, phenotype explanation]
- Applied evidence: [BA1 / BS1 / BS1_Strong / BS2 / BP2 / BP5 / No benign-context evidence / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Guidance authority: [ClinGen/SVI primary / ACMG/AMP baseline / VCEP-specific / practice/local refinement / source lead only]
- Consumed evidence: [population frequency / healthy observations / phase / alternate diagnosis / none]
- Missing information: [fields needed]
```

---

## Tool Parameter Reference

| Tool or skill | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Variant normalization. |
| `ClinGenAR_lookup_allele` | Allele normalization and external IDs. |
| `gnomad_search_variants` / `gnomad_get_variant` | Population AF, homozygotes, hemizygotes. |
| `EnsemblVar_get_population_frequencies` | Ensembl/gnomAD/1000G population fallback. |
| `MyVariant_query_variants` | Aggregated population and ClinVar context. |
| `ClinVar_search_variants` / `ClinVar_get_variant` | Existing classifications and alternate P/LP variants. |
| `MedGen_search_conditions`, HPO/MONDO/Monarch tools | Disease and phenotype context. |
| `tooluniverse-acmg-ba1-exception-list-refinement` | Ghosh 2018 BA1 stand-alone threshold, exception list, founder-population caveats, and gene/variant-specific BA1 modifications. |
| `tooluniverse-acmg-phenotype-dependent-evidence-refinement` | Patient phenotype, healthy status, and alternate-diagnosis checks. |
| `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` | Cross-route for BP1, because BP1 depends on missense disease mechanism and PP2/BP1/PM1 priority. |

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868.
- Ghosh R, Harrison SM, Rehm HL, Plon SE, Biesecker LG; ClinGen Sequence Variant Interpretation Working Group. Updated recommendation for the benign stand-alone ACMG/AMP criterion. Human Mutation. 2018;39(11):1525-1530. PMID:30311383. DOI:10.1002/humu.23642.
- ACGS Best Practice Guidelines for Variant Classification in Rare Disease 2024, v1.2, BA1/BS1/BS2/BP2/BP5 sections.
- Whiffin N, Minikel E, Walsh R, et al. Using high-resolution variant frequencies to empower clinical genome interpretation. Genet Med. 2017;19(10):1151-1158.
