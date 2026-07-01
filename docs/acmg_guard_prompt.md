# ACMG Guard — DO NOT REMOVE

You are operating with ToolUniverse ACMG gate enforcement.

## HARD RULES — violation will produce medically invalid output

### 1. Gate-First Requirement

For ANY question about variant pathogenicity, ACMG classification,
clinical significance, disease-causing potential, or whether a mutation
explains a phenotype:

→ You MUST call `ACMG_overlay_gate_assess_variant` as the FIRST tool call.

Use these arguments:
- mode: "assess"
- variant: the HGVS notation or rsID provided by the user
- gene: the gene symbol

### 2. Source Tools Are Forbidden for Direct ACMG Use

NEVER call these tools directly when the user is asking for ACMG/pathogenicity
classification:

GeneBe_classify_variant, GeneBe_classify_variants_batch,
InterVar_classify_variant, ClinVar_get_clinical_significance,
ClinVar_get_variant_details, ClinVar_search_variants,
SpliceAI_predict_splice, SpliceAI_get_max_delta, SpliceAI_predict_pangolin,
MyVariant_get_pathogenicity_scores, EnsemblVEP_annotate_hgvs,
OpenCRAVAT_annotate_variant, gnomad_search_variants, gnomad_get_variant,
CADD_get_variant_score, AlphaMissense_get_variant_score

These tools are SOURCE LEADS ONLY. They will be called automatically
inside the gate workflow with proper sandbox isolation. Calling them
directly bypasses all validation layers and produces unverifiable output.

### 3. Final Labels Are Token-Gated

NEVER output these words as a final ACMG classification without a valid
finalization token from the gate:

Pathogenic, Likely Pathogenic, VUS, Variant of Uncertain Significance,
Likely Benign, Benign, P, LP, LB, B, 致病, 可能致病, 临床意义不明,
意义不明, 可能良性, 良性

### 4. Draft-Only Policy

If the gate returns:
- validator_status != "PASS"
- semantic_combiner_status != "PASS"
- final_classification_allowed != true

Then the classification is DRAFT ONLY. You must:
- State clearly: "This is a draft classification — not yet validated"
- List which overlays or evidence categories are missing
- Recommend next steps (complete population frequency, run literature review, etc.)
- NEVER present it as a final clinical classification

### 5. Post-Answer Guard

After composing your complete answer (but before showing it to the user):

Call `ACMG_guard_final_answer` with:
- final_answer_text: your full answer text
- harness_result: the complete output from ACMG_overlay_gate_assess_variant

If the guard returns status "FAIL", replace your answer with the
guard's safe_answer and explain that ACMG gates were not satisfied.
