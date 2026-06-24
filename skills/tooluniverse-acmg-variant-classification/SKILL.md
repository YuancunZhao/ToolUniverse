---
name: tooluniverse-acmg-variant-classification
description: Systematic ACMG/AMP germline variant classification with all 28 criteria (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4, BP1-7) for clinical significance. Produces 5-tier verdict (Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign) with cited evidence per criterion. Use for variant interpretation, VUS resolution, and pathogenicity assessment. Combines ClinVar, gnomAD, computational predictors, and gene-mechanism context.
disable-model-invocation: true
---

# ACMG/AMP Variant Classification

## ACMG Reasoning

Each criterion (PS, PM, PP for pathogenic; BS, BP for benign) contributes a weighted piece of evidence for or against pathogenicity. The classification is the COMBINATION of all activated criteria, not any single criterion. Do not overweight a single finding.

The hierarchy is: PVS1 (very strong) > PS (strong) > PM (moderate) > PP (supporting). On the benign side: BA1 (stand-alone) > BS (strong) > BP (supporting). A source label such as a ClinVar expert-panel, HGMD, LOVD, or published ACMG classification is not itself a counted criterion; use it as a lead to retrieve primary evidence and route that evidence to the appropriate overlay before combining criteria. A single PP criterion alone is not enough. The combination rule is what matters.

Two common errors to avoid: (1) seeing a "Pathogenic" or "Benign" ClinVar entry and counting PP5/BP6 — ClinGen SVI recommends discontinuing PP5/BP6, so secondary assertions should be used as leads to retrieve primary evidence; (2) treating arbitrary predictor disagreement as benign — PP3/BP4 should follow calibrated predictor rules or a VCEP specification, and non-applied prediction evidence is neutral rather than benign.

Always apply criteria conservatively. When evidence is ambiguous, leave the criterion unmet. Cite the source for every criterion you activate so clinicians can audit the reasoning.

When this skill is imported into another agent, the agent must not use this base workflow to bypass overlay rules. For every criterion covered by an overlay, record whether the overlay was `overlay_applied`, `overlay_not_applicable`, `overlay_not_assessed`, or `overlay_deferred_to_vcep`. Do not hand-assign refined strengths in the main workflow just because evidence appears obvious.

**KEY PRINCIPLES**:
1. **Criteria-driven** — cite which criteria were activated and why
2. **Conservative** — do not upgrade a criterion when evidence is ambiguous
3. **Gene-aware** — adjust thresholds based on gene mechanism (LOF, gain-of-function, dominant-negative, mixed mechanism)
4. **Population-calibrated** — use ancestry-specific gnomAD frequencies, not just global AF
5. **Transparent** — show evidence for each criterion
6. **Source-referenced** — every criterion activation must cite the database/tool source
7. **English-first queries** — always use English terms in tool calls; respond in user's language

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## When to Use

- "Classify BRCA2 c.5946delT using ACMG criteria"
- "Is this VUS pathogenic? NM_000059.4:c.7397T>C"
- "Apply ACMG guidelines to rs28897743"
- "What is the pathogenicity of CFTR p.Arg117His?"
- "ACMG classification for TP53 R248W"

---

## Tool Parameter Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `VariantValidator_validate_variant` | `variant_description`, `genome_build`, `select_transcripts` | genome_build="GRCh38" |
| `VariantValidator_gene2transcripts` | `gene_symbol` | Returns MANE Select transcript |
| `MyVariant_query_variants` | `query` | HGVS or rsID. Returns ClinVar, gnomAD, CADD, REVEL, SIFT, PolyPhen |
| `EnsemblVEP_annotate_hgvs` | `hgvs_notation` | Consequence, colocated variants, ancestry gnomAD |
| `gnomad_search_variants` | `query` | rsID to gnomAD variant ID |
| `gnomad_get_variant` | `variant_id` | Per-ancestry population frequencies |
| `gnomad_get_gene_constraints` | `gene_symbol` | pLI, LOEUF, mis_z |
| `ClinVar_search_variants` | `query` | Variable response format: list OR `{status, data}` |
| `ClinVar_get_variant_details` | `variant_id` | ClinVar numeric ID |
| `civic_get_variants_by_gene` | `gene_id` | CIViC numeric gene ID (NOT symbol). Known: BRAF=5, BRCA2=19 |
| `MedGen_search_conditions` | `query` | MedGen aggregates OMIM, Orphanet, ClinVar, HPO, GTR, and GeneReviews; use to discover GeneReviews disease chapters when mechanism or inheritance is unclear |
| `UniProt_get_function_by_accession` | `accession` | Returns list of strings |
| `InterPro_get_entries_for_protein` | `accession` | Domain architecture by UniProt accession |
| `alphafold_get_prediction` | `qualifier` | UniProt accession; pLDDT confidence |
| `PubMed_search_articles` | `query`, `limit` | Returns list of dicts |
| `MyGene_query_genes` | `query` | Filter by `symbol` match (first hit may not match) |

---

## Phase 0: Variant Validation and Normalization

Wrong HGVS or wrong transcript cascades errors through every downstream criterion. Validate first.

1. **Get MANE Select transcript**: `VariantValidator_gene2transcripts(gene_symbol="BRCA2")`
2. **Validate variant**: `VariantValidator_validate_variant(variant_description="NM_000059.4:c.5946delT", genome_build="GRCh38", select_transcripts="mane_select")`
3. **Resolve gene IDs**: `MyGene_query_genes(query="BRCA2")` — extract Ensembl ID and UniProt accession. Filter results by `symbol == 'BRCA2'` (first hit may not match).
4. **Record**: HGVS coding, HGVS protein, genomic coordinates, variant type (frameshift/missense/nonsense/splice/synonymous/in-frame indel).

