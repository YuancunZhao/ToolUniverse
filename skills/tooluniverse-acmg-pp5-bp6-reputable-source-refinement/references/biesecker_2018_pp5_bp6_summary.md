# Biesecker and Harrison 2018 PP5/BP6 Summary

Primary reference:

- Biesecker LG, Harrison SM; ClinGen Sequence Variant Interpretation Working Group. The ACMG/AMP reputable source criteria for the interpretation of sequence variants. Genetics in Medicine. 2018;20(12):1687-1688. PMID:29543229. PMCID:PMC6709533. DOI:10.1038/gim.2018.42.

## Source Status

ToolUniverse `PubMed_search_articles` retrieved PubMed metadata for DOI `10.1038/gim.2018.42`, confirming PMID:29543229 and PMCID:PMC6709533. The user provided the PDF (`PIIS1098360021000162.pdf`), and this summary was aligned against the full two-page article.

## Original ACMG/AMP Criteria

The original 2015 ACMG/AMP framework included:

- `PP5`: a reputable source recently reports the variant as pathogenic, but the evidence is not available to the laboratory for independent evaluation.
- `BP6`: a reputable source recently reports the variant as benign, but the evidence is not available to the laboratory for independent evaluation.

## ClinGen SVI Recommendation

Biesecker and Harrison, on behalf of the ClinGen Sequence Variant Interpretation Working Group, recommend discontinuing PP5 and BP6 as soon as practically achievable.

The article states that ClinGen removed these criteria from the ClinGen Variant Curation Interface.

## Rationale

Key reasons:

- Primary data are preferable to expert opinion without access to primary data.
- PP5 and BP6 rely on assertions that are not directly linked to the evidence on which they were based.
- ClinVar and related data-sharing mechanisms have reduced the need to rely on secondary assertions.
- PP5/BP6 can be misused when laboratories count primary evidence, such as PS3/BS3 functional data, and then also count a secondary classification based on the same evidence.
- This double counting can lead to classification errors.

## ToolUniverse Interpretation

For ToolUniverse ACMG overlay use:

- Do not count PP5 or BP6 by default.
- Treat reputable-source assertions as evidence-discovery leads.
- Retrieve primary evidence, then route it to the appropriate ACMG criteria.
- If primary evidence is unavailable, report PP5/BP6 as not used or not assessed rather than applying the criterion.
- Use current VCEP specifications when they explicitly define how to treat curated external classifications.

## Common Routing

| Source assertion basis | Route to |
| --- | --- |
| LoF mechanism or predicted null consequence | PVS1 LoF decision-tree overlay |
| RNA/splicing assay or transcript evidence | PVS1 splicing refinement |
| Functional assay | PS3/BS3 functional assay overlay |
| Case-control or affected-case evidence | PS4 case-enrichment overlay |
| Segregation or non-segregation | PP1/BS4 segregation overlay |
| De novo observation | PS2/PM6 de novo overlay |
| Recessive biallelic observation | PM3 in-trans overlay |
| Population frequency | PM2 or benign-context overlays |
| Protein-level same-change/same-residue comparison | PS1/PM5 overlay |
| Computational prediction | PP3/BP4 overlay |

## Reporting Language

Use concise wording:

```text
PP5/BP6 was not counted. The secondary classification was used only as a lead to retrieve primary evidence, following Biesecker and Harrison 2018 ClinGen SVI guidance recommending discontinuation of PP5/BP6.
```
