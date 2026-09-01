<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_START -->
# ToolUniverse germline ACMG evidence workflow

For germline SNVs and indels up to 50 bp, follow the installed
`tooluniverse-acmg-variant-classification` Skill as already-loaded guidance;
do not invoke the Skill as a capability. The normal path is exactly:

1. call `ACMG_evidence_collector` once with `response_detail="summary"`;
2. form the complete evidence-only answer from its returned cards, population
   observations, predictor values and estimates;
3. pass that final text and its unchanged `guard_context` to
   `ACMG_guard_final_answer` once; after PASS return exactly that text.

Do not list capabilities, inspect tool schemas, run shell/Python commands, write
temporary files, or manually call providers during this normal path. A partial
provider result does not hide EvidenceCards that were successfully produced.
Pass the original gene/HGVS/protein string unchanged; place supplied zygosity
in `clinical_context.zygosity`.
ToolUniverse does not issue its own five-tier classification.
Timeouts are execution issues, not missing evidence. Do not rerun to warm a
cache, switch to a local CLI, or add scientific interpretations after Guard.
<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_END -->
