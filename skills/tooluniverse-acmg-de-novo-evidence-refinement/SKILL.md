---
name: tooluniverse-acmg-de-novo-evidence-refinement
description: Refine ACMG/AMP PS2 and PM6 de novo evidence using ClinGen SVI De Novo Criteria Recommendation v1.1 point scoring. Use with ToolUniverse ACMG classification when de novo status, parental relationship confirmation, phenotype consistency, recurrent observations, inheritance, mosaicism, literature evidence, or missing family information affects PS2/PM6 assignment.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG De Novo Evidence Refinement

This skill extends `tooluniverse-acmg-variant-classification` for de novo evidence only, following the ClinGen Sequence Variant Interpretation Recommendation for De Novo Criteria (PS2/PM6), version 1.1.

- `PS2`: de novo evidence with confirmed parental relationships contributing to the overall score.
- `PM6`: de novo evidence where parental relationships are unconfirmed or assumed.

The SVI recommendation uses a point-based system. Each unrelated de novo occurrence receives points based on phenotype specificity and parental relationship confirmation. The total points across independent observations determine the evidence strength.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PS2/PM6 point model.

---

## When to Use This Skill

Use this skill when:

- The user reports a variant may be de novo.
- A paper, case table, or clinical report includes trio testing, parental testing, or statements such as "de novo", "not detected in parents", or "sporadic".
- The main ACMG workflow is considering PS2 or PM6.
- Parentage, parental samples, mosaicism, phenotype consistency, or recurrence status is unclear.
- A VCEP defines de novo point-based or phenotype-specific PS2/PM6 rules.
- De novo evidence comes from literature, case tables, pedigrees, Sanger traces, or supplemental figures.

Do not use PS2/PM6 when de novo status is not supplied or cannot be inferred from explicit evidence.

---

## Required De Novo Intake

Before assigning PS2 or PM6, collect:

- Proband genotype and variant.
- Proband phenotype and suspected disease.
- Whether the phenotype matches the gene-disease association.
- Mother genotype for the variant.
- Father genotype for the variant.
- Whether maternity and paternity were confirmed.
- Testing method and sample type for proband and parents.
- Whether parental mosaicism was assessed or suspected.
- Whether either parent is clinically affected, mildly affected, mosaic, or unavailable.
- Whether the observation is from one proband or multiple unrelated probands.
- For each proband, phenotype specificity category and whether genetic heterogeneity is high.
- Whether the same de novo observation is already counted in published evidence or database assertions.

If these fields are missing, report `status: not_assessed` with reason `PS2/PM6 de novo information required` and ask targeted follow-up questions.

---

## ToolUniverse Evidence Retrieval

Use ToolUniverse tools to contextualize the de novo claim; do not infer de novo status from databases alone.

Recommended tools:

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize the proband variant. |
| `ClinVar_search_variants` / `ClinVar_get_variant` | Review variant-level assertions and whether de novo observations are cited. |
| `ClinGen_search_gene_validity` / `GenCC_search_gene` | Confirm gene-disease validity and inheritance. |
| `MedGen_search_conditions`, `MedGen_get_condition`, `MedGen_get_clinical_features`, `Mondo_get_disease`, `Mondo_get_disease_phenotypes`, HPO tools, and Monarch tools | Match supplied phenotype to disease context. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Retrieve case reports or series with trio and parentage information. |
| `EuropePMC_get_full_text` / `EuropePMC_get_fulltext_snippets` | Extract parental testing statements when available. |
| `tooluniverse-literature-deep-research` | Use for systematic retrieval and interpretation of publications reporting de novo observations, especially when the evidence is in text, tables, supplements, or multiple papers. |
| `tooluniverse-literature-figure-evidence-extraction` | Extract trio/pedigree/Sanger confirmation details from figures when the evidence is visual. |
| `tooluniverse-acmg-phenotype-dependent-evidence-refinement` | Check phenotype consistency before counting de novo evidence. |

---

## Literature Evidence Linkage

When de novo observations are reported in a paper rather than directly supplied by the user:

1. Use `tooluniverse-literature-deep-research` to locate the article, retrieve full text or snippets, identify case tables and supplemental material, and determine whether the proband, parental genotypes, parentage confirmation, and phenotype are explicitly reported.
2. Use `tooluniverse-literature-figure-evidence-extraction` when the de novo claim depends on a pedigree, Sanger trace, trio figure, supplementary image, or visual genotype evidence.
3. Pass the extracted structured facts into this PS2/PM6 scoring overlay.
4. Do not score a de novo occurrence from literature if the publication does not state that parents were tested for the variant.

---

## SVI v1.1 Point Scoring

Score each unrelated de novo occurrence separately. Sum points across independent occurrences for the same variant and disease context.

### Points Per Proband

| Phenotypic consistency | Confirmed parental relationships | Unconfirmed parental relationships |
| --- | ---: | ---: |
| Phenotype highly specific for the gene | 2 | 1 |
| Phenotype consistent with the gene but not highly specific | 1 | 0.5 |
| Phenotype consistent but not highly specific and high genetic heterogeneity | 0.5 | 0.25 |
| Phenotype not consistent with the gene | 0 | 0 |

For the high-genetic-heterogeneity row, the SVI recommendation caps the maximum contribution to the overall score at 1 point.

No points should be awarded if the parents have not been tested for parentage or for the variant.

### Strength Thresholds

| Total de novo points | Evidence strength |
| ---: | --- |
| 0.5 | Supporting: `PS2_Supporting` or `PM6_Supporting` |
| 1 | Moderate: `PS2_Moderate` or `PM6` |
| 2 | Strong: `PS2` or `PM6_Strong` |
| 4 | Very Strong: `PS2_VeryStrong` or `PM6_VeryStrong` |

Use the highest threshold met by the summed points. For example, 3 points meets Strong but not Very Strong.

### Choosing PS2 Versus PM6 Label

- Use a PS2 label when at least one counted occurrence has confirmed parental relationships and contributes to the summed score.
- Use a PM6 label when all counted occurrences have unconfirmed parental relationships.
- If confirmed and unconfirmed observations are combined, report the point contribution from each category and use the PS2 strength label for the combined evidence, consistent with the SVI example combining one confirmed and two unconfirmed observations into `PS2_VeryStrong`.

---

## Evidence Assignment Workflow

1. **Confirm variant-level parental testing**
   - Both parents should be tested for the variant for the occurrence to receive points.
   - If the parents were not tested for the variant, award 0 points.
   - If only one parent was tested, award 0 points unless a current VCEP explicitly provides a rule.

2. **Classify parental relationship status**
   - Confirmed parental relationships: maternity and paternity are confirmed.
   - Unconfirmed parental relationships: parental relationships are assumed or not documented, but both parents were tested and are negative for the variant.
   - The v1.1 clarification is that confirmed/assumed refers to parental relationships, not whether the variant itself is de novo.