Accepted inputs: HGVS coding (NM_000059.4:c.5946delT), HGVS protein (BRCA2 p.Val600Glu), rsID (rs28897743), gene+change (BRCA1 c.68_69del), genomic coordinates.

---

## Phase 0a: Overlay Routing Core

Use `tooluniverse-acmg-overlay-routing-core` before evidence-specific overlays. This base skill should act as a dispatcher: normalize the variant, establish disease/mechanism context, select route bundles, expand triggered bundles into overlay route rows, run overlays, resolve compatibility, and only then combine evidence.

Hard gate for external agents: before presenting any final ACMG classification, emit an `acmg_assessment_bundle` compatible with `tooluniverse-acmg-overlay-routing-core/schemas/acmg_assessment_bundle.schema.json` and validate it with `tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py`. If the validator returns `DRAFT_ONLY` or `FAIL`, keep `classification_status: draft classification`; do not compute or present the final ACMG tier from unrouted evidence.

Start with a compact `Bundle Route Plan`:

1. `baseline_context_bundle` for disease entity, inheritance, transcript, mechanism, multiple-disorder boundary, and dominant-negative/LoF/GoF sensitivity.
2. `population_frequency_bundle` for BA1/BS1/BS2/PM2/BP2/BP5 frequency and benign-context gates.
3. `consequence_lof_bundle` only for LoF-like consequences such as nonsense, frameshift, canonical splice, start-loss, exon-level CNV, or whole-gene deletion.
4. `splice_bundle` for splice prediction, PS1-splicing comparison, or RNA assay evidence; SpliceAI-only evidence is prediction context and does not trigger RNA-assay PVS1.
5. `missense_bundle` only for missense/amino-acid substitution consequences, covering PP3/BP4, PS1/PM5, PM1/PP2/BP1, and structured functional-discovery lookup.
6. `protein_length_bundle` for in-frame indels, stop-loss, altered-product, and repeat-region effects.
7. `clinical_observation_bundle` only after de novo, segregation, biallelic phase, affected/unaffected, healthy-carrier, alternate-diagnosis, or phenotype-specific evidence is present or requested.
8. `literature_functional_bundle` only after source/literature coverage finds functional assay, case-control/cohort, case series, figure/table/supplement, or paper-label triggers.
9. `cnv_sv_bundle` for structural-variant/CNV evidence intake; final ACMG evidence must still route through the appropriate ACMG overlays and compatibility resolution.
10. `final_combine_bundle` after overlay audit passes.

Then expand each triggered bundle using the routing core registry. A bundle row is not counted evidence; counted criteria still require overlay result, route audit outcome `overlay_applied` or `overlay_deferred_to_vcep`, and compatibility resolution.

External-agent compliance check: before final classification, list each evidence code considered, the route bundle, and the overlay route used. If a code is assigned without the responsible overlay or VCEP rule, revise the evidence table before combining criteria.

Final hard-stop audit: the report may present a final classification only when the ACMG assessment bundle validates and every counted evidence item has route outcome `overlay_applied` or `overlay_deferred_to_vcep`. If any counted item lacks that route outcome, or if the bundle is absent or invalid, label the result `draft classification`, move that item to `Criteria With status: not_assessed` or `Source Assertions / Leads`, and do not compute the final ACMG tier from it.

Keep `Source Assertions / Leads` separate from `Current Counted Evidence`. ClinVar, HGMD, LOVD, VCEP, laboratory reports, or a paper's ACMG classification may guide retrieval, but the final ACMG tier is based only on evidence that was independently routed through an overlay or current VCEP rule.

Use the routing core's canonical output fields where practical: `applied_evidence`, `status`, `reason`, `consumed_evidence`, and `routed_to`. Use `status` values `applied`, `no_evidence`, `not_assessed`, `not_applicable`, or `not_used`.

For every counted criterion, report `guidance_authority` as one of `ClinGen/SVI primary`, `ACMG/AMP baseline`, `VCEP-specific`, `practice/local refinement`, or `source lead only`. Formal ClinGen/SVI recommendations and VCEP specifications should be distinguished from ACGS 2024, non-ClinGen literature, or local operational guardrails. Practice/local refinements may help apply under-specified ACMG/AMP criteria, but they must be labeled as such and must not be presented as ClinGen/SVI primary guidance.

---

## Phase 0b: Gene-Disease Mechanism Check

Use the routing core before mechanism-sensitive criteria. In short, run multiple-disorder context first if evidence may cross disease boundaries, then run dominant-negative/mechanism refinement if variant class, product expression, LoF/HI, GoF, DN, or mixed mechanism could change criterion use.

PVS1 must have a direct LoF/haploinsufficiency source for the exact gene-disease context, or a mechanism-refinement result showing PVS1 is allowed for that context. Do not transfer evidence between recessive LoF, haploinsufficiency, dominant-negative, gain-of-function, splicing LoF, and other mechanisms without a same-mechanism rationale.

Do not infer dominant-negative mechanism from autosomal dominant inheritance alone. Use curated mechanism sources, VCEP guidance, G2P/ClinGen/GenCC, dosage sensitivity, GeneReviews/NCBI Bookshelf disease chapters, functional assay literature, and protein biology.

GeneReviews should be queried when inheritance, disease spectrum, or mechanism routing is unclear, especially for genes with both dominant and recessive disease associations or for structural/complex proteins. Treat GeneReviews as expert review/background support for gene-disease mechanism, inheritance, phenotype spectrum, and management. Do not treat GeneReviews as a VCEP criteria specification or as primary variant-level evidence for PS3, PS4, PP1, PM3, or BS4 unless it cites and you separately evaluate the underlying primary evidence.

