# Running the ACMG/CSpec tools from this worktree (local)

The two tools added on this branch — `ClinGen_search_cspec` and
`ACMG_calculate_classification` — exist **only in this repository checkout**.
They are NOT in the PyPI release (tooluniverse 1.4.1 at the time of writing),
so `uvx tooluniverse …` / any remote MCP install pin will not have them.
Until this branch is released, point every runtime at this worktree's
environment.

Worktree: `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`
(branch `codex/acmg-svi-cspec-lightweight`, baseline
`752188d0f4daf9005d96edca0b7c8f0dfc7f10c6`)

## One-time setup

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
uv sync            # creates .venv with the project installed editable
```

Do not use `uv sync --all-extras`: the `graph` extra needs pygraphviz, which
requires system graphviz headers.

## Environment note: hidden `.pth` files under iCloud-synced ~/Documents

This workspace lives under `~/Documents`, which macOS syncs through iCloud's
file provider. On this machine the daemon marks every `*.pth` in
`.venv/lib/python3.12/site-packages/` with the macOS `UF_HIDDEN` flag within
seconds, and CPython's `site` module **skips hidden `.pth` files** — which
silently drops the editable-install path and makes both `import tooluniverse`
and `tooluniverse-smcp-stdio` fail with `ModuleNotFoundError` in fresh
processes. Regular module imports are NOT affected by the flag; only `.pth`
processing is.

Diagnosis and repair (environment state, not a code issue):

```bash
ls -lO .venv/lib/python3.12/site-packages/*.pth   # "hidden" in flags column
chflags nohidden .venv/lib/python3.12/site-packages/__editable__.tooluniverse-1.4.1.pth
env -u PYTHONPATH .venv/bin/python -c 'import tooluniverse; print(tooluniverse.__file__)'
```

If the flag returns within seconds (it does here — the daemon re-applies it),
the durable fix already installed in this venv is
`.venv/lib/python3.12/site-packages/sitecustomize.py`, which appends this
workspace's `src` directory to `sys.path` at interpreter startup — exactly
what the hidden `.pth` would have done. It works even though the daemon
hides it too, because hidden `.py` files import normally. If you rebuild the
venv somewhere `.pth` files keep their visibility, delete that
`sitecustomize.py`.

Note: `uv run` may try to append extra resolution entries to `uv.lock`
(cuda-bindings etc.) unless frozen; if you want to keep `uv.lock` pristine,
export `UV_FROZEN=1` or pass `--frozen`.

## SDK (Python)

```python
# run inside the worktree: uv run python my_script.py
from tooluniverse.tools import ClinGen_search_cspec, ACMG_calculate_classification

specs = ClinGen_search_cspec(gene="MYOC")
# → status success; data[0].specification_id "GN019", version "2.1",
#   PVS1 not applicable at any strength, PM2 applicable at Supporting
#   (AF ≤ 0.0001). Read data[0].url with get_webpage_text_from_url before
#   classifying under it.

result = ACMG_calculate_classification(
    variant_context={"variant": "NM_000715.3:c.1000C>T", "gene": "MYOC",
                     "disease": None, "inheritance_mode": None},
    rule_context={"cspec_lookup_status": "no_released_spec",
                  "combination_method": "tavtigian2020",
                  "specification": None, "applicable_rules_complete": True},
    evidence=evidence_28_records,   # exactly 28, one per ACMG/AMP code
    blocking_issues=[],
)
# → data.classification_status "computed", classification, total_score,
#   point_contributions, uncounted_records; or "needs_review" with
#   classification null and review_reasons.
```

Full input contract: see the tool's docstring or
`skills/tooluniverse-acmg-variant-classification/SKILL.md`.

## MCP (stdio)

Run the server from this worktree (this is what an MCP client config should
point at — not `uvx tooluniverse`):

```bash
/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/tooluniverse-smcp-stdio
```

Example client entry (JSON):

```json
{
  "mcpServers": {
    "tooluniverse-local": {
      "command": "/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/tooluniverse-smcp-stdio"
    }
  }
}
```

For a minimal session exposing only the two new tools (fast startup):

```bash
.venv/bin/tooluniverse-smcp-stdio \
  --include-tools ClinGen_search_cspec ACMG_calculate_classification
```

Verified over MCP on 2026-09-09: `tools/list` exposes both;
`ClinGen_search_cspec(gene="MYOC")` returns GN019 v2.1 with the Glaucoma VCEP;
`ACMG_calculate_classification` returns the Tavtigian 2020 result
(PVS1 + PM2_Supporting → Likely Pathogenic, 9 points).

## Tests

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
uv run pytest tests/unit/test_clingen_cspec_tool.py \
              tests/unit/test_acmg_calculate_classification.py \
              tests/integration/test_acmg_mcp_stdio.py -q --no-cov
```

The MCP test spawns the stdio server from the same venv and needs no network
(the CSpec network path is exercised by the online smoke recorded in
`docs/superpowers/plans/` implementation notes).