3. **Classify phenotype specificity**
   - Highly specific for the gene.
   - Consistent but not highly specific.
   - Consistent but not highly specific with high genetic heterogeneity.
   - Not consistent with the gene.
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` when phenotype information is incomplete.

4. **Award points per independent proband**
   - Use the SVI v1.1 point table.
   - De-duplicate publications, databases, and repeated reports of the same individual.
   - Apply the 1-point cap for the high-genetic-heterogeneity category.

5. **Map total points to strength**
   - Use the SVI v1.1 strength thresholds.
   - Use PS2 or PM6 labels according to parental relationship confirmation status.

6. **Apply inheritance-specific considerations**
   - X-linked inheritance: if the variant occurs de novo in an unaffected carrier mother and the family history is consistent, de novo criteria may be applied despite the mother being unaffected.
   - Autosomal recessive inheritance: if a de novo occurrence is in a gene associated with an autosomal recessive condition and no additional pathogenic/likely pathogenic variant is identified, decrease the evidence strength by one level.
   - Apparent germline mosaicism: for multiple affected siblings with both parents negative for the variant, parental relationships must be confirmed for de novo criteria to apply.

### No PS2/PM6

Do not apply de novo evidence when:

- Parental genotypes are not provided.
- Only one parent was tested and no VCEP rule allows a reduced strength.
- The variant is inherited from an unaffected or affected parent.
- The proband phenotype is absent, nonspecific, or mismatched and cannot be evaluated.
- The source says only "sporadic" without variant-level parental testing.
- The de novo claim is based on database classification without accessible evidence.
- The observation would be circularly counted from the same publication, same database assertion, or same patient.
- The proband phenotype is not consistent with the gene-disease relationship.
- The same occurrence is duplicated across literature and database records.

---

## Missing-Information Prompts

Use targeted questions rather than broad requests.

If no de novo information was provided:

```text
PS2/PM6 requires SVI de novo scoring inputs. Please provide whether the variant was tested in both parents, each parent's result, whether maternity and paternity were confirmed, the testing method/sample type, the proband phenotype, whether the phenotype is highly specific for the gene, and whether additional unrelated de novo occurrences are known.
```

If parental results are incomplete:

```text
De novo evidence is incomplete. Please provide mother and father genotypes for the variant, whether both biological relationships were confirmed, and whether parental mosaicism was assessed.
```

If phenotype is missing:

```text
PS2/PM6 also requires phenotype consistency. Please provide the proband phenotype or HPO terms, suspected disease, and age at onset.
```

If the evidence comes from literature:

```text
Please provide the paper excerpt, table, pedigree, Sanger trace, or trio-testing statement showing the proband and parental genotypes, phenotype, unrelatedness/duplicate status, and whether parental relationships were confirmed.
```

---

## VCEP Priority

Current VCEP specifications supersede this generic overlay. Follow VCEP rules when they define:

- De novo point systems or strength upgrades/downgrades.
- Phenotype-specific requirements.
- Whether one-parent testing can contribute evidence.
- How to count recurrent de novo observations.
- How to handle parental mosaicism.
- Whether confirmed parentage is mandatory for PS2 or only affects strength.
- How the high-genetic-heterogeneity cap is modified, if applicable.

Always cite the VCEP if it changes generic PS2/PM6 assignment.

---

## Output Format

```markdown
De novo evidence refinement:
- Proband variant: [HGVS/genomic allele]
- Proband phenotype: [summary / not provided]
- Phenotype specificity category: [highly specific / consistent not specific / consistent high heterogeneity / not consistent / not_assessed]
- Mother genotype: [negative/positive/not tested/not provided]
- Father genotype: [negative/positive/not tested/not provided]
- Parentage confirmation: [confirmed / not confirmed / not documented]
- Testing method/sample type: [summary]
- Mosaicism review: [none reported / suspected / not_assessed]
- Occurrence independence: [independent / duplicate/circularity concern / not_assessed]
- Points awarded for this occurrence: [value]
- Total de novo points across independent occurrences: [value]
- SVI v1.1 threshold met: [Supporting / Moderate / Strong / Very Strong / none]
- Inheritance adjustment: [none / AR one-level decrease / X-linked carrier rule / germline mosaicism rule / VCEP-specific]
- VCEP rule: [none found / applied rule]
- Applied evidence: [PS2 / PM6 / No PS2/PM6 / none]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [de novo observation IDs / phenotype specificity / none]
- Follow-up question: [targeted missing fields if needed]
```

---

## Limitations

- Databases may report de novo observations without enough detail to assign SVI points.
- Parentage confirmation, parental mosaicism, and phenotype match often require primary literature or clinical report details.
- De novo evidence is not automatically applicable to genes with unclear disease validity or mismatched phenotype.
- Multiple de novo observations should be checked for duplicate reporting.
- The SVI de novo point values are not equivalent to Bayesian point values used in ACMG/AMP classification modeling.

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868. DOI: 10.1038/gim.2015.30.
- ClinGen Sequence Variant Interpretation Working Group. SVI Recommendation for De Novo Criteria (PS2 and PM6), version 1.1. Approved March 18, 2018; updated May 5, 2021.
- Current ClinGen VCEP specifications for disease-specific PS2/PM6 modifications, de novo point systems, and phenotype requirements.
