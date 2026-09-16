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
