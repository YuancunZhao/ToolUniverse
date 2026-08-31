"""Disease-isolated CSpec/VCEP scenario evaluation for ACMG v4."""

from __future__ import annotations

import copy
import hashlib
import json
import operator
import re
from typing import Any

from .compatibility import (
    aggregate_evidence_cards,
    resolve_automatic_and_verified_compatibility,
)
from .rule_catalog import CSPEC_SCENARIO_POLICY_VERSION, is_valid_strength_for_criterion
from .summary import compute_bayesian_score, detect_conflicts


_OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "=": operator.eq,
}


def _criterion(row: dict[str, Any]) -> str:
    return str(row.get("criterion") or "").split("/", 1)[0]


def _strength(row: dict[str, Any]) -> str:
    return str(row.get("strength") or "")


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _normalized_moi(value: Any) -> str:
    token = _normalized(value)
    return {
        "ad": "autosomaldominant",
        "ar": "autosomalrecessive",
        "xld": "xlinkeddominant",
        "xlr": "xlinkedrecessive",
    }.get(token, token.removesuffix("inheritance"))


def _scenario_group_keys(scenario: dict[str, Any]) -> set[str]:
    assertion = scenario.get("assertion")
    if isinstance(assertion, dict):
        panel = _normalized(assertion.get("expert_panel"))
        mondo = _normalized(assertion.get("mondo_id"))
        moi = _normalized_moi(assertion.get("inheritance"))
        return {f"{panel}|{mondo}|{moi}"} if panel and mondo and moi else set()
    specification = scenario.get("specification")
    if not isinstance(specification, dict):
        return set()
    panel = _normalized(specification.get("vcep"))
    keys: set[str] = set()
    for disease in specification.get("diseases") or []:
        if not isinstance(disease, dict):
            continue
        mondo = _normalized(disease.get("mondo_id"))
        for moi in disease.get("inheritance") or []:
            normalized_moi = _normalized_moi(moi)
            if panel and mondo and normalized_moi:
                keys.add(f"{panel}|{mondo}|{normalized_moi}")
    return keys


def _scenario_card_id(
    card_id: str,
    scenario_id: str,
    rule_hash: str,
    evaluation_status: str,
) -> str:
    payload = f"{card_id}:{scenario_id}:{rule_hash}:{evaluation_status}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:20]
    return f"acmg-card:v4:{digest}"


