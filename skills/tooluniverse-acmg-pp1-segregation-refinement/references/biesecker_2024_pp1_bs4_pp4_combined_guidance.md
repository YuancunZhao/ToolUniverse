# Biesecker et al. 2024 PP1/BS4/PP4 Combined Guidance Summary

## Source

- Biesecker LG, Byrne AB, Harrison SM, Pesaran T, Schaffer AA, Shirts BH, Tavtigian SV, Rehm HL; ClinGen Sequence Variant Interpretation Working Group. ClinGen guidance for use of the PP1/BS4 co-segregation and PP4 phenotype specificity criteria for sequence variant pathogenicity classification. American Journal of Human Genetics. 2024;111(1):24-38. PMID: 38103548. PMCID: PMC10806742. DOI: 10.1016/j.ajhg.2023.11.009.

ToolUniverse `PubMed_search_articles` confirmed PMID, PMCID, DOI, journal, and abstract. The user supplied the full PDF as `mmc2.pdf`; this summary was aligned against the article text, Tables 2-4, and Supplemental Table S1.

## Main Change for ToolUniverse

This paper should not replace the existing PP1 or PP4 overlays wholesale. It adds a combined rule layer for cases where phenotype specificity (`PP4`) and family co-segregation or non-segregation (`PP1`/`BS4`) are based on the same locus, phenotype, family, or diagnostic-yield evidence.

The key principle is that PP4 and PP1 are not always independent. In some contexts, phenotype specificity already implicates the locus so strongly that expected co-segregation adds little or no independent evidence. In other contexts, PP4 diagnostic-yield points and PP1 co-segregation points can be added, but their combined locus evidence is capped.

## Applicability

Use this guidance when:

- the gene-disease validity is definitive or strong;
- the disease is Mendelian and the inheritance model is clear;
- phenotype specificity or diagnostic yield affects PP4;
- family segregation or non-segregation affects PP1 or BS4;
- locus homogeneity, locus heterogeneity, or exclusion of other loci changes the interpretation;
- more than one plausible candidate variant is present on the implicated allele.

Use formal segregation analysis or a VCEP rule instead when penetrance is low, phenocopy rate is high, the pedigree is large or complex, consanguinity materially affects the model, or the available diagnostic-yield data are weak.

## Diagnostic Yield to PP4 Points

Diagnostic yield means the historical demonstrated yield of pathogenic variants from molecular testing similar to the testing method used for the case, conditional on a matching phenotype definition. Round down to the nearest supported value.

| Diagnostic yield | Points |
| --- | ---: |
| 99.9% | 12 |
| 99.8% | 11.5 |
| 99.7% | 11 |
| 99.6% | 10.5 |
| 99.4% | 10 |
| 99.2% | 9.5 |
| 98.8% | 9 |
| 98.3% | 8.5 |
| 97.5% | 8 |
| 96.5% | 7.5 |
| 95.0% | 7 |
| 93.0% | 6.5 |
| 90.2% | 6 |
| 86.4% | 5.5 |
| 81.6% | 5 |
| 75.4% | 4.5 |
| 68.0% | 4 |
| 59.6% | 3.5 |
| 50.6% | 3 |
| 41.5% | 2.5 |
| 33.0% | 2 |
| 25.4% | 1.5 |
| 19.1% | 1 |

The paper recommends a practical lower limit of about +1.0 point, corresponding to about 20% diagnostic yield. Below that, do not use diagnostic-yield PP4 unless a VCEP has a specific rule.

## Co-Segregation Points

Use this table for simple pedigrees when disease-specific VCEP or formal likelihood analysis is not available.

| Co-segregating individuals | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Autosomal-recessive affected | 2.0 | 4.0 | 6.0 | 8.0 | 10.0 |
| Autosomal-recessive unaffected | 0.4 | 0.8 | 1.2 | 1.6 | 2.0 |
| Autosomal-dominant affected and informative unaffected | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |
| X-linked-recessive male affected and informative unaffected | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |

Only count unaffected individuals if the disease is fully penetrant for their age, sex, and clinical evaluation. Do not count unaffected parents used only to establish phase. Additional autosomal-recessive unaffected segregations above five add +0.4 each. Additional X-linked obligate heterozygous females can be counted when informative.

