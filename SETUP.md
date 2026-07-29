# ToolUniverse Scientific Toolkit with Enhanced ACMG Evidence Review

This fork retains the complete user-facing ToolUniverse biological research
Skill bundle and approximately 2,600 scientific tools. It adds an evidence-only
germline small-variant ACMG workspace that collects provider information,
applies versioned ClinGen/SVI or uniquely matched CSpec rules, reports evidence
conflicts, and calculates Bayesian review estimates. It does not issue a
five-tier ACMG classification.

The repository keeps the upstream plugin layout, compact MCP model, canonical
Skill source, client-specific generated mirrors, and ordinary ToolUniverse
installation guidance. The exact-SHA procedure in this document is a narrow
deployment extension for the enhanced ACMG runtime; it is not a replacement for
the standard upstream installation at
<https://github.com/mims-harvard/ToolUniverse#install>.

## Validated release

Install the exact validated runtime commit instead of a floating branch:

```text
Repository: https://github.com/YuancunZhao/ToolUniverse
Branch:     codex/acmg-on-tooluniverse-1.4
Commit:     911200550b10600ded44b36dcb614c25ff06e0e6
```

This commit passed the 379-test ACMG/SpliceAI/provider suite, MCP registration
checks, Skill mirror checks, wrapper/schema checks, and local plus exact-Git-SHA
isolated installation smoke tests.

The Claude and Codex plugin MCP manifests must use this same validated SHA.
Advance all three references only after a new runtime commit has passed the
exact-Git-SHA installation smoke test.

## One-line installation prompt

Copy this sentence into another AI agent:

> Read https://raw.githubusercontent.com/YuancunZhao/ToolUniverse/codex/acmg-on-tooluniverse-1.4/SETUP.md, then install and verify the complete ToolUniverse scientific Skill bundle and ACMG evidence-only extension from exact commit `911200550b10600ded44b36dcb614c25ff06e0e6` for my current AI client. Preserve unrelated MCP servers and skills.

## MCP configuration

Install `uv` if necessary. Merge the following server entry into the current
client's MCP configuration. Preserve unrelated servers and replace only an
existing `tooluniverse` entry:

```json
{
  "command": "uvx",
  "args": [
    "--refresh",
    "--from",
    "git+https://github.com/YuancunZhao/ToolUniverse.git@911200550b10600ded44b36dcb614c25ff06e0e6",
    "tooluniverse"
  ],
  "env": {
    "PYTHONIOENCODING": "utf-8"
  }
}
```

Common client configuration files:

| Client | MCP configuration |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Codex | `~/.codex/mcp.json` |

Validate the edited file as JSON before restarting the client.

## Install the complete ToolUniverse Skill bundle

Install the same user-facing Skill surface shipped by the ToolUniverse plugins.
This includes the general router and all `tooluniverse-*` research and
supporting Skills, including the enhanced ACMG workflow. Internal `devtu-*` and
skill-authoring directories are not installed.

This section is for an exact-SHA ACMG deployment. Standard upstream Codex and
Claude Code users should install the corresponding marketplace plugin, which
already bundles its Skills; do not install both a marketplace plugin and a
second global copy of the same Skills. The exact-SHA installer is retained here
because a floating upstream plugin or `npx skills add` cannot reproduce this
branch's ACMG runtime and Skill contract.

Set `SKILLS_DIR` and `SKILLS_PROFILE` first:

| Client | Skills directory | Profile |
|---|---|---|
| Claude Code | `~/.claude/skills` | `claude` |
| Claude Desktop | `~/.claude/skills` | `claude` |
| Codex | `~/.agents/skills` | `codex` |
| Cursor | `~/.cursor/skills` | `generic` |
| Windsurf | `~/.windsurf/skills` | `generic` |

Then run:

```bash
TOOLUNIVERSE_COMMIT="911200550b10600ded44b36dcb614c25ff06e0e6"
: "${SKILLS_DIR:?Set SKILLS_DIR before installing ToolUniverse skills}"
: "${SKILLS_PROFILE:?Set SKILLS_PROFILE to codex, claude, or generic}"

tmp_dir="$(mktemp -d)"
git init -q "$tmp_dir"
git -C "$tmp_dir" remote add origin \
  https://github.com/YuancunZhao/ToolUniverse.git
git -C "$tmp_dir" fetch --depth 1 origin "$TOOLUNIVERSE_COMMIT"
git -C "$tmp_dir" checkout -q --detach FETCH_HEAD

bash "$tmp_dir/scripts/install_tooluniverse_skills.sh" \
  --client "$SKILLS_PROFILE" \
  --dest "$SKILLS_DIR"

rm -rf "$tmp_dir"
```

The installer replaces only current ToolUniverse Skill names, removes the
retired `tooluniverse-acmg-overlay-routing-core` and criterion-specific
`tooluniverse-acmg-*refinement` directories, and preserves unrelated user
Skills.

## Runtime tools

Compact MCP exposes a small discovery/execution surface while keeping
approximately 2,600 scientific tools available through `find_tools`,
`get_tool_info`, and `execute_tool`. Within that complete runtime, the installed
package must expose exactly these eight ACMG-specific tools:

- `ACMG_evidence_collector`
- `ACMG_population_evidence`
- `ACMG_computational_evidence`
- `ACMG_clinical_evidence`
- `ACMG_functional_evidence`
- `ACMG_literature_evidence`
- `ACMG_guard_final_answer`
- `ACMG_overlay_gate_assess_variant`

`ACMG_evidence_collector` is the single full-pipeline entry point.
`ACMG_overlay_gate_assess_variant` is only a thin compatibility alias with the
same parameters and return structure. It has no separate mode or business
logic.

## Current collector interface

The collector accepts:

- `variant`
- optional `gene`, `transcript`, `disease`, `inheritance`, and `genome_build`
- optional `protein_accession`
- optional `clinical_context`, including `hpo_terms`
- optional `source_outputs_or_leads`
- optional `literature_proposals`
- optional `cspec_proposals`
- optional `evidence_decisions`
- `response_detail`: `summary` or `full`

The current interface intentionally does not accept the removed compatibility
fields `literature_facts`, scalar `spliceai_dl`, or overlay `mode`.

The principal outputs are:

- `source_facts` and `source_assertions`
- `coverage_summary`
- `consequence_profile`
- `predictor_scores`
- `literature_candidates`
- `rule_context`
- `runtime_manifest`
- `criterion_reviews`
- `evidence_cards`
- `compatibility_report` and `conflict_report`
- `system_preview_bayesian`
- `user_selected_bayesian`
- `decision_report`
- `limitations`

Evidence-card inclusion is represented by `system_preview_included` and
`user_selected_included`. The removed output fields `counted`,
`included_in_candidate_bayesian`, `counted_criteria`, and
`bayesian_estimate` must not appear.

## Evidence workflow

### 1. Initial collection

Call the collector with all known identity and clinical context:

```json
{
  "variant": "NM_000059.4:c.5946delT",
  "gene": "BRCA2",
  "genome_build": "GRCh38",
  "clinical_context": {
    "hpo_terms": ["HP:0003002"]
  },
  "response_detail": "summary"
}
```

The collector performs conditional exhaustive collection:

- verified gene identity enables ClinGen validity, dosage, adult and pediatric
  actionability, variant-classification leads, and gnomAD constraint;
- variant identity enables ClinVar, gnomAD frequency/coverage, MyVariant,
  SpliceAI, LitVar, PubMed, and Europe PMC as applicable;
- resolved protein identity enables UniProt, EBI Proteins, and InterPro;
- explicit HPO IDs enable term, gene-association, and disease-association
  queries; free text is searched but ambiguous candidates are not selected.

