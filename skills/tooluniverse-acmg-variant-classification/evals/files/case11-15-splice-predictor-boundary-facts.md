# Synthetic splice/predictor boundary facts (cases 11–15)

All scenarios below are synthetic fixtures. Fixed identifiers:
gene = `TESTGENE2`, disease = `Synthetic splice-fixture disease`,
inheritance = autosomal dominant. TESTGENE2 is fictitious; do not query
any database for it.

A synthetic rule search has already been completed and its conclusions
are to be taken as verified inputs: no applicable Released CSpec exists,
no specification candidates are awaiting adjudication, and the generic
rule materials are complete (cspec_lookup_status = no_released_spec,
specification = null, applicable_rules_complete = true).

Five independent fact blocks follow. Each evaluation uses exactly one
block; never merge facts across blocks.

## Fact block 11 (fixture:11)

- Variant under evaluation: `NM_999998.1:c.1200+1G>A`, a canonical +1
  splice-donor variant.
- LoF is an established disease mechanism for TESTGENE2 (verified input).
- A completed synthetic RNA-level annotation (verified input) shows the
  variant activates a cryptic donor site within ±20 nt of the canonical
  exon boundary; splicing through the cryptic site keeps the reading
  frame IN FRAME and this is the major transcript.
- The in-frame transcript product deletes 80 amino acids (16% of the
  500-amino-acid protein), and the deleted segment lies inside the
  gene's critical functional region, whose role is established by
  independent experiments.
- No evidence of preserved protein function exists; no rescue transcript
  has been observed.
- No evidence beyond these facts is provided.

## Fact block 12 (fixture:12)

- Variant under evaluation: `NM_999998.1:c.1200+2A>G`, a canonical +2
  splice variant in the same synthetic setting as block 11.
- A completed synthetic RNA study (verified input) demonstrates
  established functional rescue at this site: splicing is fully
  reconstituted, the transcript is indistinguishable from wild type, no
  aberrant splice product is detected, and protein function is
  preserved.
- LoF is an established disease mechanism for TESTGENE2.
- No evidence beyond these facts is provided.

## Fact block 13 (fixture:13)

- Variant under evaluation: `NM_999998.1:c.1000C>T` (missense) in the
  same synthetic setting.
- BayesDel without-MAF (noAF model) was preselected, before seeing this
  variant's result, as the single scoring predictor; version and
  calibration are compatible with Pejaver et al. 2022 (noAF model).
- The collected annotation record contains BOTH BayesDel outputs
  (synthetic MyVariant dbNSFP-style fields):
  `dbnsfp.bayesdel.no_af.score = 0.60`;
  `dbnsfp.bayesdel.add_af.score = 0.10`.
- No domain evidence, no RNA evidence, and no known applicability or
  data-quality problems exist for this variant.

## Fact block 14 (fixture:14)

- Variant under evaluation: `NM_999998.1:c.1000C>T`, predicted
  consequence p.Arg334Gln.
- A reference variant `NM_999998.1:c.1001G>A` (different nucleotide
  change, same transcript and residue), also predicted p.Arg334Gln, is
  classified Pathogenic by an expert panel (verified current).
- Verified mechanism annotation for the REFERENCE variant: its
  pathogenicity operates through aberrant SPLICING — it activates a
  cryptic acceptor site confirmed by RNA studies; the amino-acid
  annotation alone is not the established disease mechanism.
- The variant under evaluation has been checked for splicing impact
  (synthetic RNA context and splice screen, verified input): no splice
  effect is detected; its consequence is the plain missense change.
- No other evidence is provided.

## Fact block 15 (fixture:15)

- Variant under evaluation: `NM_999998.1:c.1001G>T`, predicted
  consequence p.Arg334Leu (same residue as block 14, different
  amino-acid change).
- A reference variant at the same residue predicted p.Arg334Gln is
  classified Pathogenic by an expert panel (verified current).
- Verified mechanism annotation for the REFERENCE variant:
  pathogenic through aberrant splicing (cryptic acceptor site,
  RNA-confirmed), as in block 14.
- The variant under evaluation has no corresponding splice effect
  (verified input); its consequence is the plain missense change.
- No other evidence is provided.