## Combined PP1/PP4 Cap

All PP1 plus PP4 locus evidence is capped at +5.0 points per variant. PP1/PP4 alone should not produce a likely pathogenic or pathogenic classification; independent variant-level evidence is required for stronger final classifications.

| Combined points | Maximum allowable code combination |
| --- | --- |
| 0-0.9 | Not applicable |
| 1-1.9 | `PP1` or `PP4_Supporting` |
| 2-2.9 | `PP1_Moderate`, `PP4_Moderate`, or `PP1` + `PP4_Supporting` |
| 3-3.9 | `PP1` + `PP4_Moderate`, `PP1_Moderate` + `PP4_Supporting`, or `PP1_Moderate` |
| 4-4.9 | `PP1_Strong`, `PP4_Strong`, or `PP1_Moderate` + `PP4_Moderate` |
| >=5 | `PP1_Strong` + `PP4_Supporting`, or `PP4_Strong` + `PP1` |

## Locus Homogeneity and Heterogeneity

In a locus-homogeneous, high-diagnostic-yield phenotype, PP4 can capture the locus evidence and additional PP1 should generally not be added for expected perfect co-segregation.

In locus-heterogeneous disease, assign PP4 points from the diagnostic yield for the gene-phenotype dyad, then add PP1/BS4 points from informative family observations. If testing excludes other plausible loci, reassess the diagnostic-yield points for the remaining locus.

For phenotypes with high locus heterogeneity and uncertain diagnostic yield, use PP4 cautiously or not at all. Examples of broad or nonspecific phenotypes that usually should not receive PP4 from diagnostic yield alone include isolated arrhythmia, intellectual disability, seizures, isolated thoracic aortic aneurysm, nonsyndromic hearing loss without specific features, and cancer phenotypes with high phenocopy rates.

## BS4 and Negative Evidence

Robust non-segregation remains strong benign evidence, approximately -4.0 points, when it distinguishes the variant or locus in autosomal-dominant, autosomal-recessive homozygous, or X-linked settings.

In autosomal-recessive compound heterozygosity, non-segregation in relatives at the locus may provide little or no variant-specific benign evidence, because it may show that one of two alleles is not causative without identifying which allele is benign.

Negative evidence at one locus can provide indirect positive evidence for another locus in a heterogeneous disease, but only when the testing strategy, locus set, and phenotype assumptions support that conclusion.

## Evidence Apportionment

PP1 and PP4 evidence implicate an allele or locus, not automatically a single variant. If multiple plausible variants are present in cis on the implicated allele, apportion evidence across variants by posterior probability rather than dividing points arithmetically.

Supplemental Table S1 provides a worksheet:

1. Sum non-PP1/PP4/BS4 evidence for each candidate variant.
2. Convert each variant's non-PP1/PP4/BS4 points to posterior probability.
3. Calculate relative pathogenicity odds between variants.
4. Combine the relative odds with diagnostic yield.
5. Convert adjusted posterior probabilities back to points.
6. Ensure the adjusted posteriors sum to the diagnostic yield.

## Double Counting

- Do not fully stack PP1 and PP4 when both arise from the same locus/phenotype/family evidence.
- Do not count the same affected individual as both PP4 and PS4.
- Family members of a PP4 or PS4 proband may still contribute PP1 if independently informative.
- Do not use PP1/PP4 evidence alone to reach likely pathogenic or pathogenic.
- If a VCEP embeds phenotype specificity into PS4, PS2/PM6, or another evidence code, do not add PP4 separately unless explicitly permitted.

## Practical ToolUniverse Translation

For ToolUniverse overlays:

1. Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` to collect phenotype specificity, diagnostic yield, and missing clinical fields.
2. Use `tooluniverse-acmg-pp1-segregation-refinement` when PP4 interacts with PP1 or BS4.
3. Use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when family information, pedigrees, or supplementary tables are embedded in publications.
4. Keep PS4, PM3, PS2/PM6, and PP4 case observations separate unless a VCEP says otherwise.