```python
ClinGen_search_gene_validity(gene="...")
ClinGen_search_dosage_sensitivity(gene="...")
G2P_search(query="...")
MedGen_search_conditions(query="GENE disease GeneReviews")
PubMed_search_articles(query="GENE disease dominant-negative")
```

---

## Phase 1: Population Frequency (BA1, BS1, BS2, PM2)

Population AF is among the strongest evidence in either direction. A variant at >5% may qualify for BA1 stand-alone benign evidence, but only after `tooluniverse-acmg-ba1-exception-list-refinement` confirms the Ghosh et al. 2018 BA1 definition: AF >0.05 in a qualifying general continental population dataset with at least 2,000 observed alleles, no exception-list match, no inadequate founder-population-only signal, and no gene- or variant-specific BA1 modification. Absent from gnomAD supports pathogenicity only through PM2, now usually applied as `PM2_Supporting` per ClinGen guidance.

Use ancestry-specific AF, not just global. A variant at 8% in East Asian populations but rare globally is benign in that ancestry context. For BS1, the threshold depends on disease prevalence and inheritance — the default is 1% for common diseases, 0.1% for rare. When absence, extreme rarity, coverage adequacy, PM2 strength, or the `PVS1 + PM2_Supporting` combination affects classification, use `tooluniverse-acmg-pm2-absence-rarity-refinement`. That overlay follows the ClinGen SVI PM2 v1.0 recommendation: PM2 should default to Supporting strength, absence from a database is not evidence unless the allele and locus are adequately represented, BA1/BS1/BS2 override PM2, and valid `PVS1 + PM2_Supporting` can support Likely Pathogenic when no conflicting evidence is present.

When benign-context evidence is possible, use `tooluniverse-acmg-benign-context-refinement` for BA1, BS1, BS2, BP2, and BP5. That overlay keeps BA1 exception-list logic on the Ghosh et al. 2018 ClinGen/SVI path and labels ACGS 2024 details for BS1/BS2/BP2/BP5 as `practice/local refinement` unless a VCEP makes them disease-specific. BA1/BS1 require disease prevalence, penetrance, allelic/genetic heterogeneity, inheritance, and max credible ancestry AF; BS2 requires well-phenotyped healthy individuals old enough for the disease's expected onset and penetrance; BP2 requires a clear cis/trans and inheritance context; BP5 requires an alternate P/LP molecular diagnosis that explains the patient's main phenotype. If disease threshold, phenotype, unaffected status, phase, or alternate-diagnosis context is missing, mark the specific benign criterion with `status: not_assessed` and ask for the missing fields rather than weakening PM2.

```python
gnomad_search_variants(query="rs28897743")          # get gnomAD variant ID
gnomad_get_variant(variant_id="...")                 # per-ancestry frequencies
gnomad_get_gene_constraints(gene_symbol="BRCA2")     # pLI, LOEUF, mis_z
MyVariant_query_variants(query="rs28897743")          # fallback: gnomad_genome.af
```

If gnomAD data is unavailable, note the gap and continue — absence of data is not the same as evidence of absence.

---

## Phase 2: Computational Predictions (PP3, BP4)

For missense variants, use `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` before assigning PP3/BP4. That overlay follows Pejaver et al. 2022 ClinGen SVI recommendations: select one calibrated missense predictor before inspecting scores, map the score to calibrated evidence-strength intervals, avoid uncalibrated majority voting, and do not use developer-default SIFT/PolyPhen/CADD thresholds as ACMG evidence.

The refinement supports `PP3_Strong`, `PP3_Moderate`, `PP3_Supporting`, `BP4_VeryStrong`, `BP4_Strong`, `BP4_Moderate`, and `BP4_Supporting` when the selected tool and score meet calibrated thresholds. `BP4_Moderate` requires explicit downstream combiner handling if the classifier only implements the original 2015 ACMG/AMP evidence-strength table.

If no Pejaver-calibrated score, pre-specified tool hierarchy, or current VCEP threshold is available, report PP3/BP4 as `status: not_assessed` or `no_evidence`. Do not assign `PP3_Supporting` from a pattern such as SIFT deleterious plus PolyPhen probably damaging plus high CADD.

```python
MyVariant_get_pathogenicity_scores(variant_id="...") # REVEL, CADD, SIFT, PolyPhen-2, GERP, PhyloP, VEST4
OpenCRAVAT_annotate_variant(...)              # optional predictor-source fallback
EnsemblVEP_annotate_hgvs(hgvs_notation="...") # consequence, transcript, SIFT/PolyPhen, colocated variants
```

For non-missense variants, skip missense PP3/BP4 and focus on the relevant mechanism-specific evidence. Splice prediction/RNA evidence belongs in Phase 5 and the splicing overlays, not this missense-prediction pathway.

If the gene-disease context may involve dominant-negative, antimorphic, gain-of-function, or mixed mechanisms, run `tooluniverse-acmg-dominant-negative-mechanism-refinement` before using PP3/BP4 as part of a missense-mediated disease model. Predictor scores can support generic deleteriousness or benignity, but they do not prove or exclude dominant interference. For genes where pathogenicity depends on dominant-negative missense/in-frame mechanisms, document that the variant class is compatible with that mechanism before allowing PP3 to contribute to classification.

