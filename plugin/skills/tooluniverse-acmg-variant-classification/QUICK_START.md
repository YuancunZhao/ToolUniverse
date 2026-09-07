# ACMG two-call quick start

The v4.7 summary includes card `observed_facts`, explicit criterion statuses,
literature titles, review-only incomplete/negative facts, and per-query
`literature_review.search_summary`. These do not change scientific thresholds.
Optional retrieval controls, omitted in normal calls:

```json
{"literature_search_limits":{"pubmed":50,"europe_pmc":100,"litvar":50,"pubtator":10},"fulltext_match_classes":["exact_variant_match","equivalent_variant_match","provider_linked_variant_match"]}
```

Each provided limit must be an integer from 1 to 1000. Empty match classes
disable normal fulltext retrieval, but not submitted proposal re-anchoring.
Review-only facts and invalid-card diagnostics are not EvidenceCards.

Normal evaluation uses one collector call and one Guard call. Do not discover
the already-known tools or write the result to a file.

The Skill is execution guidance, not another capability to call. Preserve an
original `GENE;NM_:c.(p.)` input string in `variant`; if zygosity was supplied,
place it in `clinical_context.zygosity`.

## Native compact MCP

Wait for the configured MCP response; a timeout is not a negative evidence
result. Do not switch to a local CLI or repeat collection to warm a cache.
Send the complete final response to Guard and return exactly the checked text
after PASS. Population values are in `population_observations` even without a
PM2 card; consequence summary groups use `shared`, `columns`, and `rows`.
40 KB is a soft optimization target, not a failed-collection status. Use larger
summaries directly with the same two calls; do not fetch full or write files
just because of size. Referenced sources are in `source_facts`. Grouped
`other_card_results.card_ids` retains every atomic result without resumming it.
Give the evidence table, estimates, conflicts and important limitations; the
complete background indexes remain in the tool result without being recited.
Literature retrieval is internal: PMC/JATS is preferred, PubTator BioC is an
independent fallback, and open-access PDF snippets are last resort. Do not retry
the collector merely because PubTator search failed; the same run continues
through the remaining sources.

Internal recovery is not an extra host call: the collector retries transient
failures once and falls back to named transcript/disease providers. If recovery
is exhausted, `recoverable_gaps.repair_plan` supports an optional targeted
enrichment round. Follow its argument dependencies without guessing coordinates
or changing the selected NM. Submit original named-tool results, query, version
and retrieval timestamp as `caller_verified_context`; attribution alone is not
independent verification. Only after the new collector result is returned may
you draft and Guard a new answer. Do not reuse an earlier Guard context or
repeat an identical failed recovery step. Normal runs still use two calls.

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

For example, do not shorten
`RTEL1;NM_001283009.2:c.3718G>C(p.Ala1240Pro)`: pass it unchanged and add
`"clinical_context":{"zygosity":"heterozygous"}` when that was reported.

Draft the evidence-only response from the returned `evidence_cards`, source
indexes, VCEP/CSpec scenarios, estimates, conflicts, and limitations. Then call
`execute_tool` again:

When reading `consequence_profile`, do not treat an empty/failed provider or an
alternate-transcript annotation as a vote against the selected transcript.
Different normalization-only HGVS strings are preserved in
`equivalent_or_alternate_representations` and are not allele conflicts unless
authoritative genomic build/coordinate/ref/alt facts actually disagree.
For SpliceAI, use the selected-transcript four-channel values; the provider-
global maximum is context only.

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
a file path. Its compact `criterion_review_claims` allow accurate statements
such as “PVS1 is insufficiently informed” without creating a PVS1 EvidenceCard.

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
  externally extracted material. Read `proposal_report` for the disposition of
  every submitted item. A document-hash/excerpt/locator-backed external review
  card remains outside automatic and verified estimates.
- Use `evidence_decisions` for accept/reject or a direction-consistent
  `strength_override`; an external review card without a mapped strength needs
  that override and a reason. `reviewer` and `decided_at` remain optional.

The result remains evidence-only: display `automatic_bayesian`,
`verified_bayesian`, optional `user_selected_bayesian`, and conflicts, but do
not convert them into ToolUniverse's own five-tier label.
