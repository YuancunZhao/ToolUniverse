# Quick Start: De Novo Evidence Refinement

Use this overlay when PS2 or PM6 may apply, or when the user asks whether a variant is de novo evidence. This overlay follows ClinGen SVI De Novo Criteria Recommendation v1.1: score each independent de novo occurrence, sum points, then map the total to PS2/PM6 strength.

---

## SVI v1.1 Point Table

| Phenotypic consistency | Confirmed parental relationships | Unconfirmed parental relationships |
| --- | ---: | ---: |
| Phenotype highly specific for the gene | 2 | 1 |
| Phenotype consistent with the gene but not highly specific | 1 | 0.5 |
| Phenotype consistent but not highly specific and high genetic heterogeneity | 0.5 | 0.25 |
| Phenotype not consistent with the gene | 0 | 0 |

High-genetic-heterogeneity observations can contribute at most 1 point to the overall score.

| Total points | Evidence strength |
| ---: | --- |
| 0.5 | `PS2_Supporting` or `PM6_Supporting` |
| 1 | `PS2_Moderate` or `PM6` |
| 2 | `PS2` or `PM6_Strong` |
| 4 | `PS2_VeryStrong` or `PM6_VeryStrong` |

Use PS2 labels when at least one counted observation has confirmed parental relationships; use PM6 labels when all counted observations have unconfirmed parental relationships.

---

## Example 1: Confirmed De Novo Trio, Highly Specific Phenotype

**Scenario**: The proband is affected, both parents test negative, and maternity and paternity are confirmed.

**Expected behavior**:

- Confirm phenotype matches the gene-disease relationship.
- Confirm parental testing method and sample type are adequate.
- If the phenotype is highly specific for the gene, award 2 points.
- Apply `PS2` at Strong strength unless a VCEP specifies a different strength.

---

## Example 2: Confirmed Trio, Consistent but Not Specific Phenotype

**Scenario**: One affected proband has a de novo variant, parental relationships are confirmed, but the phenotype is consistent with the gene and not highly specific.

**Expected behavior**:

- Award 1 point.
- Apply `PS2_Moderate` if this is the only independent occurrence.

---

## Example 3: Assumed De Novo Without Parentage Confirmation

**Scenario**: Both parents test negative, but maternity and paternity confirmation is not documented.

**Expected behavior**:

- Confirm phenotype consistency.
- Award points from the unconfirmed-parental-relationships column.
- Apply `PM6` at the strength corresponding to the total points.
- Follow VCEP rules if they define a different strength.

---

## Example 4: Multiple Independent Occurrences

**Scenario**: One confirmed de novo proband with a highly specific phenotype and two unrelated unconfirmed de novo probands with the same highly specific phenotype.

**Expected behavior**:

- Award 2 + 1 + 1 = 4 points.
- Apply `PS2_VeryStrong`, because at least one contributing occurrence has confirmed parental relationships and the total reaches 4.

---

## Example 5: One Parent Tested

**Scenario**: Only the mother was tested and is negative; the father was not tested.

**Expected behavior**:

- Award 0 points under SVI v1.1 unless a VCEP explicitly allows partial parental testing.
- Ask for the missing parent genotype and parentage information.

---

## Example 6: No Phenotype Provided

**Scenario**: The variant is reported as de novo, but no phenotype is supplied.

**Expected behavior**:

- Do not apply PS2/PM6 until phenotype consistency can be evaluated.
- Ask for proband phenotype or HPO terms, suspected disease, and age at onset.

---

## Example 7: Literature Figure or Pedigree

**Scenario**: A paper figure shows trio Sanger traces or a pedigree, but the text is ambiguous.

**Expected behavior**:

- Use `tooluniverse-literature-deep-research` to retrieve and interpret the article, tables, and supplemental context.
- Use `tooluniverse-literature-figure-evidence-extraction` to extract proband and parental genotypes.
- Record whether parental relationships were confirmed or only parental absence was shown.
- Assign PS2/PM6 points only if the extracted evidence is sufficient.

---

## Example 8: Autosomal Recessive Disease Without Second Allele

**Scenario**: A de novo occurrence is reported in a gene associated with an autosomal recessive condition, but no second pathogenic or likely pathogenic variant is identified.

**Expected behavior**:

- Score the de novo occurrence normally.
- Decrease the final evidence strength by one level.

---

## Minimal Missing-Information Prompt

```markdown
PS2/PM6 cannot be assessed from the provided information.

Please provide:
- Proband phenotype or HPO terms and suspected disease.
- Mother genotype for the variant.
- Father genotype for the variant.
- Whether maternity and paternity were confirmed.
- Testing method and sample type for the proband and parents.
- Whether parental mosaicism was assessed or suspected.
- Whether there are additional unrelated de novo observations and whether any are duplicate reports.
```

---

## Minimal Report Block

```markdown
De novo evidence refinement:
- Proband phenotype: [summary / not provided]
- Phenotype specificity category: [highly specific / consistent not specific / high heterogeneity / not consistent]
- Mother genotype: [result]
- Father genotype: [result]
- Parentage confirmation: [confirmed / not confirmed / not documented]
- Points: [per occurrence and total]
- SVI threshold: [Supporting / Moderate / Strong / Very Strong / none]
- Applied evidence: [PS2 / PM6 / none]
- Status: [applied / not_applicable / not_assessed]
- Reason: [point total and parentage basis / de novo information required]
- Follow-up request: [targeted missing fields]
```