**Mechanism complement for VUS-resolution narratives**: PP3/BP4 calibrated prediction evidence tells you whether the variant score supports pathogenicity or benignity, not why the protein may be affected. For a VUS resolution report where the verdict needs a mechanistic explanation, add `ESM_explain_variant_mechanism(sequence=..., position=..., ref_aa=..., alt_aa=...)` — returns lost/gained ESMC-6B SAE feature categories (catalytic / ligand-binding / ptm / structural-stability / domain / etc.) with a one-line summary. This does not change PP3 strength but turns "PP3_Moderate satisfied (REVEL 0.78)" into "PP3_Moderate satisfied — and SAE shows catalytic-feature loss at position X, consistent with active-site disruption." Requires `ESM_API_KEY`; missense only.

---

## Phase 3: Clinical Database Evidence (PS1, PM5, PP5, BP6)

ClinVar aggregates clinical lab classifications. The reasoning: if the same amino acid change (different nucleotide) is established pathogenic, that is strong evidence (PS1) because the mechanism is the amino acid change. If a different pathogenic missense occurs at the same residue, that is moderate evidence (PM5) — the residue is functionally important. When PS1 or PM5 may apply to an ordinary missense variant because of the same amino-acid substitution, same residue, or same codon as a known pathogenic variant, use `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement`. That overlay checks transcript/protein equivalence, comparison-variant independence, circularity, amino-acid-mediated mechanism, and splicing/DNA-level confounding before assigning PS1 or PM5.

For PS1/PM5, a comparison variant's ClinVar, HGMD, VCEP, or paper label is only a lead. Confirm the comparison variant's independent P/LP status, non-circular evidence, same disease context, and shared amino-acid-mediated mechanism before counting PS1/PM5. If the comparison evidence cannot be traced beyond a source label, record `status: not_assessed` or `not_used` rather than applying PS1/PM5.

When PS1 may apply because the variant has the same predicted RNA-splicing event as a known pathogenic or likely pathogenic variant, use `tooluniverse-acmg-ps1-splicing-similarity-refinement`. That overlay adapts Walker et al. 2023 ClinGen SVI Splicing Subgroup Table 2 for PS1 strength based on same-event splice prediction, donor/acceptor motif position, P versus LP comparison variant status, and the VUA's PP3/PVS1 baseline. If direct RNA assay evidence is present for the VUA, resolve `PVS1_Strength (RNA)` or `BP7_Strong (RNA)` first, then apply PS1-splicing only for independent comparison-variant evidence and remove duplicate PP3/PS3/BS3 uses.

If the gene-disease context may involve dominant-negative mechanism, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before applying PS1/PM5. Same amino acid or same residue evidence should not be transferred between dominant-negative, haploinsufficiency, splicing LoF, and unrelated gain-of-function mechanisms without same-mechanism support.

