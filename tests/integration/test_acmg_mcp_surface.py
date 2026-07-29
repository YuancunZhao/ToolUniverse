"""MCP discovery/execute surface required by the evidence-only ACMG setup."""

from __future__ import annotations

import pytest

from tooluniverse.smcp import SMCP


@pytest.mark.asyncio
async def test_compact_mode_exposes_discovery_and_execute_tools():
    server = SMCP(
        name="ACMG compact surface test",
        compact_mode=True,
        search_enabled=True,
    )

    tools = await server.get_tools()
    names = set(tools)

    assert {
        "find_tools",
        "list_tools",
        "grep_tools",
        "get_tool_info",
        "execute_tool",
    } <= names
