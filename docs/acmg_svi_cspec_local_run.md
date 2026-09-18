# Running the ACMG/CSpec tools from this worktree (local)

`ClinGen_search_cspec` and `ACMG_calculate_classification` exist only in
this checkout — NOT in the PyPI release — so point every runtime at this
worktree's environment until this branch ships.

Worktree: `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`
(branch `codex/acmg-svi-cspec-lightweight`, official baseline `752188d0`)

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
  over DS_AG/AL/DG/DL only; DP_* converted to int without truncation,
  with field-path warnings; `raw_response` returned verbatim; errors and
  warnings propagate to both SpliceAI tools. Real-API check: the variant
  that previously scored 0.0 now returns max delta 0.997.
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
