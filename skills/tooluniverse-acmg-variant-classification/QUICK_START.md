# ACMG Evidence Assessment Quick Start

1. Call `ACMG_evidence_collector` with at least `variant` and, when known,
   `gene`, `transcript`, `disease`, and `inheritance`.
2. Inspect `workflow_status`, `recoverable_gaps`, and `next_actions` before
   drafting an answer. The collector automatically runs applicable
   multi-provider consequence recovery; a VEP failure is not a stopping point.
   A partial provider failure remains visible and cannot masquerade as
   deterministic evidence.
3. Treat `source_assertions` as external leads. Use `source_facts` for observed
   values and `evidence_cards` for criterion/strength suggestions.
4. Execute every pending host action without asking the user whether to
   continue. For CSpec prose, submit `cspec_proposals` with specification ID,
   version, content hash, criterion, locator/excerpt, structured
   interpretation, confidence, and extractor version. ToolUniverse re-fetches
   the online CSpec and verifies every anchor.
5. For every exact/equivalent paper request, try the listed full-text tools in
   order, read the complete accessible text section by section, and inspect
   relevant tables, figures, captions, and supplements. Submit
   `literature_proposals` with PMID/PMCID, fact type, locator, excerpt,
   per-field excerpts, structured facts, interpretation, confidence, extractor
   version, unresolved questions, and a `reading_manifest`. Abstract-only or
   unavailable papers remain source leads.
6. Review `system_preview_bayesian` and `conflict_report`. This is a review
   estimate; card inclusion is represented only by
   `system_preview_included`.
7. If proposals were submitted, automatically call the collector again. Process
   only newly discovered request IDs on a possible final incremental pass.
   Do not end while a recoverable consequence gap or mandatory full-text
   request remains.
8. After user review, call the collector again with `evidence_decisions`
   (`card_id`, `accept|reject`, optional reasoned `strength_override`) and use
   `user_selected_bayesian`. Unmatched card IDs do not affect other evidence.
9. Use `ACMG_guard_final_answer`; do not return a five-tier final label in this
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

Follow returned `next_actions` immediately. After the host LLM anchors an
applicable paper or CSpec passage, repeat the same call with
`literature_proposals` and/or `cspec_proposals`; this is part of automatic
evidence collection, not the user decision round. A literature proposal should
also include:

```json
{
  "reading_manifest": {
    "status": "complete",
    "sections_read": ["methods", "results", "discussion"],
    "tables_read": ["Table 1"],
    "figures_read": ["Figure 2"],
    "supplements_read": [],
    "variant_match_locations": ["Table 1, row 4"],
    "limitations": []
  }
}
```

Only after the user asks to select evidence, repeat the call with:

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
