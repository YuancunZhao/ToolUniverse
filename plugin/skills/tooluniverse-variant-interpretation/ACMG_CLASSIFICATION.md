# ACMG Classification — Navigation

This file no longer maintains a second copy of the algorithm, evidence
thresholds, or classification-confidence tables. Germline small-variant
classification has exactly one pipeline and one reference set:

1. **Unified workflow** — the `tooluniverse-acmg-variant-classification`
   skill's `SKILL.md`: variant/scope confirmation, CSpec candidate
   adjudication, fact collection, 28-criterion evaluation, calculator
   call, and result reporting.
2. **Per-criterion rules** — the same skill's `SVI_REFERENCE.md`: the 28
   codes with facts, applicability, strength adjustments, exclusions, and
   sources (including the calibrated PP3/BP4 thresholds and the PVS1
   decision tree).
3. **Tool material for evidence collection** — this skill's
   `TOOLS_REFERENCE.md`, `CODE_PATTERNS.md`, and `EXAMPLES.md`: raw
   scores, provider labels, query patterns, and worked collection
   examples. None of them assigns ACMG codes, strengths, or a final
   classification.

The deterministic combination itself is performed only by the
`ACMG_calculate_classification` calculator via the unified skill.
