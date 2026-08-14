# ACMG two-call quick start

Normal evaluation uses one collector call and one Guard call. Do not discover
the already-known tools or write the result to a file.

## Native compact MCP

Call `execute_tool`:

```json
{
  "tool_name": "ACMG_evidence_collector",
  "arguments": {
    "variant": "NM_000059.4:c.5946delT",
    "gene": "BRCA2",
    "disease": "MONDO:0011450",
    "inheritance": "autosomal dominant",
    "response_detail": "summary"
  }
}
```

Draft the evidence-only response from the returned `evidence_cards`, source
indexes, VCEP/CSpec scenarios, estimates, conflicts, and limitations. Then call
`execute_tool` again:

```json
{
  "tool_name": "ACMG_guard_final_answer",
  "arguments": {
    "final_answer_text": "<draft evidence-only answer>",
    "guard_context": {"<exact object returned by collector>": "..."}
  }
}
```

Pass `guard_context` as an object, unchanged—not as a manually rebuilt list or
a file path.

## Reasonix capability proxy

Collector:

```json
{
  "action": "call",
  "capability_id": "mcp-tool:tooluniverse/execute_tool",
  "arguments": {
    "tool_name": "ACMG_evidence_collector",
    "arguments": {
      "variant": "NM_000059.4:c.5946delT",
      "gene": "BRCA2",
      "response_detail": "summary"
    }
  }
}
```

Guard:

```json
{
  "action": "call",
  "capability_id": "mcp-tool:tooluniverse/execute_tool",
  "arguments": {
    "tool_name": "ACMG_guard_final_answer",
    "arguments": {
      "final_answer_text": "<draft evidence-only answer>",
      "guard_context": {"<exact object returned by collector>": "..."}
    }
  }
}
```

## Optional inputs

- Put user-provided case/family/phase/assay facts in
  `clinical_observations`; `clinical_context` is background only.
- Use `literature_proposals` or `cspec_proposals` only to add unresolved
  externally extracted material.
- Use `evidence_decisions` for accept/reject or a direction-consistent
  `strength_override`; only an override requires a reason. `reviewer` and
  `decided_at` remain optional.

The result remains evidence-only: display `automatic_bayesian`,
`verified_bayesian`, optional `user_selected_bayesian`, and conflicts, but do
not convert them into ToolUniverse's own five-tier label.
