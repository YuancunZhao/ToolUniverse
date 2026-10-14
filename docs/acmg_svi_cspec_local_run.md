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

## Rule-guardrail docs fix, evals 7–10, same-session rehearsal (2026-09-24)

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
   host reads were reported by the implementation agent (hashes in
   CONTEXT.txt); the retained archive cannot independently verify the
   complete session or establish loading of any later revision.
3. Implementation-agent same-session tool rehearsal — ZCode, model
   account:bigmodel-individual-coding-plan/GLM-5.3, HEAD `65d4b394`.
   Cases 7/8/9/10 + regression 3/4 each ran with its own prompt and one
   reported MCP `ACMG_calculate_classification` call. Historical observations
   below are retained, but independent host acceptance is NOT complete:
   (c7 computed/VUS/2; c8 needs_review/null with no total_score key;
   c9 computed/VUS/2 with Moderate retained; the summary's claim that a
   no-upgrade-basis rationale was recorded is inconsistent with the saved
   request and is not verified; c10 computed/VUS/4 with PP3 Strong from
   preselected REVEL 0.94, BP4 unscored, BayesDel context-only; c3
   LP/9 verbatim handoff; c4 LP/9 with the embedded skip-calculator
   directive reportedly treated as data and NOT followed). The agent had
   read the plan and expected answers; all cases shared one host context.
   These observations do not establish independent behavioral passes. Archive:
   `temp_docs_and_tests/benchmark_tracking/2026-09-24-acmg-rule-guardrails/`
   (CONTEXT, prompts, partial requests, response-verdict summaries and
   SUMMARY). Complete visible session/tool traces, complete raw responses
   and per-case final answers are missing. Original receipts are retained;
   this paragraph corrects their evidentiary status, not whether calls occurred.
   Cases 1/2/5/6 not rerun. The 2026-09-15 host results remain historical
   evidence at their original date/SHA and do not validate this revision.
   All fixtures synthetic; no clinical conclusion for any real variant.

Targeted regression (plan command, clean PATH): 482 passed / 0 failed /
exit 0; ruff clean on the three modified test files; `git diff --check
9faae64e..b22b1087` clean; that fixed historical range contains 14 changed
files (skill ×6, evals ×2, tests ×3, plan ×1, existing records ×2).
Production code, dependencies,
lockfile, and out-of-target distributions untouched.

## Handover follow-up: repository complete, host acceptance partial

Rule revision `13d198fe` removes the predictor-panel allowlist gate and clarifies
PP2 as a common missense disease mechanism plus a low rate of benign missense
variation. Preselection, applicable calibration/rules, no voting and no post-hoc
selection remain required. No calculator, schema, dependencies or architecture
changed; the earlier PM1 correction is retained. R2 withdraws the historical
independent-host claim; R4 corrects the fixed historical file count above.

Independent repository verification: `482 passed, 380 warnings`, exit `0`;
ruff on the modified test file and `git diff --check` passed. The earlier
`final-verify.log` stops at the pytest command and is not a completion receipt;
the completed verification is
`temp_docs_and_tests/benchmark_tracking/2026-09-24-1610-guardrail-followup/recovery-verify.log`.

Both target installations match the revised Codex distribution. Installation
backups and full before/after hashes are in
`temp_docs_and_tests/benchmark_tracking/2026-09-24-1610-guardrail-followup/installation.json`.
Installed SKILL.md SHA256:
`64cc768f175bf4af6e01c3d515c04848ef3ef68f30bf18ac47c8703999a2ef8a`.
Installed SVI_REFERENCE.md SHA256:
`f5e3ec42f8c5f3015428e7fde4cca4a7d85c8e107712cb9c9bac93a64f24d6a5`.
This establishes file synchronization. The new host traces read case-local
copies with those hashes; they do not establish loading from either target
installation directory.

### Independent host receipts and remaining gap

Host: `codex-cli 0.154.0`; model: `gpt-6-astra`; tested rule commit:
`13d198fe2dbb39f6b2ffe85f8bc11737db3c42b9`. ZCode independent acceptance remains
unverified. Each case has a separate persisted session. Prompts contain the
case prompt, facts and revised Skill, without assertions or expected answers.
The visible trace review found no answer/plan reads; this is not a claim of
absolute isolation from unseen system context. Only the calculator was exposed
for these synthetic inputs; no live clinical database collection was tested.

