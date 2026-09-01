"""Release-smoke CLI contract tests without performing an installation."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "verify_acmg_install_smoke.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("acmg_install_smoke", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_online_provider_flag_is_opt_in(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source", "local"])
    assert module._parse_args().online_providers is False

    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--source", "local", "--online-providers"],
    )
    assert module._parse_args().online_providers is True


def test_git_ref_requires_a_full_commit_sha(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--source", "git-ref", "--git-ref", "deadbeef"],
    )
    with pytest.raises(SystemExit, match="2"):
        module._parse_args()


def test_embedded_online_gate_is_syntax_valid_and_covers_required_sources():
    module = _load_module()
    compile(module.ONLINE_CHECKS_PROGRAM, "<online-provider-smoke>", "exec")
    for name in (
        "ClinGen_search_cspec",
        "ClinGen_get_variant_classifications",
        "ClinVar_search_variants",
        "gnomad_get_variant",
        "MyVariant_get_pathogenicity_scores",
        "EuropePMC_get_full_text",
        "ACMG_evidence_collector",
    ):
        assert name in module.ONLINE_CHECKS_PROGRAM
    assert 'result.get("status") in {"success", "degraded"}' in (
        module.ONLINE_CHECKS_PROGRAM
    )


def test_zcode_config_is_read_only_and_requires_long_timeout(tmp_path):
    module = _load_module()
    path = tmp_path / "config.json"
    value = {
        "mcp": {
            "servers": {"tooluniverse": {"command": "uvx", "args": ["tooluniverse"]}}
        }
    }
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="600000"):
        module._zcode_server(path)
    value["mcp"]["servers"]["tooluniverse"]["timeoutMs"] = 900000
    path.write_text(json.dumps(value))
    before = path.read_bytes()
    assert module._zcode_server(path)["timeoutMs"] == 900000
    assert path.read_bytes() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["", "sha", "import_path"])
async def test_configured_mcp_checks_actual_manifest_even_with_same_version(
    monkeypatch, mismatch
):
    import fastmcp

    module = _load_module()
    configs = json.loads(
        (module.ROOT / "src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )

    class Client:
        def __init__(self, transport, timeout):
            assert transport.command == "uvx"
            assert timeout == 600
            assert transport.env["PYTHONNOUSERSITE"] == "0"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call_tool(self, name, args):
            from types import SimpleNamespace

            if name == "get_tool_info":
                data = {"tools": configs}
            elif args["tool_name"] == "ACMG_evidence_collector":
                data = {
                    "runtime_manifest": {
                        "tooluniverse_version": "1.4.1+acmg.9",
                        "distribution_vcs_commit": ("b" if mismatch == "sha" else "a")
                        * 40,
                        "package_location": "/local/checkout/tooluniverse"
                        if mismatch == "import_path"
                        else "/isolated/package/tooluniverse",
                        "distribution_package_location": "/isolated/package/tooluniverse",
                        "package_matches_distribution": mismatch != "import_path",
                    },
                    "final_classification_allowed": False,
                    "guard_context": {},
                }
            else:
                data = {"status": "PASS"}
            return SimpleNamespace(data=data)

    monkeypatch.setattr(fastmcp, "Client", Client)
    call = module._verify_configured_mcp(
        {
            "command": "uvx",
            "args": [],
            "timeoutMs": 600000,
            "env": {"PYTHONNOUSERSITE": "0"},
        },
        "1.4.1+acmg.9",
        "a" * 40,
    )
    if mismatch:
        with pytest.raises(ValueError, match="installation mismatch"):
            await call
    else:
        report = await call
        assert report["acmg_tools"] == 8
        assert (
            report["runtime_manifest"]["package_location"]
            == "/isolated/package/tooluniverse"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_ACMG_SLOW_MCP") != "1",
    reason="Opt-in 31-second stdio transport check",
)
async def test_stdio_response_can_exceed_thirty_seconds(tmp_path):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    # Test-only server: no new production tools or provider network calls.
    server = tmp_path / "slow.py"
    server.write_text("""import asyncio
from fastmcp import FastMCP
mcp = FastMCP("slow-transport-test")
@mcp.tool()
async def controlled_delay() -> dict:
    await asyncio.sleep(31)
    return {"status": "complete"}
mcp.run(transport="stdio")
""")
    async with Client(
        StdioTransport(command=sys.executable, args=[str(server)]), timeout=600
    ) as client:
        assert _load_module()._mcp_payload(
            await client.call_tool("controlled_delay", {})
        ) == {"status": "complete"}
