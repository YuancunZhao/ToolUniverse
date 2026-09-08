# SVI Reference — Applying the 28 ACMG/AMP Criteria

Companion to `SKILL.md`. For each criterion: the facts you must hold before
marking it `met`, when it applies, how strengths adjust, what excludes it or
forbids double counting, and the governing source.

**Precedence:** an applicable Released CSpec/VCEP specification overrides this
file for that gene. Where no generic rule exists, this file says so — never
invent a threshold to fill the gap; leave the criterion at `not_assessed` /
`needs_review` or carry a blocking issue.

**Sources & versions** (as indexed by the ClinGen variant-classification
guidance page, checked 2026-09): Richards et al. 2015 (ACMG/AMP original);
Tavtigian et al. 2020 (point system; points: Supporting ±1, Moderate ±2,
Strong ±4, VeryStrong ±8; thresholds ≥10 P / 6–9 LP / 0–5 VUS / −6..−1 LB /
≤−7 B); ClinGen SVI working-group recommendations per criterion below.
Per-gene specifications carry their own version — record the CSpec id and
version in `rule_context` and in each `rule_refs` entry.

## Status semantics (record precisely)

| Status | Meaning |
|---|---|
| `met` | Evidence affirmatively satisfies the criterion at the recorded strength |
| `not_met` | Examined; does not satisfy |
| `not_assessed` | Not evaluated (data absent, out of scope, no time) — say why |
| `not_applicable` | Cannot apply to this variant/gene (mechanism, variant type, or specification says so) |
| `needs_review` | Evidence exists but unresolved (phase, validation, conflict) |
| `deprecated` | Retired code (PP5, BP6) — recorded, never scored |

Unknown ≠ not evaluated ≠ not applicable ≠ not met. Only `met` scores.

## Cross-cutting rules

- **One fact, one code.** Every scoring fact gets a stable `evidence_ids`
  entry. The same fact under two codes → the calculator pauses with
  `duplicate_scoring_facts`. Different facts from one paper are fine.
- **Direction conflict.** Positive and negative points sum (Tavtigian 2020);
  BA1 vs any pathogenic `met` → pause, not arithmetic.
- **Strength modifiers must be rule-backed.** Upgrade/downgrade only per SVI
  guidance or the applicable specification, citing the rule in `rule_refs`.
- **Default strengths** — PVS1 VeryStrong; PS*/BS* Strong; PM* Moderate;
  PP*/BP* Supporting; BA1 StandAlone (separate path). Codes may run at
  non-default strengths only with the citations above.

---

## Pathogenic criteria

### PVS1 — null variant in a LoF-mechanism gene (VeryStrong default)
- **Facts required:** (1) variant type predicted loss-of-function (nonsense,
  frameshift, canonical ±1/±2 splice, start-loss, single/multi-exon deletion);
  (2) LoF is an established disease mechanism for the gene (ClinGen dosage
  sensitivity / validity curations, gnomAD LOEUF/pLI, literature); (3) the
  clinically relevant transcript(s) (MANE Select/Plus Clinical; VCEP-defined
  isoform) — consequence must be established on the transcript used;
  (4) NMD expectation (last exon or last ~50 bp of penultimate exon → NMD
  escape); (5) known rescue/alternative transcripts or exon-skipping that
  preserves the reading frame.
- **Apply when** all of: LoF established, variant LoF on the clinical
  transcript, NMD expected → **PVS1 (VeryStrong)**.
- **Strength adjustments** (SVI PVS1 decision tree, v1.1 2019/2020 update):
  NMD escape → **Strong**; exon skipping/in-frame rescue transcript possible
  or role in minor transcript → **Moderate/Supporting** per the tree;
  start-loss and splice-region variants follow the tree's dedicated branches.
- **Exclusions:** LoF not a disease mechanism (dominant-negative genes,
  haploinsufficiency not established) → `not_applicable` (e.g., MYOC CSpec
  marks PVS1 not applicable at all strengths); variant in a transcript
  without clinical relevance → do not apply. **Never assign PVS1 before the
  LoF mechanism itself is established** — without mechanism evidence the
  criterion is `not_met`/`needs_review`, not PVS1 at reduced strength.
- **Double counting:** a frameshift also changing protein length is covered
  by PVS1 when LoF holds — do not also take PM4 for the same fact.
- **Source:** ClinGen SVI PVS1 decision tree (2019; 2020 update); gene
  specifications override.

### PS1 — same amino-acid change as an established pathogenic variant (Strong)
- **Facts:** reference variant with the same protein change (different
  nucleotide), its pathogenicity established (expert panel / equivalent), same
  transcript and residue, protein-level (not merely predicted) identity.
