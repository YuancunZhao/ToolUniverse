---
name: tooluniverse-acmg-overlay-routing-core
description: Shared routing and reporting core for ToolUniverse ACMG/AMP overlay skills. Use before evidence-specific overlays to standardize disease context, mechanism context, phenotype/source/literature intake, double-counting guards, output status values, and evidence-strength labels without changing criterion-specific rules.
disable-model-invocation: true
---

# ACMG Overlay Routing Core

This skill is a lightweight coordination layer for ToolUniverse ACMG/AMP overlay skills. It does not assign ACMG evidence by itself and does not change any criterion threshold, strength adjustment, or VCEP rule.

Use it to decide which context overlays must run before evidence-specific overlays, to keep output labels consistent, and to avoid circular or duplicated evidence use.

---

## Routing Order

Apply this order before assigning final evidence codes:

1. **Variant normalization**
   - Normalize HGVS, transcript, consequence, genome build, and zygosity.
   - Use the base `tooluniverse-acmg-variant-classification` workflow and ToolUniverse variant annotation tools.

2. **Disease-entity boundary**
   - If the gene has multiple associated disorders, inheritance models, dosage states, phenotype spectra, or mechanisms, use `tooluniverse-acmg-multiple-disorder-context-refinement`.
   - This determines whether evidence can be aggregated or must be split by disease, inheritance, mechanism, or variant class.

3. **Mechanism boundary**
   - If LoF/haploinsufficiency, gain-of-function, dominant-negative, antimorphic, recessive LoF, altered-product, or mixed mechanism could change evidence use, use `tooluniverse-acmg-dominant-negative-mechanism-refinement`.
   - This step routes mechanism-sensitive criteria such as PVS1, PS1/PM5, PS3/BS3, PM1/PP2/BP1/PP3, PM4/BP3, PS4, PP1/BS4, PM3, and PS2/PM6.

4. **Clinical context intake**
   - If phenotype, affected/unaffected status, disease specificity, diagnostic yield, phase, family data, de novo data, alternate diagnosis, or healthy-carrier context is required, use `tooluniverse-acmg-phenotype-dependent-evidence-refinement`.
   - Use criterion-specific overlays for scoring after the required clinical fields are collected.

5. **Source and literature intake**
   - Use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` when a secondary assertion is being considered.
   - Use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when primary evidence is embedded in papers, tables, supplements, pedigrees, traces, gels, blots, RT-PCR/minigene panels, or assay figures.

6. **Evidence-specific overlay**
   - Apply the relevant ACMG overlay for the criterion being assessed.
   - VCEP or current disease-specific specifications override generic overlay guidance.

---

## Canonical Status Values

Use these status values in reports and structured summaries:

| Status | Meaning |
| --- | --- |
| `applied` | A criterion or strength was assigned. |
| `no_evidence` | The criterion was considered but available evidence does not support applying it. |
| `not_assessed` | Required information is missing or unavailable. Ask for targeted fields when user-provided clinical data are needed. |
| `not_applicable` | The criterion does not apply to the variant class, disease mechanism, or disease context. |
| `not_used` | Evidence is recorded as a lead or context but is intentionally not counted. |

Do not use free-text variants such as "not assessable" or "not assessed" as the only status in structured output. Put the free-text explanation in `reason`.

---

## Canonical Output Fields

Each overlay should be able to report this minimal block:

```markdown
ACMG overlay result:
- overlay: [skill name]
- criterion: [ACMG code or context gate]
- applied_evidence: [evidence label or none]
- status: [applied / no_evidence / not_assessed / not_applicable / not_used]
- reason: [short evidence-specific rationale]
- consumed_evidence: [data sources or evidence already used]
- routed_to: [next overlay if applicable]
```

Evidence-specific overlays may add fields needed for their criterion, such as points, OddsPath, phase status, assay validity, transcript consequence, or case-count details.

---

## Strength Labels

Use these strength terms in evidence labels:

- `Supporting`
- `Moderate`
- `Strong`
- `VeryStrong`

Examples:

- `PM2_Supporting`
- `PS2_VeryStrong`
- `PM3_Strong`
- `BP4_Moderate`

Do not introduce underscore-separated variants of very-strong strength names. For backward-compatible display text, keep established labels such as `PVS1_N/A` in narrative output, but represent them structurally as `status: not_applicable` when possible.

---

## Boundary Rules

- **BA1 and benign context**: BA1 exception-list review is the BA1 stand-alone gate. If BA1 is valid, do not use PM2 or BS1 for the same disease context. If BA1 is blocked but frequency remains too high, route to benign-context BS1 review.
- **Phenotype and PP1/BS4/PP4**: phenotype-dependent refinement collects clinical context. PP1 segregation refinement performs PP1/BS4/PP4 combined scoring, diagnostic-yield conversion, evidence apportionment, and the +5.0 cap.
- **PVS1 and splicing**: baseline PVS1 uses `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`. RNA/Walker evidence uses `tooluniverse-acmg-pvs1-splicing-refinement` after the baseline branch is identified.
- **PS1-splicing**: `tooluniverse-acmg-ps1-splicing-similarity-refinement` is comparison-variant evidence, not direct PVS1 evidence.
- **PP5/BP6**: reputable-source assertions are source leads by default. Do not count PP5/BP6 unless a current VCEP or explicitly approved local legacy policy requires it.
- **Double counting**: if the same primary evidence supports multiple possible criteria, choose the criterion-specific path and record the other criteria as `not_used` or `no_evidence` with a reason.

---

## Common Routing Map

| Situation | Route |
| --- | --- |
| Multiple gene-associated disorders or mechanisms | Multiple-disorder context, then mechanism overlay if needed. |
| Possible dominant-negative or altered-product mechanism | Mechanism overlay before evidence-specific criteria. |
| Missing phenotype, family, de novo, phase, healthy-carrier, or alternate-diagnosis context | Phenotype-dependent intake before criterion scoring. |
| Secondary source assertion only | PP5/BP6 source refinement, then retrieve primary evidence. |
| Literature evidence in figures or supplements | Literature deep research plus figure evidence extraction. |
| Baseline LoF PVS1 | PVS1 LoF decision-tree overlay. |
| RNA/splicing PVS1 or BP7 | PVS1 splicing overlay after baseline context. |
| Same predicted splicing event as known P/LP variant | PS1-splicing overlay, keeping evidence independent from direct RNA evidence. |

---

## Limitations

- This routing core does not replace any evidence-specific overlay.
- It does not decide final pathogenicity.
- It should not be used to override current VCEP specifications.
- It is intentionally documentation-only and creates no new ToolUniverse MCP tool.
