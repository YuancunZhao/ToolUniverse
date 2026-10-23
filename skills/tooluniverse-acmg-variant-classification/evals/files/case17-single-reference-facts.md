# Synthetic single-reference facts (case 17)

All facts below are a synthetic fixture. Fixed identifiers:
gene = `TESTGENE4`, transcript = `NM_999995.1`,
disease = `Synthetic single-reference disease`,
inheritance = autosomal dominant. TESTGENE4 and NM_999995.1 are
fictitious; do not query any database for them.

A synthetic rule search has already been completed and its conclusions
are to be taken as verified inputs: no applicable Released CSpec exists,
no specification candidates are awaiting adjudication, and the generic
rule materials are complete (cspec_lookup_status = no_released_spec,
specification = null, applicable_rules_complete = true).

## Fact block 17 (fixture:17)

- Reference codon at residue 334 of `NM_999995.1` is `GGA` (Gly),
  spanning `c.1000_1002` (c.1000 G, c.1001 G, c.1002 A).
- Variant under evaluation: `NM_999995.1:c.1000G>A`. The first codon
  base changes G→A, giving `AGA` and the missense consequence
  `p.Gly334Arg` (verified input).
- Sole reference variant: `NM_999995.1:c.1000G>C`. The first codon base
  changes G→C, giving `CGA` and the missense consequence
  `p.Gly334Arg` (verified input). This reference variant's
  pathogenicity is independently established by expert-panel review
  (verified input).
- Neither the variant under evaluation nor the reference variant acts
  through altered splicing (verified input): the established consequence
  of both is the missense change stated above, with no cryptic-site or
  aberrant-splice involvement.
- No other pathogenic variant at residue 334 — in particular none with
  a different amino-acid change — is known for this transcript
  (verified input).
- No domain evidence, no segregation evidence, no population-frequency
  evidence, no functional-study evidence, and no other criterion-level
  evidence is provided beyond these facts.
