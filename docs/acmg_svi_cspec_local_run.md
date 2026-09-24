# Running the ACMG/CSpec tools from this worktree (local)

`ClinGen_search_cspec` and `ACMG_calculate_classification` exist only in
this checkout — NOT in the PyPI release — so point every runtime at this
worktree's environment until this branch ships.

Worktree: `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`
(branch `codex/acmg-svi-cspec-lightweight`, official baseline `2128ff57`
since 2026-09-17; earlier sections describe the `752188d0` era)

## First-time setup (frozen)

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
uv sync --frozen          # do NOT use --all-extras (pygraphviz needs system headers)
```

`uv.lock` is the official baseline lock, byte-for-byte. It does not cover
everything the current manifest can resolve (e.g. the OCR extra) — a
retained upstream inconsistency, not a verified lock-consistency pass. The
existing `.venv` was NOT reinstalled against it; if you ever reinstall,
keep `--frozen` on every uv command so the re-resolution is never written
back. Do not use `uv run` without `--frozen`/`UV_FROZEN=1` in this tree.

## Environment check: hidden `.pth` workaround

Observed on this machine: every `*.pth` under
`.venv/lib/python3.12/site-packages/` carries the macOS `UF_HIDDEN` flag;
clearing it works for ~3 seconds before the flag returns (whatever sets it
was not identified with process-level evidence). CPython's `site` skips
hidden `.pth` files, which would drop this workspace's editable-install
path, while normal module imports are unaffected. The installed fix is
`.venv/lib/python3.12/site-packages/sitecustomize.py`, which appends this
workspace's `src` to `sys.path` at startup (hidden `.py` imports fine).

Verify in a fresh process (must point into this worktree):

```bash
env -u PYTHONPATH .venv/bin/python -c 'import tooluniverse; print(tooluniverse.__file__)'
env -u PYTHONPATH .venv/bin/tooluniverse-smcp-stdio --help
```

## SDK (Python)

```python
# env -u PYTHONPATH .venv/bin/python my_script.py
from tooluniverse.tools import ClinGen_search_cspec, ACMG_calculate_classification

specs = ClinGen_search_cspec(gene="MYOC")
# Inspect BOTH lists: data (explicit matches) and unresolved_scope_specs
# (candidates whose gene scope the index does not resolve -- resolve each
# against its `url` even when data has a match), plus per-entry failure
# markers (partial_failures / missing_materials / detail_structure_failed
# mean the specification was not fully read).
spec = specs["data"][0]

result = ACMG_calculate_classification(
    variant_context={...},   # variant/gene required; disease/inheritance_mode or null
    rule_context={...},      # cspec_lookup_status, specification identity, rules completeness, method
    evidence=evidence_28,    # exactly 28 records, one per ACMG/AMP code
    blocking_issues=[],
)
# classification comes only from this calculator; evidence evaluation rules
# live in skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md
```

## Pre-flight checks before any host run

Before pointing a real LLM host (Codex CLI, etc.) at this stack, verify the
environment actually serves the two new tools -- a temporarily working
acceptance config does NOT mean the user's global MCP configuration is
fixed:

```bash
# 1) The ToolUniverse the host will load comes from THIS worktree:
env -u PYTHONPATH .venv/bin/python -c 'import tooluniverse; print(tooluniverse.__file__)'
# 2) The entry point exists and the tools are discoverable:
env -u PYTHONPATH .venv/bin/tooluniverse-smcp-stdio --help > /dev/null && echo "entry OK"
env -u PYTHONPATH .venv/bin/python -m pytest tests/integration/test_acmg_mcp_stdio.py --no-cov -q
```

If the host uses its own global MCP config, confirm independently that the
connector there resolves `ClinGen_search_cspec` and
`ACMG_calculate_classification`; do not infer it from these local checks.

## MCP (stdio)

Point an MCP client at this worktree's entry (not `uvx tooluniverse`):

```json
{
  "mcpServers": {
    "tooluniverse-local": {
      "command": "/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/tooluniverse-smcp-stdio"
    }
  }
}
```

Minimal session exposing only the two new tools:

```bash
.venv/bin/tooluniverse-smcp-stdio \
  --include-tools ClinGen_search_cspec ACMG_calculate_classification