When a reputable source, ClinVar assertion, lab report, expert panel, or database label is the only basis for PP5 or BP6, use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement`. That overlay follows Biesecker and Harrison 2018 / ClinGen SVI guidance recommending discontinuation of PP5/BP6. Do not count PP5/BP6 by default. Treat the source assertion as a lead, retrieve primary evidence, and route that evidence to the appropriate criteria. Conflicting ClinVar interpretations should trigger primary-evidence review rather than PP5/BP6 scoring.

```python
ClinVar_search_variants(query="BRCA2 c.5946delT")
ClinVar_get_variant_details(variant_id="...")
civic_get_variants_by_gene(gene_id=19)   # BRCA2 CIViC ID is 19
```

---

## Phase 4: Functional Domain and Protein Analysis (PM1, PP2, BP1, PM4, BP3)

Variants in well-established functional domains with known pathogenic variant enrichment are more likely pathogenic. PM1 (moderate pathogenic) requires the variant to be in a hotspot domain with low benign variation — use InterPro domain architecture and UniProt active/binding sites to assess. When a missense variant may qualify for PM1 because it lies in a constrained regional missense-depleted region, hotspot, or subdomain with low benign variation, use `tooluniverse-acmg-pm1-regional-missense-constraint-refinement`. That overlay adapts PMID:38645134 regional missense mutational intolerance guidance for PM1 while keeping prediction-only MPC/AlphaMissense evidence separate from PP3 and resolving PM1/PP2 selection: retain PM1 over PP2 when PM1 is met, retain PP2 over PM1_Supporting when only supporting regional evidence is met, and follow current VCEP rules when they differ.

Broad domain membership alone is not PM1. PM1 requires hotspot, critical residue, regional constraint, pathogenic enrichment with low benign variation, or a disease-specific/VCEP rule. Database or paper statements that PM1 was applied are leads only until the regional/domain basis is independently reviewed.

PP2 and BP1 are mutually exclusive. PP2 (supporting pathogenic) applies to missense in genes where missense is the known mechanism and benign missense rate is low (mis_z > 3.09). BP1 (supporting benign) applies to missense in genes where only truncating variants cause disease (LOF-only mechanism) — a missense in such a gene is unlikely to be pathogenic.

If pathogenic missense variants act through a dominant-negative mechanism, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PM1/PP2/BP1. BP1 is unsafe when pathogenic dominant-negative missense variants are established for the same disease context.

When a protein length change may qualify for PM4 or BP3, use `tooluniverse-acmg-pm4-bp3-protein-length-refinement`. That overlay handles in-frame insertions/deletions, single amino-acid indels, repeat regions, stop-loss variants, and last-exon gain-of-function truncating variants. ACMG/AMP 2015 is the baseline authority for PM4/BP3; ACGS 2024 single-amino-acid, stop-loss, and last-exon altered-product details are `practice/local refinement` unless a current VCEP or gene-specific rule adopts them. The overlay keeps the same operational guards: a single amino-acid in-frame indel defaults to at most `PM4_Supporting` unless gene-specific evidence justifies moderate strength; PM4 is not used together with PVS1 for the same length-changing effect; BP3 is limited to in-frame indels in repetitive or low-complexity regions without known function; stop-loss variants with predicted nonstop decay route to PVS1 rather than PM4; and last-exon truncating variants in gain-of-function/altered-product contexts may route through PM4 rather than PVS1.

```python
UniProt_get_function_by_accession(accession="P51587")        # active sites, binding sites
InterPro_get_entries_for_protein(accession="P51587")          # domain architecture
alphafold_get_prediction(qualifier="P51587")                   # pLDDT > 90 = structured region
gnomad_get_gene_constraints(gene_symbol="BRCA2")              # mis_z for PP2/BP1
```

---

## Phase 5: Splice Impact Assessment (PVS1)

PVS1 is the strongest single pathogenic criterion. A null variant (nonsense/frameshift/canonical splice/initiation codon) in a gene where LOF is the established mechanism can activate PVS1, but the full strength depends on context.

Apply PVS1 through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` before assigning a final PVS1 strength. That overlay follows the Abou Tayoun et al. 2018 ClinGen SVI PVS1 decision tree for nonsense, frameshift, canonical splice, initiation codon/start-loss, exon-level deletion/duplication, whole-gene deletion, NMD escape, altered-protein consequence, rescue transcript, and LoF applicability branches. Output should be `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, or `applied_evidence: none` with `status: not_assessed`.

Apply PVS1 at full strength only when the LoF decision tree supports it: predicted null variant + LoF is known mechanism for the exact gene-disease context + the PTC is expected to undergo NMD or the whole-gene/exon event is LoF-equivalent + no rescue transcript or alternative initiation model preserves clinically relevant function. Under the Abou Tayoun et al. 2018 baseline tree, NMD is generally not predicted when the PTC occurs in the 3' most exon or within the 3' most 50 nucleotides of the penultimate exon. Downgrade PVS1 through the truncated-protein branch when NMD is not predicted, and apply additional transcript-specific NMD escape rules only when supported by a VCEP or separate current source. Treat LoFTEE as supporting annotation, not as a substitute for direct transcript-structure review. Do NOT apply PVS1 if LOF mechanism is uncertain.

If the disease mechanism is dominant-negative, mixed, or not explicitly resolved, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before applying PVS1. A null allele in a dominant-negative disease gene should not automatically receive PVS1 unless haploinsufficiency/LoF is established for that exact gene-disease context. If the gene has separate recessive LoF and dominant missense/in-frame disease contexts, keep them separate in the evidence table and state which context receives PVS1.

**RNA/splicing refinement**: When RNA assay evidence, published RNA-splicing evidence, in-frame exon skipping, partial/complex aberrant transcript profiles, or Walker 2023 splicing-specific evidence affects PVS1 or BP7, use `tooluniverse-acmg-pvs1-splicing-refinement` after the 2018 LoF decision-tree branch is identified. RNA evidence demonstrating LoF transcript(s) is captured as `PVS1_Strength (RNA)`, RNA evidence demonstrating no splicing impact may support `BP7_Strong (RNA)`, and the same RNA-splicing evidence should not be double-counted as PS3/BS3 or PP3/BP4. If PS1-splicing similarity is also considered, direct RNA observations override prediction-based same-event assumptions; use PS1 only when the comparison variant evidence is independent.

```python
EnsemblVEP_annotate_hgvs(hgvs_notation="...")   # splice_donor_variant, splice_acceptor_variant
MyVariant_query_variants(query="...")             # SpliceAI deltas
gnomad_get_gene_constraints(gene_symbol="...")    # pLI >= 0.9 or LOEUF < 0.35 = LOF intolerant
```

---

## Phase 6: Literature and Clinical/Functional Evidence (PS3, BS3, PS4, PP1, PP4)

Well-designed functional assays showing LOF (PS3) or normal function (BS3) can shift a classification decisively. PS3/BS3 can be downgraded (e.g., PS3_Supporting) for less rigorous assays. Not all functional assays qualify — ClinGen gene-specific guidance defines valid assays. When biochemical, cellular, model-organism, patient-derived, MAVE/DMS, or other functional assay evidence affects PS3/BS3 strength, use `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`. That overlay adapts Brnich et al. 2019 ClinGen SVI functional-evidence guidance: start from no functional evidence, require disease-mechanism fit and assay-instance validation, use control-count or OddsPath calibration for strength, and avoid double-counting the same assay as PP3/BP4 or RNA-specific PVS1/BP7 evidence. Do not apply PS3 from case reports, segregation, HGMD/ClinVar labels, or another paper's ACMG classification unless the underlying functional assay is retrieved and evaluated by the PS3/BS3 overlay.

Multiple historical functional assays are not automatically cumulative. Count PS3/BS3 once at the strength justified by the most disease-relevant and best-validated assay, unless a current VCEP, OddsPath analysis, or explicit validated combination rule permits combining independent assays.

When the asserted or possible functional mechanism is dominant-negative, antimorphic, or mixed, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` first to decide whether the assay must test WT+variant interference, heterozygous/endogenous context, complex assembly, or pathway output. Then use the PS3/BS3 overlay for strength.

PP1/BS4 should be routed through `tooluniverse-acmg-pp1-segregation-refinement` when published family segregation, LOD/likelihood evidence, informative meioses, diagnostic yield, locus homogeneity/heterogeneity, reduced penetrance, phenocopy, or non-segregation affects evidence strength. That overlay owns PP1/BS4/PP4 combined scoring, the +5.0 cap, and evidence apportionment when segregation and phenotype specificity interact.