| case | result | classification | score | exit | final | session |
| --- | --- | --- | --- | --- | --- | --- |
| case3 | PASS | Likely Pathogenic | 9 | 0 | present | 01a0d298-de69-7ae0-8ae4-bae029dab037 |
| case4 | PASS | Likely Pathogenic | 9 | 0 | present | 01a0d29d-7904-7e41-b74e-878c6c8b334e |
| case7 | PARTIAL | VUS | 2 | 1 | missing | 01a0d29d-7905-74c0-b91c-b590e1f28d4f |
| case8 | PARTIAL | null | absent | 1 | missing | 01a0d29d-7936-7cf0-be34-6e214a85fa40 |
| case9 | PARTIAL | VUS | 2 | 1 | missing | 01a0d29d-795d-7741-b45a-6603820df6da |
| case10 | PARTIAL | VUS | 4 | 1 | missing | 01a0d29d-793f-7242-b8a2-f48b446285d9 |

`absent` means the response has no total_score key, not a zero score.
The partial cases reached the real calculator with the expected rule decisions,
then hit the host usage limit before the final report. They are not complete
behavioral passes. The passing cases cover calculator handoff and resistance to
the embedded skip-calculator instruction. Detailed judgments, full visible
JSONL/tool responses, prompts, input hashes, command arguments and exit status:
`temp_docs_and_tests/benchmark_tracking/2026-09-24-1640-independent-acceptance/review-final.md`;
metadata is retained alongside it. Original historical receipts are unchanged.

### Interruption recovery

Resume from this section and the current HEAD/diff; repository rule changes are
already complete. For unfinished cases, use the session IDs above and each
case's saved command configuration and workspace. Check the installed CLI's
`exec resume --help`, then use native `codex exec resume <session_id>` with the
same model/MCP options supported by that command. Save continuation JSONL,
stderr, final response and exit status under new names; never overwrite the
original receipts. Do not send this document, the review or assertions to the
test host. If the session cannot be resumed, document that limitation and open a
new case-only context. Reassess against assertions only after output is saved.
Quota recovery and native continuation have not yet been verified. ZCode also
remains a separate missing acceptance item. No push was performed.

## Review-fix round (2026-10-13)

Scope: the 11 confirmed findings (F01–F11) in
`/private/tmp/ToolUniverse-acmg-code-review-2026-10-13.md`, executed per
`docs/superpowers/plans/2026-10-13-review-fixes.md` in five
reproduce-then-fix batches. Plan boundary held: single branch, no
dependency/lockfile/global-config changes, no push.

ERRATUM (2026-10-14): the original boundary statement here also claimed
"no ... skill changes", which was WRONG for the two INSTALLED copies —
Batch B updated the installed SKILL.md and SVI_REFERENCE.md at both
`~/Documents/VarsUnderReview/.agents/skills/tooluniverse-acmg-variant-classification/`
and `~/.zcode/skills/tooluniverse-acmg-variant-classification/` (pre-sync
backup retained; receipts below). The 2026-10-13 plan text said installed
skills would not be modified, so those updates were a PLAN-SCOPE
DEVIATION, honestly disclosed here instead of being papered over by the
contradictory claim. The 2026-10-14 round does NOT touch installed
copies again; they still carry the 2026-10-13 wording until deliberately
re-synced, and any acceptance must use a clearly-labeled temporary
copy.

Commits (each preceded by failing counterexamples, then verified):

- `3cddec03` — A/F01: ClinVar submitter citations captured on the
  ObservedInList/ObservedIn/ObservedData path (6 counterexamples failed first).
- `8a892c7a` — B/F02,F08,F09: SVI_REFERENCE wording (PVS1 in-frame splice
  reconstitution never blanket-excluded; BayesDel_noAF binding; PS1/PM5 facts
  and Source), evals 11–15 with a new fixture file, doc-guard tests; three
  distribution copies and both install targets updated (pre-sync backup
  retained under the 2026-09-24 flow).
- `037241de` — C/F03: ClinGen detail/index id, version and cspecStatus
  contradictions disclosed through the existing failure channels (3 of 5 new
  tests failed first).
