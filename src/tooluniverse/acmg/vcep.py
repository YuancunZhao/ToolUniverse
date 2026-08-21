"""ClinGen Evidence Repository assertions and scenario-safe VCEP cards."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .models import EvidenceCard, SourceFact
from .rule_catalog import ACMG_CRITERIA, is_valid_strength_for_criterion


VCEP_ASSERTION_PARSER_VERSION = "2026-08-09-v3"
VCEP_ALLELE_MATCH_POLICY_VERSION = "2026-08-09-v3"
VCEP_MOI_POLICY_VERSION = "2026-08-09-v3"
VCEP_ALLELE_MATCH_TIERS = (
    "clinvar_variation_id",
    "caid",
    "verified_coding_or_genomic_hgvs",
)
VCEP_MOI_ALIASES = {
    "autosomal_dominant": frozenset(
        {"autosomal dominant", "autosomal dominant inheritance", "ad"}
    ),
    "autosomal_recessive": frozenset(
        {"autosomal recessive", "autosomal recessive inheritance", "ar"}
    ),
    "x_linked_dominant": frozenset(
        {"x linked dominant", "x linked dominant inheritance", "xld"}
    ),
    "x_linked_recessive": frozenset(
        {"x linked recessive", "x linked recessive inheritance", "xlr"}
    ),
    "x_linked": frozenset({"x linked", "x linked inheritance"}),
    "mitochondrial": frozenset(
        {"mitochondrial", "mitochondrial inheritance", "maternal inheritance"}
    ),
}
VCEP_NEGATIVE_APPLIED_STATUSES = frozenset(
    {
        "not met",
        "not_met",
        "not applicable",
        "not_applicable",
        "not applied",
        "not_applied",
        "unmet",
        "excluded",
        "rejected",
        "false",
    }
)


def _negative_applied_status(value: Any) -> bool:
    normalized = re.sub(r"[_-]+", " ", str(value or "").strip().casefold())
    normalized = re.sub(r"\s+", " ", normalized)
    return any(
        normalized == status.replace("_", " ")
        or normalized.startswith(f"{status.replace('_', ' ')} ")
        for status in VCEP_NEGATIVE_APPLIED_STATUSES
    )


def _normalized(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _canonical_identity_token(value: Any) -> str:
    return _normalized(value)


def _inheritance_classes(value: Any) -> set[str]:
    raw = str(value or "").strip().casefold()
    if not raw:
        return set()
    normalized = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    classes: set[str] = set()
    for inheritance_class, tokens in VCEP_MOI_ALIASES.items():
        if normalized in tokens:
            classes.add(inheritance_class)
    return classes


def _match_status(expected: Any, observed: Any, *, inheritance: bool = False) -> str:
    if not str(expected or "").strip():
        return "candidate"
    if not str(observed or "").strip():
        return "candidate"
    if inheritance:
        expected_values = _inheritance_classes(expected)
        observed_values = _inheritance_classes(observed)
        if not expected_values or not observed_values:
            return "candidate"
        return "matched" if expected_values & observed_values else "mismatch"
    expected_value = _normalized(expected)
    observed_value = _normalized(observed)
    return "matched" if expected_value == observed_value else "mismatch"


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _all_strings(child)]
    if isinstance(value, list):
        return [text for child in value for text in _all_strings(child)]
    return []


def _version_key(value: Any) -> tuple[int, ...]:
    numbers = tuple(int(token) for token in re.findall(r"\d+", str(value or "")))
    return numbers or (0,)


def _values(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value] if value not in (None, "") else []


def _hgvs_kind(value: Any) -> str:
    token = _canonical_identity_token(value)
    if ":c." in token:
        return "coding_hgvs"
    if ":g." in token:
        return "genomic_hgvs"
    if ":p." in token or token.startswith("p."):
        return "protein_hgvs"
    return ""


def _verified_hgvs_tokens(identity: dict[str, Any]) -> set[str]:
    values: list[Any] = [
        identity.get("validated_hgvs_c"),
        identity.get("hgvs_c"),
        identity.get("hgvs_g"),
    ]
    normalization = identity.get("normalization")
    normalization = normalization if isinstance(normalization, dict) else {}
    selected = normalization.get("selected_candidate")
    if isinstance(selected, dict):
        values.extend([selected.get("hgvs_c"), selected.get("hgvs_g")])
    # Version-different aliases are accepted only when the identity resolver
    # explicitly records them as verified equivalents.
    values.extend(_values(normalization.get("verified_hgvs_aliases")))
    return {
        token
        for value in values
        if (token := _canonical_identity_token(value))
        and _hgvs_kind(token) in {"coding_hgvs", "genomic_hgvs"}
    }


def _row_hgvs_tokens(row: dict[str, Any]) -> set[str]:
    values = [row.get("Variation"), *_values(row.get("HGVS"))]
    return {
        token
        for value in values
        if (token := _canonical_identity_token(value)) and _hgvs_kind(token)
    }


def _identity_match(row: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    expected_variation_ids = {
        str(value).strip()
        for key in ("variation_id", "clinvar_variation_id")
        for value in _values(identity.get(key))
        if str(value).strip().isdecimal()
    }
    observed_variation_id = str(row.get("ClinVar Variation Id") or "").strip()
    if observed_variation_id and observed_variation_id in expected_variation_ids:
        return {
            "status": "matched",
            "basis": "clinvar_variation_id",
            "matched_identifiers": [observed_variation_id],
            "rejection_reasons": [],
        }

    def normalized_caid(value: Any) -> str:
        token = str(value or "").strip().casefold()
        return token.split(":", 1)[1] if token.startswith(("car:", "caid:")) else token

    expected_caids = {
        normalized_caid(value)
        for value in _values(identity.get("caid"))
        if str(value).strip()
    }
    observed_caid = str(row.get("CAID") or "").strip()
    if observed_caid and normalized_caid(observed_caid) in expected_caids:
        return {
            "status": "matched",
            "basis": "caid",
            "matched_identifiers": [observed_caid],
            "rejection_reasons": [],
        }

    expected_hgvs = _verified_hgvs_tokens(identity)
    observed_hgvs = _row_hgvs_tokens(row)
    allele_matches = sorted(expected_hgvs & observed_hgvs)
    if allele_matches:
        return {
            "status": "matched",
            "basis": "verified_allele_hgvs",
            "matched_identifiers": allele_matches,
            "rejection_reasons": [],
        }

    expected_protein = _canonical_identity_token(identity.get("hgvs_p"))
    protein_matches = sorted(
        token
        for token in observed_hgvs
        if _hgvs_kind(token) == "protein_hgvs" and token == expected_protein
    )
    rejection_reasons: list[str] = []
    if protein_matches:
        rejection_reasons.append("protein_hgvs_is_context_only")
    if identity.get("rsid"):
        rejection_reasons.append("rsid_alone_is_not_allele_specific")
    if expected_hgvs and observed_hgvs:
        rejection_reasons.append("allele_hgvs_mismatch")
    return {
        "status": "candidate"
        if protein_matches or identity.get("rsid")
        else "mismatch",
        "basis": "protein_or_rsid_context"
        if protein_matches or identity.get("rsid")
        else "none",
        "matched_identifiers": protein_matches,
        "rejection_reasons": sorted(
            set(rejection_reasons or ["no_exact_allele_identifier_match"])
        ),
    }


def _disease_match_status(expected: Any, row: dict[str, Any]) -> str:
    expected_value = str(expected or "").strip()
    observed_mondo = str(row.get("Mondo Id") or "").strip()
    observed_name = str(row.get("Disease") or "").strip()
    if not expected_value:
        return "candidate"
    if expected_value.casefold().startswith("mondo:"):
        if not observed_mondo:
            return "candidate"
        return (
            "matched"
            if _normalized(expected_value) == _normalized(observed_mondo)
            else "mismatch"
        )
    if observed_name and _normalized(expected_value) == _normalized(observed_name):
        return "candidate"
    return "mismatch" if observed_name else "candidate"


def _strength_from_parts(criterion: str, level: str) -> str:
    normalized_level = str(level or "").casefold().replace(" ", "")
    if normalized_level in {"", "default", "strong"} and criterion.startswith(
        ("PS", "BS")
    ):
        return criterion
    if normalized_level in {"", "default", "moderate"} and criterion.startswith("PM"):
        return criterion
    if normalized_level in {"", "default", "supporting"} and criterion.startswith(
        ("PP", "BP")
    ):
        return criterion
    if criterion == "PVS1" and normalized_level in {"", "default", "verystrong"}:
        return "PVS1"
    mapping = {
        "verystrong": "VeryStrong",
        "strong": "Strong",
        "moderate": "Moderate",
        "supporting": "Supporting",
    }
    suffix = mapping.get(normalized_level)
    return f"{criterion}_{suffix}" if suffix else criterion


def _criterion_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    structured: list[dict[str, Any]] = []
    container = row.get("Applied Criteria")
    values = container if isinstance(container, list) else [container]
    for value in values:
        if not isinstance(value, dict):
            continue
        criterion = str(
            value.get("criterion")
            or value.get("code")
            or value.get("acmgCriterion")
            or ""
        ).upper()
        if criterion not in ACMG_CRITERIA:
            continue
        met = value.get("met")
        status = (
            str(value.get("status") or value.get("result") or "").strip().casefold()
        )
        if (
            met is False
            or _negative_applied_status(met)
            or _negative_applied_status(status)
        ):
            continue
        strength = str(value.get("strength") or value.get("evidenceStrength") or "")
        structured.append(
            {
                "criterion": criterion,
                "strength": _strength_from_parts(criterion, strength),
                "evidence_summary": value.get("evidenceSummary")
                or value.get("description"),
                "pmids": value.get("pmids") or value.get("publications") or [],
                "raw": dict(value),
            }
        )
    return structured


def _unparsed_criterion_mentions(row: dict[str, Any]) -> list[dict[str, str]]:
    text = "\n".join(
        _all_strings(
            [
                row.get("Guidelines"),
                row.get("Evidence Summaries"),
            ]
        )
    )
    found: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"(?<![A-Z0-9])(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])"
        r"(?:[_\s-]*(Very\s*Strong|Strong|Moderate|Supporting))?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        criterion = match.group(1).upper()
        key = f"{criterion}:{match.start()}"
        found[key] = {
            "criterion": criterion,
            "text": " ".join(
                text[max(0, match.start() - 80) : match.end() + 120].split()
            ),
        }
    return list(found.values())


def parse_vcep_assertions(
    source_facts: dict[str, SourceFact],
    *,
    identity: dict[str, Any],
    disease: str = "",
    inheritance: str = "",
) -> tuple[dict[str, Any], list[dict[str, Any]], list[EvidenceCard]]:
    """Return external assertions and exact applied-criterion cards."""
    history: list[dict[str, Any]] = []
    for fact in source_facts.values():
        if fact.tool_name != "ClinGen_get_variant_classifications":
            continue
        for row in fact.features.get("variant_classifications") or []:
            if not isinstance(row, dict):
                continue
            identity_match = _identity_match(row, identity)
            history.append(
                {
                    **row,
                    "source_fact_id": fact.fact_id,
                    "exact_variant_match": identity_match["status"] == "matched",
                    "identity_match_status": identity_match["status"],
                    "identity_match_basis": identity_match["basis"],
                    "matched_identifiers": identity_match["matched_identifiers"],
                    "identity_rejection_reasons": identity_match["rejection_reasons"],
                    "unparsed_criterion_mentions": _unparsed_criterion_mentions(row),
                }
            )
    exact = [
        row
        for row in history
        if row["exact_variant_match"] and _normalized(row.get("Status")) == "released"
    ]
    exact.sort(
        key=lambda row: (
            str(row.get("Release Date") or ""),
            _version_key(row.get("Version")),
        ),
        reverse=True,
    )
    latest_by_scenario: dict[str, dict[str, Any]] = {}
    for row in exact:
        scenario_key = "|".join(
            [
                str(row.get("Expert Panel") or ""),
                str(row.get("Mondo Id") or row.get("Disease") or ""),
                str(row.get("MOI") or ""),
            ]
        )
        latest_by_scenario.setdefault(scenario_key, row)
    assertions: list[dict[str, Any]] = []
    cards: list[EvidenceCard] = []
    for scenario_key, row in latest_by_scenario.items():
        scenario_hash = hashlib.sha256(scenario_key.encode()).hexdigest()[:16]
        scenario_id = f"vcep:{scenario_hash}"
        disease_status = _disease_match_status(disease, row)
        inheritance_status = _match_status(
            inheritance, row.get("MOI"), inheritance=True
        )
        applicability_status = (
            "mismatch"
            if "mismatch" in {disease_status, inheritance_status}
            else "matched"
            if disease_status == inheritance_status == "matched"
            else "candidate"
        )
        assertion = {
            "scenario_id": scenario_id,
            "classification": row.get("Assertion"),
            "expert_panel": row.get("Expert Panel"),
            "condition": row.get("Disease"),
            "mondo_id": row.get("Mondo Id"),
            "inheritance": row.get("MOI"),
            "version": row.get("Version"),
            "release_date": row.get("Release Date"),
            "status": row.get("Status"),
            "caid": row.get("CAID"),
            "clinvar_variation_id": row.get("ClinVar Variation Id"),
            "hgvs": list(row.get("HGVS") or []),
            "identity_match_status": row.get("identity_match_status"),
            "identity_match_basis": row.get("identity_match_basis"),
            "matched_identifiers": list(row.get("matched_identifiers") or []),
            "unparsed_criterion_mentions": list(
                row.get("unparsed_criterion_mentions") or []
            ),
            "disease_match_status": disease_status,
            "inheritance_match_status": inheritance_status,
            "applicability_status": applicability_status,
            "source_fact_id": row.get("source_fact_id"),
            "external_assertion_only": True,
        }
        assertions.append(assertion)
        if applicability_status == "mismatch":
            continue
        for criterion_row in _criterion_rows(row):
            criterion = criterion_row["criterion"]
            strength = criterion_row["strength"]
            if not is_valid_strength_for_criterion(criterion, strength):
                continue
            source_id = str(row.get("source_fact_id") or "")
            cards.append(
                EvidenceCard(
                    criterion=criterion,
                    strength=strength,
                    evidence_status="expert_panel_applied",
                    source_label="ClinGen Evidence Repository VCEP",
                    observed_facts={
                        "assertion": assertion,
                        "applied_criterion": criterion_row,
                    },
                    rule_basis="Released VCEP variant curation",
                    strength_source="vcep_applied_criterion",
                    rule_source={
                        "type": "vcep_assertion",
                        "rule_id": str(row.get("Expert Panel") or "ClinGen VCEP"),
                        "version": str(
                            row.get("Version") or row.get("Release Date") or "released"
                        ),
                        "parser_version": VCEP_ASSERTION_PARSER_VERSION,
                    },
                    rule_id=str(row.get("Expert Panel") or "clingen-vcep"),
                    rule_version=str(
                        row.get("Version") or row.get("Release Date") or "released"
                    ),
                    rule_reference="ClinGen Evidence Repository",
                    scenario_id=scenario_id,
                    source_fact_ids=[source_id] if source_id else [],
                    source_pmids=[
                        str(value)
                        for value in criterion_row.get("pmids") or []
                        if value
                    ],
                    verification_dimensions={
                        "identity_status": "matched",
                        "source_status": "available",
                        "extraction_status": "structured",
                        "version_status": "versioned",
                        "disease_match_status": disease_status,
                        "inheritance_match_status": inheritance_status,
                        "independence_status": "independent",
                    },
                    provenance_chain=[
                        "Criterion and strength were applied by the named released VCEP; the five-tier label remains an external assertion."
                    ],
                )
            )
    return (
        {
            "status": "exact_assertion_found" if assertions else "not_found",
            "parser_version": VCEP_ASSERTION_PARSER_VERSION,
            "assertion_count": len(assertions),
            "history": history,
        },
        assertions,
        cards,
    )


__all__ = [
    "VCEP_ALLELE_MATCH_POLICY_VERSION",
    "VCEP_ALLELE_MATCH_TIERS",
    "VCEP_ASSERTION_PARSER_VERSION",
    "VCEP_MOI_ALIASES",
    "VCEP_MOI_POLICY_VERSION",
    "VCEP_NEGATIVE_APPLIED_STATUSES",
    "parse_vcep_assertions",
]
