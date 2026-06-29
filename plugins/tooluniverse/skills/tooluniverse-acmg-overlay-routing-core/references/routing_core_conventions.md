# ACMG Overlay Routing Core Conventions

This reference defines shared conventions for ToolUniverse ACMG overlay documentation.

## Routing Order

1. Variant normalization.
2. Multiple-disorder context when the gene has more than one disease association, inheritance model, dosage state, phenotype spectrum, or mechanism.
3. Mechanism context when LoF, haploinsufficiency, gain-of-function, dominant-negative, antimorphic, recessive LoF, altered-product, or mixed mechanism changes evidence assignment.
4. Clinical context intake when phenotype, affected status, unaffected status, family data, de novo data, phase, healthy-carrier context, or alternate diagnosis is required.
5. Source and literature extraction when evidence comes from secondary assertions, papers, tables, supplements, pedigrees, or figures.
6. Evidence-specific overlay.

## Status Values

| Status | Use |
| --- | --- |
| `applied` | Evidence code or strength assigned. |
| `no_evidence` | Evidence reviewed but criterion not met. |
| `not_assessed` | Missing required information. |
| `not_applicable` | Wrong variant class, disease context, or mechanism. |
| `not_used` | Context or source recorded but intentionally not counted. |

## Strength Values

Canonical strength names are `Supporting`, `Moderate`, `Strong`, and `VeryStrong`.

Keep existing display labels where clinically recognizable, such as `PVS1_N/A`, but prefer structured status fields for machine-readable output.

## Evidence Consumption

Whenever an evidence item could support more than one criterion, record the criterion that consumes it. Mark the overlapping criterion as `not_used` or `no_evidence` with a reason.

Common examples:

- BA1 excludes PM2 and BS1 for the same disease context when BA1 is valid.
- RNA evidence used for `PVS1_Strength (RNA)` or `BP7_Strong (RNA)` should not also be PS3/BS3 or PP3/BP4 for the same splicing effect.
- PP1 and PP4 locus evidence is capped together under ClinGen combined guidance.
- Recessive biallelic probands with phase/genotype evidence usually route to PM3 rather than PS4.
- PP5/BP6 source assertions are not counted when the underlying primary evidence can be reviewed directly.
