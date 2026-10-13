"""Regression guard for Fix-C-20260918: stringified JSON arrays reaching
``ClinVar_search_variants`` as a single string.

Real JSON arrays (``["a", "b"]``) query correctly through the deployed MCP
entry, but some hosts serialize the array into ONE string before it reaches
the server. Treated as a single name, the quote-stripping downstream folded
it into a malformed term -- live example::

    variant_name = '["NM_001042492.3:c.6642+26C>G", "c.6642+26C>G"]'
    -> '"[NM_001042492.3:c.6642+26C>G, c.6642+26C>G]"[Variant name]'

which matches nothing. The fix compat-parses exactly that shape with stdlib
``json.loads`` at the name-query entry:

- a real array, a single string, and the stringified form of the same array
  produce equivalent queries;
- plain names and legal HGVS internal brackets keep their original meaning;
- only string elements are accepted; nested arrays, non-string items and
  malformed array strings raise explicit errors (never comma-split guesses);
- ``search_params`` discloses the received type and the names actually used,
  and a warning is attached when compat parsing occurred;
- a ``variant_name`` with no usable names at all is an error, not a
  silently-dropped filter.

All network access is mocked; no test reaches NCBI.
"""

import json
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import (
    ClinVarSearchVariants,
    _coerce_stringified_name_array,
)

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


_ESEARCH_OK = {
    "status": "success",
    "data": {
        "esearchresult": {
            "count": "1",
            "idlist": ["12345"],
            "querytranslation": "NF1[gene]",
        }
    },
}


def _run_with_mock(tool, arguments):
    """Run a search with the eSearch round-trip mocked; return (result, term)."""
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_ESEARCH_OK,
    ) as mock_request:
        result = tool.run(arguments)
    term = None
    for call in mock_request.call_args_list:
        params = call[0][1] if len(call[0]) > 1 else call[1]
        if isinstance(params, dict) and params.get("db") == "clinvar" and "term" in params:
            term = params["term"]
            break
    return result, term


def test_stringified_array_builds_same_query_as_real_array():
    names = ["NM_001042492.3:c.6642+26C>G", "c.6642+26C>G"]
    args = {"gene": "NF1", "max_results": 10}

    _, term_real = _run_with_mock(_tool(), {**args, "variant_name": names})
    result, term_str = _run_with_mock(
        _tool(), {**args, "variant_name": json.dumps(names)}
    )

    assert result["status"] == "success"
    assert term_str == term_real
    for name in names:
        assert f'"{name}"[Variant name]' in term_str
    assert " OR " in term_str
    # the malformed folded term from the old behavior is gone: no quoted
    # spelling may START with '[' (parse the quoted spellings; a bare
    # `"[` substring also appears in the legal `...name"[Variant name]`
    # field-tag suffix, so substring matching cannot tell them apart)
    import re as _re

    spellings = _re.findall(r'"([^"]*)"\[Variant name\]', term_str)
    assert spellings, "expected quoted [Variant name] terms"
    assert all(not s.startswith("[") for s in spellings)


def test_plain_single_string_untouched():
    result, term = _run_with_mock(
        _tool(), {"gene": "HBB", "variant_name": "Glu6Val"}
    )
    assert result["status"] == "success"
    assert '"Glu6Val"[Variant name]' in term


def test_hgvs_internal_brackets_preserved():
    name = "NM_004006.2:c.[2376G>A]"
    result, term = _run_with_mock(_tool(), {"gene": "TPP1", "variant_name": name})
    assert result["status"] == "success"
    assert f'"{name}"[Variant name]' in term


def test_hgvs_internal_brackets_inside_stringified_array():
    names = ["NM_004006.2(TPP1):c.[2376G>A]", "c.[2376G>A]"]
    result, term = _run_with_mock(
        _tool(), {"gene": "TPP1", "variant_name": json.dumps(names)}
    )
    assert result["status"] == "success"
    for name in names:
        assert f'"{name}"[Variant name]' in term


def test_empty_json_array_string_is_error():
    result, term = _run_with_mock(_tool(), {"gene": "NF1", "variant_name": "[]"})
    assert result["status"] == "error"
    assert "no usable names" in result["error"]


def test_empty_real_array_is_error():
    result, _ = _run_with_mock(_tool(), {"gene": "NF1", "variant_name": []})
    assert result["status"] == "error"
    assert "no usable names" in result["error"]


def test_blank_string_is_error():
    result, _ = _run_with_mock(_tool(), {"gene": "NF1", "variant_name": "   "})
    assert result["status"] == "error"
    assert "no usable names" in result["error"]