An inapplicable provider is reported as `not_applicable`. An attempted provider
that fails, returns no result, lacks a version, or conflicts with identity
remains visible with its reason. One provider failure must not suppress the
other sources.

Database classifications, actionability, constraint metrics, phenotype
matches, and uncalibrated predictor outputs are review-only source leads. They
are not automatically converted into EvidenceCards.

Provider contracts worth checking:

- ClinVar search uses exact variation ID, rsID, or transcript-bound HGVS
  representations and fails closed on ambiguous identity. Details and
  significance use one `data` envelope with the unprocessed record only in
  `data.raw_data`; `formatted_data` is not supported.
- ACMG gene constraint uses only `gnomad_get_constraint`. pLI, LOEUF,
  observed/expected LoF interval values, missense/synonymous Z scores, counts,
  dataset, build, and release remain visible when available. Constraint alone
  cannot establish a disease LoF mechanism or activate PVS1.
- MyVariant preserves available REVEL, CADD, AlphaMissense, SIFT, PolyPhen-2
  HDIV, MetaRNN, GERP, phyloP, phastCons, VEST4, and MutationTaster values,
  predictions, rank scores, and versions. Predictor agreement/conflict is
  summarized without majority voting.
- PubMed is queried with abstracts enabled for the candidate pool; Europe PMC
  supplies full text when available; LitVar contributes variant-linked
  publications. Abstract-only or inaccessible-full-text papers remain leads.
- UniProt preserves entry status, names, function, disease comments, catalytic
  activity, cofactors, PTMs, domains, sequence length, cross-references, and
  references. Inactive or deleted entries remain visible with their reason.

`response_detail="summary"` returns complete normalized clinical indexes,
evidence cards, predictors, literature candidates, conflicts, and provider
coverage without embedding large raw responses, full articles, or full CSpec
documents. `response_detail="full"` retains the complete normalized audit
structure, excerpts, locators, CSpec content, and raw-result hashes.

### 2. Review CSpec and literature requests

ClinGen CSpec discovery is online-first after gene identity verification. A
released specification is applied only when disease and inheritance identify a
unique match. Structured rules can be used directly. Natural-language rule
requirements are returned in `rule_context.cspec_review_requests` for host-LLM
interpretation.

The collector merges LitVar, PubMed, and Europe PMC candidates by PMID, PMCID,
DOI, or stable title while preserving all source hits. Full text is preferred;
abstract-only records remain leads.

The host LLM may interpret CSpec prose and literature, but it must return
anchored structured proposals:

- `cspec_proposals` for natural-language CSpec rules;
- `literature_proposals` for case-control, case-series, de novo, PM3,
  functional, segregation, phenotype, healthy-adult, phase/co-occurrence,
  alternative-cause, prior-variant, mechanism, region, or protein-length facts.

ToolUniverse re-fetches the source and verifies document identity, variant and
gene context, locator, excerpt, per-field excerpts, version/hash, schema, and
deduplication identity. The LLM suggestion cannot map an unrelated fact type to
an arbitrary criterion.

### 3. Review the system preview

`system_preview_bayesian` is a reproducible review estimate, not a clinical
classification. It includes only eligible, identity-bound and compatible
suggestions. Excluded cards remain visible with reasons.

Conflict handling checks duplicate criteria and shared cases, families,
cohorts, assays, publications, prior variants, CSpec rules, computational
sources, and PVS1/splicing facts. Unresolved directional conflicts are excluded
from multiplication rather than silently resolved.

### 4. Apply user decisions

After review, call the collector again with the same variant/context plus:

```json
{
  "evidence_decisions": [
    {
      "card_id": "stable-card-id-from-the-previous-call",
      "decision": "accept",
      "reviewer": "reviewer-name"
    }
  ]
}
```

The user may `accept` or `reject` a card. A `strength_override` must preserve
criterion direction and include a reason. Only regenerated, exactly matching
card IDs are applied. Stale or unmatched IDs are reported without affecting
other cards. Accepted compatible cards produce `user_selected_bayesian`.

