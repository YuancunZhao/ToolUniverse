"""Tests for DECIPHER sequence-variant NMD escape tool."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


HTML = """<!doctype html><html><body>
<script>window.__NUXT__=(function(a,b,c,d){return {data:[{
genomicPosition:{assembly:"GRCh38",chr:"15",start:56464157,end:56464157,
ref_sequence:"T",alt_sequence:"A"},
genes:[{hgnc_description:"meiosis specific nuclear structural 1",
omim_morbid_diseases:[{disease_name:
"Heterotaxy, visceral, 9, autosomal, with male infertility"}]}],
transcripts:[{ensembl_transcript_name:"MNS1-201",refseq_accs:["NM_018365.4"]}]
}],routePath:"/sequence-variant/15-56464157-T-A"}}(null,false,true,"15"));
</script>
</body></html>"""


def _make_tool():
    from tooluniverse.decipher_tool import DECIPHERSequenceVariantNMDTool

    return DECIPHERSequenceVariantNMDTool(
        {
            "name": "DECIPHER_get_sequence_variant_nmd",
            "type": "DECIPHERSequenceVariantNMDTool",
        }
    )


def _resp(status_code=200, text=HTML):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


class TestDECIPHERSequenceVariantNMDTool(unittest.TestCase):
    def test_mns1_k32ter_overlaps_first_100bp_escape(self):
        tool = _make_tool()
        with patch.object(tool.session, "get", return_value=_resp()) as get:
            result = tool.run(
                {
                    "variant_id": "15-56464157-T-A",
                    "coding_hgvs": "NM_018365.4:c.94A>T",
                    "protein_position": 32,
                    "transcript_id": "NM_018365.4",
                }
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["variant_id"], "15-56464157-T-A")
        basic_context = result["data"]["basic_variant_context"]
        self.assertEqual(basic_context["refseq_transcripts"], ["NM_018365.4"])
        nmd = result["data"]["nmd_escape"]
        self.assertTrue(nmd["overlaps_nmd_escape"])
        self.assertEqual(nmd["matched_region"]["protein_end"], 34)
        self.assertIn("coding_hgvs", nmd["matched_by"])
        self.assertIn("protein_position", nmd["matched_by"])
        get.assert_called_once()

    def test_later_truncation_does_not_overlap_first_100bp_escape(self):
        tool = _make_tool()
        with patch.object(tool.session, "get", return_value=_resp()):
            result = tool.run(
                {"variant_id": "15-56464157-T-A", "coding_hgvs": "c.250A>T"}
            )

        self.assertEqual(result["status"], "success")
        nmd = result["data"]["nmd_escape"]
        self.assertFalse(nmd["overlaps_nmd_escape"])
        self.assertEqual(nmd["interpretation_status"], "not_detected")

    def test_missing_position_is_success_but_indeterminate(self):
        tool = _make_tool()
        with patch.object(tool.session, "get", return_value=_resp()):
            result = tool.run({"variant_id": "15-56464157-T-A"})

        self.assertEqual(result["status"], "success")
        nmd = result["data"]["nmd_escape"]
        self.assertIsNone(nmd["overlaps_nmd_escape"])
        self.assertEqual(nmd["interpretation_status"], "insufficient_position")

    def test_invalid_variant_id_returns_error(self):
        result = _make_tool().run({"variant_id": "NM_018365.4:c.94A>T"})
        self.assertEqual(result["status"], "error")
        self.assertIn("chr-pos-ref-alt", result["error"])

    def test_404_returns_structured_error(self):
        tool = _make_tool()
        with patch.object(
            tool.session,
            "get",
            return_value=_resp(status_code=404, text="not found"),
        ):
            result = tool.run(
                {"variant_id": "15-56464157-T-A", "protein_position": 32}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])

    def test_unexpected_page_returns_structured_error(self):
        tool = _make_tool()
        with patch.object(
            tool.session,
            "get",
            return_value=_resp(text="<html>home</html>"),
        ):
            result = tool.run(
                {"variant_id": "15-56464157-T-A", "protein_position": 32}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("expected sequence-variant", result["error"])


if __name__ == "__main__":
    unittest.main()