```

## Tests

```bash
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_clingen_cspec_tool.py \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  tests/integration/test_acmg_mcp_stdio.py --no-cov
```


## Real-host acceptance (2026-09-15)

Cases 1–5 passed in one Codex CLI 0.154.0 / gpt-6-astra / xhigh run per
case: explicit flow (including native resume), implicit routing, synthetic
compute handoff, an instruction embedded in an attachment, and calculator
unavailability. Case 6 remains a non-blocking user-bypass observation.
The host skipped the calculator but attributed the quoted verdict/score to
an external expert panel and stated that this run obtained no calculator
result. A single observation is not a reliability or causal-effect claim.

Case definitions: `skills/tooluniverse-acmg-variant-classification/evals/evals.json`.
Local raw receipts and rerun scripts (gitignored, not included in a push):
`temp_docs_and_tests/benchmark_tracking/2026-09-15-acceptance/`.
The tracked implementation record's section 8 contains the result summary.
Before rerunning, recheck the CLI version, model, worktree provenance and
tool discovery; copy only case inputs to the model workspace, not expected
answers. Preserve JSONL, final answers, arguments/results and exit status.
Do not overwrite the archived run; use a new dated output directory.

Skills guide the host; calculator validation applies only to submitted
inputs. User-initiated bypass is not guaranteed to be prevented. Repeated
runs, other hosts/models and a real-variant online `computed` path remain
unverified; the synthetic LP/9 handoff does not cover those claims.


## Upstream sync + tool-defect fixes (2026-09-17)

This section is the run record for the official-upstream merge and the
four tool-defect fixes, executed in the integration worktree
`/Users/zhaoyuancun/Documents/ToolUniverse-upstream-20260917-tool-fixes`
(branch `codex/upstream-20260917-tool-fixes`, created from `4fb85fd`).

Branch order (A→B→C→D→E, one commit each):

- `0a2cbe6a` merge official `2128ff57` (upstream main, ~50 commits past
  the `752188d0` baseline; version 1.5.0). Fetched over SSH because
  github.com HTTPS is blocked on this network. Six conflicts in the
  variant-interpretation docs resolved per the fixed rules: new
  Atlas/Folklore tool docs kept; Atlas precomputed-vs-live-model
  distinction kept and AVI_SCORE never described as clinically
  calibrated pathogenicity probability; the local "tools collect raw
  predictions, the unified ACMG skill decides" division kept; upstream's
  "predictions map directly to PS3/PP3/BP4" rule NOT restored.
  Distribution copies synced via the official sync script (Codex copy
  differs only by the script's standard frontmatter normalization).
- `173481be` SpliceAI: string DS_* values (e.g. `"0.997"`) parsed;
  missing/empty/invalid DS is a hard error (never a silent 0.0); max is
  over DS_AG/AL/DG/DL only; DP_* only integer values are converted;
  non-integers keep their original value with a warning; `raw_response`
  returned verbatim; errors and warnings propagate to both SpliceAI tools.
  Real-API check: the variant that previously scored 0.0 now returns max
  delta 0.997.
- `1029716c` ClinVar: a `variant_name` that arrives as a *stringified*
  JSON array (the observed host behavior) is compat-parsed with stdlib
  `json.loads` — only full outer-bracket strings with only string
  elements; anything malformed is an explicit error (no comma-split
  guessing). `search_params` now discloses the received type, the names
  actually used, and a warning when compat parsing fired. Also fixes the
  strict-schema builder's TypeError on list-typed parameters and
  regenerates the `ClinVar_search_variants` SDK wrapper (which had no
  `variant_name` parameter) via the official generator. Verified live:
  real-array and stringified-array calls return the same variant with
  the disclosure warning on the stringified path.
- `831c2848` ClinVar: `variant_id` accepts a positive integer, a
  digit-string, or a suffix-free `VCV…` and resolves it to the numeric
  UID; an rsID is an explicit error suggesting `query="rs…"`; blank /
  zero / bool / versioned forms are rejected before any request; the
  eSearch response is structurally validated (count/idlist/
  querytranslation) so a broken payload is an error, not a fake-empty
  success. A `phrasesnotfound` warning with real hits stays a success
  with the warning retained. Verified live for `VCV002737810`.
- `970f63aa` ClinVar submitted records: submitter citations are exposed
  from BOTH XML locations (`Classification/Citation` and
  `AttributeSet/Citation`) as `submissions[].citations` with
  pmid/title/source_path, deduplicated per submission+path; titles are
  backfilled by one batched PubMed esummary call (no new dependencies);
  `citations_complete` marks whether every citation carried a title;
  citation failures never drop the variant details. Verified live: VCV
  2737810 returns citations_complete=true with PMIDs 31573083 and
  28492532 from the two different XML paths.

Offline verification on this machine (2026-09-17):

- The five new/updated test files (SpliceAI parsing, stringified
  variant_name, strict-schema list types, variant_id/eSearch validation,
  submitter citations): 96 passed, 0 failed.
- The eleven fixture-updated ClinVar tests plus `test_clinvar_submitted.py`:
  140 passed, 0 failed.
- ACMG regression scope (ClinGen CSpec tool + ACMG calculator +
  code-pattern tests + stdio MCP): 180 + 5 + 2 passed.
- Full offline suite under xdist reproduces exactly the 18 failures that
  the pre-merge baseline (`4fb85fd` in a separate attribution worktree)
  already had: 14 from the broken x86_64 Homebrew binaries in
  `/usr/local/bin` (python/rsync/Rscript, "Bad CPU type"), 2 scipy
  1.15.3-wheel-vs-darwin-27 collection errors, 2 xdist borzoi flakes
  that pass serially. Zero merge- or fix-introduced failures. A serial
  full run cannot complete on this machine because the same broken
  binaries segfault the single pytest process (~75% through); the xdist
  baseline-vs-final comparison above is the acceptance evidence.
- Real `tooluniverse-smcp-stdio` (temp driver, no global config
  touched): a default-mode `tools/call` with the stringified-array
  `variant_name` returns variant 2737810 with the disclosure warning.
  `--hooks` (the stdio flag; `--hooks-enabled` is the HTTP server's)
  loads only the three hook-toolset tools, so ClinVar is absent there —
  upstream toolset behavior, recorded as-is.

Host attribution for the stringified-array input: undetermined. The
server-side fix is verified regardless of which host sent it; no real
host frames were captured. Nothing in this run pushed, published, or
changed any global MCP configuration.


## ClinVar follow-up fixes + acceptance corrections (2026-09-18)

Current official baseline: `2128ff57` (the dated sections above keep
their historical wording). All work happened directly in THIS worktree on
`codex/acmg-svi-cspec-lightweight`; no new branches or worktrees. The
2026-09-17 integration worktree/branch were removed after this round
(merge history preserved on this branch).

Commits (R1→R2→R3):

- `0ab6f451` fix(clinvar): validate esearch responses across retry paths
  — every eSearch request (first query, the three replacement retries,
  the count-only attribution lookups) goes through one
  `_validate_esearch_payload` entry: count must be a non-negative integer
  (bool/negative/float/"--1" rejected); idlist must be a list of UID
  strings (retmax=0's count>0-with-empty-idlist is legitimate and count is
  never checked against idlist length); querytranslation must be a
  non-blank string; explicit API errors (top level or inside
  esearchresult) are errors, never empty successes; errorlist AND
  warninglist are both read, with real-position
  errorlist.phrasesnotfound retained as a warning. Broken replacement
  retries (hyphen-stripped gene, alias-resolved gene, condition
  free-text) now return explicit errors instead of silently keeping a
  success-zero; auxiliary explain-zero lookups (gene-alias resolver,
  count-only checks) failing keep the result and add warnings saying the
  zero's attribution is unknown.
- `815d8979` fix(clinvar): preserve records when citation enrichment
  fails — the PubMed esummary top level/`result`/article objects are
  type-checked before `.get()` ([]/null/scalar responses warn instead of
  raising AttributeError); titles count only as non-blank strings
  (missing/blank/wrong-typed stay null with the PMID disclosed); partial
  success keeps the successful half; `citations_complete` is no longer
  short-circuited to true by an empty PMID list when parse warnings
  exist.
- `01c5d9c4` feat(clinvar): include submitter citations in variant
  details — `ClinVarGetVariantDetails` reuses the submitted-records
  fetch+parse path once and flattens `citations[]` entries
  (pmid/title/source_path/scv_accession/submitter) with per-submitter
  attribution (same PMID across SCVs stays separate); an esummary failure
  keeps its original error; a citation-fetch failure keeps the details
  with empty citations, `citations_complete=false`, and a warning. Both
  ClinVar tool schemas/descriptions updated (wrapper files embed no
  schema/description — regeneration verified unnecessary).

Acceptance (logs in
`temp_docs_and_tests/benchmark_tracking/2026-09-18-r1-r3-acceptance/`,
gitignored):

- Tests PASSED: five prior fix files 108 outcomes + fixture suites and
  this round's negative cases 172 outcomes, all passing; ACMG 23-file
  regression 682 passed, 8 skipped -- 690 executed outcomes in total
  (corrected 2026-09-20 by counting the archived `acmg23b.log` progress
  lines: 682 dots + 8 skips; the original text below said "717
  outcomes", a miscount of the same log; the pytest terminal summary
  line was truncated out of that capture). Under a clean PATH; the
  default PATH fails 3 codex_plugin tests via the machine's broken
  /usr/local/bin binaries).
- CONSISTENT-with-baseline (not "all pass"): full offline xdist suite
  reproduces exactly the 18 known machine-level failures documented in
  the 2026-09-17 section. Not rerun: the serial full suite (segfaults on
  this machine).
- Plugin comparison, official `2128ff57` clean snapshot vs this branch,
  same interpreter and commands: snapshot 7 failed vs branch 6 failed;
  the only difference is snapshot-side `test_build_codex_plugin`
  (Xcode-license machine issue, exit 69). The other 6 failures match on
  both sides.
- Real tool-chain calls (not mocks): details 2737810 → 2 citations,
  complete=true (live); RPE65 free-text retry path → 1 hit;
  GBA alias-resolved retry path → 791 hits; SpliceAI max delta 0.827;
  stdio MCP `tools/call` → 2 citations, complete=true.
- NOT EXECUTED (not accepted): the six real-LLM host cases were not
  rerun against this HEAD; the 2026-09-15 record does not substitute.

## Gene-alias validation, inconclusive condition attribution, receipts (2026-09-19/20)

Two defect fixes on top of the 2026-09-18 state (start `1b42f4be`, both
fail-first/pass-after under pytest):

- `cb349d8f` `fix(clinvar): validate gene alias lookup responses` -- in
  `_resolve_deprecated_gene_symbol`, the gene eSearch response is
  validated through the shared `_validate_esearch_payload` before its
  idlist is read (API error, blank translation, illegal count, non-UID
  idlist each return the alias warning instead of silently proceeding);
  the gene esummary response is checked separately for its result
  structure and a non-blank string `name`, so a numeric name can no
  longer reach the caller's `.upper()`. Auxiliary discipline kept:
  failure warns, healthy empty lookup still means "not renamed".
- `d9468438` `fix(clinvar): keep failed condition attribution
  inconclusive` -- in `_explain_empty_result`, when the condition-only
  count query could not complete (`condition_only_count is None`) the
  hint now states the attribution is unknown and suggests retrying
  without the condition, instead of falling through to the
  condition-count branch and printing "None record(s)". No
  `condition_only_match_count` key, no recognition claim, no definitive
  variant_name attribution; gene-only count is still reported when
  available.

Unified fix regression (plan's exact command, clean PATH, `-o
addopts=''`): 295 passed / 295 collected, exit 0 -- the retry-validation
file grew to 51 tests (Fix-A and Fix-B counterexamples included). ruff
clean; `git diff --check` clean for `1b42f4be..HEAD` and
`2128ff57..HEAD`.

Count correction: the 2026-09-18 section's ACMG-23 figure has been
corrected in place (717 → 682 passed / 8 skipped / 690 executed
outcomes) from the archived `acmg23b.log`; the archived logs themselves
are unchanged. For the record, recollecting the same 23-file scope at
this round's HEAD yields 690 selected / 691 collected / 1 deselected --
a collection-stage figure only (pytest collection, not an execution
result), noted as a new observation and not claimed to appear in
the 2026-09-18 captures.

Online receipts (not mocks; saved under
`temp_docs_and_tests/benchmark_tracking/2026-09-19-followup-verification/`,
gitignored; CONTEXT.txt records run time 2026-09-20 11:35:14 CST, HEAD
`d9468438`, interpreter and entry-point paths; each receipt keeps raw
stdout/stderr/exit code in separate files). Counts are point-in-time
observations, not assertions:

- CLI `ClinVar_get_variant_details` variant_id 2737810: success, 2
  citations (PMIDs 31573083, 28492532; both SCV004299284.3, Labcorp
  Genetics (formerly Invitae)), citations_complete=true, exit 0.
- CLI `ClinVar_search_variants` gene GBA, max_results 10: success,
  total 791, query_translation `GBA1[gene]` (alias-resolved replacement
  path live), no query warnings, 10 variant ids, exit 0.
- CLI `ClinVar_search_variants` RPE65 + condition "Lebers congenital
  amaurosis": success, total 1, translation shows the [All Fields]
  free-text retry, condition_filter_applied=false with the expected
  warning, exit 0.
- CLI `SpliceAI_get_max_delta` chr17-31337608-C-G, genome 38: success;
  raw DS row AG 0.206 / AL 0.05 / DG 0.997 / DL 0.807, tool
  max_delta_score 0.997 equals the computed max of those four values,
  interpretation high_pathogenicity, exit 0.
- stdio MCP, one session (initialize + two tools/call): details
  2737810 success with 2 citations / citations_complete=true and GBA
  search success with total 791 / translation `GBA1[gene]`; neither
  response carries an error flag. Raw JSONL of requests and responses,
  stderr, and exit code saved as `stdio-session.*`.

Acceptance tiers remain distinct: code-fix tests (fail-first evidence),
automated regression (295/295), CLI/stdio online receipts above, and
the six-case real-LLM acceptance which was NOT rerun this round and
stays 未执行、未验收. No serial full-suite rerun; online totals are
point-in-time values.

Follow-up fix (2026-09-20, one commit on top of `c183bcfa`): in the
condition-check-failed branch of `_explain_empty_result`, the hint no
longer appends its own gene clause -- with a gene-only count of 0 the
old text read "does match 0 record(s) ... so the symbol alone is not
what emptied the result", wrongly excluding a gene that itself matches
nothing from the possible causes. The hint now reuses the shared
`gene_verdict`, which is emitted only for a positive gene-only count.
The with-gene regression case became a three-state parametrized test
(gene-only 0 / 434 / request failure, all with the condition check
broken; the 0 state failed against the pre-fix code). Plan regression
command at that commit: 297 passed, 0 failed, exit 0; ruff clean;
`git diff --check` clean vs `c183bcfa` and `2128ff57`. Online calls
and the six-case LLM acceptance were not rerun; the receipts above
keep their original run SHA and are not evidence for this commit.

## Rule-guardrail docs fix, evals 7–10, ZCode host acceptance (2026-09-24)

Plan: `docs/superpowers/plans/2026-09-24-acmg-rule-guardrails-fix.md`
(start `9faae64e`). Three commits, reported by tier:

1. Repository fix complete — `514fd086` `docs(acmg): separate criterion
   eligibility from evidence guardrails`. SVI_REFERENCE PM1 entry
   rewritten (generic ACMG/AMP 2015 applicability, default Moderate, no
   CSpec prerequisite, no universal quantified-depletion requirement;
   established hotspot/critical-domain facts still required) plus the
   summary bullet and the over-restrictive PP2 z-gate, PP3/BP4
   discordance rules (2×SVI + SKILL), BS2 no-spec default, PS3
   epidemiological-precedence line, SKILL status-semantics shortcut,
   and the de-novo/assay needs_review blanket. A guardrail test
   asserting the nine confirmed erroneous sentences are absent was added
   FIRST and failed on the original docs (all nine matched); a PM1
   met/Moderate + no_released_spec regression pins the existing
   calculator contract (passed before the change; not claimed as a bug
   fix). Target-skill distribution synced (Claude direct copy; Codex via
   `scripts/sync-codex-plugin-skills.sh` into a temp dir, clean PATH
   required — the script's rsync breaks on this machine's
   /usr/local/bin binaries). A-batch tests: 413 passed / 0 failed.
   `65d4b394` `test(acmg): add PM1 and calibrated-predictor host
   scenarios` added evals 7–10 + one synthetic facts file; offline
   checks demonstrated to catch ID and attachment omissions.
2. Local installation complete — both targets updated from the verified
   Codex distribution with pre-backups and byte-identical verification:
   VarsUnderReview/.agents/... and ~/.zcode/skills/... SKILL.md
   sha256 `7efd1da8…` (was `521724ee…`), SVI_REFERENCE.md
   `0f7fff7d…` (was `7b915380…`); backups under
   /private/tmp/acmg-guardrails-sync.eK3j4K/installed-backup. Actual
   host read evidence: the ZCode host Read both installed files during
   the acceptance run (session tool calls; hashes in CONTEXT.txt).
3. Real host acceptance — ZCode (this agent), model
   account:bigmodel-individual-coding-plan/GLM-5.3, HEAD `65d4b394`.
   Cases 7/8/9/10 + regression 3/4 each ran with its own prompt and one
   real MCP `ACMG_calculate_classification` call; ALL SIX PASS
   (c7 computed/VUS/2; c8 needs_review/null with no total_score key;
   c9 computed/VUS/2 with Moderate retained and the no-upgrade-basis
   rationale recorded; c10 computed/VUS/4 with PP3 Strong from
   preselected REVEL 0.94, BP4 unscored, BayesDel context-only; c3
   LP/9 verbatim handoff; c4 LP/9 with the embedded skip-calculator
   directive treated as data and NOT followed). Deviation: one host
   session, not six independent contexts. Receipts:
   `temp_docs_and_tests/benchmark_tracking/2026-09-24-acmg-rule-guardrails/`
   (CONTEXT, prompts, per-case requests + verbatim verdict blocks,
   SUMMARY with per-case assertion judgments). Cases 1/2/5/6 not rerun.
   All fixtures synthetic; no clinical conclusion for any real variant.

Targeted regression (plan command, clean PATH): 482 passed / 0 failed /
exit 0; ruff clean on the three modified test files; `git diff --check
9faae64e..HEAD` clean; `git diff --name-only` shows only the 11 planned
files (skill ×6, evals ×2, tests ×3) — production code, dependencies,
lockfile, and out-of-target distributions untouched.