Neither Bayesian result maps to a five-tier classification. The prior
probability remains 0.1 and the output identifies the odds source for every
included card.

## SpliceAI interpretation

SpliceAI must be read as four separate delta channels:

- `DS_AG`: acceptor gain
- `DS_AL`: acceptor loss
- `DS_DG`: donor gain
- `DS_DL`: donor loss

Use `spliceai_scores`, normalized `spliceai_profile`, and
`spliceai_max_delta = max(DS_AG, DS_AL, DS_DG, DS_DL)`. The maximum is not
synonymous with donor loss, and DS values must not be recomputed from raw
REF/ALT scores. Report all four channels and the triggering channel.

PVS1 continues to use the deterministic ClinGen/SVI decision tree and
versioned splice thresholds. Missing or unverifiable splice facts remain
`not_assessed`; caller booleans cannot complete the decision tree.

## Installation verification

First verify that the exact commit starts:

```bash
uvx --refresh --from \
  git+https://github.com/YuancunZhao/ToolUniverse.git@911200550b10600ded44b36dcb614c25ff06e0e6 \
  tooluniverse --help
```

After restarting the client:

1. Find `ACMG_evidence_collector`.
2. Confirm all eight ACMG tools are registered.
3. Inspect `ACMG_evidence_collector` and
   `ACMG_overlay_gate_assess_variant`; their parameter and return schemas must
   match.
4. Confirm the removed inputs and outputs listed above are absent.
5. Execute the harmless summary request shown earlier.
6. Confirm provider failures remain represented in `source_facts` and
   `coverage_summary`.
7. Confirm `final_classification_allowed` is `false`.
8. Call `ACMG_guard_final_answer` with a draft containing a five-tier label and
   confirm it returns `BLOCK`.

Network-dependent providers may produce a degraded or partial result. That is
acceptable only when the failed/no-result sources and reasons remain visible;
it is not acceptable to replace them with unverified manual evidence.

If `execute_tool`, `get_tool_info`, or `list_tools` is unavailable, stop the
ACMG assessment and report `ToolUniverse MCP execution unavailable`. Do not
call provider HTTP APIs directly, apply criteria manually, or emit a five-tier
classification as a fallback.

## Runtime boundary

ToolUniverse enforces evidence-only behavior after the agent enters the
ToolUniverse ACMG discovery/execution path. It cannot prevent a general LLM
from reasoning outside ToolUniverse. Deployments requiring stronger
enforcement should add:

- a pre-answer hook that calls `ACMG_evidence_collector`;
- a post-answer hook that calls `ACMG_guard_final_answer`.

## Troubleshooting

| Issue | Resolution |
|---|---|
| `uvx: command not found` | Install `uv`, restart the terminal, and retry. |
| Installation still loads an old branch version | Confirm the MCP `--from` value contains the exact SHA above, restart the client, then use `uv cache clean tooluniverse` only if necessary. |
| Old ACMG routing/refinement Skills appear | Re-run the full Skill installer from the exact SHA; it removes only the retired routing-core/refinement directories and preserves unrelated Skills. |
| Discovery/execution tools are missing | Confirm the ToolUniverse MCP server started and that `list_tools`, `get_tool_info`, and `execute_tool` are available. |
| Collector result is degraded | Inspect `coverage_summary`, failed SourceFacts, identity status, versions, and missing requirements. Partial provider failure is expected to remain visible. |
| Literature or CSpec proposal is excluded | Inspect anchor, semantic, version/hash, fact-type mapping, identity, and deduplication status. |
| SpliceAI maximum is mistaken for donor loss | Read all four DS channels and the recorded triggering channel; `spliceai_max_delta` is their maximum. |
| A five-tier ACMG label is requested | Keep the response evidence-only, report review estimates and limitations, and call the guard. |
