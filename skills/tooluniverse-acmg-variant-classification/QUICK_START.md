# ACMG Evidence Automation v3 Quick Start

## One-call automatic collection

```json
{
  "variant": "NM_000059.4:c.5946delT",
  "gene": "BRCA2",
  "disease": "MONDO:0011450",
  "inheritance": "autosomal dominant",
  "response_detail": "summary"
}
```

Call `ACMG_evidence_collector`. If identity is not blocked, report:

1. EvidenceCards with source, criterion, strength, evidence status, rule source,
   verification dimensions, calculation roles, and caveats;
2. exact VCEP assertions with explicit attribution;
3. isolated CSpec/VCEP rule scenarios;
4. `automatic_bayesian`, `verified_bayesian`, and conflicts;
5. `user_selected_bayesian` only when decisions were supplied.

The collector performs consequence fallback, literature retrieval and rule
extraction, and online CSpec/VCEP discovery. Do not ask the user to approve
these read-only steps and do not require a host LLM proposal for normal output.

## Structured clinical observations

```json
{
  "variant": "NM_000059.4:c.5946delT",
  "gene": "BRCA2",
  "clinical_observations": [
    {
      "observation_id": "family-001",
      "observation_type": "segregation",
      "source_type": "lab_report",
      "source_id": "report-001",
      "locator": "pedigree page 3",
      "values": {
        "informative_meioses": 4,
        "phenotype_consistent": true
      }
    }
  ]
}
```

Caller-supplied observations can generate source-backed candidates for the
automatic estimate. A re-fetchable publication, provider, or report anchor is
required for the verified estimate. `clinical_context` remains retrieval
background and does not itself create case or family evidence.

## Optional supplements

Use `literature_proposals` or `cspec_proposals` only to supplement unresolved
prose or reproduce an earlier extraction. The collector validates source IDs,
locators, excerpts, document/specification hashes, fact types, and legal
criterion directions. Without these optional inputs it must still return
source-backed candidates and automatic scoring.

## User decisions

```json
{
  "variant": "NM_000059.4:c.5946delT",
  "gene": "BRCA2",
  "evidence_decisions": [
    {
      "card_id": "<stable card id>",
      "decision": "accept"
    }
  ]
}
```

Use `decision=accept|reject`. A direction-consistent `strength_override`
requires `reason`. `reviewer` and `decided_at` are optional and never change
eligibility or calculation.

## Final answer guard

```json
{
  "final_answer_text": "<draft evidence-only answer>",
  "guard_context": "<guard_context returned by the collector>"
}
```

Call `ACMG_guard_final_answer`. A VCEP label may be stated only as an attributed
external assertion. ToolUniverse does not output its own five-tier final
classification; `final_classification_allowed` remains `false`.