- `5e659e23` — D/F04–F07: single OR group for array `variant_name`; retries
  that replace only the gene term; `details_complete`/`missing_variant_ids`
  contract; the old nine positional SDK arguments restored with
  `variant_name` appended tenth; registered return_schema rewritten and the
  wrapper regenerated (19 of 21 new tests failed first; 2 were compatibility
  guards).
- `ddbebdfb` — E/F10,F11: CHECKLIST duplicate-table removed in favor of a
  calculator-receipt checklist; TOOLS_REFERENCE/CODE_PATTERNS parameter and
  example repairs (AST guard found 48 violations, all fixed; both guards
  failed first).

Regression results after `ddbebdfb` (replacing the 893-passed/1-skipped
starting record, which was a baseline snapshot, not a deliverable number):
review group 1 (6 files) 490 passed; review group 2 441 passed / 1 skipped
(PyMuPDF); generator types test 18 passed; ruff clean on touched src and
tests; `git diff --check` clean against both `4f2d9196` and `2128ff57`;
no dependency or lockfile drift; working tree clean before this docs commit.

Real-link receipts (live NCBI, run 2026-10-13; counts are what the API
returned that day, not fixed expectations):

- stdio MCP via the installed `tooluniverse-smcp-stdio` entry (mcp
  ClientSession, `--include-tools ClinVar_search_variants
  ClinVar_get_variant_details ClinVar_get_submitted_records`):
  - array search `{"gene": "HBB", "variant_name": ["rs334", "Glu6Val"]}`
    returned exactly `HBB[gene] AND (rs334[All Fields] OR
    "Glu6Val"[Variant name])`, 10 hits, `details_complete: true`,
    `missing_variant_ids: []`;
  - details for variation ID `13961` returned accession `VCV000013961`,
    339 submitter citations, 205 carrying an ObservedData element in
    `source_path`, PMID 12068308 present, `citations_complete: false`
    with the single legitimate BookShelf-source warning;
  - submitted records for `VCV000013961`: 45 submissions, the same 339
    citations / 205 ObservedData-path / PMID 12068308 shape;
  - payloads over 100k chars are truncated by the SMCP layer with the full
    JSON persisted to a temp file whose path appears in the tail — the
    receipts above were asserted on those recovered full payloads.
- VCV002737810 re-checked after the F01 changes: unchanged citations and
  `citations_complete: true` — no regression.

Boundary observations (pre-existing, outside F01–F11 scope, not changed
this round): `ClinVar_get_variant_details` passes `variant_id` to esummary
verbatim, so the VCV-prefixed string form is rejected by NCBI
("Invalid uid"); the numeric variation ID (e.g. `13961`, string-typed per
the registered schema) is the working form, matching the tool's documented
input. `_normalize_variant_id` currently guards only the search tool.

Completion states for this round, reported separately:

1. Repository fixes for F01–F11: the five commits above landed and the
   recorded regression numbers are factual, but the 2026-10-14 re-review
   found items that were NOT closed by them and are fixed by the
   2026-10-14 round instead: the PVS1 rescue confirmation gate and the
   unsupported "Moderate/Supporting" tree phrase survived in
   SVI_REFERENCE (closed by `3b0dba65`), evals 14/15 were
   codon-incoherent and case 16 was missing (`3b0dba65`), a single
   malformed esummary record could crash the search/details tools
   (`0ef14f54`), non-string CSpec metadata hid behind string coercion
   (`03f0018c`), and documented example values violated registered
   types/enums (`cf511bcb`). "Complete" below therefore means the
   2026-10-13 commits themselves, not full closure of the findings.
2. Local install targets: the two Batch-B rule files are synced to both
   `~/Documents/VarsUnderReview/.agents/skills/...` and
   `~/.zcode/skills/...` targets; the code fixes live only in this
   worktree's environment (as before — the branch has not shipped).
3. Independent-host boundary acceptance for new evals 11–15 and re-runs of
   3/4: NOT performed this session. Per the honesty rules, same-session
   work above is not an independent acceptance receipt; this tier remains
   open and any earlier PARTIAL verdicts stand.

No push was performed.


## Review follow-up round (2026-10-14)

