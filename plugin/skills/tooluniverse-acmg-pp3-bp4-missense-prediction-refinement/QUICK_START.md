# Quick Start: PP3/BP4 Missense Prediction Refinement

Use this overlay inside `tooluniverse-acmg-variant-classification` when a missense variant needs computational evidence assignment.

## Minimal Workflow

1. Normalize the variant and confirm the classified transcript/protein consequence is missense.
2. Check whether a current VCEP rule specifies a different computational tool or threshold.
3. Before reading prediction scores, choose one calibrated tool or follow a pre-specified hierarchy.
4. Retrieve scores with ToolUniverse, preferably `MyVariant_get_pathogenicity_scores`, `OpenCRAVAT_annotate_variant`, or Ensembl VEP.
5. Map the selected score to the Pejaver et al. 2022 calibrated threshold table.
6. Assign one code only: `PP3_*`, `BP4_*`, or no computational evidence.

If an aggregator such as OpenCRAVAT returns `pp3_pathogenic` or `bp4_benign`, use that label only as a cross-check. The applied evidence code must come from the raw score and the Pejaver calibrated interval.

## Example Tool Sequence

```text
VariantValidator_validate_variant(variant="...")
EnsemblVEP_annotate_hgvs(hgvs_notation="...")
MyVariant_get_pathogenicity_scores(variant_id="...")
OpenCRAVAT_annotate_variant(chrom="chr...", pos=..., ref_base="...", alt_base="...", annotators="revel,cadd_exome,sift,polyphen2,vest,primateai,fathmm")
```

## Expected Behaviors

### REVEL high pathogenic score

Input evidence: missense variant; REVEL selected before score review; REVEL = 0.95.

Expected: apply `PP3_Strong`, because REVEL >= 0.932 is calibrated as `PP3_Strong`.

### REVEL moderate pathogenic score

Input evidence: missense variant; REVEL selected; REVEL = 0.80.

Expected: apply `PP3_Moderate`, because 0.80 falls in [0.773, 0.932).

### REVEL benign-supporting score

Input evidence: missense variant; REVEL selected; REVEL = 0.20.

Expected: apply `BP4_Supporting`, because 0.20 falls in (0.183, 0.290].

### REVEL benign-moderate score

Input evidence: missense variant; REVEL selected; REVEL = 0.05.

Expected: apply `BP4_Moderate`, because 0.05 falls in (0.016, 0.183]. Record a downstream combiner note if the classifier does not natively support moderate benign evidence.

### CADD 20

Input evidence: missense variant; CADD PHRED = 20.

Expected: do not apply `PP3`. Under Pejaver et al., CADD 20 is inside the `BP4_Moderate` interval, not a pathogenic interval.

### SIFT/PolyPhen-2 defaults

Input evidence: SIFT is "deleterious" at the common 0.05 threshold and PolyPhen-2 is "probably damaging" at the developer default.

Expected: do not apply `PP3` from these defaults. Use only calibrated intervals. SIFT requires exactly 0 for `PP3_Moderate` or (0, 0.001] for `PP3_Supporting`; PolyPhen-2 HumVar requires >=0.999 for `PP3_Moderate` or [0.978, 0.999) for `PP3_Supporting`.

### Multiple predictors conflict

Input evidence: REVEL suggests `PP3_Moderate`, CADD suggests `BP4_Supporting`, and no pre-specified tool or hierarchy existed before score review.

Expected: do not cherry-pick. Either use a documented pre-existing local/VCEP hierarchy, or mark computational evidence as non-applied context.

### Aggregator-provided PP3/BP4 label

Input evidence: OpenCRAVAT returns both a raw REVEL score and a convenience `pp3_pathogenic` label.

Expected: do not apply the convenience label directly. Recalculate the evidence code from the raw REVEL score using the Pejaver interval table, then record the aggregator label only as a consistency check.

### PM1 and PP3 both met

Input evidence: variant lies in a PM1-qualified hotspot and REVEL = 0.95.

Expected: retain `PM1` and `PP3_Strong` as separately documented codes only if independent enough, but cap their combined pathogenic contribution at Strong unless a VCEP gives a different rule.

### Prediction-only splice concern

Input evidence: variant is exonic or near splice region; high SpliceAI; missense predictor score also available.

Expected: do not treat splice prediction as missense `PP3/BP4`. Resolve splicing evidence with a splicing-specific overlay. Use this overlay only for the missense impact question, and avoid double counting.

### Functional assay or DMS result

Input evidence: DMS or functional assay shows damaging protein effect.

Expected: do not count the same assay as `PP3`. Evaluate it with `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.

### VCEP-specific rule exists

Input evidence: disease-specific VCEP specifies a gene-specific REVEL threshold or a different predictor.

Expected: use the VCEP rule first and cite it. Use the Pejaver genome-wide calibration only as background if the VCEP does not supersede it.

## Reporting Template

```text
Computational evidence: [applied code or none].
Selected tool: [tool], selected because [VCEP/local hierarchy/default hierarchy].
Score: [score] from [ToolUniverse source].
Calibration: Pejaver et al. 2022 interval [interval].
Reasoning: [why PP3/BP4 applies or does not apply].
Double-counting check: [PM1 cap, splicing exclusion, functional assay exclusion].
Combiner note: [BP4_Moderate handling if relevant].
```
