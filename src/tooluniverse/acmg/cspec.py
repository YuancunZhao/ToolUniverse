"""Runtime-normalized ClinGen CSpec contracts.

The ClinGen registry is the source of truth.  Local compiled contracts are
optional accelerators only and must be bound to the exact online document
hash before they can add executable details.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .rule_catalog import (
    ACMG_CRITERIA,
    generic_bayesian_odds_for,
    is_valid_strength_for_criterion,
    strength_level_for,
)


_APPLICABLE = {"applicable", "apply", "yes", "true"}
CSPEC_RULE_PARSER_VERSION = "2026-08-09-v3"
_SAFE_INTERPRETATION_FIELDS = {
    "alternative_in_frame_start",
    "ba1_exception",
    "benign_variation_depleted",
    "critical_exons",
    "critical_region_established",
    "exon_absent_from_relevant_transcripts",
    "exon_lof_frequent_af_threshold",
    "exon_lof_frequent_in_population",
    "lof_mechanism_established",
    "maximum_credible_af",
    "mutually_exclusive_with",
    "operator",
    "case_count_threshold",
    "condition_logic",
    "point_table",
    "pathogenic_upstream_of_alternative_start",
    "predicted_frame_outcome",
    "predictor",
    "predictor_rules",
    "protein_accession",
    "regions",
    "rescue_transcript_known",
    "residues",
    "strength",
    "strength_ceiling",
    "threshold",
    "transcript",
    "variant_types",
}


_PREDICTORS = ("REVEL", "SpliceAI", "CADD", "AlphaMissense")
_OPERATOR_ALIASES = {
    ">=": ">=",
    "≥": ">=",
    "=>": ">=",
    "<=": "<=",
    "≤": "<=",
    "=<": "<=",
    ">": ">",
    "<": "<",
}


def _deterministic_text_contract(
    criterion: str, source_text: str
) -> tuple[dict[str, Any], list[str]]:
    """Parse a deliberately small, auditable subset of CSpec prose.

    Unrecognized prose remains visible and does not block the general rule
    scenario.  Parsed values are never inferred from a search query.
    """
    parsed: dict[str, Any] = {"parser_version": CSPEC_RULE_PARSER_VERSION}
    unparsed: list[str] = []
    normalized = " ".join(source_text.split())
    if not normalized:
        return {}, []

    predictor_rules: list[dict[str, Any]] = []
    predictor_pattern = re.compile(
        rf"\b({'|'.join(re.escape(value) for value in _PREDICTORS)})\b"
        r"(?:\s+(?:score|value))?\s*(>=|<=|=>|=<|≥|≤|>|<)\s*"
        r"(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    for match in predictor_pattern.finditer(normalized):
        predictor_rules.append(
            {
                "predictor": match.group(1),
                "operator": _OPERATOR_ALIASES[match.group(2)],
                "threshold": float(match.group(3)),
            }
        )
    if len(predictor_rules) == 1:
        parsed.update(predictor_rules[0])
    elif predictor_rules:
        parsed["predictor_rules"] = predictor_rules

    mcaf_match = re.search(
        r"\b(?:maximum\s+credible\s+(?:allele\s+)?frequency|MCAF)\b"
        r"\s*(?:is|of|[:=]|<=|=<|≤)?\s*"
        r"(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        normalized,
        re.IGNORECASE,
    )
    if mcaf_match:
        parsed["maximum_credible_af"] = float(mcaf_match.group(1))

    case_match = re.search(
        r"(>=|<=|=>|=<|≥|≤|>|<|at least|no more than)\s*(\d+)\s*"
        r"(?:independent\s+)?(?:probands?|cases?|families)",
        normalized,
        re.IGNORECASE,
    )
    if case_match:
        operator = case_match.group(1).casefold()
        parsed["operator"] = {
            "at least": ">=",
            "no more than": "<=",
        }.get(operator, _OPERATOR_ALIASES.get(operator, operator))
        parsed["case_count_threshold"] = int(case_match.group(2))

    point_rows: list[dict[str, Any]] = []
    point_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:points?|pts?)\s*(?:=|corresponds? to|supports?)\s*"
        r"(Very\s*Strong|Strong|Moderate|Supporting)",
        re.IGNORECASE,
    )
    for match in point_pattern.finditer(normalized):
        strength = _strength_code(criterion, match.group(2))
        if strength:
            point_rows.append(
                {"minimum_points": float(match.group(1)), "strength": strength}
            )
    if point_rows:
        parsed["point_table"] = sorted(
            point_rows, key=lambda row: float(row["minimum_points"]), reverse=True
        )

    residue_values: set[int] = set()
    regions: list[dict[str, int]] = []
    if re.search(r"\b(?:residue|codon|amino acid|region)\b", normalized, re.I):
        for start, end in re.findall(r"\b(\d{1,5})\s*[-–]\s*(\d{1,5})\b", normalized):
            start_value, end_value = int(start), int(end)
            if start_value <= end_value:
                regions.append({"start": start_value, "end": end_value})
        for value in re.findall(r"\b(?:residue|codon)\s*(\d{1,5})\b", normalized, re.I):
            residue_values.add(int(value))
    if residue_values:
        parsed["residues"] = sorted(residue_values)
    if regions:
        parsed["regions"] = regions

    variant_type_match = re.search(
        r"\b(?:applies?\s+to|applicable\s+to|variant\s+types?\s*[:=])\s*"
        r"([^.;]{1,160})",
        normalized,
        re.IGNORECASE,
    )
    if variant_type_match:
        variant_aliases = {
            "missense": "missense",
            "nonsense": "stop_gained",
            "stop gained": "stop_gained",
            "frameshift": "frameshift",
            "splice": "splice",
            "in-frame deletion": "inframe_deletion",
            "in frame deletion": "inframe_deletion",
            "in-frame insertion": "inframe_insertion",
            "in frame insertion": "inframe_insertion",
            "synonymous": "synonymous",
        }
        variant_text = variant_type_match.group(1).casefold()
        variant_types = sorted(
            {
                normalized_type
                for token, normalized_type in variant_aliases.items()
                if token in variant_text
            }
        )
        if variant_types:
            parsed["variant_types"] = variant_types

    mutually_exclusive = {
        value.upper()
        for match in re.finditer(
            r"\b(?:mutually\s+exclusive\s+with|do\s+not\s+use\s+with|"
            r"must\s+not\s+be\s+combined\s+with)\s+"
            r"((?:PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])"
            r"(?:\s*(?:,|/|and|or)\s*(?:PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7]))*)",
            normalized,
            re.IGNORECASE,
        )
        for value in re.findall(
            r"PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7]",
            match.group(1),
            re.IGNORECASE,
        )
        if value.upper() != criterion
    }
    if mutually_exclusive:
        parsed["mutually_exclusive_with"] = sorted(mutually_exclusive)

    ceiling_match = re.search(
        r"\b(?:maximum(?:\s+strength)?|maximal\s+strength|strength\s+ceiling|"
        r"capped\s+at|must\s+not\s+exceed|not\s+to\s+exceed)\s*"
        r"(?:is|of|[:=]|at)?\s*(Very\s*Strong|Strong|Moderate|Supporting)\b",
        normalized,
        re.IGNORECASE,
    )
    if ceiling_match:
        ceiling = _strength_code(criterion, ceiling_match.group(1))
        if ceiling:
            parsed["strength_ceiling"] = ceiling

    applied_strength_match = re.search(
        r"\b(?:apply|applied|use|award|assign)(?:\s+the\s+criterion)?\s+"
        r"(?:at|as)\s+(Very\s*Strong|Strong|Moderate|Supporting)\b",
        normalized,
        re.IGNORECASE,
    )
    if applied_strength_match:
        strength = _strength_code(criterion, applied_strength_match.group(1))
        if strength:
            parsed["strength"] = strength

    condition_groups = sum(
        bool(parsed.get(key))
        for key in (
            "predictor",
            "predictor_rules",
            "maximum_credible_af",
            "case_count_threshold",
            "point_table",
            "residues",
            "regions",
            "variant_types",
        )
    )
    if condition_groups > 1:
        has_any = bool(re.search(r"\b(?:or|either)\b", normalized, re.I))
        has_all = bool(re.search(r"\b(?:and|all\s+of)\b", normalized, re.I))
        if has_any != has_all:
            parsed["condition_logic"] = "any" if has_any else "all"
        else:
            unparsed.append("multi_condition_logic_ambiguous")

    # A recognized number does not make an entire paragraph executable when
    # uncaptured exceptions or conditional clauses remain.  Parsed fields stay
    # visible, while the scenario falls back to a source-backed candidate.
    unsupported_condition = re.search(
        r"\b(?:except(?:ion)?|unless|provided\s+that|only\s+(?:if|when)|"
        r"subject\s+to|on\s+the\s+condition\s+that)\b",
        normalized,
        re.IGNORECASE,
    )
    if unsupported_condition:
        unparsed.append("unsupported_conditional_or_exception_clause")

    recognized_content = set(parsed) - {"parser_version"}
    if not recognized_content:
        unparsed.append("no_supported_numeric_or_enumerated_rule_detected")
        return {}, unparsed
    return parsed, unparsed


def cspec_content_hash(candidate: dict[str, Any]) -> str:
    """Return a stable hash for the exact rule-bearing CSpec payload."""
    payload = candidate.get("specification")
    if not isinstance(payload, dict):
        payload = {
            "specification_id": candidate.get("specification_id"),
            "version": candidate.get("version"),
            "criterion_modifications": candidate.get("criterion_modifications") or [],
            "diseases": candidate.get("diseases") or [],
            "url": candidate.get("url"),
        }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _criterion_code(value: Any) -> str:
    code = str(value or "").strip().upper().split("_", 1)[0]
    return code if code in ACMG_CRITERIA else ""


def _strength_code(criterion: str, value: Any) -> str:
    raw = str(value or "").strip().replace(" ", "")
    if not raw:
        return ""
    aliases = {
        "verystong": "VeryStrong",
        "verystrong": "VeryStrong",
        "strong": "Strong",
        "moderate": "Moderate",
        "supporting": "Supporting",
        "standalone": "StandAlone",
    }
    level = aliases.get(raw.casefold())
    if level == "StandAlone" and criterion == "BA1":
        return "BA1"
    if level:
        default_level = strength_level_for(criterion, criterion)
        candidate = criterion if level == default_level else f"{criterion}_{level}"
    else:
        candidate = raw
    return candidate if is_valid_strength_for_criterion(criterion, candidate) else ""


def _text_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, str) and value.strip():
        values.append(value.strip())
    elif isinstance(value, dict):
        for nested in value.values():
            values.extend(_text_values(nested))
    elif isinstance(value, list):
        for nested in value:
            values.extend(_text_values(nested))
    return values


def _criterion_source_text(modification: dict[str, Any]) -> str:
    return "\n".join(
        _text_values(
            {
                "instructions": modification.get("instructions"),
                "strengths": modification.get("strengths"),
            }
        )
    )


def _structured_criterion(modification: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    criterion = _criterion_code(modification.get("criterion"))
    if not criterion:
        return "", {}
    applicability = str(modification.get("applicability") or "").strip()
    strengths: list[str] = []
    descriptor_applicability_values: list[str] = []
    default_strength = _strength_code(criterion, modification.get("default_strength"))
    if default_strength:
        strengths.append(default_strength)
    for descriptor in modification.get("strengths") or []:
        if not isinstance(descriptor, dict):
            continue
        descriptor_applicability = str(
            descriptor.get("applicability") or applicability
        ).strip()
        if descriptor_applicability:
            descriptor_applicability_values.append(descriptor_applicability)
        if (
            descriptor_applicability
            and descriptor_applicability.casefold() not in _APPLICABLE
        ):
            continue
        strength = _strength_code(criterion, descriptor.get("strength"))
        if strength and strength not in strengths:
            strengths.append(strength)
    source_text = _criterion_source_text(modification)
    applicability_values = [
        value for value in (applicability, *descriptor_applicability_values) if value
    ]
    explicitly_applicable = any(
        value.casefold() in _APPLICABLE for value in applicability_values
    )
    explicitly_not_applicable = bool(applicability_values) and not explicitly_applicable
    if explicitly_not_applicable:
        strengths = []
    result = {
        "criterion": criterion,
        "applicability": applicability,
        "allowed_strengths": strengths,
        "structured_source": {
            "criterion_id": modification.get("criterion_id"),
            "default_strength": modification.get("default_strength"),
        },
        "instructions": modification.get("instructions"),
        "source_text": source_text,
        "mutually_exclusive_with": [],
        "rule_applicable": not explicitly_not_applicable,
        "verification": "dynamic_cspec_structured",
    }
    parsed, parse_gaps = _deterministic_text_contract(criterion, source_text)
    if parsed:
        result.update(parsed)
        result["deterministic_parse_status"] = "partial" if parse_gaps else "parsed"
    else:
        result["deterministic_parse_status"] = "unresolved"
    result["deterministic_parse_gaps"] = parse_gaps
    if len(strengths) == 1:
        result["strength"] = strengths[0]
    return criterion, result


def _proposal_report(
    proposal: dict[str, Any],
    *,
    candidate: dict[str, Any],
    content_hash: str,
    modifications: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    criterion = _criterion_code(proposal.get("criterion"))
    errors: list[str] = []
    if str(proposal.get("specification_id") or "") != str(
        candidate.get("specification_id") or ""
    ):
        errors.append("specification_id_mismatch")
    if str(proposal.get("version") or "") != str(candidate.get("version") or ""):
        errors.append("specification_version_mismatch")
    if str(proposal.get("content_hash") or "") != content_hash:
        errors.append("specification_content_hash_mismatch")
    if not criterion or criterion not in modifications:
        errors.append("criterion_not_present_in_matched_cspec")
    elif modifications[criterion].get("rule_applicable") is False:
        errors.append("criterion_not_applicable_in_matched_cspec")
    excerpt = str(proposal.get("excerpt") or "").strip()
    source_text = (
        str(modifications.get(criterion, {}).get("source_text") or "")
        if criterion
        else ""
    )
    if not excerpt or excerpt.casefold() not in source_text.casefold():
        errors.append("cspec_excerpt_not_found")
    extractor = proposal.get("extractor")
    if (
        not isinstance(extractor, dict)
        or not extractor.get("name")
        or not extractor.get("version")
    ):
        errors.append("extractor_version_missing")
    strength = _strength_code(criterion, proposal.get("suggested_strength"))
    if not strength:
        errors.append("invalid_strength_for_criterion")
    interpretation = proposal.get("structured_interpretation")
    if not isinstance(interpretation, dict):
        errors.append("structured_interpretation_required")
        interpretation = {}
    unsafe_fields = sorted(set(interpretation) - _SAFE_INTERPRETATION_FIELDS)
    if unsafe_fields:
        errors.append("unsupported_interpretation_fields:" + ",".join(unsafe_fields))
    report = {
        "specification_id": proposal.get("specification_id"),
        "version": proposal.get("version"),
        "content_hash": proposal.get("content_hash"),
        "criterion": criterion or proposal.get("criterion"),
        "status": "verified" if not errors else "rejected",
        "errors": errors,
    }
    if errors:
        return report, None
    contract = {
        key: value
        for key, value in interpretation.items()
        if key in _SAFE_INTERPRETATION_FIELDS
    }
    contract.update(
        {
            "criterion": criterion,
            "strength": strength,
            "allowed_strengths": sorted(
                {
                    *modifications[criterion].get("allowed_strengths", []),
                    strength,
                }
            ),
            "applicability": modifications[criterion].get("applicability"),
            "instructions": modifications[criterion].get("instructions"),
            "source_text": modifications[criterion].get("source_text"),
            "cspec_excerpt": excerpt,
            "cspec_locator": proposal.get("locator"),
            "llm_interpretation": proposal.get("interpretation"),
            "confidence": proposal.get("confidence"),
            "extractor": dict(proposal.get("extractor") or {}),
            "verification": "dynamic_cspec_llm",
        }
    )
    return report, contract


def build_dynamic_cspec_contract(
    candidate: dict[str, Any],
    *,
    proposals: list[dict[str, Any]] | None = None,
    compiled_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize one uniquely applicable online CSpec into a runtime contract."""
    content_hash = cspec_content_hash(candidate)
    criteria: dict[str, dict[str, Any]] = {}
    review_requests: list[dict[str, Any]] = []
    for modification in candidate.get("criterion_modifications") or []:
        if not isinstance(modification, dict):
            continue
        criterion, normalized = _structured_criterion(modification)
        if not criterion:
            continue
        criteria[criterion] = normalized
        if (
            normalized.get("source_text")
            and normalized.get("deterministic_parse_status") != "parsed"
        ):
            review_requests.append(
                {
                    "specification_id": candidate.get("specification_id"),
                    "version": candidate.get("version"),
                    "content_hash": content_hash,
                    "criterion": criterion,
                    "locator": modification.get("criterion_id") or criterion,
                    "text": normalized["source_text"],
                    "reason": "natural_language_cspec_rule_not_fully_parsed",
                }
            )

    proposal_reports: list[dict[str, Any]] = []
    for proposal in proposals or []:
        if not isinstance(proposal, dict):
            continue
        report, interpreted = _proposal_report(
            proposal,
            candidate=candidate,
            content_hash=content_hash,
            modifications=criteria,
        )
        proposal_reports.append(report)
        if interpreted is not None:
            criteria[str(interpreted["criterion"])] = {
                **criteria[str(interpreted["criterion"])],
                **interpreted,
            }

    compiled_status = "not_available"
    if isinstance(compiled_contract, dict):
        if str(compiled_contract.get("content_hash") or "") == content_hash:
            compiled_status = "hash_verified"
            compiled_criteria = compiled_contract.get("criteria")
            if isinstance(compiled_criteria, dict):
                for criterion, contract in compiled_criteria.items():
                    if (
                        criterion in criteria
                        and criteria[criterion].get("rule_applicable") is not False
                        and isinstance(contract, dict)
                    ):
                        criteria[criterion] = {
                            **criteria[criterion],
                            **contract,
                            "verification": "compiled_hash_verified",
                        }
        else:
            compiled_status = "ignored_hash_unbound"

    countable_strengths = sorted(
        {
            strength
            for contract in criteria.values()
            for strength in contract.get("allowed_strengths") or []
            if is_valid_strength_for_criterion(
                str(contract.get("criterion") or ""), str(strength)
            )
        }
    )
    bayesian_odds = {
        strength: odds
        for strength in countable_strengths
        if (odds := generic_bayesian_odds_for(strength.split("_", 1)[0], strength))
        is not None
    }
    spec_id = str(candidate.get("specification_id") or "")
    primary_reference = candidate.get("url")
    if not primary_reference and spec_id:
        primary_reference = f"https://cspec.genome.network/cspec/ui/svi/doc/{spec_id}"
    version = str(candidate.get("version") or "")
    return {
        "specification_id": spec_id,
        "rule_id": f"clingen-cspec-runtime-{spec_id.casefold()}",
        "version": version,
        "gene": candidate.get("gene"),
        "diseases": list(candidate.get("diseases") or []),
        "status": "released_online",
        "primary_reference": primary_reference,
        "content_hash": content_hash,
        "criteria": criteria,
        "countable_strengths": countable_strengths,
        "bayesian_odds": bayesian_odds,
        "review_requests": review_requests,
        "proposal_reports": proposal_reports,
        "compiled_contract_status": compiled_status,
        "rule_source": "online_clingen_cspec",
    }


__all__ = [
    "CSPEC_RULE_PARSER_VERSION",
    "build_dynamic_cspec_contract",
    "cspec_content_hash",
]