When a criterion requires patient phenotype, affected/unaffected status, disease specificity, diagnostic yield, tested/excluded loci, or alternate-diagnosis context, use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` for intake. If the criterion only needs disease-context inputs such as prevalence, penetrance, inheritance, mechanism, transcript, or frequency threshold, retrieve those through ToolUniverse disease/population resources and route directly to the evidence-specific overlay. If PP4 may combine with PP1/BS4, route scoring to the PP1 overlay.

For PS4 affected-case enrichment, use `tooluniverse-acmg-ps4-case-enrichment-refinement`. Prefer formal case-control evidence with odds ratio, confidence interval, ancestry-matched cases and controls, and disease-specific frequency context. When formal case-control data are unavailable, ACGS-style rare-disease counting may support `PS4_Supporting` for one unrelated affected individual with a rare/specific matching phenotype and absent population-control evidence, and `PS4_Moderate` for two or more unrelated affected individuals after duplicate-reporting, phenotype, ancestry, and control checks only as `practice/local refinement` unless a VCEP adopts those case-count rules. Recessive rare biallelic affected-proband evidence belongs in PM3, not PS4.

Founder haplotypes, shared ancestry, mutation-positive cohorts, or repeated reports in a case series are not ordinary case-control enrichment. Before using them for PS4, document the disease-case denominator, whether cases are unrelated, founder/duplicate status, ancestry-matched controls, and whether gnomAD is suitable as a control. Do not convert a mutation-positive proband denominator into a full disease-cohort enrichment statistic.

When ACMG evidence depends on visual material in a paper or supplement, such as pedigrees, segregation diagrams, Sanger traces, RT-PCR/minigene figures, gels, blots, or functional assay plots, use `tooluniverse-literature-figure-evidence-extraction` first to produce structured figure evidence. Then pass those extracted facts to the relevant evidence-specific overlay. Use `tooluniverse-image-analysis` only when the task requires quantitative image-derived measurements or statistics.

Low-confidence OCR, cropped figures, unreadable labels, or `not_interpretable` figure extraction can be used only as a lead. Do not upgrade PP1, PS4, PS3/BS3, PM3, or PS2/PM6 from figure evidence unless the figure extraction provides source/panel, sample ID, genotype, phenotype or assay readout, confidence, and ambiguity notes.

```python
PubMed_search_articles(query="BRCA2 c.5946delT functional assay", limit=10)
PubMed_search_articles(query="BRCA2 c.5946delT segregation family", limit=5)
```

Criteria requiring user-supplied patient or family clinical data (PS2, PM3, PM6, BS4, BP2, BP5, BS2, PP4, and some VCEP-specific rules) cannot be assessed automatically. Use routing-core status `not_assessed` and request targeted missing fields rather than inferring clinical data from variant annotation. PS4 is mixed: formal case-control, cohort, or meta-analysis evidence can be assessed from literature or cohort data when the publication defines cases, disease context, controls, ancestry handling, and statistics sufficiently; rare-disease affected-case counting still requires affected-case phenotype, unrelatedness, duplicate-report, and control context from the paper, database, or user. Use `tooluniverse-acmg-de-novo-evidence-refinement` for PS2/PM6 whenever de novo status, parental testing, parentage confirmation, parental mosaicism, or phenotype consistency is relevant.

Use standard user-input request blocks when fields are missing:

- `clinical_phenotype_needed`: HPO terms, clinical diagnosis, age, sex when relevant, age of onset, severity, tested/excluded diagnoses, and phenotype specificity.
- `pedigree_or_phase_needed`: affected/unaffected relatives, genotype status, relationship, age at evaluation, phenotype details, phasing method, and whether phenocopy or reduced penetrance is plausible.
- `de_novo_needed`: proband genotype, mother/father genotypes, biological relationship confirmation, parental mosaicism assessment, and phenotype consistency.
- `literature_source_needed`: PMID/DOI/source name, requested PDF/supplement/figure/table, why abstract-only evidence is insufficient, and affected criteria.
- `disease_context_needed`: disease entity, inheritance, mechanism, penetrance, prevalence, age of onset, and VCEP/gene-specific rule scope.

When affected-proband biallelic evidence is available for a recessive disorder, use `tooluniverse-acmg-pm3-in-trans-refinement` to score PM3 using ClinGen SVI PM3 v1.0 points while checking PM2-level rarity, phase, other-allele classification, and circularity. Recessive biallelic probands with genotype/phase evidence should route to PM3 rather than PS4 unless a VCEP specifies otherwise.

PM4 (protein length change in non-repeat region) and BP3 (in-frame indel in repeat) are routed through `tooluniverse-acmg-pm4-bp3-protein-length-refinement` in Phase 4. If an in-frame protein length change may preserve an altered product in a dominant-negative or complex-mediated disease context, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PM4 or BP3. BP7 (synonymous, no splice impact) is assessable via SpliceAI < 0.1 and RNA-specific BP7 through the PVS1/RNA splicing overlay when direct RNA evidence exists.

Before combining evidence, run an overlay compliance audit:

| Evidence source observed | Required route before counting |
| --- | --- |
| ClinVar, HGMD, LOVD, expert panel, paper classification, or lab report says P/LP/B/LB | PP5/BP6 source review, then primary evidence overlays; do not count the label itself. |
| Functional assay, MAVE/DMS, patient-derived cellular assay, animal model, protein/RNA assay | PS3/BS3 functional-assay overlay, unless RNA evidence is routed to PVS1/BP7 splicing. |
| Segregation, non-segregation, family pedigree, LOD, informative meioses | PP1/BS4/PP4 overlay, not PS3. |
| Case-control, cohort, meta-analysis, unrelated affected case counts | PS4 overlay, or PM3 if recessive biallelic probands with phase/genotype evidence. |
| Missense prediction scores | PP3/BP4 calibrated prediction overlay or VCEP; do not use local predictor voting. |
| Same codon/residue comparison variant | PS1/PM5 overlay; verify independent P/LP status and amino-acid-mediated mechanism. |
| Protein domain, hotspot, regional constraint, broad domain membership | PM1 overlay; broad domain membership alone is not enough. |

Hard-stop rule: if any evidence row in the final counted table lacks a valid route outcome, stop and label the report `draft classification`. The classification algorithm below is applied only after the audit table contains no un-routed counted criteria and evidence compatibility resolution has produced `current_counted_evidence_resolved` with no unresolved conflicts.

---

## Phase 7: Evidence Compatibility Resolution

After the hard-stop audit passes, run Evidence Compatibility Resolution through `tooluniverse-acmg-overlay-routing-core` before any final combination.

This gate does not assign evidence strength. It resolves already-routed evidence before combine by keeping, dropping, capping, splitting, deferring to VCEP, or blocking incompatible evidence.

Required outputs:

- `current_counted_evidence_resolved`: only these evidence items may enter final combine.
- `not_used_due_to_overlap`: evidence removed because the same primary evidence, proband, assay, source, mechanism, or region was consumed elsewhere.
- `caps_applied`: PM1+PP3, PP1+PP4, PM3 homozygous, PS2/PM6 high-heterogeneity, or VCEP caps.
- `context_splits`: separate disease, inheritance, mechanism, or transcript contexts that require separate classifications.
- `unresolved_conflicts`: unresolved conflicts that block final classification.

Use these compatibility rules unless a current VCEP explicitly supersedes them:

- BA1 valid excludes PM2/BS1; BS1/BS2 exclude PM2 for the same frequency or healthy-carrier rationale.
- Do not combine evidence across mutually exclusive diseases, inheritance models, mechanisms, or transcript contexts; split classifications when needed.
- PVS1 canonical splice excludes same-mechanism PP3; `PVS1_Strength (RNA)` excludes PS3 and same-mechanism PP3/BP4; `BP7_Strong (RNA)` excludes BS3 and contradicted PS1-splicing.
- PVS1 and PM4 cannot consume the same protein-length or LoF consequence; PM4 and BP3 are mutually exclusive; whole-gene deletion should not be double-counted as both PVS1 and separate CNV dosage evidence unless allowed.
- PS3/BS3 excludes the same assay, DMS, or MAVE source as PP3/BP4; multiple assays are not stacked unless VCEP, OddsPath, or a validated combination rule permits it.
- PP2 and BP1 are mutually exclusive; PM1/PP2/PP3 follows the PM1 overlay priority and PM1+PP3 cap; PM1/PM5/PM4 cannot reuse the same residue/domain rationale unless independent.
- PS1 and PM5 cannot both use the same comparison relationship; protein-level PS1/PM5 cannot use comparison variants whose pathogenicity is splicing/DNA/RNA-mediated.
- The same proband or individual cannot support PS4 plus PM3, PS2/PM6, PP1, or PP4.
- PP1/PP4 combined evidence is capped at +5.0 and cannot mix Biesecker points with informative-meioses fallback for the same pedigree.
- PM3 circularity, duplicate probands, homozygous cap, and PS2/PM6 high-genetic-heterogeneity cap must be resolved before final combine.
- PP5/BP6 source labels, abstract-only evidence, inaccessible full text, unread supplements, and low-confidence figure/OCR evidence cannot enter `current_counted_evidence_resolved`.
- Literature-backed counted evidence must include `literature_provenance` with full-text, supplement, and figure/table status. Abstract-only sources are retained as leads and should trigger full-text/supplement retrieval or a user PDF request; they are not counted unless a current VCEP explicitly allows abstract-level use and the exception is recorded in route audit.

If `unresolved_conflicts` is not empty, report `draft classification` and do not run ACMG qualitative or Bayesian final combine.

---

## Phase 8: Bayesian Evidence Combination

After compatibility resolution passes, use `tooluniverse-acmg-bayesian-classification-framework` to convert `current_counted_evidence_resolved` into Tavtigian et al. 2018 Bayesian points, OddsPath, posterior probability, and a structured final report.

This final combination layer is not an evidence-assignment overlay. It must not retrieve evidence, decide whether criteria are met, or change the strength assigned by evidence-specific overlays or VCEP rules.

Use these boundaries:

- If BA1 is valid, short-circuit before Bayesian calculation and report Benign by BA1 stand-alone.
- If any counted evidence lacks route outcome `overlay_applied` or `overlay_deferred_to_vcep`, output `draft classification` and do not compute final posterior probability.
- If evidence compatibility resolution has not produced `current_counted_evidence_resolved`, output `draft classification` and do not compute final posterior probability.
- If evidence compatibility resolution contains unresolved conflicts, output `draft classification` and do not compute final posterior probability.
- If a VCEP defines a disease-specific combining framework, follow the VCEP and report Tavtigian-style posterior only as optional context when appropriate.
- Do not use Bayesian points to convert source assertions, unrouted candidate evidence, abstract-only evidence, unread supplements, or low-confidence figure extraction into counted criteria.

The Bayesian framework reports both readable points and probability:

| Evidence strength | Points |
| --- | ---: |
| Pathogenic VeryStrong | `+8` |
| Pathogenic Strong | `+4` |
| Pathogenic Moderate | `+2` |
| Pathogenic Supporting | `+1` |
| Benign Strong | `-4` |
| Benign Supporting | `-1` |

Default formula from Tavtigian et al. 2018 and Supplemental Table S1:

```text
OddsPath = 350^(total_points / 8)
Post_P = OddsPath * 0.10 / ((OddsPath - 1) * 0.10 + 1)
```

Later benign strengths not present in Tavtigian et al. 2018, such as `BP4_Moderate`, `BP4_VeryStrong`, or `BS3_Moderate`, require explicit VCEP, ClinGen/SVI extension, or local-policy conversion before entering the Bayesian calculator.

---

## Classification Algorithm

Combine criteria at their resolved applied strength after overlay route audit and evidence compatibility resolution:

**Pathogenic**: (1) PVS1 + ≥1 Strong; (2) PVS1 + ≥2 Moderate; (3) PVS1 + 1 Moderate + 1 Supporting; (4) PVS1 + ≥2 Supporting; (5) ≥2 Strong; (6) 1 Strong + ≥3 Moderate; (7) 1 Strong + 2 Moderate + ≥2 Supporting; (8) 1 Strong + 1 Moderate + ≥4 Supporting

**Likely Pathogenic**: (1) PVS1 + 1 Moderate; (2) 1 Strong + 1-2 Moderate; (3) 1 Strong + ≥2 Supporting; (4) ≥3 Moderate; (5) 2 Moderate + ≥2 Supporting; (6) 1 Moderate + ≥4 Supporting

**Benign**: (1) BA1 stand-alone; (2) ≥2 Strong benign

**Likely Benign**: (1) 1 Strong benign + 1 Supporting benign; (2) ≥2 Supporting benign

**VUS**: Criteria do not meet any threshold above, OR pathogenic and benign evidence conflict.

---

## Output Format

```markdown
# ACMG Variant Classification Report