- **Adjustments:** downgrades per specification; methionine-residue and
  start-codon situations follow the SVI PS1/PM5 comparison rules.
- **Exclusions:** reference variant VUS/LB/B → PS1 does not apply (consider
  nothing — do not score it); nucleotide-level identity is not required, but
  protein-level identity is.
- **Double counting:** PS1 (same AA change) and PM5 (different AA, same
  residue) are different facts and may coexist; do not count the same
  reference variant twice within one code.
- **Source:** ClinGen SVI PS1/PM5 comparison requirements (2020).

### PS2 / PM6 — de novo (Strong by SVI counting)
- **Facts:** confirmed de novo observation(s) in a proband with a consistent,
  highly specific phenotype; parentage confirmed by testing (PS2) vs
  documented-but-unconfirmed (PM6).
- **SVI counting (de novo specifications, 2020)** — replaces fixed strengths:
  1 de novo (parentage confirmed, phenotype consistent & specific) →
  **Moderate**; 2 de novos (≥1 confirmed) → **Strong**; ≥3 → **VeryStrong**.
  Without confirmed parentage the observation supports at most **Supporting**;
  inconsistent or non-specific phenotype → do not apply.
- **Record:** count, confirmation status, phenotype specificity in
  `evidence_ids`/`rationale`; insufficient family information → `needs_review`
  with the gap stated (never assume de novo from a single affected child).
- **Source:** ClinGen SVI PS2/PM6 de novo specifications (2020).

### PS3 — functional evidence for pathogenicity (Strong default)
- **Facts:** a functional assay result showing damaging effect; assay
  validation status against known pathogenic AND benign controls.
- **Apply when** the assay is validated per the SVI functional framework for
  this gene (both control classes, adequate replication) → **Strong**.
  Partially validated (limited controls) → **Moderate/Supporting** by
  validation category. A single unvalidated biochemical study → at most
  **Supporting**. No generic upgrade to VeryStrong without a specification.
- **Exclusions:** assays without benign controls cannot separate
  hypomorphs from pathogenic effects; epidemiological contradictions take
  precedence and must be documented, not averaged away.
- **Double counting:** one assay → one code (PS3 or its contribution to a
  domain/hotspot claim), never both PS3 and PM1 from the same assay fact.
- **Source:** ClinGen SVI functional evidence specifications for PS3/BS3
  (2023); gene specifications list validated assays.

### PS4 — case–control enrichment (Strong default)
- **Facts:** allele frequency in cases vs matched controls with statistical
  significance and adequate power/effect size; study quality.
- **Adjustments:** per SVI PS4 (2018) the strength follows the evidence
  strength of association; very large effect sizes in well-powered studies
  may support **VeryStrong**, weak/small studies are downgraded — do not fix
  a threshold without the specification.
- **Exclusions:** population stratification, ascertainment bias; conflicting
  case-control studies → `needs_review`.
- **Source:** ClinGen SVI PS4 recommendations (2018).

### PM1 — hotspot / critical functional domain (Moderate default)
- **Facts:** variant lies in a VCEP-specified critical region or a
  well-defined functional domain with significant depletion of benign
  missense variation (domain architecture from UniProt/InterPro; gnomAD
  regional constraint).
- **Apply when** the region is defined by specification or by domain-level
  benign depletion; somatic hotspot data may support PM1 in cancer-gene
  contexts per the specification.
- **No generic threshold exists.** Without a specification-defined region or
  quantified depletion, PM1 is `not_met`, not a weaker PM1.
- **Double counting:** the same domain fact used with PM1 must not also
  carry PP2 (missense enrichment) — one fact, one code.
- **Source:** ClinGen SVI PM1 specifications (2021).

### PM2 — absent / extremely rare (Supporting by SVI default)
- **Facts:** gnomAD (and matching ancestry) frequency with callability —
  coverage at the locus, quality; homozygote/hi-quality counts.
- **Apply at Supporting by default** (ClinGen SVI 2020): PM2_Supporting.
  Higher strengths only if a specification states them. Absence must be
  supported by adequate coverage — absent call ≠ absent allele.
- **Disease-aware frequency:** the disease's maximum credible frequency
  (see BS1) governs BA1/BS1/BS2 decisions, not a flat 0.0001; PM2 is about
  absence/rarity, BA1/BS1 about excess.
- **Exclusions:** BA1 or BS1 met → do not also record PM2 as met (conflict;
  resolve first). Recessive genes: ultra-low frequency still applies per
  original caveat.
- **Source:** ClinGen SVI PM2_Supporting recommendation (2020).

### PM3 — in trans with a pathogenic variant, recessive (Moderate default)
- **Facts:** proband observations with the variant in trans with an
  established pathogenic allele; phase evidence per observation (confirmed by
  family/typing vs inferred).
