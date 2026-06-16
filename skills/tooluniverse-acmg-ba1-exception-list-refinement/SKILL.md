---
name: tooluniverse-acmg-ba1-exception-list-refinement
description: Refine ACMG/AMP BA1 stand-alone benign evidence using Ghosh et al. 2018 ClinGen SVI BA1 recommendation and the BA1 exception list. Use before applying BA1 when allele frequency exceeds 0.05, when a variant may be on the BA1 exception list, or when gene-specific BA1 thresholds, founder populations, penetrance, or population-dataset adequacy affect frequency-based benign classification.
disable-model-invocation: true
---

# ACMG BA1 Exception List Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule: `BA1`, the stand-alone benign criterion based on very high population allele frequency.

It follows Ghosh et al. 2018 / ClinGen SVI BA1 guidance, PMID:30311383, and the July 30, 2018 BA1 exception list supplied by the user. Use this overlay before assigning BA1 from any population frequency above 0.05.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this evidence-specific BA1 logic.

This skill is an overlay only. It does not create a new MCP tool and does not replace disease-specific VCEP specifications.

---

## When to Use This Skill

Use this skill when:

- a variant has allele frequency greater than 0.05 in any population dataset;
- the main ACMG workflow is considering BA1 as stand-alone benign evidence;
- a variant may be one of the ClinGen BA1 exception-list variants;
- a gene-specific or variant-specific BA1 modification exists or may exist;
- the high frequency is observed in a founder or bottlenecked population;
- the population source has unclear allele number, relatedness, ancestry structure, or coverage;
- BA1 conflicts with pathogenic evidence, ClinVar assertions, VCEP rules, or disease-specific penetrance.

Do not use BA1 as a generic "high frequency" code without checking this overlay. If BA1 does not apply but frequency is still too high for the disease, route forward to `tooluniverse-acmg-benign-context-refinement` for BS1 or related benign-context evidence. Do not route back into this BA1 overlay unless a new BA1-specific question arises.

---

## Core Principle

BA1 is a stand-alone benign rule only when the allele frequency threshold is met in an adequate general population dataset and no exception applies.

Use the updated Ghosh et al. 2018 definition:

```text
Allele frequency is >0.05 in any general continental population dataset of at least 2,000 observed alleles and the variant is found in a gene without a gene- or variant-specific BA1 modification.
```

If BA1 applies, the variant can be classified Benign without further evidence evaluation under the generic ACMG/AMP framework. If the variant is on the BA1 exception list or a gene/variant-specific exception applies, do not use BA1; evaluate all other evidence normally.

---

