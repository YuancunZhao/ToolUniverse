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

Primary SVI documents behind these rules (every numeric table verified
against source text on 2026-09-09 — none from memory):

- **PVS1** — SVI decision tree: Abou Tayoun et al. 2018 (PMC6185798);
  splicing/RNA extensions Walker et al. 2023 (PMC10357475).
- **PS2/PM6** — SVI "Recommendation for de novo Criteria (PS2 & PM6)"
  **v1.1** (approved 2018-03-18, updated 2021-05-05): per-proband points
  2/1/0.5/0.25 by phenotype class × parentage; combined 0.5/1/2/4 →
  Supporting/Moderate/Strong/VeryStrong.
- **PS3/BS3** — Brnich et al., Genome Medicine 2020 (PMC6938631): strength
  from zero by validation (≤10 controls → Supporting; ≥11 → Moderate;
  OddsPath >2.1/>4.3/>18.7/>350 pathogenic ladder; benign capped at
  Strong).
- **PM2** — SVI PM2 recommendation **v1.0** (approved 2020-09-04): apply at
  Supporting (PM2_Supporting).
- **PM3** — SVI PM3 recommendation v1.0 (Oza et al. 2018, Table 6a):
  per-proband 1.0/0.5/0.25/0 by phase × other-variant class; combined
  0.5/1/2/4 → Supporting/Moderate/Strong/VeryStrong.
- **PP1/BS4/PP4** — Biesecker et al., AJHG 2023 (PMC10806742): co-segregation
  points per individual by inheritance model; PP4 diagnostic-yield points;
  locus evidence (PP1+PP4) capped at +5.0 (enforced by the calculator);
  BS4 non-segregation = −4.0 (AD / AR-homozygous / X-linked).
- **PP3/BP4** — Pejaver et al., AJHG 2022 (PMC9748256): one pre-specified
  calibrated tool; exact intervals in the PP3 entry; PP3+PM1 summed
  strength ≤ Strong (enforced by the calculator); splicing thresholds from
  Walker et al. 2023 (SpliceAI ≥0.2 / ≤0.1).
- **PP5/BP6** — Biesecker & Harrison, Genet Med 2018 (PMC6709533):
  discontinue use entirely.
- **BA1** — Ghosh et al., Hum Mutat 2018 (PMC6188666) + the SVI BA1
  exception list (July 2018): >5% stand-alone benign; enumerated exceptions;
  lower gene-specific thresholds via defined criteria.
