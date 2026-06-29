#!/usr/bin/env python3
"""Create non-counted ACMG route candidates from user-supplied context."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


TRIGGERS = [
    (
        "de_novo_ps2_pm6",
        re.compile(r"\b(de novo|trio|parents?\s+negative|parental testing|maternity|paternity|parentage|mosaicism)\b", re.I),
        ["PS2", "PM6"],
    ),
    (
        "pp1_bs4_pp4_segregation",
        re.compile(r"\b(segregation|co-segregation|cosegregation|affected relatives?|pedigree|cascade)\b", re.I),
        ["PP1", "BS4", "PP4"],
    ),
    (
        "pm3_in_trans",
        re.compile(r"\b(compound heterozyg|in trans|phase confirmed|phased|biallelic|trans configuration)\b", re.I),
        ["PM3"],
    ),
    (
        "phenotype_dependent_pp4",
        re.compile(r"\b(HPO|phenotype specificity|highly specific phenotype|specific phenotype|diagnostic yield)\b", re.I),
        ["PP4"],
    ),
    (
        "benign_context_bs2",
        re.compile(r"\b(unaffected adult carrier|healthy homozygote|healthy carrier|observed in unaffected|unaffected individual)\b", re.I),
        ["BS2"],
    ),
    (
        "benign_context_bp5",
        re.compile(r"\b(alternate diagnosis|alternative diagnosis|another molecular diagnosis|explains phenotype)\b", re.I),
        ["BP5"],
    ),
]


def _flatten_context(context: dict[str, Any]) -> str:
    parts = []
    for key in ("family_context", "phenotype_context", "disease_context", "inheritance_context", "zygosity", "phase_context"):
        value = context.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        else:
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def discover_user_context_routes(context: dict[str, Any]) -> list[dict[str, Any]]:
    text = _flatten_context(context)
    routes: list[dict[str, Any]] = []
    for route, pattern, criteria in TRIGGERS:
        match = pattern.search(text)
        if not match:
            continue
        routes.append(
            {
                "criterion_group": route,
                "criteria": criteria,
                "source_type": "user_context",
                "route_outcome": "overlay_required",
                "counted": False,
                "trigger_text": match.group(0),
                "reason": "User context can trigger route planning only; criterion-specific validator must pass before evidence can be counted.",
            }
        )
    return routes


def main(argv: list[str] | None = None) -> int:
    payload = json.loads(sys.stdin.read() if not argv else argv[0])
    routes = discover_user_context_routes(payload if isinstance(payload, dict) else {})
    print(json.dumps({"route_candidates": routes}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
