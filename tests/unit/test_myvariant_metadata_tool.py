from tooluniverse.mygene_tool import MyVariantTool


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "build_version": "20250624",
            "build_date": "2025-06-24",
            "src": {
                "dbnsfp": {
                    "version": "4.8a",
                    "download_date": "2025-01-17",
                    "upload_date": {"dbnsfp_hg19_v1": "2025-02-19"},
                    "url": "https://sites.google.com/site/jpopgen/dbNSFP",
                }
            },
        }


def test_myvariant_metadata_returns_dbnsfp_version(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.mygene_tool.requests.get", lambda *_args, **_kwargs: _Response()
    )
    tool = MyVariantTool(
        {"name": "MyVariant_get_metadata", "fields": {"operation": "get_metadata"}}
    )

    result = tool.run({"source": "dbnsfp"})

    assert result["status"] == "success"
    assert result["version"] == "4.8a"
    assert result["build_version"] == "20250624"
