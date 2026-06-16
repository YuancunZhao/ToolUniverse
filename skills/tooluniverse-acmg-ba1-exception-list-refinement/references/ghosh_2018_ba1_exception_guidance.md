# Ghosh et al. 2018 BA1 Summary and Exception List

Primary reference:

- Ghosh R, Harrison SM, Rehm HL, Plon SE, Biesecker LG; ClinGen Sequence Variant Interpretation Working Group. Updated recommendation for the benign stand-alone ACMG/AMP criterion. Human Mutation. 2018;39(11):1525-1530. PMID:30311383. PMCID:PMC6188666. DOI:10.1002/humu.23642.

Supplemental/reference material:

- ClinGen Sequence Variant Interpretation Working Group. BA1 Exception List. July 30, 2018. User-provided PDF: `ba1_exception_list_07_30_2018.pdf`.

## Source Status

ToolUniverse `PubMed_search_articles` retrieved PubMed metadata and abstract for DOI `10.1002/humu.23642`, confirming PMID:30311383 and PMCID:PMC6188666. The user provided the full article PDF (`ghosh2018.pdf`) and the BA1 exception-list PDF (`ba1_exception_list_07_30_2018.pdf`). This summary was aligned against both files.

## Updated BA1 Definition

Ghosh et al. 2018 update the generic BA1 criterion to:

```text
Allele frequency is >0.05 in any general continental population dataset of at least 2,000 observed alleles and found in a gene without a gene- or variant-specific BA1 modification.
```

Operational implications:

- BA1 is stand-alone benign evidence.
- The AF threshold is evaluated in any qualifying population dataset, not only one matching the patient's ancestry.
- The dataset must have at least 2,000 observed alleles at the site.
- Observed alleles are used instead of individuals, which matters for sex chromosomes.
- Founder/bottlenecked populations require caution because pathogenic alleles can rise to high frequency.
- Current VCEP or gene-specific rules can define numerically lower BA1 thresholds.

## BA1 Exception Logic

Do not apply BA1 automatically when:

- the variant is on the ClinGen BA1 exception list;
- a VCEP or expert group defines a gene-specific or variant-specific BA1 modification;
- the high frequency is seen only in a founder/bottlenecked population and population structure has not been adequately handled;
- the population dataset does not have at least 2,000 observed alleles;
- allele normalization, build, or population-frequency source is uncertain.

If BA1 is blocked but frequency remains too high for the disease, evaluate BS1 through disease-specific benign-context rules.

## Static Exception List

| Gene | Variant | Classification in list | Criteria applied without BA1/BS1 | ClinVar ID | CA ID | GRCh37 position | ExAC pop | MAF | Disease |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ACAD9 | NM_014049.4:c.-44_-41dupTAAG | VUS | PS3_Supporting; BS2 | 1018 | CA114709 | 3:128598490 C>CTAAG | AFR | 0.1261 | ACAD9 deficiency |
| GJB2 | NM_004004.5:c.109G>A (p.Val37Ile) | Pathogenic | PS4; PP1_Strong; PM3_VeryStrong; PS3_Moderate | 17023 | CA172210 | 13:20763612 C>T | EAS | 0.07242 | Autosomal recessive deafness |
| HFE | NM_000410.3:c.187C>G (p.His63Asp) | Pathogenic* | PS4 | 10 | CA113797 | 6:26091179 C>G | NFE | 0.1368 | Hereditary hemochromatosis |
| HFE | NM_000410.3:c.845G>A (p.Cys282Tyr) | Pathogenic* | PS4; PP3 | 9 | CA113795 | 6:26093141 G>A | NFE | 0.05135 | Hereditary hemochromatosis |
| MEFV | NM_000243.2:c.1105C>T (p.Pro369Ser) | VUS | PM3; PM5 | 2551 | CA280114 | 16:3299586 G>A | EAS | 0.07156 | Familial Mediterranean fever |
| MEFV | NM_000243.2:c.1223G>A (p.Arg408Gln) | VUS | PM3; PM5 | 2552 | CA280116 | 16:3299468 C>T | EAS | 0.05407 | Familial Mediterranean fever |
| PIBF1 | NM_006346.2:c.1214G>A (p.Arg405Gln) | VUS | PM3; BS2 | 217689 | CA210261 | 13:73409497 G>A | AMR | 0.09858 | Joubert syndrome |
| ACADS | NM_000017.3:c.511C>T (p.Arg171Trp) | VUS | PS3_Moderate; PM3; PP3 | 3830 | CA312214 | 12:121175678 C>T | FIN | 0.06589 | ACADS deficiency |
| BTD | NM_000060.4:c.1330G>C (p.Asp444His) | Pathogenic | PS3; PM3_Strong; PP3; PP4 | 1900 | CA090886 | 3:15686693 G>C | FIN | 0.05398 | Biotinidase deficiency |

Notes:

- Asterisked HFE entries are common low-penetrance variants; the article notes that the ACMG/AMP framework is not designed for this variant type.
- ACADS and BTD were detected at >5% MAF only in the Finnish population.
- Genomic coordinates in the exception-list PDF are GRCh37.
- AFR: African/African American; AMR: Latino; EAS: East Asian; NFE: non-Finnish European; FIN: Finnish.

## Exception List Review Approach

Ghosh et al. cross-referenced ClinVar pathogenic assertions with ExAC variants above 0.05 in major subpopulations. They removed variants from exception-list consideration when they were better considered common susceptibility/modifier alleles, had unproven gene-disease association, represented traits rather than disease, had very limited evidence, were somatic only, or involved noncoding genes.

The final nine variants were curated without using BA1 or BS1 to avoid circularity. BS2 was used only where substantial homozygotes were observed and the phenotype met the "full penetrance expected at an early age" condition.

## Reporting Language

```text
BA1 was not applied because the variant matches the ClinGen BA1 exception list. The variant should be evaluated using the remaining ACMG evidence criteria, without using BA1 or BS1 circularly.
```
