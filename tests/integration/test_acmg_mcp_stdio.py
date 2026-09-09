"""MCP integration test: the two new ACMG/CSpec tools over stdio.

Spawns the ToolUniverse SMCP stdio server restricted to the two new tools,
then verifies MCP discovery and one full deterministic execution of
ACMG_calculate_classification. No network: the ClinGen_search_cspec network
path is covered by the recorded online smoke, not here.
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

import pytest


def _server_command():
    found = shutil.which("tooluniverse-smcp-stdio")
    if found:
        return found
    candidate = Path(sys.prefix) / "bin" / "tooluniverse-smcp-stdio"
    return str(candidate) if candidate.exists() else None


SERVER = _server_command()

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
    """Established PVS1 + PM2_Supporting (plan's fixed-material scenario)."""
    special = {
        "PVS1": _ev(
            "PVS1",
            "met",
            strength="VeryStrong",
            rationale="Canonical null variant; LoF established; NMD expected",
            source_refs=["PMID:31801624"],
            rule_refs=["SVI PVS1 decision tree v1.1"],
            evidence_ids=["pvs1-nmd-lof"],
        ),
        "PM2": _ev(
            "PM2",
            "met",
            strength="Supporting",
            rationale="Absent from gnomAD v4 with adequate coverage",
            source_refs=["gnomAD v4.1"],
            rule_refs=["SVI PM2_Supporting 2020"],
            evidence_ids=["gnomad-af-absent"],
        ),
    }
    return [special.get(c, _ev(c)) for c in PATHOGENIC + BENIGN]


def _golden_arguments():
    """Synthetic fixture: interface and arithmetic only, no real variant."""
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
    """Drive one stdio JSON-RPC session; returns (tool_names, calculator_result)."""

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
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listed = await client.list_tools()
                names = [t.name for t in listed.tools]

                call = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=_golden_arguments(),
                )
                payload = json.loads(call.content[0].text)
                return names, payload

    return asyncio.run(session())


@pytest.mark.skipif(SERVER is None, reason="tooluniverse-smcp-stdio not installed")
def test_mcp_discovers_and_executes_both_new_tools():
    names, payload = _run_mcp_session()

    assert "ClinGen_search_cspec" in names
    assert "ACMG_calculate_classification" in names

    assert payload["status"] == "success"
    assert payload["metadata"] == {"calculator_type": "variant_classification"}
    data = payload["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9
    assert data["pathogenic_points"] == 9