def _walk(value: Any, *, path: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            rows.extend(_walk(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(_walk(child, path=f"{path}[{index}]"))
    else:
        rows.append((path, value))
    return rows


def _numeric_values(row: dict[str, Any], keys: set[str]) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []
    for path, value in _walk(
        {
            "observed_facts": row.get("observed_facts"),
        }
    ):
        normalized_key = _normalized(path.rsplit(".", 1)[-1])
        if normalized_key not in {_normalized(key) for key in keys}:
            continue
        if isinstance(value, bool):
            continue
        try:
            found.append((path, float(value)))
        except (TypeError, ValueError):
            continue
    return found


def _first_numeric(row: dict[str, Any], keys: set[str]) -> tuple[str, float] | None:
    values = _numeric_values(row, keys)
    return values[0] if values else None


def _compare(value: float, operation: str, threshold: float) -> bool | None:
    comparator = _OPERATORS.get(str(operation or ""))
    return comparator(value, threshold) if comparator else None


def _predictor_condition(
    row: dict[str, Any], predictor: str, operation: str, threshold: Any
) -> dict[str, Any]:
    predictor_key = _normalized(predictor)
    candidates: list[tuple[str, float]] = []
    for path, value in _walk(
        {
            "observed_facts": row.get("observed_facts"),
        }
    ):
        normalized_path = _normalized(path)
        if predictor_key not in normalized_path or isinstance(value, bool):
            continue
        if not any(
            token in normalized_path for token in ("score", "phred", "rankscore")
        ):
            continue
        try:
            candidates.append((path, float(value)))
        except (TypeError, ValueError):
            continue
    if not candidates:
        return {
            "condition": "predictor_threshold",
            "status": "unresolved",
            "missing": [f"{predictor}_score"],
        }
    path, observed = candidates[0]
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return {
            "condition": "predictor_threshold",
            "status": "unresolved",
            "missing": ["numeric_threshold"],
        }
    met = _compare(observed, operation, threshold_value)
    return {
        "condition": "predictor_threshold",
        "status": "met" if met is True else "not_met" if met is False else "unresolved",
        "observed": observed,
        "source_path": path,
        "operator": operation,
        "threshold": threshold_value,
        "predictor": predictor,
    }


def _mcaf_condition(row: dict[str, Any], threshold: Any) -> dict[str, Any]:
    values = _numeric_values(
        row,
        {
            "af",
            "allele_frequency",
            "global_af",
            "af_global",
            "popmax_af",
            "af_popmax",
            "maximum_allele_frequency",
        },
    )
    if not values:
        return {
            "condition": "maximum_credible_af",
            "status": "unresolved",
            "missing": ["allele_frequency"],
        }
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return {
            "condition": "maximum_credible_af",
            "status": "unresolved",
            "missing": ["numeric_threshold"],
        }
    path, observed = max(values, key=lambda item: item[1])
    return {
        "condition": "maximum_credible_af",
        "status": "met" if observed <= threshold_value else "not_met",
        "observed": observed,
        "source_path": path,
        "operator": "<=",
        "threshold": threshold_value,
    }


def _frequency_condition(
    row: dict[str, Any], threshold: Any, operation: str
) -> dict[str, Any]:
    values = _numeric_values(
        row,
        {
            "af",
            "allele_frequency",
            "global_af",
            "af_global",
            "popmax_af",
            "af_popmax",
            "maximum_allele_frequency",
        },
    )
    if not values:
        return {
            "condition": "population_frequency_threshold",
            "status": "unresolved",
            "missing": ["allele_frequency"],
        }
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return {
            "condition": "population_frequency_threshold",
            "status": "unresolved",
            "missing": ["numeric_threshold"],
        }
    path, observed = max(values, key=lambda item: item[1])
    met = _compare(observed, operation, threshold_value)
    return {
        "condition": "population_frequency_threshold",
        "status": "met" if met is True else "not_met" if met is False else "unresolved",
        "observed": observed,
        "source_path": path,
        "operator": operation,
        "threshold": threshold_value,
    }


def _case_count_condition(
    row: dict[str, Any], operation: str, threshold: Any
) -> dict[str, Any]:
    observed = _first_numeric(
        row,
        {
            "independent_case_count",
            "case_count",
            "proband_count",
            "family_count",
        },
    )
    if observed is None:
        case_ids = row.get("source_case_ids")
        if isinstance(case_ids, list) and case_ids:
            observed = ("source_case_ids", float(len(set(map(str, case_ids)))))
    if observed is None:
        return {
            "condition": "case_count_threshold",
            "status": "unresolved",
            "missing": ["independent_case_count"],
        }
    path, observed_value = observed
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        return {
            "condition": "case_count_threshold",
            "status": "unresolved",
            "missing": ["numeric_threshold"],
        }
    met = _compare(observed_value, operation, threshold_value)
    return {
        "condition": "case_count_threshold",
        "status": "met" if met is True else "not_met" if met is False else "unresolved",
        "observed": observed_value,
        "source_path": path,
        "operator": operation,
        "threshold": threshold_value,
    }


def _point_table_condition(row: dict[str, Any], point_table: Any) -> dict[str, Any]:
    observed = _first_numeric(row, {"total_points", "raw_points", "points"})
    if observed is None:
        return {
            "condition": "point_table",
            "status": "unresolved",
            "missing": ["points"],
        }
    path, points = observed
    entries: list[tuple[float, dict[str, Any]]] = []
    for entry in point_table or []:
        if not isinstance(entry, dict) or not entry.get("strength"):
            continue
        try:
            entries.append((float(entry.get("minimum_points") or 0), entry))
        except (TypeError, ValueError):
            continue
    if not entries:
        return {
            "condition": "point_table",
            "status": "unresolved",
            "missing": ["valid_point_table"],
        }
    entries.sort(key=lambda item: item[0], reverse=True)
    matched = next(
        (entry for minimum_points, entry in entries if points >= minimum_points),
        None,
    )
    return {
        "condition": "point_table",
        "status": "met" if matched else "not_met",
        "observed": points,
        "source_path": path,
        "mapped_strength": str((matched or {}).get("strength") or ""),
    }


def _protein_position(row: dict[str, Any]) -> tuple[str, int] | None:
    observed = _first_numeric(
        row, {"protein_position", "amino_acid_position", "residue"}
    )
    if observed:
        return observed[0], int(observed[1])
    for container in (
        row.get("variant_identity"),
        row.get("observed_facts"),
    ):
        if not isinstance(container, dict):
            continue
        for key in ("hgvs_p", "protein_hgvs"):
            match = re.search(r"p\.[A-Za-z*]{1,3}(\d+)", str(container.get(key) or ""))
            if match:
                return key, int(match.group(1))
    return None


def _region_condition(row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    observed = _protein_position(row)
    if observed is None:
        return {
            "condition": "protein_region",
            "status": "unresolved",
            "missing": ["protein_position"],
        }
    path, position = observed
    residues: set[int] = set()
    for value in contract.get("residues") or []:
        try:
            residues.add(int(value))
        except (TypeError, ValueError):
            continue
    regions: list[dict[str, Any]] = []
    for value in contract.get("regions") or []:
        if not isinstance(value, dict):
            continue
        try:
            regions.append(
                {**value, "start": int(value["start"]), "end": int(value["end"])}
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not residues and not regions:
        return {
            "condition": "protein_region",
            "status": "unresolved",
            "missing": ["valid_residue_or_region_rule"],
        }
    met = position in residues or any(
        int(region.get("start") or -1) <= position <= int(region.get("end") or -1)
        for region in regions
    )
    return {
        "condition": "protein_region",
        "status": "met" if met else "not_met",
        "observed": position,
        "source_path": path,
        "residues": sorted(residues),
        "regions": regions,
    }


def _variant_type_condition(row: dict[str, Any], allowed: Any) -> dict[str, Any]:
    allowed_types = {_normalized(value) for value in allowed or [] if value}
    observed_values: set[str] = set()
    for path, value in _walk(
        {
            "variant_identity": row.get("variant_identity"),
            "observed_facts": row.get("observed_facts"),
        }
    ):
        if any(
            token in _normalized(path)
            for token in ("consequence", "varianttype", "so_term")
        ):
            if isinstance(value, str):
                observed_values.update(
                    _normalized(token) for token in re.split(r"[,/&|]", value)
                )
    if not observed_values:
        return {
            "condition": "variant_types",
            "status": "unresolved",
            "missing": ["variant_type"],
        }
    return {
        "condition": "variant_types",
        "status": "met" if allowed_types & observed_values else "not_met",
        "observed": sorted(observed_values),
        "allowed": sorted(allowed_types),
    }


def _strength_rank(strength: str) -> int:
    if strength == "BA1" or "VeryStrong" in strength or strength == "PVS1":
        return 4
    if (
        "Strong" in strength
        or strength.startswith(("PS", "BS"))
        and "_" not in strength
    ):
        return 3
    if "Moderate" in strength or strength.startswith("PM") and "_" not in strength:
        return 2
    if (
        "Supporting" in strength
        or strength.startswith(("PP", "BP"))
        and "_" not in strength
    ):
        return 1
    return 0


def evaluate_cspec_criterion(
    row: dict[str, Any], criterion_contract: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate the finite, auditable subset of one CSpec criterion."""
    if criterion_contract.get("rule_applicable") is False:
        return {
            "status": "not_applicable",
            "conditions": [],
            "missing_inputs": [],
            "mapped_strength": "",
            "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
        }
    parse_status = str(criterion_contract.get("deterministic_parse_status") or "")
    parse_gaps = list(criterion_contract.get("deterministic_parse_gaps") or [])
    executable_fields = {
        "predictor_rules",
        "predictor",
        "maximum_credible_af",
        "population_frequency_threshold",
        "case_count_threshold",
        "point_table",
        "residues",
        "regions",
        "variant_types",
    }
    has_executable_condition = any(
        criterion_contract.get(field) not in (None, [], {}, "")
        for field in executable_fields
    )
    if (parse_status == "partial" or parse_gaps) and not has_executable_condition:
        return {
            "status": "unresolved",
            "conditions": [],
            "missing_inputs": parse_gaps or ["fully_parsed_rule"],
            "mapped_strength": "",
            "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
        }

    conditions: list[dict[str, Any]] = []
    predictor_rules = criterion_contract.get("predictor_rules")
    if isinstance(predictor_rules, list):
        conditions.extend(
            _predictor_condition(
                row,
                str(rule.get("predictor") or ""),
                str(rule.get("operator") or ""),
                rule.get("threshold"),
            )
            for rule in predictor_rules
            if isinstance(rule, dict)
        )
    elif criterion_contract.get("predictor"):
        conditions.append(
            _predictor_condition(
                row,
                str(criterion_contract.get("predictor") or ""),
                str(criterion_contract.get("operator") or ""),
                criterion_contract.get("threshold"),
            )
        )
    if criterion_contract.get("maximum_credible_af") is not None:
        conditions.append(
            _mcaf_condition(row, criterion_contract.get("maximum_credible_af"))
        )
    elif criterion_contract.get("population_frequency_threshold") is not None:
        conditions.append(
            _frequency_condition(
                row,
                criterion_contract.get("population_frequency_threshold"),
                str(criterion_contract.get("operator") or ""),
            )
        )
    if criterion_contract.get("case_count_threshold") is not None:
        conditions.append(
            _case_count_condition(
                row,
                str(criterion_contract.get("operator") or ">="),
                criterion_contract.get("case_count_threshold"),
            )
        )
    if criterion_contract.get("point_table"):
        conditions.append(
            _point_table_condition(row, criterion_contract.get("point_table"))
        )
    if criterion_contract.get("residues") or criterion_contract.get("regions"):
        conditions.append(_region_condition(row, criterion_contract))
    if criterion_contract.get("variant_types"):
        conditions.append(
            _variant_type_condition(row, criterion_contract.get("variant_types"))
        )

    condition_logic = str(criterion_contract.get("condition_logic") or "")
    if len(conditions) > 1 and condition_logic not in {"all", "any"}:
        return {
            "status": "unresolved",
            "conditions": conditions,
            "missing_inputs": ["explicit_multi_condition_logic"],
            "mapped_strength": "",
            "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
        }
    statuses = {str(condition.get("status") or "") for condition in conditions}
    if parse_status == "partial" or parse_gaps:
        status = "unresolved"
    elif not conditions:
        status = "condition_met"
    elif condition_logic == "any":
        status = (
            "condition_met"
            if "met" in statuses
            else "unresolved"
            if "unresolved" in statuses
            else "condition_not_met"
        )
    else:
        status = (
            "condition_not_met"
            if "not_met" in statuses
            else "unresolved"
            if "unresolved" in statuses
            else "condition_met"
        )

    mapped_strength = ""
    if status == "condition_met":
        point_strengths = [
            str(condition.get("mapped_strength") or "")
            for condition in conditions
            if condition.get("mapped_strength")
        ]
        mapped_strength = (
            point_strengths[0]
            if len(point_strengths) == 1
            else str(criterion_contract.get("strength") or _strength(row))
        )
    ceiling = str(criterion_contract.get("strength_ceiling") or "")
    if (
        mapped_strength
        and ceiling
        and _strength_rank(mapped_strength) > _strength_rank(ceiling)
    ):
        mapped_strength = ceiling
    return {
        "status": status,
        "conditions": conditions,
        "missing_inputs": sorted(
            {
                str(value)
                for condition in conditions
                for value in condition.get("missing") or []
                if value
            }
            | {str(value) for value in parse_gaps if value}
        ),
        "mapped_strength": mapped_strength,
        "strength_ceiling": ceiling,
        "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
    }


def _not_calculated(estimate_type: str, reason: str) -> dict[str, Any]:
    return {
        "status": "not_calculated",
        "estimate_type": estimate_type,
        "reason": reason,
        "included_card_ids": [],
        "not_a_final_classification": True,
    }


def _scenario_specification_id(scenario: dict[str, Any]) -> str:
    specification = scenario.get("specification")
    return (
        str(specification.get("specification_id") or "")
        if isinstance(specification, dict)
        else ""
    )


def _clone_for_scenario(
    row: dict[str, Any],
    scenario: dict[str, Any],
    contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    cloned = copy.deepcopy(row)
    criterion = _criterion(cloned)
    criterion_contract = (contract.get("criteria") or {}).get(criterion)
    scenario_id = str(scenario.get("scenario_id") or "")
    contract_hash = str(contract.get("content_hash") or "")
    evaluation = (
        evaluate_cspec_criterion(cloned, criterion_contract)
        if isinstance(criterion_contract, dict)
        else {
            "status": "condition_met",
            "conditions": [],
            "missing_inputs": [],
            "mapped_strength": "",
            "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
        }
    )
    cloned["scenario_id"] = scenario_id
    cloned["card_id"] = _scenario_card_id(
        str(cloned.get("card_id") or ""),
        scenario_id,
        contract_hash,
        str(evaluation.get("status") or ""),
    )
    dimensions = dict(cloned.get("verification_dimensions") or {})
    if scenario.get("applicability_status") == "candidate":
        dimensions["disease_match_status"] = "candidate"
    cloned["verification_dimensions"] = dimensions
    roles = dict(cloned.get("calculation_roles") or {})
    if not isinstance(criterion_contract, dict):
        if scenario.get("applicability_status") == "candidate":
            roles["verified"] = False
        cloned["calculation_roles"] = roles
        evaluation["rule_scope"] = "generic_svi_inherited"
        return cloned, {
            "card_id": cloned.get("card_id"),
            "criterion": criterion,
            **evaluation,
        }
    evaluation_status = str(evaluation.get("status") or "")
    base_status = str(row.get("evidence_status") or "")
    may_reconsider_not_met = bool(
        base_status == "not_met"
        and evaluation_status == "condition_met"
        and evaluation.get("conditions")
    )
    preserve_nonpositive = base_status in {"excluded", "deprecated"} or (
        base_status == "not_met" and not may_reconsider_not_met
    )
    if preserve_nonpositive:
        roles.update({"automatic": False, "verified": False})
        evaluation["scenario_card_status"] = "base_nonpositive_preserved"
    elif evaluation_status == "not_applicable":
        cloned["evidence_status"] = "excluded"
        cloned["exclusion_reason"] = "cspec_criterion_not_applicable"
        roles.update({"automatic": False, "verified": False})
    elif evaluation_status == "condition_not_met":
        cloned["evidence_status"] = "not_met"
        cloned["strength"] = "not_met"
        roles.update({"automatic": False, "verified": False})
    elif evaluation_status == "unresolved":
        cloned["evidence_status"] = "source_backed_candidate"
        roles.update({"automatic": True, "verified": False})
    else:
        mapped_strength = str(evaluation.get("mapped_strength") or "")
        if mapped_strength and is_valid_strength_for_criterion(
            criterion, mapped_strength
        ):
            cloned["strength"] = mapped_strength
        roles["automatic"] = True
        roles["verified"] = bool(
            scenario.get("applicability_status") == "matched"
            and roles.get("verified") is True
            and isinstance(criterion_contract, dict)
            and str(criterion_contract.get("verification") or "")
            in {"compiled_hash_verified", "dynamic_cspec_structured"}
        )
        if isinstance(criterion_contract, dict):
            cloned["evidence_status"] = (
                "rule_mapped" if roles["verified"] else "source_backed_candidate"
            )
    cloned["calculation_roles"] = roles
    if isinstance(criterion_contract, dict):
        specification_id = str(contract.get("specification_id") or "")
        contract_version = str(contract.get("version") or "")
        cloned["rule_basis"] = (
            f"Online ClinGen CSpec {specification_id} {contract_version}; "
            f"condition evaluation={evaluation.get('status')}"
        ).strip()
        cloned["rule_id"] = str(contract.get("rule_id") or "")
        cloned["rule_version"] = str(contract.get("version") or "")
        verification = str(criterion_contract.get("verification") or "")
        cloned["rule_source"] = {
            "type": (
                "dynamic_cspec_llm"
                if verification == "dynamic_cspec_llm"
                else "dynamic_cspec_structured"
            ),
            "rule_id": contract.get("rule_id"),
            "version": contract.get("version"),
            "content_hash": contract_hash,
            "scenario_policy_version": CSPEC_SCENARIO_POLICY_VERSION,
        }
        if verification == "dynamic_cspec_llm":
            llm_suggestion = dict(cloned.get("llm_suggestion") or {})
            llm_suggestion["cspec"] = {
                "extractor": dict(criterion_contract.get("extractor") or {}),
                "confidence": criterion_contract.get("confidence"),
                "interpretation": criterion_contract.get("llm_interpretation"),
                "locator": criterion_contract.get("cspec_locator"),
                "excerpt": criterion_contract.get("cspec_excerpt"),
            }
            cloned["llm_suggestion"] = llm_suggestion
        cloned["strength_source"] = "dynamic_cspec"
        facts = dict(cloned.get("observed_facts") or {})
        facts["cspec_contract_applied"] = {
            "specification_id": contract.get("specification_id"),
            "version": contract.get("version"),
            "content_hash": contract_hash,
            "evaluation": evaluation,
            "bayesian_odds": (
                (contract.get("bayesian_odds") or {}).get(_strength(cloned))
                if isinstance(contract.get("bayesian_odds"), dict)
                else None
            ),
            "mutually_exclusive_with": list(
                criterion_contract.get("mutually_exclusive_with") or []
            ),
        }
        cloned["observed_facts"] = facts
    return cloned, {
        "card_id": cloned.get("card_id"),
        "criterion": criterion,
        **evaluation,
    }


def build_scenario_results(
    rows: list[dict[str, Any]],
    rule_context: dict[str, Any],
    vcep_assertions: list[dict[str, Any]],
    *,
    known_source_fact_ids: set[str],
    verified_source_fact_ids: set[str],
) -> dict[str, Any]:
    """Build isolated scenario cards, estimates, conflicts, and default choice."""
    generic_rows = [
        copy.deepcopy(row)
        for row in rows
        if str(row.get("scenario_id") or "generic-svi") == "generic-svi"
    ]
    scenario_specs = list(rule_context.get("rule_scenarios") or [])
    known_scenarios = {str(row.get("scenario_id") or "") for row in scenario_specs}
    merged_assertion_scenarios: dict[str, str] = {}
    for assertion in vcep_assertions:
        scenario_id = str(assertion.get("scenario_id") or "")
        assertion_spec = {
            "scenario_id": scenario_id,
            "scenario_type": "vcep_assertion",
            "applicability_status": assertion.get("applicability_status"),
            "assertion": assertion,
        }
        assertion_keys = _scenario_group_keys(assertion_spec)
        matched_spec = next(
            (
                scenario
                for scenario in scenario_specs
                if scenario.get("scenario_type") == "vcep_cspec"
                and assertion_keys
                and assertion_keys & _scenario_group_keys(scenario)
            ),
            None,
        )
        if isinstance(matched_spec, dict):
            merged_id = str(matched_spec.get("scenario_id") or "")
            if merged_id:
                merged_assertion_scenarios[scenario_id] = merged_id
                assertion["merged_into_scenario_id"] = merged_id
                continue
        if scenario_id and scenario_id not in known_scenarios:
            scenario_specs.append(assertion_spec)
            known_scenarios.add(scenario_id)

    scenario_cards: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    matched_scenarios: list[str] = []
    for scenario in scenario_specs:
        scenario_id = str(scenario.get("scenario_id") or "generic-svi")
        applicability = str(scenario.get("applicability_status") or "candidate")
        if applicability in {"applicable", "matched"} and scenario_id != "generic-svi":
            matched_scenarios.append(scenario_id)
        if applicability == "mismatch":
            estimates.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_type": scenario.get("scenario_type"),
                    "applicability_status": applicability,
                    "applicability_reasons": list(
                        scenario.get("applicability_reasons") or []
                    ),
                    "specification_id": _scenario_specification_id(scenario),
                    "evidence_card_ids": [],
                    "automatic_bayesian": _not_calculated(
                        "automatic", "scenario_not_applicable"
                    ),
                    "verified_bayesian": _not_calculated(
                        "verified", "scenario_not_applicable"
                    ),
                    "compatibility_exclusions": [],
                    "conflict_report": {"has_conflicts": False, "conflicts": []},
                    "rule_execution_trace": [],
                }
            )
            continue

        contract = scenario.get("contract")
        traces: list[dict[str, Any]] = []
        if scenario_id == "generic-svi":
            scenario_rows = copy.deepcopy(generic_rows)
        elif isinstance(contract, dict):
            scenario_rows = []
            for row in generic_rows:
                cloned, trace = _clone_for_scenario(row, scenario, contract)
                scenario_rows.append(cloned)
                traces.append(trace)
        else:
            scenario_rows = []
            if scenario.get("scenario_type") == "vcep_assertion":
                for row in generic_rows:
                    cloned = copy.deepcopy(row)
                    cloned["scenario_id"] = scenario_id
                    cloned["card_id"] = _scenario_card_id(
                        str(cloned.get("card_id") or ""),
                        scenario_id,
                        "vcep-assertion",
                        "condition_met",
                    )
                    if applicability == "candidate":
                        dimensions = dict(cloned.get("verification_dimensions") or {})
                        dimensions["disease_match_status"] = "candidate"
                        cloned["verification_dimensions"] = dimensions
                        roles = dict(cloned.get("calculation_roles") or {})
                        roles["verified"] = False
                        cloned["calculation_roles"] = roles
                    scenario_rows.append(cloned)

        vcep_rows = (
            []
            if scenario_id == "generic-svi"
            else [
                copy.deepcopy(row)
                for row in rows
                if row.get("evidence_status") == "expert_panel_applied"
                and (
                    str(row.get("scenario_id") or "") == scenario_id
                    or merged_assertion_scenarios.get(str(row.get("scenario_id") or ""))
                    == scenario_id
                )
            ]
        )
        for row in vcep_rows:
            if str(row.get("scenario_id") or "") != scenario_id:
                row["scenario_id"] = scenario_id
                row["card_id"] = _scenario_card_id(
                    str(row.get("card_id") or ""),
                    scenario_id,
                    "merged-vcep-assertion",
                    "condition_met",
                )
        if applicability == "candidate":
            for row in vcep_rows:
                dimensions = dict(row.get("verification_dimensions") or {})
                dimensions["disease_match_status"] = "candidate"
                row["verification_dimensions"] = dimensions
                roles = dict(row.get("calculation_roles") or {})
                roles.update({"automatic": True, "verified": False})
                row["calculation_roles"] = roles
        scenario_rows.extend(vcep_rows)
        scenario_rows = aggregate_evidence_cards(scenario_rows)
        if scenario_id != "generic-svi":
            scenario_cards.extend(copy.deepcopy(scenario_rows))

        automatic_compatibility, verified_compatibility = (
            resolve_automatic_and_verified_compatibility(
                scenario_rows,
                known_source_fact_ids=known_source_fact_ids,
                verified_source_fact_ids=verified_source_fact_ids,
                scenario_id=scenario_id,
            )
        )
        automatic_score = compute_bayesian_score(
            automatic_compatibility["compatible_evidence"],
            known_source_fact_ids=known_source_fact_ids,
            estimate_type="automatic",
            calculation_role="automatic",
            eligibility="automatic",
        )
        verified_score = (
            _not_calculated("verified", "scenario_context_not_confirmed")
            if applicability == "candidate"
            else compute_bayesian_score(
                verified_compatibility["compatible_evidence"],
                verified_source_fact_ids=verified_source_fact_ids,
                estimate_type="verified",
                calculation_role="verified",
                eligibility="verified",
            )
        )
        conflict_report = detect_conflicts(
            scenario_rows,
            known_source_fact_ids=known_source_fact_ids,
            eligibility="automatic",
        )
        estimates.append(
            {
                "scenario_id": scenario_id,
                "scenario_type": scenario.get("scenario_type"),
                "applicability_status": applicability,
                "applicability_reasons": list(
                    scenario.get("applicability_reasons") or []
                ),
                "specification_id": _scenario_specification_id(scenario),
                "evidence_card_ids": [
                    str(row.get("card_id") or "")
                    for row in scenario_rows
                    if row.get("card_id")
                ],
                "automatic_bayesian": automatic_score,
                "verified_bayesian": verified_score,
                "compatibility_exclusions": [
                    {
                        "card_id": row.get("card_id"),
                        "criterion": _criterion(row),
                        "reason": row.get("reason") or row.get("exclusion_reason"),
                    }
                    for row in automatic_compatibility["excluded_evidence"]
                ],
                "conflict_report": conflict_report,
                "rule_execution_trace": traces,
            }
        )

    unique_matched = sorted(set(matched_scenarios))
    default_scenario_id = (
        unique_matched[0] if len(unique_matched) == 1 else "generic-svi"
    )
    default_reason = (
        "unique_matched_disease_scenario"
        if len(unique_matched) == 1
        else "generic_svi_no_matched_scenario"
        if not unique_matched
        else "generic_svi_ambiguous_matched_scenarios"
    )
    default_estimate = next(
        (row for row in estimates if row.get("scenario_id") == default_scenario_id),
        {},
    )
    return {
        "scenario_cards": scenario_cards,
        "scenario_estimates": estimates,
        "default_scenario_id": default_scenario_id,
        "default_selection_reason": default_reason,
        "default_card_ids": list(default_estimate.get("evidence_card_ids") or []),
        "policy_version": CSPEC_SCENARIO_POLICY_VERSION,
    }


__all__ = [
    "CSPEC_SCENARIO_POLICY_VERSION",
    "build_scenario_results",
    "evaluate_cspec_criterion",
]
