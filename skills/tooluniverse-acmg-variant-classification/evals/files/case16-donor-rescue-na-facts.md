# Synthetic donor-rescue facts (case 16)

All facts below are a synthetic fixture. Fixed identifiers:
gene = `TESTGENE3`, transcript = `NM_999996.1`,
disease = `Synthetic donor-fixture disease`,
inheritance = autosomal dominant. TESTGENE3 and NM_999996.1 are
fictitious; do not query any database for them.

A synthetic rule search has already been completed and its conclusions
are to be taken as verified inputs: no applicable Released CSpec exists,
no specification candidates are awaiting adjudication, and the generic
rule materials are complete (cspec_lookup_status = no_released_spec,
specification = null, applicable_rules_complete = true).

## Fact block 16 (fixture:16)

- Variant under evaluation: `NM_999996.1:c.1200+2T>C`, a canonical +2
  splice-donor variant replacing the donor-dinucleotide T with C,
  producing a GC dinucleotide at the donor position.
- LoF is an established disease mechanism for TESTGENE3 (verified
  input).
- A completed synthetic splice annotation (verified input, obtained
  under the applicable SVI framework's criteria — NOT from any
  variant-specific experiment) predicts that the GC dinucleotide at
  this position serves as a functional donor: splicing proceeds
  GC–AG in frame through the native exon junction, the transcript is
  predicted to be full-length and single-product, and no cryptic or
  aberrant splice product is predicted. The framework's criteria for
  treating such a predicted functional GC donor as preserving the
  gene product are met and sourced.
- No variant-specific RNA study and no variant-specific protein
  experiment has been performed for this variant, and none is pending.
- No domain evidence, no segregation evidence, no population-frequency
  evidence, and no other criterion-level evidence is provided beyond
  these facts.