def test_mixed_type_stringified_array_is_error():
    payload = json.dumps(["NM_1:c.1A>G", 42])
    result, _ = _run_with_mock(
        _tool(), {"gene": "NF1", "variant_name": payload}
    )
    assert result["status"] == "error"
    assert "[1]=42" in result["error"]
    assert "only strings" in result["error"]


def test_nested_array_stringified_is_error():
    payload = json.dumps([["c.1A>G"]])
    result, _ = _run_with_mock(
        _tool(), {"gene": "NF1", "variant_name": payload}
    )
    assert result["status"] == "error"
    assert "only strings" in result["error"]


def test_malformed_array_string_is_error_not_comma_split():
    payload = '["c.6642+26C>G", "c.6642+26C>G"'  # missing closing bracket
    result, term = _run_with_mock(
        _tool(), {"gene": "NF1", "variant_name": payload}
    )
    # not bracket-wrapped on both ends -> treated as ONE (broken) plain name
    # is the old behavior; with only a leading bracket json parsing never
    # runs. The malformed-JSON error path needs BOTH brackets but invalid
    # content -- cover that separately below.
    assert result["status"] == "error"
    assert "no usable names" in result["error"] or "valid JSON" in result["error"]


def test_unquoted_bracket_list_is_error_not_comma_split():
    payload = "[c.6642+26C>G, c.6642+26C>G]"
    result, _ = _run_with_mock(
        _tool(), {"gene": "NF1", "variant_name": payload}
    )
    assert result["status"] == "error"
    assert "valid JSON" in result["error"]
    # the error must explain comma-splitting is not guessed
    assert "comma" in result["error"]


def test_search_params_discloses_compat_parse():
    names = ["NM_001042492.3:c.6642+26C>G", "c.6642+26C>G"]
    result, _ = _run_with_mock(
        _tool(),
        {"gene": "NF1", "max_results": 10, "variant_name": json.dumps(names)},
    )
    assert result["status"] == "success"
    params = result["data"]["search_params"]
    assert params["variant_name_received_type"] == "string"
    assert params["variant_names_used"] == names
    warnings = result["data"]["warnings"]
    assert any("stringified JSON array" in w for w in warnings)


def test_search_params_discloses_real_array_without_warning():
    names = ["Glu7Val", "Glu6Val"]
    result, _ = _run_with_mock(
        _tool(), {"gene": "HBB", "variant_name": names}
    )
    assert result["status"] == "success"
    params = result["data"]["search_params"]
    assert params["variant_name_received_type"] == "list"
    assert params["variant_names_used"] == names
    # F06 (2026-10-13): `warnings` may legitimately carry detail-fetch
    # notices (this mock has no esummary payload); what a REAL array must
    # never produce is the stringified-array warning.
    warnings = result["data"].get("warnings", [])
    assert not any("stringified JSON array" in w for w in warnings)


def test_variant_alias_gets_same_compat_parsing():
    names = ["c.6642+26C>G"]
    result, term = _run_with_mock(
        _tool(), {"gene": "NF1", "variant": json.dumps(names)}
    )
    assert result["status"] == "success"
    assert '"c.6642+26C>G"[Variant name]' in term


def test_rsid_inside_stringified_array_routes_to_bare_term():
    result, term = _run_with_mock(
        _tool(), {"gene": "CYP3A5", "variant_name": json.dumps(["rs776746"])}
    )
    assert result["status"] == "success"
    assert "rs776746" in term
    assert "[Variant name]" not in term


def test_coerce_helper_passthrough_cases():
    # plain strings (even with internal brackets) come back untouched
    assert _coerce_stringified_name_array("Glu6Val") == ("Glu6Val", None)
    assert _coerce_stringified_name_array("c.[2376G>A]") == ("c.[2376G>A]", None)
    # non-strings pass through for the existing list-wrapping path
    assert _coerce_stringified_name_array(5) == (5, None)


def test_coerce_helper_parses_and_labels():
    parsed, info = _coerce_stringified_name_array('["a", "b"]')
    assert parsed == ["a", "b"]
    assert info == {
        "received_type": "string",
        "parsed_from": "stringified_json_array",
    }


def test_coerce_helper_rejects_malformed_and_non_string():
    with pytest.raises(ValueError, match="valid JSON"):
        _coerce_stringified_name_array("[a, b]")
    with pytest.raises(ValueError, match="only strings"):
        _coerce_stringified_name_array(json.dumps([["a"]]))
    with pytest.raises(ValueError, match="only strings"):
        _coerce_stringified_name_array(json.dumps(["a", None]))