- **SVI counting (PM3 specifications, 2021):** 1 phase-confirmed observation
  → **Supporting**; 2 → **Moderate**; 3–4 → **Strong**; ≥5 → **VeryStrong**.
  Phase-unconfirmed observations carry reduced weight (fractional counting
  per the specification); consult it rather than guessing.
- **Insufficient phase evidence** → `needs_review` with the gap; never count
  an unphased homozygous-compound assumption as confirmed.
- **Source:** ClinGen SVI PM3 specifications (2021).

### PM4 — protein-length change in a non-repeat region (Moderate default)
- **Facts:** variant changes protein length (frameshift in non-repeat,
  in-frame indel, exon-level deletion) outside a recognized repeat/low-
  complexity region, and LoF is NOT the gene's mechanism (else PVS1 governs).
- **Adjustments/downgrades** per specification; repeats defined by
  UniProt/InterPro annotations.
- **Double counting:** with PVS1 met, PM4 is redundant for the same fact.
- **Source:** ACMG/AMP 2015 with SVI澄清; specification-defined region lists
  where present.

### PM5 — different pathogenic missense at the same residue (Moderate default)
- **Facts:** a different amino-acid change at the same residue is
  established pathogenic (protein-level identity on the same transcript);
  reference variant's classification verified current.
- **Exclusions:** reference variant VUS or conflicting → do not apply;
  predicted (not established) pathogenicity never counts.
- **Source:** ClinGen SVI PS1/PM5 comparison requirements (2020).

### PP1 — co-segregation (Supporting default)
- **Facts:** informative meioses count (phase + affection status known),
  phenocopy handling, family structure.
- **SVI segregation counting (2022):** ≥2 informative meioses →
  **Supporting**; 3–4 → **Moderate**; 5–6 → **Strong**; ≥7 →
  **VeryStrong**; LOD-score alternatives per the specification. Phenocopies
  and reduced penetrance reduce the count.
- **Insufficient segregation data** → `not_assessed`/`needs_review`, never a
  hand-waved PP1.
- **Source:** ClinGen SVI segregation analysis recommendations (2022).

### PP2 — missense-enrichment gene (Supporting default)
- **Facts:** missense is the established disease mechanism AND the gene has
  a significantly depleted benign missense rate (gnomAD missense z-score
  > 3.09 is the common convention; VCEP definitions override).
- **Exclusions:** mutually exclusive with BP1; LoF-only genes → PP2
  `not_applicable`.
- **Source:** ACMG/AMP 2015; gnomAD constraint (Karczewski et al.);
  specification override.

### PP3 — computational evidence for pathogenicity (Supporting)
- **Apply from a single calibrated predictor meeting its pre-set threshold**
  (ClinGen SVI in-silico calibration, Pejaver et al. 2022): e.g., REVEL
  ≥ 0.7 for missense; the calibration table gives predictor-specific cutoffs
  per variant class.
- **No majority voting.** Concordance across uncalibrated predictors is not
  PP3; discordant calibrated predictors → neither PP3 nor BP4.
- **Exclusions:** synonymous (see BP7), canonical splice (PVS1 path).
- **Source:** ClinGen SVI in-silico predictor calibration (2022).

### PP4 — phenotype specificity (Supporting default)
- **Facts:** the proband's phenotype is highly specific for the gene's
  disease (and inheritance consistent), gene-disease validity established.
- **Adjustments:** specifications may upgrade with additional family
  history/segregation; without specificity evidence PP4 is `not_met`.
- **Exclusions:** non-specific phenotype, phenocopies, competing diagnoses.
- **Source:** ClinGen SVI PP4 guidance (2021); specifications override.

### PP5 — RETIRED, do not apply
- ClinGen SVI recommended discontinuing PP5/BP6 (2020). Status must be
  `deprecated` in the 28-record review; a ClinVar/lab "Pathogenic" label is
  an external conclusion — attribute it separately in the report, it never
  scores. **A ClinVar label alone must not produce PP5/BP6.**

---

## Benign criteria

### BA1 — allele frequency > 5% (StandAlone)
- **Facts:** allele frequency above 5% in a large general-population dataset
  (gnomAD, ancestry-specific maximum), data quality at the locus.
- **Apply:** stand-alone **Benign** — the calculator runs BA1 on its own path
  (total score null); BA1 met together with any pathogenic `met` pauses
  classification for conflict resolution.
- **Exceptions:** the ClinGen SVI curates a BA1 exception list (disease/
  variant contexts where >5% does not stand alone) and specifications may
  define their own — consult the current list before applying; exceptions
  are enumerated there, not invented here.
- **Source:** ACMG/AMP 2015; ClinGen SVI BA1 exceptions list (2023 revision).

