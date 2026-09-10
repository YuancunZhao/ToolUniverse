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