- **No SVI criteria-specific recommendation exists for PS4, PM1, BP5,
  PS1, or PM5** (checked against the guidance index): for those, use the
  cited generic routes (PS4: curation SOP OR>5 CI excluding 1 / PS4-LRCalc;
  PM1: specification-defined regions only) and gene/disease specifications
  as the only source of thresholds — do not invent them.

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
  (4) NMD expectation (premature termination codon NOT in the 3'-most exon
  or the 3'-most 50 bp of the penultimate exon → NMD expected); (5) known
  rescue/alternative transcripts or exon skipping preserving the reading
  frame; (6) for NMD-escaping variants: whether the removed C-terminal
  region is critical (experimental/clinical evidence, pathogenic variants
  downstream).
- **Strength assignments (SVI decision tree, Abou Tayoun et al. 2018):**
  - **VeryStrong** — nonsense/frameshift/canonical-splice frameshift with NMD
    predicted; whole-gene deletions (given LoF mechanism).
  - **Strong** — NMD escape WITH evidence the C-terminal region is critical;
    or NMD escape removing >10% of the protein; duplications with unknown
    insertion site predicted to cause frameshift/NMD (one step down).
  - **Moderate** — NMD escape, no domain criticality evidence, <10% of the
    protein removed; start-codon loss with no alternative transcripts AND
    pathogenic variant(s) reported 5' of the next downstream in-frame start.
  - **Supporting** — start-codon loss with no alternative start codons AND
    no pathogenic variants upstream of the new methionine.
  - **Not applicable at any strength** — LoF not an established disease
    mechanism; the exon is missing from an alternate biologically relevant
    transcript; the exon is enriched for high-frequency LoF variants in the
    general population; a nearby (±20 nt) strong consensus splice sequence
    may reconstitute in-frame splicing; whole-gene tandem insertion.
- **Splicing overlay (Walker et al. 2023):** canonical ±1/2 variants follow
  the gene-specific tree (some do not alter splicing → PVS1_N/A); RNA assays
  confirming aberrant splicing give **PVS1 at the strength the tree assigns
  for the confirmed transcript outcome — not PS3**; RNA-confirmed aberrant
  splicing replaces predictive PP3/BP4 for that variant.
- **Exclusions/double counting:** a frameshift also changing protein length
  is covered by PVS1 when LoF holds — do not also take PM4 for the same
  fact. **Never assign PVS1 at any strength before the LoF mechanism itself
  is established.**
- **Source:** ClinGen SVI PVS1 decision tree (Abou Tayoun et al. 2018,
  PMC6185798); splicing extensions Walker et al. 2023 (PMC10357475); gene
  specifications override (e.g., MYOC CSpec marks PVS1 not applicable).

### PS1 — same amino-acid change as an established pathogenic variant (Strong)
- **Facts:** reference variant with the same protein change (different
  nucleotide), its pathogenicity established (expert panel / equivalent), same
  transcript and residue, protein-level (not merely predicted) identity.
- **Exclusions:** reference variant VUS/LB/B → PS1 does not apply (do not
  score it); nucleotide-level identity is not required, but protein-level
  identity is.
- **Double counting:** PS1 (same AA change) and PM5 (different AA, same
  residue) are different facts and may coexist; do not count the same
  reference variant twice within one code.
- **Source:** ACMG/AMP 2015 original wording (no SVI criteria-specific
  recommendation exists for PS1/PM5 — checked against the guidance index);
  splicing-related same-change comparisons follow Walker et al. 2023;
  specifications may define additional combinations (e.g., MYOC defines
  PM5_Strong paths and PP3 caps).

### PS2 / PM6 — de novo (SVI point system, replaces fixed strengths)
- **Facts:** every proband with a de novo observation, each with (1) parental
  relationships confirmed by testing vs assumed, (2) phenotype consistency
  class, (3) parents tested for the variant — untested parents score 0 points.
- **SVI v1.1 points per proband (approved 2018-03-18, updated 2021-05-05):**

| Phenotype | Confirmed parentage | Assumed parentage |
|---|---|---|
| Highly specific for the gene | 2 | 1 |
| Consistent, not highly specific | 1 | 0.5 |
| Consistent, not highly specific + high genetic heterogeneity | 0.5 | 0.25 |
| Not consistent with the gene | 0 | 0 |

- **Combined points → strength:** 0.5 **Supporting**; 1 **Moderate**; 2
  **Strong**; 4 **VeryStrong**. These internal de novo points are NOT the
  Tavtigian 2020 classification points (the source states this explicitly).
  Example from the recommendation: one confirmed de novo with a highly
  specific phenotype = 2 points → Strong.
- **Additional rules:** X-linked — a variant de novo in an unaffected carrier
  mother with consistent family history still counts; autosomal recessive
  without a second P/LP variant identified → decrease one level; apparent
  germline mosaicism requires confirmed parentage; PS2 and PM6 may be
  recorded under either code (many VCEPs combine them under PS2).
- **Record:** per-proband count, confirmation status, phenotype class in
  `rationale`/`evidence_ids`; insufficient family information →
  `needs_review` with the gap stated (never assume de novo from one affected
  child).
- **Source:** ClinGen SVI, "Recommendation for de novo Criteria (PS2 & PM6)"
  v1.1.

### PS3 — functional evidence for pathogenicity (validation-driven strength)
- **Facts:** the assay result; the assay's validation record — positive and
  negative internal controls, technical/biological replicates, and known
  pathogenic AND known benign variant controls whose clinical classification
  was established **independently of functional data** (controls may be
  assembled across instances of the same assay class; gnomAD variants above
  BA1/BS1 frequencies can serve as benign controls).
- **Strength starts at ZERO and escalates only with validation** (SVI
  functional framework, Brnich et al. 2020):
  - without both control types and replicates → no evidence (unless
    thresholds are extremely well understood)
  - **≤10 total validation controls → at most Supporting**
  - **≥11 total validation controls (≤1 indeterminate readout) → Moderate**
  - with formal statistical validation, the **OddsPath** ladder applies:
    >2.1 Supporting; >4.3 Moderate; >18.7 Strong; **>350 VeryStrong**
- **BS3 mirror:** OddsPath <0.48 Supporting; <0.23 Moderate; <0.053 Strong;
  **benign evidence is capped at Strong** (no benign VeryStrong tier).
- **Multiple/conflicting assays:** consistent results → apply the strength
  of the most well-validated assay; conflicting → the assay that better
  matches the disease mechanism and is better validated overrides; at equal
  validation with conflicting results, use NO functional evidence. Combining
  evidence across different assay classes has no SVI consensus — the concern
  is double-counting the same functional fact.
- **RNA-splicing assays are NOT PS3/BS3** — they feed PVS1/BP7 per the
  splicing framework (Walker et al. 2023).
- **Double counting:** one assay → one code, never PS3 and PM1 from the
  same assay fact; epidemiological contradictions take precedence and must
  be documented, not averaged away.
- **Source:** Brnich et al., Genome Medicine 2020 (PMC6938631); gene
  specifications list pre-validated assays.

### PS4 — case–control enrichment (no SVI criteria-specific recommendation)
- **No SVI criteria-specific recommendation exists for PS4** (checked
  against the ClinGen guidance index). Two quantitative routes:
  - **ClinGen curation SOP default:** prevalence in affected vs controls
    significantly increased with **odds ratio > 5.0 and a confidence
    interval excluding 1.0** (adequate power and matching).
  - **PS4-LRCalc** (Rowlands et al. 2024, JMG, PMC11503184): case/control
    counts → likelihood ratio (association hypothesis, e.g. OR ≥ target,
    vs non-association, OR ≤ 1) → **exponent points on the base-2.08 log
    ladder — identical to the Tavtigian 2020 point values** (LR ≥2.08 → 1;
    ≥4.33 → 2; ≥18.72 → 4; ≥350.4 → 8; benign mirrors ≤0.48/0.23/0.053/
    0.00285 → −1/−2/−4/−8). Configured for **autosomal dominant
    heterozygous** variants; **a single case observation (n=1) may not
    drive PS4**; use the CI-conservative options (lower 70–95% CI for the
    association target, upper CI for the null) when data are thin; EPs from
    independently ascertained series sum. The 2015 framework capped PS4 at
    Strong; LRCalc permits stronger allocation where the data support it.
  - VCEP specifications frequently define proband-count tables — the
    specification's numbers replace any default.
- **Not to be double counted with PP4:** the same proband counts for PP4 or
  PS4, never both (Biesecker et al. 2023) — reuse the same `evidence_ids`
  fact so the calculator's duplicate-fact check enforces this.
- **Exclusions:** population stratification, ascertainment bias; conflicting
  studies → `needs_review`.
- **Source:** ClinGen variant curation SOP; Rowlands et al. 2024
  (PMC11503184); specifications override.

### PM1 — hotspot / critical functional domain (no SVI criteria-specific recommendation)
- **No SVI criteria-specific recommendation exists for PM1** (checked
  against the ClinGen guidance index): there is no generic numeric
  definition of a hotspot or critical region.
- **Facts:** variant lies in a VCEP-specified critical region, or a
  well-defined functional domain with quantified depletion of benign
  missense variation (domain architecture from UniProt/InterPro; gnomAD
  regional constraint); somatic hotspot data may support PM1 in cancer-gene
  contexts per the specification.
- **Apply** only from a specification-defined region or quantified domain
  depletion. Without either, PM1 is `not_met` — never a hand-scaled PM1.
- **Combination limit:** PP3 + PM1 summed strength must not exceed Strong
  (Pejaver et al. 2022); the calculator enforces this.
- **Double counting:** the same domain fact used with PM1 must not also
  carry PP2 — one fact, one code.
- **Source:** specifications are the threshold source; combination limit
  from Pejaver et al. 2022 (PMC9748256).

### PM2 — absent / extremely rare (Supporting by SVI decision)
- **Facts:** gnomAD (and matching ancestry) frequency with callability —
  coverage at the locus, quality; homozygote counts.
- **Apply at Supporting (PM2_Supporting) by SVI decision** (v1.0, approved
  2020-09-04): rarity alone does not meet the Moderate odds of
  pathogenicity (≈4.3:1) — 54% of high-quality ExAC variants are singletons.
  Higher strengths only if a specification explicitly states them. Absence
  must be supported by adequate coverage — absent call ≠ absent allele.
  The SVI pairs this downgrade with a new combination rule (VeryStrong +
  Supporting → Likely pathogenic), which the Tavtigian 2020 point system
  reproduces arithmetically (8 + 1 = 9 → LP).
- **Disease-aware frequency:** the disease's maximum credible frequency
  (see BS1) governs BA1/BS1/BS2 decisions, not a flat 0.0001; PM2 is about
  absence/rarity, BA1/BS1 about excess.
- **Exclusions:** BA1 or BS1 met → do not also record PM2 as met (conflict;
  resolve first). Recessive genes: ultra-low frequency still applies per the
  original caveat.
- **Source:** ClinGen SVI PM2 recommendation v1.0 (2020-09-04).

### PM3 — in trans with a pathogenic variant, recessive (SVI point system)
- **Facts:** proband observations with the variant paired on the other allele;
  phase evidence per observation (confirmed by family/molecular typing vs
  unknown); classification of the other variant (P/LP vs VUS); homozygous
  occurrences and consanguinity.
- **Points per proband (Oza et al. 2018, Table 6a — the table the SVI
  recommendation formalized):**
  - in trans with a Pathogenic/Likely pathogenic variant → 1.0 confirmed;
    0.5 phase unknown
  - homozygous occurrence → 0.5 (cap 1.0 across homozygous observations)
  - VUS on the other allele, or homozygous occurrence due to consanguinity
    → 0.25 (cap 0.5)
- **Combined points → strength (Table 6b):** 0.5 **Supporting**; 1
  **Moderate**; 2 **Strong**; 4 **VeryStrong**. One fully confirmed proband
  with a P/LP partner is PM3_Moderate (1.0), not Supporting; an unphased
  VUS co-occurrence scores nothing.
- **Open question (source discrepancy):** one secondary summary (Genome
  Medicine 2020, Table 4C) reports phase-unknown split as 0.5 (Pathogenic)
  vs 0.25 (Likely pathogenic); the primary Table 6a gives 0.5 for P/LP
  jointly. Pending verification against the SVI PM3 v1.0 document, apply
  Table 6a (0.5 for P/LP phase unknown) and cite the table used.
- **Insufficient phase evidence** → `needs_review` with the gap recorded;
  never assume phase from co-occurrence.
- **Source:** Oza et al., Hum Mutat 2018, Table 6a/6b (PMC6188673); SVI PM3
  recommendation v1.0; Genome Medicine 2020 overview (PMC6885382).

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
- **Source:** ACMG/AMP 2015 (no SVI criteria-specific recommendation exists
  for PM5 — checked against the guidance index); specifications may define
  upgraded paths (e.g., MYOC's PM5_Strong combinations with caps).

### PP1 — co-segregation (SVI 2023 point system)
- **Facts:** inheritance model; each genotyped co-segregating relative with
  affection status; penetrance assumption; phase (established by the first
  meiosis — two for autosomal recessive; unaffected parents establish phase
  and are not themselves counted).
- **SVI points per co-segregating individual (Biesecker et al. 2023, Table 3):**
  - autosomal dominant (affected or unaffected): **1.0** each
  - autosomal recessive, affected: **2.0** each; unaffected: **0.4** each
    (+0.4 per additional beyond five)
  - X-linked recessive male (affected or unaffected): **1.0** each; obligate
    heterozygous females may add
  - unaffected relatives count only under a full-penetrance assumption
- **Points → strength:** 1 **Supporting**; 2 **Moderate**; 4 **Strong**; 8
  **VeryStrong** (the standard Bayesian point ladder; the paper's Table 4
  gives classical-label equivalents, e.g., ≥5 = Strong + Supporting).
- **PP1 and PP4 are coupled locus evidence:** their points sum and are capped
  at **+5.0** per variant; a proband counts for PP4 or PS4, never both; with a
  single-potent-locus phenotype (diagnostic yield >90%) PP4 applies at the
  cap and co-segregation adds nothing.
- Insufficient segregation data → `not_assessed`/`needs_review`, never a
  hand-waved PP1.
- **Source:** Biesecker et al., AJHG 2023 — ClinGen PP1/BS4/PP4 guidance.

### PP2 — missense-enrichment gene (Supporting default)
- **Facts:** missense is the established disease mechanism AND the gene has
  a significantly depleted benign missense rate (gnomAD missense z-score
  > 3.09 is the common convention; VCEP definitions override).
- **Exclusions:** mutually exclusive with BP1; LoF-only genes → PP2
  `not_applicable`.
- **Source:** ACMG/AMP 2015; gnomAD constraint (Karczewski et al.);
  specification override.

### PP3 — computational evidence for pathogenicity (calibrated thresholds)
- **Use ONE pre-specified calibrated tool, chosen genome-wide BEFORE seeing
  the variant's results** (Pejaver et al. 2022; scanning multiple tools for
  the strongest evidence is explicitly warned against). No majority voting
  across uncalibrated predictors; discordant calibrated predictors → neither
  PP3 nor BP4.
- **Preferred tools (PP3 to Strong / BP4 to Moderate)** — exact calibrated
  intervals:

| Tool | PP3 Supporting | PP3 Moderate | PP3 Strong | BP4 Supporting | BP4 Moderate |
|---|---|---|---|---|---|
| REVEL | 0.644–0.773 | 0.773–0.932 | ≥0.932 | 0.183–0.290 | 0.016–0.183 |
| BayesDel | 0.13–0.27 | 0.27–0.50 | ≥0.50 | −0.36 to −0.18 | ≤−0.36 |
| MutPred2 | 0.737–0.829 | 0.829–0.932 | ≥0.932 | 0.197–0.391 | 0.010–0.197 |
| VEST4 | 0.764–0.861 | 0.861–0.965 | ≥0.965 | 0.302–0.449 | ≤0.302 |
| CADD | 25.3–28.1 | ≥28.1 | — | 17.3–22.7 | 0.15–17.3 |

  (REVEL and CADD also support stronger benign tiers: REVEL 0.003–0.016 and
  CADD ≤0.15 = BP4 Strong.)
- **Combination limits:** the summed strength of **PP3 + PM1 must not
  exceed Strong**; tools without an allele-frequency component (REVEL,
  BayesDel) may combine with PM2/BS1 without limits. A tool whose maximum
  calibrated tier is Moderate can never contribute above Moderate.
- **Splice prediction (non-canonical variants, Walker et al. 2023):**
  SpliceAI Δ ≥0.2 → PP3 (calibrated Moderate, conservatively applied at
  Supporting); Δ ≤0.1 → BP4 (same conservative Supporting); 0.1–0.2 →
  uninformative, no code.
- **Exclusions:** synonymous variants (BP7 path), canonical splice (PVS1
  path); RNA-confirmed splice outcomes replace predictive PP3/BP4.
- **Source:** Pejaver et al., AJHG 2022 (PMC9748256); Walker et al. 2023
  (PMC10357475).

### PP4 — phenotype specificity (SVI 2023 point system)
- **Facts:** the gene's diagnostic yield for the proband's specific phenotype
  (and exclusion of other candidate loci, which raises the effective yield).
- **Points follow the diagnostic-yield table (Biesecker et al. 2023, Table 2):**
  floor **+1.0 at ~20% yield**, rising with yield (≈+6.0 at 90%); round down
  between rows; yield <20% → PP4 does not apply.
- **Coupling:** PP4 points sum with PP1 co-segregation points as locus
  evidence, capped at +5.0 per variant; a proband counts for PP4 or PS4,
  never both. With yield >90%, PP4 applies at the cap and PP1 adds nothing.
- **Do not apply** for nonspecific phenotypes (isolated seizures, intellectual
  disability, arrhythmia and similar).
- **Source:** Biesecker et al., AJHG 2023 — ClinGen PP1/BS4/PP4 guidance.

### PP5 — RETIRED, do not apply
- The SVI recommendation is unambiguous: "laboratories [should] discontinue
  the use of criteria PP5 and BP6 as soon as that is practically
  achievable" (Biesecker & Harrison, Genet Med 2018 — rationale: assertions
  without primary evidence, ClinVar now exposes the underlying data, and
  reuse of the same data double-counts with codes like PS3/BS3). Status must
  be `deprecated` in the 28-record review; a ClinVar/lab "Pathogenic" label
  is an external conclusion — attribute it separately, it never scores.
  **A ClinVar label alone must not produce PP5/BP6.**