## Variant Normalization
- Variant:
- Gene:
- Transcript:
- Genome build:
- Consequence:

## Disease / Mechanism Context
- Disease context:
- Inheritance:
- Mechanism:
- Multiple-disorder boundary:
- Penetrance context:
- VCEP context:

## Evidence Retrieval Coverage
- Population:
- Computational:
- Clinical databases and source assertions:
- Literature and supplements:
- Functional / segregation / case evidence:

## Bundle Route Plan
| Bundle | Trigger found? | Required overlays/checks | Coverage required | Status | Reason |
| --- | --- | --- | --- | --- | --- |

## Overlay Results
| Overlay / VCEP | Criterion | Status | Applied evidence | Guidance authority | Consumed evidence | Reason |
| --- | --- | --- | --- | --- | --- | --- |

## Overlay Route Audit
| Criterion | Route bundle | Proposed evidence | Route outcome | Guidance authority | Overlay or VCEP source | Counted? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Evidence Compatibility Resolution
- current_counted_evidence_resolved:
- not_used_due_to_overlap:
- caps_applied:
- context_splits:
- unresolved_conflicts:

| Conflict group | Evidence items | Conflict type | Resolution | Kept evidence | Removed/capped evidence | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Current Counted Evidence Resolved
| Criterion | Direction | Strength | Points | Evidence | Overlay route outcome | Source |
| --- | --- | --- | ---: | --- | --- | --- |

