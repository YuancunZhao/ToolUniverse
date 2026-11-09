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

                # 2026-11-03 (Batch A): raw SVI point-table values through
                # the real stdio server. svi_payload mirrors the TYR
                # c.1247C>A receipt shape: PM2 Supporting + PP3 Moderate +
                # PP4 3.0 (diagnostic yield 58.9% rounds down to the
                # 50.6% Table 2 row) -> LP at exactly 6, and a clamp case
                # where PP4's raw 5.5 (86.4% row) applies at the +5.0
                # locus cap. Both start from a clean all-not-assessed base
                # (the golden fixture's PVS1 would otherwise dominate the
                # total). svips_bad puts svi_points on PS4, which the
                # handler must reject.
                svi_payload = _golden_arguments()
                svi_payload["evidence"] = [_ev(c) for c in PATHOGENIC + BENIGN]
                for record in svi_payload["evidence"]:
                    if record["criterion"] == "PM2":
                        record.update(
                            status="met", strength="Supporting",
                            rationale="Absent from population databases",
                            source_refs=["gnomAD v4.1"],
                            rule_refs=["SVI PM2 v1.0"],
                            evidence_ids=["gnomad-absent"],
                        )
                    elif record["criterion"] == "PP3":
                        record.update(
                            status="met", strength="Moderate",
                            rationale="Calibrated splicing/missense predictors",
                            source_refs=["PMID:34770040"],
                            rule_refs=["Pejaver 2022 PP3"],
                            evidence_ids=["predictors-pp3"],
                        )
                    elif record["criterion"] == "PP4":
                        record.update(
                            status="met", strength="Moderate",
                            svi_points=3.0,
                            rationale=(
                                "Diagnostic yield 58.9% in the phenotype-"
                                "matched cohort; rounds down to the 50.6% "
                                "Table 2 row"
                            ),
                            source_refs=["PMID:30097210"],
                            rule_refs=["Biesecker 2024 Table 2"],
                            evidence_ids=["cohort-yield-58.9"],
                        )
                svi_ok = await client.call_tool(
                    "ACMG_calculate_classification", arguments=svi_payload,
                )

                clamp_payload = _golden_arguments()
                clamp_payload["evidence"] = [_ev(c) for c in PATHOGENIC + BENIGN]
                for record in clamp_payload["evidence"]:
                    if record["criterion"] == "PP4":
                        record.update(
                            status="met", strength="VeryStrong",
                            svi_points=5.5,
                            rationale=(
                                "Diagnostic yield 86.4%; Table 2 row 5.5, "
                                "applied at the +5.0 locus cap"
                            ),
                            source_refs=["PMID:30097210"],
                            rule_refs=["Biesecker 2024 Table 2"],
                            evidence_ids=["cohort-yield-86.4"],
                        )
                clamp_ok = await client.call_tool(
                    "ACMG_calculate_classification", arguments=clamp_payload,
                )

                svips_bad = _golden_arguments()
                for record in svips_bad["evidence"]:
                    if record["criterion"] == "PS4":
                        record.update(
                            status="met", strength="Strong",
                            svi_points=3.0,
                            rationale="case frequency",
                            source_refs=["PMID:1"],
                            rule_refs=["SVI"],
                            evidence_ids=["ps4-cases"],
                        )
                svips_rejected = await client.call_tool(
                    "ACMG_calculate_classification", arguments=svips_bad,
                )

                # 2026-11-09 (Batch A): precision, extreme, and negative-
                # boundary matrix through the real server. precision:
                # PM2 Supporting + PP3 Moderate + PP4 2.99 = 5.99 must
                # stay VUS (display rounding may not cross a threshold).
                # overflow: PP1 1e308 + PP4 1e308 exceeds the float range
                # and must return an explicit error, never a zeroed score.
                # negative: PP1 0.4 + benign -7 = -6.6 lands inside the
                # continuous Likely Benign band (-7 < total < 0).
                precision_payload = _golden_arguments()
                precision_payload["evidence"] = [
                    _ev(c) for c in PATHOGENIC + BENIGN
                ]
                for record in precision_payload["evidence"]:
                    if record["criterion"] == "PM2":
                        record.update(
                            status="met", strength="Supporting",
                            rationale="Absent from population databases",
                            source_refs=["gnomAD v4.1"],
                            rule_refs=["SVI PM2 v1.0"],
                            evidence_ids=["gnomad-absent"],
                        )
                    elif record["criterion"] == "PP3":
                        record.update(
                            status="met", strength="Moderate",
                            rationale="Calibrated splicing/missense predictors",
                            source_refs=["PMID:34770040"],
                            rule_refs=["Pejaver 2022 PP3"],
                            evidence_ids=["predictors-pp3"],
                        )
                    elif record["criterion"] == "PP4":
                        record.update(
                            status="met", strength="Moderate",
                            svi_points=2.99,
                            rationale=(
                                "Table 2 tier points carried at full "
                                "precision (2.99); 1 + 2 + 2.99 = 5.99"
                            ),
                            source_refs=["PMID:30097210"],
                            rule_refs=["Biesecker 2024 Table 2"],
                            evidence_ids=["cohort-tier-2.99"],
                        )
                precision_ok = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=precision_payload,
                )

                overflow_payload = _golden_arguments()
                overflow_payload["evidence"] = [
                    _ev(c) for c in PATHOGENIC + BENIGN
                ]
                for record in overflow_payload["evidence"]:
                    if record["criterion"] in ("PP1", "PP4"):
                        record.update(
                            status="met", strength="Strong",
                            svi_points=1e308,
                            rationale="Synthetic overflow probe",
                            source_refs=["PMID:1"],
                            rule_refs=["Biesecker 2024 Tables 2/3"],
                            evidence_ids=[f"overflow-{record['criterion']}"],
                        )
                overflow_result = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=overflow_payload,
                )

                negative_payload = _golden_arguments()
                negative_payload["evidence"] = [
                    _ev(c) for c in PATHOGENIC + BENIGN
                ]
                for record in negative_payload["evidence"]:
                    if record["criterion"] == "PP1":
                        record.update(
                            status="met", strength="Supporting",
                            svi_points=0.4,
                            rationale="Table 3 AR unaffected relative: 0.4",
                            source_refs=["PMID:30097210"],
                            rule_refs=["Biesecker 2024 Table 3"],
                            evidence_ids=["segregation-0.4"],
                        )
                    elif record["criterion"] in ("BS1", "BS3", "BP4"):
                        strength = {
                            "BS1": "Strong", "BS3": "Moderate",
                            "BP4": "Supporting",
                        }[record["criterion"]]
                        record.update(
                            status="met", strength=strength,
                            rationale=f"Synthetic {record['criterion']} met",
                            source_refs=["PMID:1"],
                            rule_refs=["Richards 2015"],
                            evidence_ids=[f"synthetic-{record['criterion']}"],
                        )
                negative_ok = await client.call_tool(
                    "ACMG_calculate_classification",
                    arguments=negative_payload,
                )

                return names, {
                    "legal": parse(legal),
                    "rejected": parse(rejected),
                    "paused": parse(paused),
                    "incomplete_rules": parse(incomplete_rules),
                    "svi_ok": parse(svi_ok),
                    "clamp_ok": parse(clamp_ok),
                    "svips_rejected": parse(svips_rejected),
                    "precision_ok": parse(precision_ok),
                    "overflow": parse(overflow_result),
                    "negative_ok": parse(negative_ok),
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

    # 2026-11-03: svi_points through the real server.
    svi = results["svi_ok"]
    assert svi["status"] == "success", svi
    svi_data = svi["data"]
    assert svi_data["classification_status"] == "computed"
    assert svi_data["classification"] == "Likely Pathogenic"
    assert svi_data["total_score"] == 6
    pp4 = next(
        c for c in svi_data["point_contributions"] if c["criterion"] == "PP4"
    )
    assert pp4["svi_points"] == 3.0
    assert pp4["points"] == 3.0
    assert svi_data["locus_evidence"]["raw_total"] == 3.0
    assert svi_data["locus_evidence"]["capped"] is False

    clamp = results["clamp_ok"]
    assert clamp["status"] == "success", clamp
    clamp_data = clamp["data"]
    assert clamp_data["classification_status"] == "computed"
    assert clamp_data["classification"] == "VUS"
    assert clamp_data["total_score"] == 5
    assert clamp_data["locus_evidence"]["raw_total"] == 5.5
    assert clamp_data["locus_evidence"]["applied_total"] == 5.0
    assert clamp_data["locus_evidence"]["capped"] is True
    assert "review_reasons" not in clamp_data

    svips = results["svips_rejected"]
    assert isinstance(svips, dict), svips
    assert svips.get("status") == "error", (
        f"svi_points outside PP1/PP4 must be rejected, got: {svips}"
    )
    assert "PP1" in svips.get("error", "") and "PP4" in svips.get("error", "")

    # 2026-11-09: precision, overflow, and negative-band boundary.
    precision = results["precision_ok"]
    assert precision["status"] == "success", precision
    precision_data = precision["data"]
    assert precision_data["classification_status"] == "computed"
    assert precision_data["classification"] == "VUS"
    assert precision_data["total_score"] < 6
    assert abs(precision_data["total_score"] - 5.99) < 1e-9

    overflow = results["overflow"]
    assert isinstance(overflow, dict), overflow
    assert overflow.get("status") == "error", (
        f"1e308 + 1e308 must error explicitly, got: {overflow}"
    )
    lowered = overflow.get("error", "").lower()
    assert "overflow" in lowered or "float" in lowered or "finite" in lowered
    # The error receipt itself must stay strictly JSON-serializable (no
    # Infinity/NaN tokens ever reach the wire).
    json.dumps(overflow, allow_nan=False)

    negative = results["negative_ok"]
    assert negative["status"] == "success", negative
    negative_data = negative["data"]
    assert negative_data["classification_status"] == "computed"
    assert negative_data["classification"] == "Likely Benign"
    assert abs(negative_data["total_score"] - (-6.6)) < 1e-9
    assert -7 < negative_data["total_score"] < 0


# --------------------------------------------------------------------------- #
# 2026-10-23 review (Batch F): compact-mode session over the same real
# stdio entry. Compact exposes ONLY the five discovery/execution tools
# (the full catalog stays loaded in the background for execute_tool);
# the ACMG/CSpec tools are reached via get_tool_info -> execute_tool
# instead of direct registration. Assertions avoid fixed token/byte
# counts (they drift with serialization and version); this is a real
# stdio protocol check, NOT an LLM acceptance.
# --------------------------------------------------------------------------- #
_COMPACT_TOOLS = {
    "find_tools",
    "list_tools",
    "grep_tools",
    "get_tool_info",
    "execute_tool",
}


def _run_compact_session():
    """Drive one --compact-mode stdio session end to end."""

    async def session():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=SERVER,
            args=["--compact-mode"],
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
                names = sorted(t.name for t in listed.tools)

                # get_tool_info resolves each target by its single name.
                infos = {}
                for tool in (
                    "ClinGen_search_cspec",
                    "ACMG_calculate_classification",
                ):
                    call = await client.call_tool(
                        "get_tool_info", {"tool_names": tool}
                    )
                    infos[tool] = parse(call)

                legal = await client.call_tool(
                    "execute_tool",
                    arguments={
                        "tool_name": "ACMG_calculate_classification",
                        "arguments": _golden_arguments(),
                    },
                )

                incomplete_args = _golden_arguments()
                incomplete_args["rule_context"][
                    "applicable_rules_complete"
                ] = False
                incomplete = await client.call_tool(
                    "execute_tool",
                    arguments={
                        "tool_name": "ACMG_calculate_classification",
                        "arguments": incomplete_args,
                    },
                )

                # 2026-11-09: fractional precision survives the compact
                # execute_tool path too (1 + 2 + 2.99 = 5.99 stays VUS).
                precision_args = _golden_arguments()
                precision_args["evidence"] = [
                    _ev(c) for c in PATHOGENIC + BENIGN
                ]
                for record in precision_args["evidence"]:
                    if record["criterion"] == "PM2":
                        record.update(
                            status="met", strength="Supporting",
                            rationale="Absent from population databases",
                            source_refs=["gnomAD v4.1"],
                            rule_refs=["SVI PM2 v1.0"],
                            evidence_ids=["gnomad-absent"],
                        )
                    elif record["criterion"] == "PP3":
                        record.update(
                            status="met", strength="Moderate",
                            rationale="Calibrated splicing/missense predictors",
                            source_refs=["PMID:34770040"],
                            rule_refs=["Pejaver 2022 PP3"],
                            evidence_ids=["predictors-pp3"],
                        )
                    elif record["criterion"] == "PP4":
                        record.update(
                            status="met", strength="Moderate",
                            svi_points=2.99,
                            rationale="Table 2 tier at full precision",
                            source_refs=["PMID:30097210"],
                            rule_refs=["Biesecker 2024 Table 2"],
                            evidence_ids=["cohort-tier-2.99"],
                        )
                precision = await client.call_tool(
                    "execute_tool",
                    arguments={
                        "tool_name": "ACMG_calculate_classification",
                        "arguments": precision_args,
                    },
                )
                return names, infos, parse(legal), parse(incomplete), parse(
                    precision
                )

    return asyncio.run(session())


def test_compact_mode_discovers_executes_and_pauses():
    names, infos, legal, incomplete, precision = _run_compact_session()

    # Exactly the five discovery/execution tools -- no full catalog.
    assert set(names) == _COMPACT_TOOLS, names

    for tool, info in infos.items():
        assert info.get("name") == tool, (tool, info)
        assert info.get("description"), tool

    legal_data = legal["data"]
    assert legal["status"] == "success"
    assert legal_data["classification_status"] == "computed"
    assert legal_data["classification"] == "Likely Pathogenic"
    assert legal_data["total_score"] == 9

    incomplete_data = incomplete["data"]
    assert incomplete_data["classification_status"] == "needs_review"
    assert incomplete_data["classification"] is None
    # The pause is faithful: no fabricated score field at all.
    assert "total_score" not in incomplete_data
    assert "incomplete_specification_material" in [
        reason["reason"]
        for reason in incomplete_data["review_reasons"]
    ]

    # 2026-11-09: fractional precision through compact execute_tool.
    assert precision["status"] == "success", precision
    precision_data = precision["data"]
    assert precision_data["classification_status"] == "computed"
    assert precision_data["classification"] == "VUS"
    assert precision_data["total_score"] < 6
    assert abs(precision_data["total_score"] - 5.99) < 1e-9
