"""Runtime-normalized ClinGen CSpec contracts.

The ClinGen registry is the source of truth.  Local compiled contracts are
optional accelerators only and must be bound to the exact online document
hash before they can add executable details.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .rule_catalog import (
    ACMG_CRITERIA,
    generic_bayesian_odds_for,
    is_valid_strength_for_criterion,
    strength_level_for,
)


_APPLICABLE = {"applicable", "apply", "yes", "true"}
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
    "pathogenic_upstream_of_alternative_start",
    "predicted_frame_outcome",
    "predictor",
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
        if descriptor_applicability and descriptor_applicability.casefold() not in _APPLICABLE:
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
    if not isinstance(extractor, dict) or not extractor.get("name") or not extractor.get(
        "version"
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
        if normalized.get("source_text"):
            review_requests.append(
                {
                    "specification_id": candidate.get("specification_id"),
                    "version": candidate.get("version"),
                    "content_hash": content_hash,
                    "criterion": criterion,
                    "locator": modification.get("criterion_id") or criterion,
                    "text": normalized["source_text"],
                    "reason": "natural_language_cspec_rule_requires_llm_review",
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
        if (
            odds := generic_bayesian_odds_for(
                strength.split("_", 1)[0], strength
            )
        )
        is not None
    }
    spec_id = str(candidate.get("specification_id") or "")
    primary_reference = candidate.get("url")
    if not primary_reference and spec_id:
        primary_reference = (
            "https://cspec.genome.network/cspec/ui/svi/doc/" f"{spec_id}"
        )
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


__all__ = ["build_dynamic_cspec_contract", "cspec_content_hash"]
