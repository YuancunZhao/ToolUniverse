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

## Environment note: hidden `.pth` files in this workspace's venv

Observed behavior on this machine (facts): every `*.pth` in
`.venv/lib/python3.12/site-packages/` carries the macOS `UF_HIDDEN` flag;
clearing it with `chflags nohidden` makes imports work immediately, but the
flag reappears within about three seconds; `brctl download` does not prevent
the reappearance. CPython's `site` module skips hidden `.pth` files, which
silently drops the editable-install path, while regular module imports are
unaffected by the flag. The likely cause is the iCloud file provider
managing `~/Documents` (a sync daemon re-applying stored file state), but
the exact process has NOT been identified with process-level evidence --
treat the cause as unconfirmed.

Diagnosis and repair (environment state, not a code issue):

```bash
ls -lO .venv/lib/python3.12/site-packages/*.pth   # "hidden" in flags column
chflags nohidden .venv/lib/python3.12/site-packages/__editable__.tooluniverse-1.4.1.pth
env -u PYTHONPATH .venv/bin/python -c 'import tooluniverse; print(tooluniverse.__file__)'
```

If the flag returns within seconds (it does here — whatever sets it
re-applies it promptly), the durable fix already installed in this venv is
`.venv/lib/python3.12/site-packages/sitecustomize.py`, which appends this
workspace's `src` directory to `sys.path` at interpreter startup — exactly
what the hidden `.pth` would have done. It works even though it, too,
receives the hidden flag, because hidden `.py` files import normally. If
you rebuild the venv somewhere `.pth` files keep their visibility, delete
that `sitecustomize.py`.

Note on `uv.lock` (2026-09-10): the file is restored to the official
baseline `752188d0` byte-for-byte. The restored lock itself does not
cover everything the current `pyproject.toml` manifest can resolve (for
example the OCR extra), so `uv` may want to re-add entries -- this is a
retained upstream inconsistency, NOT a verified lock-consistency pass.
The existing `.venv` was NOT reinstalled against the restored lock; run
tests with `.venv/bin/python` directly, and pass `--frozen` (or
`UV_FROZEN=1`) to any `uv run`/install command so the re-resolution is
never written back.

## SDK (Python)

```python
# run inside the worktree: env -u PYTHONPATH .venv/bin/python my_script.py
from tooluniverse.tools import ClinGen_search_cspec, ACMG_calculate_classification

# 1) Real CSpec lookup for MYOC (online) -- carry the real result into
#    rule_context; do NOT hand-write no_released_spec for a gene that HAS
#    a Released specification.
specs = ClinGen_search_cspec(gene="MYOC")
# Check BOTH lists, not just data:
#   data: explicit gene matches -- MYOC -> GN019 v2.1 (Glaucoma VCEP,
#         PVS1 not applicable at any strength, PM2 applicable at
#         Supporting (AF <= 0.0001)); read data[0].url with
#         get_webpage_text_from_url before classifying under it.
#   unresolved_scope_specs: Released specifications whose gene scope the
#         index does not resolve (e.g. GN015, whose mitochondrial gene
#         rules appear only on its official page). Resolve EVERY candidate
#         even though GN019 already matches -- an explicit match does not
#         resolve other candidates; a nuclear-gene query can exclude GN015
#         on that documented basis, never on the missing `genes` alone.
#   partial_failures / missing_materials / detail_structure_failed on an
#         entry mean the specification was NOT fully read -- resolve via
#         the official page or keep cspec_lookup_status="unresolved".
assert specs["status"] == "success"
spec = specs["data"][0]
unresolved = specs["unresolved_scope_specs"]

# 2) Deterministic computation. The example variant below is SYNTHETIC
#    (TESTGENE does not exist) -- it demonstrates the interface only, with
#    the generic-rules rule_context; a real MYOC classification would pass
#    the specification block above (and MYOC's combination caps may pause
#    classification for expert review).
result = ACMG_calculate_classification(
    variant_context={"variant": "NM_999999.1:c.1000C>T", "gene": "TESTGENE",
                     "disease": "Synthetic fixture disease",
                     "inheritance_mode": "Autosomal dominant inheritance"},
    rule_context={  # generic rules example; for MYOC use the block below
        "cspec_lookup_status": "no_released_spec",
        "combination_method": "tavtigian2020",
        "specification": None, "applicable_rules_complete": True,
    },
    # "rule_context": {
    #     "cspec_lookup_status": "released_spec_found",
    #     "specification": {"id": spec["specification_id"],
    #                       "version": spec["version"],
    #                       "source_url": spec["url"],
    #                       "vcep": spec["vcep"]},
    #     "applicable_rules_complete": True,  # only after reading the full spec
    #     "combination_method": "tavtigian2020",  # or the spec's own method
    # },
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

Verified over MCP on 2026-09-09: `tools/list` exposes both tools;
`ClinGen_search_cspec(gene="MYOC")` returns GN019 v2.1 with the Glaucoma VCEP
(online smoke, recorded separately); `ACMG_calculate_classification` handles
all three outcome classes on synthetic fixtures (computed: PVS1 +
PM2_Supporting → Likely Pathogenic, 9 points; illegal input rejected;
incomplete context → needs_review).

## Tests

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_clingen_cspec_tool.py \
              tests/unit/test_acmg_calculate_classification.py \
              tests/integration/test_acmg_mcp_stdio.py -q --no-cov
```

The MCP test spawns the stdio server from the same venv and needs no network
(the CSpec network path is exercised by the online smoke recorded in
`docs/superpowers/plans/` implementation notes).