### BS1 — frequency above the disease's maximum credible frequency (Strong)
- **Facts:** disease prevalence, inheritance model, penetrance, allelic/
  locus contributions → maximum credible frequency (Whiffin et al. 2017
  framework); the variant's ancestry-specific AF vs that bound.
- **No universal cutoff:** high-penetrance genes tolerate far lower AFs than
  moderate/low-penetrance ones. Comparing against the highest AF of any
  known pathogenic variant in the gene is a useful cross-check.
- **Exclusions:** if BA1 already met, BS1 from the same AF fact is redundant.
- **Source:** Whiffin et al. 2017 (max credible frequency); specifications
  often fix numeric bounds — use theirs.

### BS2 — observed in healthy individuals (Strong)
- **Facts:** genotyped healthy individuals where full penetrance would
  exclude the genotype (e.g., healthy homozygotes for a recessive disease,
  healthy heterozygotes for a dominant high-penetrance disease), with
  age-of-onset context.
- **Caveats:** late-onset, reduced penetrance, and phenocopies weaken the
  argument; specifications define "healthy" thresholds (age, exam) —
  otherwise record `needs_review`.
- **Source:** ACMG/AMP 2015; specification-defined criteria where present.

### BS3 — functional evidence against pathogenicity (Strong default)
- Same validation framework as PS3 (SVI functional specifications, 2023):
  requires benign AND pathogenic controls; downgrades by validation
  category. One assay produces either PS3 or BS3, never both.

### BS4 — lack of segregation (Strong)
- **Facts:** affected non-carriers in a family where the disease segregates
  (informative meioses documented), phenocopy/penetrance assessed.
- **Caveats:** requires genuinely informative families; misspecified
  affection status voids it. Insufficient pedigree → `not_assessed`.
- **Source:** ACMG/AMP 2015; SVI segregation counting applies (2022).

### BP1 — missense in a LoF-only gene (Supporting)
- Mirror of PP2; mutually exclusive with it. Facts: gene where only
  truncating variants cause disease; variant is missense.

### BP2 — observed in cis with a pathogenic variant, or in trans without disease (Supporting)
- **Facts:** phase (cis/trans) established by family/molecular data.
- **Unknown phase → `needs_review` with the gap recorded**; never assume
  phase from co-occurrence alone.

### BP3 — in-frame indel in a repeat region (Supporting)
- Mirror of PM4; repeat region per UniProt/InterPro. If the gene mechanism
  makes indels pathogenic (specification), BP3 may be `not_applicable`.

### BP5 — alternate molecular diagnosis in the proband (Supporting)
- Apply only when the alternative diagnosis is molecularly confirmed;
  an unconfirmed alternative diagnosis does not support BP5. Use with
  caution in genes with variable expressivity.
- **Source:** ClinGen SVI BP5 caution (2018 statement).

### BP6 — RETIRED, do not apply
- See PP5. ClinVar "Benign" consensus labels are attributed externally,
  never scored.

### BP7 — synonymous with no splice impact (Supporting)
- **Facts:** synonymous variant AND no predicted splice effect from a
  calibrated predictor (SpliceAI < 0.1 is the common default;
  specifications may set their own).
- **Exclusions:** borderline predictor output → `needs_review`; variants
  near exon boundaries or in genes with known cryptic-splice mechanism
  follow the specification.

---

## Quick tables

**Default strengths → points (Tavtigian 2020)**

| Family | Default | Points |
|---|---|---|
| PVS1 | VeryStrong | +8 |
| PS1–PS4 | Strong | +4 |
| PM1–PM6 | Moderate | +2 |
| PP1–PP4 | Supporting | +1 |
| PP5 | deprecated | 0 (never scored) |
| BA1 | StandAlone | separate path (Benign; total null) |
| BS1–BS4 | Strong | −4 |
| BP1–BP5, BP7 | Supporting | −1 |
| BP6 | deprecated | 0 (never scored) |

Strength modifiers shift a code along ±1/±2/±4/±8; BA1 never converts.

**Common shared-fact pairs (one code per fact)**

| Facts | Correct handling |
|---|---|
| One functional assay | PS3 xor BS3 (not both, not also PM1) |
| One domain/hotspot claim | PM1 xor PP2 contribution |
| One AF dataset | BA1 / BS1 / PM2 pick the code the fact supports; conflicting codes → resolve before scoring |
| One segregation dataset | PP1 xor BS4 |
| One reference pathogenic variant | PS1 (same AA) and PM5 (same residue, different AA) are distinct facts and may both stand |
| LoF frameshift in non-repeat region | PVS1 (LoF mechanism) xor PM4 (LoF not mechanism) |
