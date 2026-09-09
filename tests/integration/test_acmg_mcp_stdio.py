"""MCP integration test: the two new ACMG/CSpec tools over stdio.

Spawns the ToolUniverse SMCP stdio server restricted to the two new tools
and verifies, through a real MCP session: discovery of both tools, a legal
deterministic computation, rejection of illegal input, and a needs_review
pause. No network: the ClinGen_search_cspec network path is covered by the
separately recorded online smoke.

The server is always taken from THIS test interpreter's environment
(``sys.prefix/bin``) -- never from a global PATH lookup -- so the test can
never silently pass against a different installation. A missing entry point
fails the suite; it is not skipped.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

SERVER = str(Path(sys.prefix) / "bin" / "tooluniverse-smcp-stdio")

PATHOGENIC = [
    "PVS1", "PS1", "PS2", "PS3", "PS4",
    "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
    "PP1", "PP2", "PP3", "PP4", "PP5",
]
BENIGN = [
    "BA1", "BS1", "BS2", "BS3", "BS4",
    "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
]


def _ev(criterion, status="not_assessed", **kw):
    rec = {
        "criterion": criterion,
        "status": status,
        "strength": None,
        "rationale": "",
        "source_refs": [],
        "rule_refs": [],
        "evidence_ids": [],
    }
    rec.update(kw)
    return rec


def _golden_evidence():
    """Synthetic fixture: interface and arithmetic only, no real variant."""
    special = {
        "PVS1": _ev(
            "PVS1",
            "met",
            strength="VeryStrong",
            rationale="Canonical null variant; LoF established; NMD expected",
            source_refs=["PMID:31801624"],
            rule_refs=["SVI PVS1 decision tree"],
            evidence_ids=["pvs1-nmd-lof"],
        ),
        "PM2": _ev(
            "PM2",
            "met",
            strength="Supporting",
            rationale="Absent from population databases with adequate coverage",
            source_refs=["gnomAD v4.1"],
            rule_refs=["SVI PM2 v1.0"],
            evidence_ids=["gnomad-af-absent"],
        ),
    }
    return [special.get(c, _ev(c)) for c in PATHOGENIC + BENIGN]


def _golden_arguments():
    return {
        "variant_context": {
            "variant": "NM_999999.1:c.1000C>T",
            "gene": "TESTGENE",
            "disease": "Synthetic fixture disease",
            "inheritance_mode": "Autosomal dominant inheritance",
        },
        "rule_context": {
            "cspec_lookup_status": "no_released_spec",
            "combination_method": "tavtigian2020",
            "specification": None,
            "applicable_rules_complete": True,
        },
        "evidence": _golden_evidence(),
        "blocking_issues": [],
    }


def _run_mcp_session():
    """Drive one stdio MCP session; returns (tool_names, results_by_case).

    cases: computed (legal), rejected (illegal references), paused
    (incomplete variant context).
    """

    async def session():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=SERVER,
            args=[
                "--include-tools",
                "ClinGen_search_cspec",
                "ACMG_calculate_classification",
            ],
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONUNBUFFERED": "1",
                "TOOLUNIVERSE_LIGHT_IMPORT": "1",
            },
        )

        def parse(call):
            try:
                return json.loads(call.content[0].text)
            except (ValueError, AttributeError, IndexError):
                return {"isError": True, "raw": str(call)}

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listed = await client.list_tools()
                names = [t.name for t in listed.tools]

                legal = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=_golden_arguments(),
                )

                rejected_args = _golden_arguments()
                for record in rejected_args["evidence"]:
                    if record["criterion"] == "PM2":
                        record["evidence_ids"] = [None]
                rejected = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=rejected_args,
                )

                paused_args = _golden_arguments()
                paused_args["variant_context"] = dict(
                    paused_args["variant_context"], disease=None
                )
                paused = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=paused_args,
                )

                incomplete_rules_args = _golden_arguments()
                incomplete_rules_args["rule_context"][
                    "applicable_rules_complete"
                ] = False
                incomplete_rules = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=incomplete_rules_args,
                )
                return names, {
                    "legal": parse(legal),
                    "rejected": parse(rejected),
                    "paused": parse(paused),
                    "incomplete_rules": parse(incomplete_rules),
                }

    return asyncio.run(session())


def test_server_entry_comes_from_this_environment():
    # Fail loudly rather than skip: acceptance requires this interpreter's
    # own environment to expose the entry point.
    assert Path(SERVER).exists(), (
        f"tooluniverse-smcp-stdio entry point is missing from the current "
        f"test environment ({SERVER}); run tests with the worktree venv "
        "(.venv/bin/python -m pytest), not a global or PyPI installation"
    )


def test_mcp_discovers_and_executes_both_new_tools():
    names, results = _run_mcp_session()

    assert "ClinGen_search_cspec" in names
    assert "ACMG_calculate_classification" in names

    legal = results["legal"]
    assert legal["status"] == "success"
    assert legal["metadata"] == {"calculator_type": "variant_classification"}
    data = legal["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9
    assert data["pathogenic_points"] == 9

    rejected = results["rejected"]
    assert isinstance(rejected, dict), rejected
    assert rejected.get("status") == "error", (
        f"illegal input must be rejected with an explicit error, got: "
        f"{rejected}"
    )
    assert rejected.get("error")

    paused = results["paused"]
    assert paused["data"]["classification_status"] == "needs_review"
    assert paused["data"]["classification"] is None
    assert "incomplete_variant_context" in [
        r["reason"] for r in paused["data"]["review_reasons"]
    ]

    incomplete = results["incomplete_rules"]
    assert incomplete["data"]["classification_status"] == "needs_review"
    assert incomplete["data"]["classification"] is None
    assert "incomplete_specification_material" in [
        r["reason"] for r in incomplete["data"]["review_reasons"]
    ]
