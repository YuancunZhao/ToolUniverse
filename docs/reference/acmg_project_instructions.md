<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_START -->
# ToolUniverse germline ACMG evidence workflow

For germline SNVs and indels up to 50 bp, follow the installed
`tooluniverse-acmg-variant-classification` Skill. The normal path is exactly:

1. call `ACMG_evidence_collector` once with `response_detail="summary"`;
2. draft the evidence-only answer from its returned cards and estimates;
3. pass its `guard_context` unchanged to `ACMG_guard_final_answer` once.

Do not list capabilities, inspect tool schemas, run shell/Python commands, write
temporary files, or manually call providers during this normal path. A partial
provider result does not hide EvidenceCards that were successfully produced.
ToolUniverse does not issue its own five-tier classification.
<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_END -->
