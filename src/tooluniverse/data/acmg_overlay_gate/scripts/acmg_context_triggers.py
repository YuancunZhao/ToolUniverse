#!/usr/bin/env python3
"""CLI wrapper for canonical ToolUniverse ACMG context triggers."""

from __future__ import annotations

from acmg_final_answer_guard import _load_canonical_module


_canonical = _load_canonical_module("context_triggers")

discover_user_context_routes = _canonical.discover_user_context_routes
main = _canonical.main


if __name__ == "__main__":
    raise SystemExit(main())
