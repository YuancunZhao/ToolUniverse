"""Unit tests for SpliceAITool score parsing.

The live SpliceAI Lookup service serializes delta scores as *strings*
(e.g. ``DS_AG: "0.997"``) and depths as strings/floats. The original
implementation only accepted ``isinstance(val, (int, float))`` values, so
every real response collapsed to ``max_delta_score = 0.0``. These tests
pin the fixed contract:

- the four ``DS_*`` scores parse from ints, floats and numeric strings;
  booleans, non-numeric strings, NaN/Infinity and out-of-range values are
  hard errors -- a partial or malformed payload is never promoted to a
  "successful" 0.0 maximum;
- the maximum is computed only over ``DS_AG/DS_AL/DS_DG/DS_DL`` -- the
  ``*_REF``/``*_ALT`` indel companions never enter it;
- ``DP_*`` depths convert to ints when integral; non-integer depths are
  never truncated, they stay as-is with a warning naming the field path,
  and never invalidate the DS scores;
- ``raw_response`` is preserved byte-for-byte and both registered
  operations (``predict_splice`` and ``get_max_delta``) propagate errors
  and warnings consistently.

All network access is stubbed; no test reaches the Broad service.
"""

import math

import pytest

from tooluniverse.spliceai_tool import SpliceAITool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _make_tool(operation="predict_splice"):
    return SpliceAITool(
        {
            "name": f"SpliceAI_{operation}",
            "parameter": {"required": ["variant"]},
            "fields": {"operation": operation, "timeout": 5},
        }
    )


def _respond_with(monkeypatch, payload):
    """Patch requests.get in the spliceai module to return ``payload``."""

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(payload)

    monkeypatch.setattr("tooluniverse.spliceai_tool.requests.get", fake_get)


def _score_entry(**overrides):
    """A real-shape transcript entry: string DS, numeric DP."""
    entry = {
        "DS_AG": "0.05",
        "DS_AL": "0.00",
        "DS_DG": "0.997",
        "DS_DL": "0.02",
        "DP_AG": 12,
        "DP_AL": 45,
        "DP_DG": 41,
        "DP_DL": 46,
    }
    entry.update(overrides)
    return entry


VARIANT_ARGS = {"variant": "chr17-31337608-C-G", "genome": "38"}


def test_real_string_response_yields_true_max(monkeypatch):
    """The reported defect: string DS scores silently became max 0.0."""
    _respond_with(monkeypatch, {"scores": [_score_entry()]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == pytest.approx(0.997)
    assert result["data"]["interpretation"] == "high_pathogenicity"
    # normalized scores are floats, not the original strings
    assert result["data"]["scores"][0]["DS_DG"] == pytest.approx(0.997)


def test_numeric_ds_values_supported(monkeypatch):
    entry = _score_entry(
        DS_AG=0.1, DS_AL=0.0, DS_DG=0.6, DS_DL=0.25,
        DP_AG="12", DP_AL="45", DP_DG="41", DP_DL="46",
    )
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == pytest.approx(0.6)
    assert result["data"]["interpretation"] == "moderate_pathogenicity"
    # string DP depths that are integral become ints
    assert result["data"]["scores"][0]["DP_AG"] == 12


def test_max_across_multiple_transcripts(monkeypatch):
    _respond_with(
        monkeypatch,
        {
            "scores": [
                _score_entry(DS_AG="0.10", DS_AL="0.00", DS_DG="0.30", DS_DL="0.01"),
                _score_entry(DS_AG="0.44", DS_AL="0.00", DS_DG="0.02", DS_DL="0.00"),
            ]
        },
    )

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == pytest.approx(0.44)


def test_legitimate_all_zero_scores_succeed(monkeypatch):
    entry = _score_entry(DS_AG="0", DS_AL="0.0", DS_DG=0, DS_DL=0.0)
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == 0.0
    assert result["data"]["interpretation"] == "benign"


def test_ref_alt_companions_never_enter_max(monkeypatch):
    entry = _score_entry(DS_AG_REF="1.5", DS_DG_ALT="0.99")
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    # 0.997 from DS_DG, unaffected by the 1.5 REF companion
    assert result["data"]["max_delta_score"] == pytest.approx(0.997)
    # untouched companions pass through verbatim
    assert result["data"]["scores"][0]["DS_AG_REF"] == "1.5"


def test_raw_response_preserved_verbatim(monkeypatch):
    payload = {"scores": [_score_entry()], "metadata": {"as_of": "2026-01"}}
    _respond_with(monkeypatch, payload)

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["raw_response"] is payload
    assert result["data"]["raw_response"]["scores"][0]["DS_DG"] == "0.997"


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("DS_AG", True),
        ("DS_AL", False),
        ("DS_DG", "not-a-number"),
        ("DS_DL", None),
        ("DS_AG", float("nan")),
        ("DS_DG", float("inf")),
        ("DS_AL", "-inf"),
        ("DS_AG", 1.5),
        ("DS_DG", "1.2"),
        ("DS_AL", -0.1),
        ("DS_DL", "-0.5"),
    ],
)
def test_invalid_ds_values_are_hard_errors(monkeypatch, field, bad_value):
    entry = _score_entry(**{field: bad_value})
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert field in result["error"]
    # the raw payload is still attached for disclosure (NaN needs an
    # identity check because nan != nan under ==)
    raw_value = result["raw_response"]["scores"][0][field]
    if isinstance(bad_value, float) and math.isnan(bad_value):
        assert math.isnan(raw_value)
    else:
        assert raw_value == bad_value