---

## Benign criteria

### BA1 — allele frequency > 5% (StandAlone)
- **Refined SVI wording (Ghosh et al. 2018):** "Allele frequency is >0.05 in
  any general continental population dataset of at least 2,000 observed
  alleles and found in a gene without a gene- or variant-specific BA1
  modification." Recommended ExAC/gnomAD continental subsets exclude
  Finnish European (founder population); no need to match the case's
  geographic origin to the dataset; datasets must be primarily unrelated
  individuals; caution for bottlenecked populations.
- **Apply:** stand-alone **Benign** — the calculator runs BA1 on its own
  path (total score null); BA1 met together with any pathogenic `met`
  pauses classification for conflict resolution.
- **Exception list (SVI-curated, interim):** nine initial exempted variants
  (Ghosh 2018 + July 2018 list): HFE C282Y / H63D (common low-penetrance —
  ACMG criteria not designed for this class), GJB2 V37I, MEFV P369S /
  R408Q, BTD D444H and ACADS R171W (Finnish-only >5%), ACAD9 c.-44_-41dup,
  PIBF1 R405G. Petition form on the ClinGen SVI site amends the list; labs
  may keep in-house lists — consult the current version.
- **Lower gene-specific thresholds:** expert groups may set a numerically
  lower BA1 threshold based on known prevalence, penetrance, and genetic
  heterogeneity — validated against known pathogenic variation,
  conservative, a valid exclusion for the most common associated disorder,
  and not below where BS1 would apply.