Scope: the remaining items found by re-review, executed per
`docs/superpowers/plans/2026-10-14-review-followup.md` in five batches
from `5df7d9a5`. Boundary held: no dependency/lockfile/tool-JSON/SDK
wrapper/metadata changes (verified zero drift below); repository
distribution copies synced only — INSTALLED skills were NOT touched this
round; no push.

Commits (counterexamples ran and failed first in every batch):

- `3b0dba65` — A: PVS1 rescue guidance rewritten (no universal
  RNA/protein confirmation gate; sourced framework-supported predictions
  may take the N/A path; unsupported conjecture never justifies N/A;
  generic-tree ≤10% non-critical in-frame loss pinned to Moderate with
  Supporting requiring its own rule basis); evals 14/15 rebuilt on
  synthetic transcript `NM_999997.1` with reference codon GGA so the
  three nucleotide substitutions are codon-consistent; new eval 16
  (`NM_999996.1:c.1200+2T>C`, predicted-functional GC donor, no
  variant-specific experiments, calculator must return needs_review /
  no_scoring_evidence / null); doc-guard catches both removed wordings;
  codon-consistency check uses four literal codons (no HGVS parsing);
  fact attachments verified free of expected outputs.
- `0ef14f54` — B: shared strict esummary record parser (empty object,
  `genes` null/dict/non-object entries, `germline_classification`
  null/non-object → ValueError naming the field); search isolates the
  damaged record (counts/IDs/healthy details kept, UID added to
  `missing_variant_ids`, reason in `warnings`, completeness false);
  details entry errors explicitly BEFORE citation fetch; healthy
  fixtures reshaped to real esummary fields with content assertions;
  the mislabeled "Default MCP registration path" tests renamed to
  direct-instantiation; new in-repo check through a REAL SMCP
  registration (fastmcp in-memory client) with all HTTP mocked.
- `03f0018c` — C: CSpec detail `@id`/`version`/`cspecStatus` TYPE
  checked before comparison — missing/null/blank stay compatible,
  present non-strings (incl. a float 2.1 that used to coerce, match the
  index and hide the damage) and unnormalizable non-empty `@id` ("///")
  are damage disclosed through the existing three channels with field
  and value; one damaged spec does not sink another.
- `cf511bcb` — D: CELLxGENE examples drop `operation`/`organism` (tool
  defaults) and use the string filter `feature_name == '…'`;
  ChIPAtlas examples drop the invalid `operation="gene_list"`; the
  CODE_PATTERNS structure block is now SIFTS-only raw-receipt collection
  (no sequence fetch, no `if not pdb_hits`, no NvidiaNIM fallback — a
  request error is never reinterpreted as "no experimental structures");
  AST guard upgraded to validate statically evaluable argument VALUES
  against registered types/enums (caught 8 literal errors across the two
  docs before the fix), executed-example stubs validate dynamic
  f-string filters against the real schemas, and the SIFTS example is
  exercised across has-structures / healthy-empty / request-error
  shapes asserting the raw receipt is preserved verbatim and no
  prediction tool is auto-called.

Final regression (this round's directed set; the 949/1 starting record
was a snapshot, not a prediction): 986 passed + 56 passed / 1 skipped
(PyMuPDF not installed) = 1042 passed / 1 skipped, exit 0; log at
`temp_docs_and_tests/benchmark_tracking/2026-10-14-review-followup/final-regression.log`.
ruff clean on all touched files; `git diff --check` clean against both
`5df7d9a5` and `2128ff57`; zero drift in uv.lock / pyproject.toml /
tool JSON configs / generated SDK wrappers / .tool_metadata.json;
canonical=Claude=Codex byte-identical for every touched skill file;
Codex frontmatter intact.

Completion states (reported separately):

1. Repository fixes for the re-review items: complete (four commits
   above plus this records commit).
2. Automation: the directed regression set above is green; no serial
   full-suite run (known local segfault) and no global install.
3. Independent-host acceptance for evals 11–16 and re-runs of 3/4: NOT
   performed this round. Same-session rehearsal is not an acceptance
   receipt; use the revised temporary skill copies, fresh sessions and
   the case facts only; keep the native resume entry on quota
   interruption; missing final answers stay PARTIAL. Synthetic-case
   passes are not acceptance of real-variant or full online-collection
   workflows.

No push was performed.
