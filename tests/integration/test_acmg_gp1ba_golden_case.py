"""Offline GP1BA regression for MONDO, transcript, and PM2 rule routing."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.guard import validate_guard_context


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "acmg" / "gp1ba_q587h.json"
)


class GP1BAProviderFixture:
    def __init__(self):
        self.responses = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.calls: list[dict[str, Any]] = []

    def run_one_function(self, call: dict[str, Any], **_kwargs: Any) -> Any:
        self.calls.append(deepcopy(call))
        name = str(call.get("name") or "")
        if name in self.responses:
            return deepcopy(self.responses[name])
        return {"status": "unavailable", "reason": "GP1BA fixture has no result"}

    def run_many_functions(
        self, calls: list[dict[str, Any]], **kwargs: Any
    ) -> list[Any]:
        return [self.run_one_function(call, **kwargs) for call in calls]


def test_gp1ba_name_resolves_gn079_and_alternate_transcript_does_not_block(
    check_acmg_summary,
):
    fixture = GP1BAProviderFixture()
    result = ACMGEvidencePipeline(fixture).run(
        {
            "variant": "GP1BA;NM_000173.7:c.1761A>C(p.Gln587His)",
            "gene": "GP1BA",
            "transcript": "NM_000173.7",
            "disease": "Bernard-Soulier syndrome",
            "inheritance": "autosomal recessive",
            "genome_build": "GRCh38",
            "response_detail": "full",
        }
    )

    normalization = result["variant"]["normalization"]
    assert normalization["identity_verification_basis"] == "cross_provider_agreement"
    assert normalization["provider_query_variant"] == "GP1BA;NM_000173.7:c.1761A>C"
    assert normalization["submitted_hgvs_p"] == "p.Gln587His"
    assert normalization["protein_identity_status"] == "matched"

    consequence = result["consequence_profile"]
    assert consequence["annotation_status"] == "resolved"
    assert consequence["hgvs_p"].endswith("p.Gln587His")
    assert consequence["hard_identity_conflicts"] == []
    assert any(
        row.get("hgvs_p", "").endswith("p.Gln561His")
        for row in consequence["alternate_transcript_observations"]
    )

    context = result["rule_context"]
    assert context["cspec_status"] == "dynamic_structured_applied"
    assert context["applicable_specification"]["specification_id"] == "GN079"
    assert context["unmatched_reasons"] == []
    assert context["disease_context"]["mondo_id"] == "MONDO:0009276"

    pm2 = next(card for card in result["evidence_cards"] if card["criterion"] == "PM2")
    assert pm2["strength"] == "not_met"
    assert pm2["rule_evaluation"]["threshold"] == 0.0001114
    assert pm2["rule_evaluation"]["status"] == "condition_not_met"
    assert "coverage" not in pm2["rule_evaluation"]["primary_reason"].casefold()

    pvs1_review = next(
        row for row in result["criterion_reviews"] if row["criterion"] == "PVS1"
    )
    assert pvs1_review["route_status"] == "not_applicable"
    assert validate_guard_context(result["guard_context"]) == (True, "")
    assert result["final_classification_allowed"] is False
    summary = ACMGEvidencePipeline(GP1BAProviderFixture()).run(
        {
            "variant": "GP1BA;NM_000173.7:c.1761A>C(p.Gln587His)",
            "gene": "GP1BA",
            "transcript": "NM_000173.7",
            "disease": "Bernard-Soulier syndrome",
            "inheritance": "autosomal recessive",
            "genome_build": "GRCh38",
            "response_detail": "summary",
        }
    )
    check_acmg_summary(summary)
    guard = json.dumps(
        summary["guard_context"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert len(guard) < 5_000


def test_gp1ba_direct_mondo_matches_disease_name_scenario():
    fixture = GP1BAProviderFixture()
    common = {
        "variant": "NM_000173.7:c.1761A>C",
        "gene": "GP1BA",
        "transcript": "NM_000173.7",
        "inheritance": "autosomal recessive",
        "response_detail": "full",
    }
    named = ACMGEvidencePipeline(fixture).run(
        {**common, "disease": "Bernard-Soulier syndrome"}
    )
    direct = ACMGEvidencePipeline(fixture).run({**common, "disease": "MONDO:0009276"})

    assert (
        named["rule_context"]["applicable_specification"]["specification_id"]
        == (direct["rule_context"]["applicable_specification"]["specification_id"])
    )
    assert (
        named["rule_context"]["executable_contract"]["content_hash"]
        == (direct["rule_context"]["executable_contract"]["content_hash"])
    )
