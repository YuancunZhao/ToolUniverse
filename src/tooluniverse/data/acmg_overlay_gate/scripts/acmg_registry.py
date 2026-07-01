#!/usr/bin/env python3
"""CLI-compatible wrapper for canonical ToolUniverse ACMG registry helpers."""

from __future__ import annotations

from acmg_final_answer_guard import _load_canonical_module


_canonical = _load_canonical_module("registry")

load_overlay_registry = _canonical.load_overlay_registry
criterion_to_overlay = _canonical.criterion_to_overlay
criterion_to_group = _canonical.criterion_to_group
required_coverage_for_criterion = _canonical.required_coverage_for_criterion
discovery_routes = _canonical.discovery_routes
baseline_routes_for_variant_type = _canonical.baseline_routes_for_variant_type
source_lead_routes = _canonical.source_lead_routes
