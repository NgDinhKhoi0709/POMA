"""D01 provenance checks must reject an altered upstream artifact."""

import json

import pytest

from scripts.audit_d01 import _source_manifest


def test_source_manifest_rejects_changed_upstream_file(tmp_path):
    source = tmp_path / "source.json"
    source.write_text('{"predictions":[]}', encoding="utf-8")
    derived = tmp_path / "derived.json"
    derived.write_text(
        json.dumps({
            "manifest": {
                "source": str(source),
                "source_sha256": "0" * 64,
            },
            "predictions": [],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Broken source lineage"):
        _source_manifest(derived)
