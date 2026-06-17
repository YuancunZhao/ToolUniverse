# Quick Start: PM4/BP3 Protein-Length Refinement

Use this overlay for in-frame indels, stop-loss variants, and protein-length changes where PM4 or BP3 may apply.

---

## Example 1: Single Amino-Acid Deletion

**Scenario**: A one-residue in-frame deletion affects a conserved functional region.

**Expected behavior**:

- Apply `PM4_Supporting` by default.
- Apply full `PM4` only when gene-specific, VCEP, or strong functional-region evidence supports it.
- Mark single-amino-acid default downgrading as `practice/local refinement` unless a VCEP adopts it.

---

## Example 2: In-Frame Indel in Nonfunctional Repeat

**Scenario**: An in-frame insertion/deletion lies in a repetitive region with no known function and benign population context.

**Expected behavior**:

- Apply `BP3`.
- Do not also apply PM4.

---

## Example 3: Stop-Loss With Nonstop-Mediated Decay

**Scenario**: A stop-loss variant has no downstream in-frame stop codon in the 3' UTR and nonstop-mediated decay is expected.

**Expected behavior**:

- Route to PVS1.
- Do not apply PM4 for the same consequence.

---

## Example 4: Last-Exon Truncating GOF Variant

**Scenario**: A last-exon frameshift produces an altered product in a gene where GOF or dominant-negative last-exon variants cause disease.

**Expected behavior**:

- Use mechanism refinement first.
- Consider PM4 if the altered product mechanism is supported.
- Do not apply PVS1 unless LoF/haploinsufficiency is established for the exact disease context.

---

## Minimal Report Block

```markdown
PM4/BP3 protein-length refinement:
- Consequence: [in-frame indel / stop-loss / last-exon truncating]
- Region: [functional / repeat no known function / unclear]
- Mechanism: [LoF / GOF / dominant-negative / unclear]
- PVS1 conflict: [none / route to PVS1]
- Applied evidence: [PM4 / PM4_Supporting / BP3 / none]
- Status: [applied / not_applicable / not_assessed]
- Guidance authority: [ACMG/AMP baseline / VCEP-specific / practice/local refinement]
- Reason: [protein-length mechanism / PVS1 route / missing region or mechanism data]
```
