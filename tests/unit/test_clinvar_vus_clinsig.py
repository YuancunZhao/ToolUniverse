"""Unit test: ClinVar_search_variants maps 'Uncertain significance' to clinsig_vus.

Regression: filtering clinical_significance="Uncertain significance" -- the single
LARGEST ClinVar category -- returned total_count 0. NCBI indexes VUS under the
token clinsig_vus[prop], NOT the naive clinsig_uncertain_significance[prop] the
tool built, so it was a silent false-empty. The tool now ORs in the correct
token via a clinsig-alias map.
"""
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _term_for(arguments):
    tool = ClinVarSearchVariants({"name": "ClinVar_search_variants"})
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {"esearchresult": {"count": "1", "idlist": ["16870"], "querytranslation": "x[All Fields]"}}},
    ) as mock_request:
        tool.run(arguments)
    return next(c[0][1]["term"] for c in mock_request.call_args_list if "term" in c[0][1])


def test_uncertain_significance_includes_vus_token():
    term = _term_for(
        {"gene": "BRCA2", "clinical_significance": "Uncertain significance"}
    )
    assert "clinsig_vus[prop]" in term
    # the original forms are still present (union, never drops matches)
    assert 'clinsig uncertain significance"[Filter]' in term


def test_underscore_and_casing_variants_also_get_vus():
    for val in ("Uncertain_significance", "uncertain significance", "UNCERTAIN SIGNIFICANCE"):
        term = _term_for({"gene": "BRCA2", "clinical_significance": val})
        assert "clinsig_vus[prop]" in term, val


def test_non_aliased_value_unchanged():
    term = _term_for({"gene": "BRCA2", "clinical_significance": "Pathogenic"})
    assert "clinsig_vus" not in term
    assert '("clinsig pathogenic"[Filter] OR clinsig_pathogenic[prop])' in term
