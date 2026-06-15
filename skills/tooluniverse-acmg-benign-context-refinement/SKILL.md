---
name: tooluniverse-acmg-benign-context-refinement
description: Refine ACMG/AMP benign-context evidence BA1, BS1, BS2, BP2, and BP5 using ACGS 2024 practice guidance, disease-specific frequency thresholds, healthy-observation context, alternate molecular diagnosis, cis/trans context, penetrance, and phenotype requirements.
disable-model-invocation: true
---

# ACMG Benign-Context Refinement

This skill extends `tooluniverse-acmg-variant-classification` for benign evidence that depends on disease context, phenotype context, or alternate molecular explanations:

- `BA1`: allele frequency is too high for disease.
- `BS1`: allele frequency is greater than expected for disease.
- `BS2`: variant observed in healthy individuals incompatible with disease penetrance/onset.
- `BP2`: observed in trans with a pathogenic variant for a fully penetrant dominant disorder, or in cis with a pathogenic variant in any inheritance pattern.
- `BP5`: variant found in a case with an alternate molecular basis for disease.

This overlay does not change the PM2 overlay. Population rarity/absence still follows `tooluniverse-acmg-pm2-absence-rarity-refinement`.

---

## When to Use This Skill

Use this skill when:

- BA1 or BS1 may apply from population frequency.
- BS2 may apply from healthy adult observations, homozygotes, hemizygotes, or curated unaffected carriers.
- BP2 may apply because another pathogenic variant explains a fully penetrant dominant disease or because the variant is in cis with a pathogenic variant.
- BP5 may apply because another molecular diagnosis explains the patient's phenotype.
- Disease prevalence, penetrance, age of onset, inheritance, ancestry, or phenotype affects benign evidence.

Do not apply benign-context evidence when the required disease or phenotype context is missing.

---

## Evidence Retrieval Workflow

1. **Normalize the variant and disease context**
   - Use `VariantValidator_validate_variant`, `ClinGenAR_lookup_allele`, `EnsemblVEP_annotate_hgvs`, and `MyVariant_query_variants`.
   - Record disease, inheritance, penetrance, age of onset, disease prevalence, and relevant transcript.

2. **Retrieve population data**
   - Use `gnomad_search_variants`, `gnomad_get_variant`, `EnsemblVar_get_population_frequencies`, `dbsnp_get_frequencies`, and `MyVariant_query_variants`.
   - Record global AF, maximum ancestry AF, AC/AN, homozygote/hemizygote count, data quality flags, and coverage concerns.

3. **Assess disease-specific thresholds**
   - Use VCEP thresholds when available.
   - Use disease prevalence, penetrance, allelic heterogeneity, genetic heterogeneity, and inheritance model to evaluate maximum credible frequency.
   - Use conservative assumptions when precise prevalence or penetrance data are unavailable.

4. **Assess phenotype and alternate diagnosis**
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when phenotype, healthy status, or alternate molecular diagnosis affects BS2, BP2, or BP5.
   - Use MedGen/HPO/MONDO/Monarch tools and literature only to contextualize supplied phenotype, not to invent patient phenotype.

5. **Assess phase and genotype context**
   - For BP2, document whether the variant is in cis or trans with another pathogenic variant and whether the inheritance model supports benign evidence.
   - For BP5, document whether the alternate P/LP variant or diagnosis explains all or most of the phenotype.

---

## BA1 and BS1

Apply BA1 when allele frequency exceeds a stand-alone benign threshold for the disease context. The generic 5% threshold is usually too high for rare diseases, so use disease-specific/VCEP thresholds when available.

Apply BS1 when allele frequency is greater than expected for the disorder but does not meet BA1.

ACGS 2024 practice points:

- For high-penetrance autosomal dominant disorders, `BS1_Strong` can be stand-alone evidence for likely benign when the disease-specific threshold is exceeded.
- Use maximum ancestry AF, not global AF alone.
- Use current gnomAD data and check quality flags, paralogous regions, low read depth, and poor genotyping regions.
- Do not apply PM2 if BA1 or BS1 applies.

---

## BS2

Apply BS2 only when healthy observations are incompatible with pathogenicity for the disease context.

ACGS 2024 practice examples:

- For a highly penetrant dominant disease, BS2 can be supported by at least two heterozygous healthy appropriately phenotyped individuals.
- For severe pediatric-onset recessive disease, at least two healthy homozygotes or phenotype-incompatible homozygotes in population data may support BS2.
- For recessive disorders, at least two appropriately phenotyped healthy homozygotes can support BS2.
- For late-onset or reduced-penetrance disorders, require more healthy observations and more detailed phenotyping.

If unaffected status, age, penetrance, or clinical evaluation is unclear, mark BS2 as not assessable and ask for those fields.

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

ACGS 2024 cautions:

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
- Frequency threshold: [BA1/BS1 threshold source or not assessable]
- Healthy-observation evidence: [individuals, age, phenotype, genotype]
- Phase/alternate diagnosis: [cis/trans, other P/LP variant, phenotype explanation]
- Applied evidence: [BA1 / BS1 / BS1_Strong / BS2 / BP2 / BP5 / No benign-context evidence / Not Assessed]
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
| `tooluniverse-acmg-phenotype-dependent-evidence-refinement` | Patient phenotype, healthy status, and alternate-diagnosis checks. |

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868.
- ACGS Best Practice Guidelines for Variant Classification in Rare Disease 2024, v1.2, BA1/BS1/BS2/BP2/BP5 sections.
- Whiffin N, Minikel E, Walsh R, et al. Using high-resolution variant frequencies to empower clinical genome interpretation. Genet Med. 2017;19(10):1151-1158.