- **Source:** Ghosh et al., Hum Mutat 2018 (PMC6188666); SVI BA1 exception
  list (July 2018).

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

### BS3 — functional evidence against pathogenicity
Same SVI validation framework as PS3 (Brnich et al. 2020): strength starts
at zero and escalates with validation (≤10 controls → Supporting max;
≥11 → Moderate; formal OddsPath analysis gives the full ladder). The benign
OddsPath ladder: <0.48 Supporting; <0.23 Moderate; <0.053 Strong —
**benign functional evidence is capped at Strong** (no VeryStrong tier).
One assay produces either PS3 or BS3, never both; RNA-splicing assays feed
BP7/PVS1 instead.

### BS4 — lack of segregation
- **Facts:** affected relatives who do NOT carry the variant (genotyped,
  informative, full-penetrance reasoning); misspecified affection status
  voids the criterion.
- **SVI 2023 rule:** non-segregation = **−4.0 points** (Strong benign) for
  autosomal dominant, autosomal-recessive homozygous, and X-linked contexts;
  for autosomal-recessive compound heterozygotes non-segregation provides
  little to no benign evidence.
- **Source:** Biesecker et al., AJHG 2023 (same point system as PP1/PP4).

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

### BP5 — alternate molecular diagnosis in the proband
- **No SVI criteria-specific recommendation exists for BP5** (checked
  against the guidance index). Apply only when the alternative diagnosis is
  molecularly confirmed; an unconfirmed alternative diagnosis does not
  support BP5. Use with caution in genes with variable expressivity —
  specifications define their own conditions where present.
- **Source:** ACMG/AMP 2015 original; specifications override.

### BP6 — RETIRED, do not apply
- See PP5. ClinVar "Benign" consensus labels are attributed externally,
  never scored.

### BP7 — synonymous/intronic with no splice impact
- **Predictive route (Walker et al. 2023):** BP7 applies when SpliceAI Δ
  **≤ 0.1** (BP4 conditions met) AND:
  - synonymous variants: NOT at the first base or the last 3 bases of the
    exon;
  - intronic variants: at or beyond positions **+7/−21** of the donor/
    acceptor regions.
  Conservation filters are discouraged without empirical justification.
  SpliceAI 0.1–0.2 is uninformative — no code either way.
- **RNA route:** RNA assays from non-tumor patient tissue confirming no
  splicing impact → **BP7_Strong (RNA)**, applicable irrespective of
  position for intronic variants.
- **Exclusions:** borderline predictor output → `needs_review`; variants
  near exon boundaries or in genes with known cryptic-splice mechanisms
  follow the specification.
- **Source:** Walker et al. 2023 (PMC10357475).

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