## Evidence Retrieval Workflow

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant`, `ClinGenAR_lookup_allele`, `EnsemblVEP_annotate_hgvs`, and `MyVariant_query_variants`.
   - Record HGVS c./p./g., transcript, rsID, ClinGen Allele Registry ID, ClinVar Variation ID, genome build, and normalized genomic allele.
   - For table matching, compare by gene plus HGVS, ClinVar ID, ClinGen Allele Registry ID, and genomic coordinate when available.

2. **Retrieve population frequency**
   - Use `gnomad_search_variants`, `gnomad_get_variant`, `EnsemblVar_get_population_frequencies`, `dbsnp_get_frequencies`, and `MyVariant_query_variants`.
   - Record global AF, maximum ancestry/subpopulation AF, AC/AN, homozygote/hemizygote count, data quality flags, coverage, and whether the population is a general continental population or founder/bottlenecked population.

3. **Check BA1 threshold adequacy**
   - BA1 requires AF >0.05 in a qualifying general continental population dataset.
   - The relevant population dataset must have at least 2,000 observed alleles at the site.
   - Use observed alleles, not individuals, which matters for sex chromosomes outside pseudoautosomal regions.
   - Do not require the patient's ancestry to match the high-frequency population for BA1; Ghosh et al. allow BA1 if any qualifying specified population exceeds the threshold, provided no exception applies.

4. **Check exception list and disease-specific modifications**
   - Check the static BA1 exception list in `references/ghosh_2018_ba1_exception_guidance.md`.
   - Check ClinGen/VCEP specifications, ClinVar expert-panel comments, and disease-specific literature for gene-specific or variant-specific BA1 thresholds lower than 0.05.
   - If the variant is on the exception list or a current VCEP/gene-specific exception applies, do not apply BA1.

5. **Assess founder and dataset caveats**
   - Be cautious when AF >0.05 is observed only in founder or bottlenecked populations, such as Finnish or Ashkenazi Jewish datasets.
   - If relatedness, effective population size, or population structure makes the dataset unsuitable, report `status: not_assessed` with reason `BA1 population dataset not adequate`, or route to BS1 if disease-specific thresholds support it.
   - Do not use population datasets with substantial relatedness unless a population genetic assessment supports effective population size.

6. **Route conflicts**
   - If BA1 is blocked but frequency is still too high for disease, use `tooluniverse-acmg-benign-context-refinement` for BS1.
   - If the variant is on the BA1 exception list, evaluate pathogenic and benign evidence normally without BA1 or BS1 circularity.
   - If the disease is low penetrance, common, incompletely penetrant, or not well modeled by Mendelian ACMG rules, report that BA1/BS1 require disease-specific expert calibration.

---

## BA1 Assignment Rules

### Apply BA1

Apply `BA1` only when all are true:

- AF >0.05 in at least one qualifying general continental population dataset.
- The dataset has at least 2,000 observed alleles at the site.
- The population source is appropriate for stand-alone benign filtering.
- The variant is not on the ClinGen BA1 exception list.
- No gene-specific, variant-specific, or VCEP BA1 modification supersedes the generic threshold.
- There is no unresolved dataset quality, relatedness, build, allele-normalization, or population-structure problem.

### Do Not Apply BA1

Use `No BA1 - exception list` when the variant matches one of the Ghosh 2018 exception-list variants.

Use `No BA1 - gene/variant-specific threshold` when a VCEP or expert specification defines a lower BA1 threshold or excludes the generic BA1 threshold.

Use `status: not_assessed` with reason `BA1 population dataset not adequate` when AF appears high but population dataset quality, observed allele number, relatedness, founder effect, or allele normalization is not adequate.

Use `No BA1 - use BS1 review` when AF is high for the disease context but does not meet stand-alone BA1 conditions.

---

## Static BA1 Exception List

The July 30, 2018 ClinGen BA1 exception list contains these variants. If the assessed variant matches one of these entries, do not apply BA1 automatically even if AF >0.05.

| Gene | Variant | ClinVar ID | ClinGen Allele Registry ID | ExAC population | MAF | Disease |
| --- | --- | --- | --- | --- | --- | --- |
| ACAD9 | NM_014049.4:c.-44_-41dupTAAG | 1018 | CA114709 | AFR | 0.1261 | ACAD9 deficiency |
| GJB2 | NM_004004.5:c.109G>A (p.Val37Ile) | 17023 | CA172210 | EAS | 0.07242 | Autosomal recessive deafness |
| HFE | NM_000410.3:c.187C>G (p.His63Asp) | 10 | CA113797 | NFE | 0.1368 | Hereditary hemochromatosis |
| HFE | NM_000410.3:c.845G>A (p.Cys282Tyr) | 9 | CA113795 | NFE | 0.05135 | Hereditary hemochromatosis |
| MEFV | NM_000243.2:c.1105C>T (p.Pro369Ser) | 2551 | CA280114 | EAS | 0.07156 | Familial Mediterranean fever |
| MEFV | NM_000243.2:c.1223G>A (p.Arg408Gln) | 2552 | CA280116 | EAS | 0.05407 | Familial Mediterranean fever |
| PIBF1 | NM_006346.2:c.1214G>A (p.Arg405Gln) | 217689 | CA210261 | AMR | 0.09858 | Joubert syndrome |
| ACADS | NM_000017.3:c.511C>T (p.Arg171Trp) | 3830 | CA312214 | FIN | 0.06589 | ACADS deficiency |
| BTD | NM_000060.4:c.1330G>C (p.Asp444His) | 1900 | CA090886 | FIN | 0.05398 | Biotinidase deficiency |

Notes:

- The HFE variants are common low-penetrance variants; the article notes that generic ACMG/AMP criteria are not designed for this variant type.
- ACADS and BTD were detected above 5% MAF only in the Finnish population in the supplied list.
- Genomic coordinates in the original list use GRCh37.

---

## Double-Counting and Circularity

- Do not use BA1 and PM2 together.
- Do not use BA1 and BS1 together for the same disease context.
- When evaluating exception-list variants, do not use BA1 or BS1 to decide whether the variant belongs on the exception list; Ghosh et al. assessed those variants while ignoring BA1 and BS1.
- Use BS2 only when healthy observations are incompatible with disease penetrance and age of onset.
- Do not let a pathogenic ClinVar assertion override BA1 by itself. Use PP5/BP6 reputable-source refinement and retrieve primary evidence.

---

## Output Format

```markdown
BA1 exception-list refinement:
- Variant: [HGVS / genomic allele / rsID / CA ID / ClinVar ID]
- Population source: [gnomAD / ExAC / 1000G / other]
- Maximum qualifying AF: [population, AF, AC/AN]
- Observed alleles at site: [AN]
- General continental population: [yes / no / founder or bottlenecked / unclear]
- Exception-list match: [none / matched entry]
- Gene/VCEP-specific BA1 rule: [none / threshold / exception / not assessed]
- Applied evidence: [BA1 / No BA1 - exception list / No BA1 - gene-specific rule / No BA1 - use BS1 review / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Routed to: [none / tooluniverse-acmg-benign-context-refinement for BS1]
- Rationale: [brief explanation with sources]
```

---

## Tool Parameter Reference

| Tool or skill | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Normalize HGVS and transcript consequence. |
| `ClinGenAR_lookup_allele` | Resolve ClinGen Allele Registry ID and cross-references. |
| `ClinVar_search_variants`, `ClinVar_get_variant` | Retrieve ClinVar Variation ID, clinical assertions, and linked evidence. |
| `gnomad_search_variants`, `gnomad_get_variant` | Current population AF, AC/AN, ancestry-specific AF, homozygotes. |
| `EnsemblVar_get_population_frequencies` | Population frequency fallback for rsID-resolved variants. |
| `dbsnp_get_frequencies`, `MyVariant_query_variants` | Aggregated frequency and identifier fallback. |
| `PubMed_search_articles`, `EuropePMC_search_articles` | Disease-specific threshold and penetrance literature. |
| `tooluniverse-acmg-benign-context-refinement` | BS1/BS2/BP2/BP5 when BA1 does not apply. |
| `tooluniverse-acmg-pm2-absence-rarity-refinement` | PM2 absence/rarity after BA1/BS1/BS2 have been excluded. |
| `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` | Treat ClinVar/source assertions as leads, not automatic BA1 exceptions. |

---

## Primary References

- Ghosh R, Harrison SM, Rehm HL, Plon SE, Biesecker LG; ClinGen Sequence Variant Interpretation Working Group. Updated recommendation for the benign stand-alone ACMG/AMP criterion. Human Mutation. 2018;39(11):1525-1530. PMID:30311383. PMCID:PMC6188666. DOI:10.1002/humu.23642.
- ClinGen Sequence Variant Interpretation Working Group. BA1 Exception List. July 30, 2018. User-provided PDF: `ba1_exception_list_07_30_2018.pdf`.
