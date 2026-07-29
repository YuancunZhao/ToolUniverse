# ACMG Evidence Assessment Quick Start

1. Call `ACMG_evidence_collector` with at least `variant` and, when known,
   `gene`, `transcript`, `disease`, and `inheritance`.
2. Review `coverage_summary` and `limitations`. A partial provider failure must
   remain visible and must not masquerade as deterministic evidence.
3. Treat `source_assertions` as external leads. Use `source_facts` for observed
   values and `evidence_cards` for criterion/strength suggestions.
4. Review `rule_context.cspec_review_requests`. For CSpec prose, the host LLM
   submits `cspec_proposals` with specification ID, version, content hash,
   criterion, locator/excerpt, structured interpretation, confidence, and
   extractor version. ToolUniverse re-fetches the online CSpec and verifies
   every anchor.
5. For papers, the host LLM submits `literature_proposals` with PMID/PMCID,
   fact type, locator, excerpt, per-field excerpts, structured facts,
   interpretation, confidence, extractor version, and unresolved questions.
   Criterion/strength are optional suggestions; ToolUniverse applies the
   allowed fact-type mapping after re-fetching the full text.
6. Review `system_preview_bayesian` and `conflict_report`. This is a review
   estimate; card inclusion is represented only by
   `system_preview_included`.
7. After user review, call the collector again with `evidence_decisions`
   (`card_id`, `accept|reject`, optional reasoned `strength_override`) and use
   `user_selected_bayesian`. Unmatched card IDs do not affect other evidence.
8. Use `ACMG_guard_final_answer`; do not return a five-tier final label in this
   evidence-only phase.

For one evidence domain, call the matching `ACMG_*_evidence` group tool. These
tools and the collector share the same pure rule functions.

## Three-phase BRCA2 example

Initial collection:

```json
{
  "variant": "NM_000059.4:c.5946delT",
  "gene": "BRCA2",
  "disease": "MONDO:0011450",
  "inheritance": "autosomal dominant",
  "response_detail": "summary"
}
```

After the host LLM anchors an applicable paper or CSpec passage, repeat the
same call with `literature_proposals` and/or `cspec_proposals`. After review,
repeat it with:

```json
{
  "evidence_decisions": [
    {
      "card_id": "<stable-card-id-returned-by-the-previous-call>",
      "decision": "accept"
    }
  ]
}
```

`reviewer` and `decided_at` are optional provenance fields. Their absence never
blocks the call or changes compatibility or Bayesian scoring. Finally call:

```json
{
  "final_answer_text": "<draft evidence-only answer>",
  "collector_result": "<complete collector result>"
}
```

with `ACMG_guard_final_answer`.