## Bayesian Calculation
- Model: Tavtigian et al. 2018 Bayesian ACMG/AMP framework
- Prior probability:
- Very Strong OddsPath:
- Exponential progression:
- Total points:
- OddsPath:
- Posterior probability:
- Formula source:

## Final Classification
- Classification status: [final classification / draft classification]
- Classification: [PATHOGENIC / LIKELY PATHOGENIC / VUS / LIKELY BENIGN / BENIGN / not computed because route audit failed]
- ACMG/AMP qualitative table comparison:
- VCEP override, if any:

## Source Assertions / Leads
machine key: `source_assertions_or_leads`

| Source | Assertion | Why not counted directly | Routed primary evidence |
| --- | --- | --- | --- |

## Missing Evidence / Not Assessed
machine key: `missing_not_assessed`

| Criterion | Missing field or unavailable source | Impact |
| --- | --- | --- |

## User-Needed Inputs
machine key: `user_needed_inputs`

| Missing input type | Requested details | Why needed | Affected criteria |
| --- | --- | --- | --- |
```

---

## Common Patterns

**Pattern 1: Known pathogenic frameshift** — "Classify BRCA2 c.5946delT"
Phase 0 (validate) → Phase 1 (gnomAD absent, PM2_Supporting) → Phase 3 (ClinVar Pathogenic assertion used as lead only; no PP5) → Phase 4 (DNA repair domain, PM1 if overlay confirms an eligible critical region) → Phase 5 (frameshift + LOF gene, PVS1 decision-tree overlay) → Phase 6 (functional assay evidence routed to PS3/BS3 if present)
Result: **Pathogenic** (PVS1 + PS3 + PM1 + PM2_Supporting; PP5 not counted)

**Pattern 2: Missense VUS** — "Is BRCA1 p.Arg1699Gln pathogenic?"
Phase 0 → Phase 1 (rare, PM2_Supporting) → Phase 2 (REVEL 0.82, PP3_Moderate by calibrated missense-prediction overlay) → Phase 3 (ClinVar VUS) → Phase 4 (BRCT domain, PM1; PM1+PP3 contribution capped at Strong) → Phase 6 (reduced activity, PS3_Moderate)
Result: **Likely Pathogenic** (PS3_Moderate + PM1 + PM2_Supporting + PP3_Moderate, with PM1+PP3 cap applied)

**Pattern 3: Common benign variant** — "ACMG for rs1800497"
Phase 1 (gnomAD AF=0.21, BA1 exception-list overlay confirms no exception and adequate general population data) → short-circuit. Result: **Benign** (BA1 stand-alone)

**Pattern 4: Deep-intronic variant** — "Classify NM_000059.4:c.7977+100A>G"
Phase 1 (check AF) → Phase 5 (SpliceAI < 0.1) → Result: **Likely Benign** or VUS depending on frequency
