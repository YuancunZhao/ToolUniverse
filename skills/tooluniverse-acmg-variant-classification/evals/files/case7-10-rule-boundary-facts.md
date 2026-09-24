# Synthetic rule-boundary facts (cases 7–10)

All scenarios below are synthetic fixtures. Fixed identifiers:
variant = `NM_999999.1:c.1000C>T` (missense), gene = `TESTGENE`,
disease = `Synthetic fixture disease`, inheritance = autosomal dominant.
TESTGENE is fictitious; do not query any database for it.

A synthetic rule search has already been completed and its conclusions
are to be taken as verified inputs: no applicable Released CSpec exists,
no specification candidates are awaiting adjudication, and the generic
rule materials are complete (cspec_lookup_status = no_released_spec,
specification = null, applicable_rules_complete = true).

Three independent fact blocks follow. Each evaluation uses exactly one
block; never merge facts across blocks.

## Fact block A (fixture:A)

- The missense variant lies within residues 300–360, a critical
  functional domain whose role is established by independent experiments
  and studies.
- A completed synthetic review has verified that no benign variation has
  been observed in this region.
- No VCEP exists for this gene; no quantitative domain-depletion
  estimate has been produced; no applicable rule or calibration supports
  a non-default strength for this domain evidence.
- No evidence beyond these domain facts is provided.

## Fact block B (fixture:B)

- A database annotation places residues 300–360 in a protein domain.
- The critical functional significance of this annotated domain has not
  yet been confirmed by experiments or studies.
- No benign-missense-variation distribution material for the region is
  available.
- No VCEP exists; no quantitative domain-depletion estimate; no
  non-default-strength rule or calibration — as in block A.
- No evidence beyond this annotation is provided. These are case-fact
  gaps, not an unread or missing rule file.

## Fact block C (fixture:C)

- Missense prediction is applicable to this variant.
- REVEL was preselected, before seeing this variant's result or any
  other result for it, as the single scoring predictor; its version and
  calibration are compatible with Pejaver et al. 2022.
- Preselected REVEL value for this variant: 0.94.
- An additionally collected, NON-preselected predictor result is also
  present: BayesDel (no-AF version) = -0.40.
- No domain evidence, no RNA or other independent evidence, and no known
  input or applicability problems exist for this variant.
