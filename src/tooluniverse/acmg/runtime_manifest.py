"""Stable runtime and ruleset provenance for ACMG evidence results."""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
from typing import Any

from . import pvs1, rule_catalog


ACMG_RUNTIME_VERSION = "evidence-only-1"
COLLECTOR_SCHEMA_VERSION = "2026-07-27"
UPSTREAM_BASE_COMMIT = "089eb8e6308fc64ae5af3de4bfbec32b5cf07b61"
BAYESIAN_PRIOR = 0.1


def _distribution_provenance() -> tuple[str, str]:
    """Return the installed VCS revision when distribution metadata provides it."""
    try:
        distribution = metadata.distribution("tooluniverse")
    except metadata.PackageNotFoundError:
        return "", "source_tree"
    direct_url = distribution.read_text("direct_url.json")
    if not direct_url:
        return "", "installed_distribution"
    try:
        payload = json.loads(direct_url)
    except (TypeError, json.JSONDecodeError):
        return "", "installed_distribution"
    vcs_info = payload.get("vcs_info")
    if isinstance(vcs_info, dict):
        return str(vcs_info.get("commit_id") or ""), "vcs"
    directory_info = payload.get("dir_info")
    if isinstance(directory_info, dict) and directory_info.get("editable") is True:
        return "", "editable"
    return "", "installed_distribution"


def _ruleset_payload() -> dict[str, Any]:
    generic_odds = [
        {
            "direction": direction,
            "strength": strength,
            "odds": odds,
        }
        for (direction, strength), odds in sorted(
            rule_catalog._GENERIC_TAVTIGIAN_ODDS.items()
        )
    ]
    return {
        "criterion_rules": rule_catalog.RULE_CATALOG,
        "consequence_policies": rule_catalog.CONSEQUENCE_POLICIES,
        "spliceai_rule": rule_catalog.SPLICEAI_RULE,
        "pvs1_rule": {
            "rule_id": pvs1.RULE_ID,
            "version": pvs1.RULE_VERSION,
            "reference": pvs1.RULE_REFERENCE,
        },
        "generic_tavtigian_odds": generic_odds,
        "bayesian_prior": BAYESIAN_PRIOR,
    }


def ruleset_hash() -> str:
    canonical = json.dumps(
        _ruleset_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cspec_index(rule_context: dict[str, Any] | None) -> list[dict[str, str]]:
    context = rule_context if isinstance(rule_context, dict) else {}
    candidates = (
        context.get("applicable_specification"),
        context.get("executable_contract"),
    )
    indexed: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        row = {
            "specification_id": str(
                candidate.get("specification_id")
                or candidate.get("spec_id")
                or candidate.get("id")
                or ""
            ),
            "version": str(candidate.get("version") or ""),
            "content_hash": str(candidate.get("content_hash") or ""),
        }
        identity = (
            row["specification_id"],
            row["version"],
            row["content_hash"],
        )
        if any(identity) and identity not in seen:
            seen.add(identity)
            indexed.append(row)
    return indexed


def build_runtime_manifest(
    rule_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        package_version = metadata.version("tooluniverse")
    except metadata.PackageNotFoundError:
        package_version = "0.0.0+source"
    revision, source_type = _distribution_provenance()
    return {
        "tooluniverse_version": package_version,
        "acmg_runtime_version": ACMG_RUNTIME_VERSION,
        "collector_schema_version": COLLECTOR_SCHEMA_VERSION,
        "upstream_base_commit": UPSTREAM_BASE_COMMIT,
        "ruleset_hash": ruleset_hash(),
        "distribution_vcs_commit": revision,
        "distribution_source_type": source_type,
        "applicable_cspec": _cspec_index(rule_context),
    }


__all__ = [
    "ACMG_RUNTIME_VERSION",
    "BAYESIAN_PRIOR",
    "COLLECTOR_SCHEMA_VERSION",
    "UPSTREAM_BASE_COMMIT",
    "build_runtime_manifest",
    "ruleset_hash",
]
