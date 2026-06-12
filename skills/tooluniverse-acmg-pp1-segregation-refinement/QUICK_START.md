# Quick Start: PP1 Segregation Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when family segregation evidence affects PP1 strength or BS4.

The examples below assume that variant identity, gene-disease validity, inheritance, and phenotype fit have already been checked with ToolUniverse tools.

---

## Example 1: Strong Co-Segregation

**Scenario**: A heterozygous variant in an autosomal dominant disease gene is present in eight affected relatives across a large pedigree. There are at least seven informative meioses, no affected non-carriers, and no unexplained unaffected carriers.

**Expected behavior**:

- Apply `PP1_Strong`.
- Report the informative meioses and absence of contradictory segregation.
- Do not count the same relatives again as independent case-level probands.

---

## Example 2: Moderate Co-Segregation

**Scenario**: A variant co-segregates in a family with five or six informative meioses, phenotype fit is strong, and no contradictions are reported.

**Expected behavior**:

- Apply `PP1_Moderate`.
- Record pedigree details and inheritance model.
- State that no gene-specific VCEP threshold was available if using the default threshold.

---

## Example 3: Supporting Co-Segregation

**Scenario**: A variant is present in two to four informative affected relatives, with no contradictory segregation and a plausible gene-disease mechanism.

**Expected behavior**:

- Apply `PP1` at supporting strength.
- Do not upgrade unless more informative meioses, a credible LOD score, or VCEP-specific criteria support stronger evidence.

---

## Example 4: Published LOD Score

**Scenario**: A paper reports a variant-specific LOD score of 3.2 in a disease-consistent pedigree.

**Expected behavior**:

- Apply `PP1_Strong` if the LOD score is credible and variant-specific.
- Record whether the LOD is variant-specific, locus-level, or gene-level.
- If the LOD is only locus-level and multiple candidate variants remain, reduce strength or withhold PP1 for the individual variant.

---

## Example 5: Apparent Non-Segregation

**Scenario**: One affected relative does not carry the variant, but the phenotype is common and the reported diagnosis is not specific.

**Expected behavior**:

- Do not automatically apply BS4.
- Withhold or downgrade PP1 until phenocopy and phenotype-certainty issues are resolved.
- Explain why the affected non-carrier is not definitive non-segregation.

---

## Example 6: Robust Non-Segregation

**Scenario**: Multiple definitely affected relatives do not carry the variant, paternity/sample identity and genotype quality are confirmed, and phenocopy is unlikely.

**Expected behavior**:

- Apply `BS4`.
- Do not apply PP1.
- State why reduced penetrance or phenocopy does not explain the observation.

---

## Example 7: Adult-Onset or Reduced-Penetrance Disease

**Scenario**: Several unaffected variant carriers are young relatives in an adult-onset cancer predisposition syndrome.

**Expected behavior**:

- Do not treat the young unaffected carriers as strong contradiction.
- Reduce or withhold PP1 if the segregation evidence depends on unaffected carriers.
- Prefer case-control or other evidence if the phenotype has high phenocopy risk.

---

## Example 8: Case-Control and Segregation in One Paper

**Scenario**: A paper includes a family pedigree and a case-control cohort, and some family members are also counted in the cohort.

**Expected behavior**:

- Do not double count the same individuals.
- Use the most informative evidence path for each individual.
- Record which individuals or data were excluded from PP1 to avoid double counting.

---

## Minimal Report Block

```markdown
PP1 refinement:
- Gene-disease context: [gene], [disease], [inheritance], [ClinGen/GenCC status]
- Variant: [HGVS], qualifying because [mechanism/consequence/frequency]
- Segregation: [LOD or informative meioses], [affected carriers], [contradictions]
- Modifiers: [penetrance/phenocopy/age/phenotype certainty]
- Double-counting check: [what was excluded or not reused]
- Applied evidence: [PP1 / PP1_Moderate / PP1_Strong / BS4 / No PP1]
```
