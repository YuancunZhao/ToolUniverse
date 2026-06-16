# Quick Start: PS4 Case-Enrichment Refinement

Use this overlay when affected-case enrichment, case-control evidence, or rare-disease affected-case counts may support PS4.

---

## Example 1: One Rare-Disease Case

**Scenario**: One unrelated affected proband has a rare and specific phenotype, the same variant is absent from adequately represented gnomAD data, and the evidence is not better captured by PM3, de novo, or segregation criteria.

**Expected behavior**:

- Apply `PS4_Supporting`.
- Record phenotype specificity, unrelatedness, population-control source, and duplicate-report check.

---

## Example 2: Two or More Unrelated Affected Cases

**Scenario**: At least two unrelated affected individuals have a rare and specific phenotype and the variant is absent from population controls.

**Expected behavior**:

- Apply `PS4_Moderate` by ACGS rare-disease practice guidance unless a VCEP specifies a different case-count rule.
- Confirm cases are not duplicate reports.

---

## Example 3: Recessive Biallelic Cases

**Scenario**: Affected individuals have the assessed variant in trans or phase unknown with another rare P/LP allele.

**Expected behavior**:

- Route to `tooluniverse-acmg-pm3-in-trans-refinement`.
- Do not count the same biallelic observations as PS4.

---

## Example 4: Case-Control Evidence With Ancestry Mismatch

**Scenario**: A case-control study reports enrichment, but controls are poorly ancestry matched or gnomAD ancestry representation is weak.

**Expected behavior**:

- Do not apply PS4 at full strength.
- Report `applied_evidence: none` with `status: not_assessed`, or downgrade only if a VCEP/local rule supports it.
- Ask for ancestry-matched control data if needed.

---

## Minimal Report Block

```markdown
PS4 case-enrichment refinement:
- Evidence type: [case-control / rare-disease case count]
- Affected unrelated carriers: [count]
- Phenotype specificity: [rare and specific / broad / not supplied]
- Control source and ancestry match: [summary]
- Population frequency: [AF/AC/AN]
- Duplicate-report status: [summary]
- Applied evidence: [PS4 / PS4_Moderate / PS4_Supporting / none]
- Status: [applied / not_applicable / not_assessed]
- Reason: [case-enrichment basis / duplicate or unrelatedness concern / missing literature or cohort fields]
```