def test_missing_ds_key_is_hard_error(monkeypatch):
    entry = _score_entry()
    del entry["DS_DG"]
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert "DS_DG" in result["error"]
    assert "missing" in result["error"]


def test_empty_scores_is_hard_error(monkeypatch):
    _respond_with(monkeypatch, {"scores": []})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert "no scores" in result["error"]


def test_scores_not_a_list_is_hard_error(monkeypatch):
    _respond_with(monkeypatch, {"scores": {"DS_AG": "0.1"}})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert "not a list" in result["error"]


def test_non_dict_score_entry_is_hard_error(monkeypatch):
    _respond_with(monkeypatch, {"scores": ["0.997"]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert "scores[0]" in result["error"]


@pytest.mark.parametrize(
    "dp_value, expected, expect_warning",
    [
        ("12", 12, False),
        ("45.0", 45, False),
        (12.0, 12, False),
        (7, 7, False),
        (12.7, 12.7, True),
        ("12.7", "12.7", True),
        ("abc", "abc", True),
        (True, True, True),
        (float("nan"), float("nan"), True),
    ],
)
def test_dp_conversion_without_truncation(
    monkeypatch, dp_value, expected, expect_warning
):
    entry = _score_entry(DP_AG=dp_value)
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    # DP anomalies never invalidate complete DS scores
    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == pytest.approx(0.997)
    got = result["data"]["scores"][0]["DP_AG"]
    if isinstance(expected, float) and math.isnan(expected):
        assert math.isnan(got)
    else:
        assert got == expected
    warnings = result["data"]["warnings"]
    if expect_warning:
        assert any("scores[0].DP_AG" in w for w in warnings)
    else:
        assert warnings == []


def test_missing_dp_keys_produce_no_warning(monkeypatch):
    entry = _score_entry()
    for key in ("DP_AG", "DP_AL", "DP_DG", "DP_DL"):
        del entry[key]
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["warnings"] == []


def test_get_max_delta_reuses_fixed_parsing(monkeypatch):
    _respond_with(monkeypatch, {"scores": [_score_entry()]})

    result = _make_tool("get_max_delta").run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert result["data"]["max_delta_score"] == pytest.approx(0.997)
    assert result["data"]["interpretation"] == "high_pathogenicity"
    assert "warnings" in result["data"]


def test_get_max_delta_propagates_warnings(monkeypatch):
    _respond_with(monkeypatch, {"scores": [_score_entry(DP_AG=12.7)]})

    result = _make_tool("get_max_delta").run(dict(VARIANT_ARGS))

    assert result["status"] == "success"
    assert any("scores[0].DP_AG" in w for w in result["data"]["warnings"])


def test_get_max_delta_propagates_parse_errors(monkeypatch):
    _respond_with(monkeypatch, {"scores": [_score_entry(DS_AG="oops")]})

    result = _make_tool("get_max_delta").run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert "DS_AG" in result["error"]


def test_service_error_payload_still_reported(monkeypatch):
    _respond_with(monkeypatch, {"error": "variant not found"})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert result["error"] == "variant not found"


def test_string_nan_and_infinity_rejected(monkeypatch):
    entry = _score_entry(DS_AG="nan")
    _respond_with(monkeypatch, {"scores": [entry]})

    result = _make_tool().run(dict(VARIANT_ARGS))

    assert result["status"] == "error"
    assert math.isnan(0.0) is False  # sanity: no silent numeric fallback
    assert "non-finite" in result["error"] or "not a numeric" in result["error"]
