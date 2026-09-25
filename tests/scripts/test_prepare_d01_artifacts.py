"""D01 conversions must keep original answers and trace their sources."""

import hashlib
import json

import pytest

from scripts.prepare_d01_artifacts import adapt_baseline, materialize_single


def _write(path, records):
    path.write_text(json.dumps({"predictions": records}), encoding="utf-8")
    return path


def test_legacy_adapter_preserves_one_answer_and_source_hash(tmp_path):
    source = _write(
        tmp_path / "legacy.json",
        [{"qa_id": "a", "table_id": "t", "predicted_answer": [" x "], "parse_ok": False}],
    )
    payload = adapt_baseline(source, tmp_path / "adapted.json")

    assert payload["predictions"] == [
        {"qa_id": "a", "table_id": "t", "prediction": ["x"]}
    ]
    assert payload["manifest"]["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert payload["manifest"]["source_parse_failures"] == 1


def test_single_answer_uses_logged_first_answer_only_on_finalizer_failure(tmp_path):
    source = _write(
        tmp_path / "gsa.json",
        [
            {"qa_id": "a", "prediction": ["selected"]},
            {"qa_id": "b", "error": {"type": "LLMContractError"}},
        ],
    )
    raw = _write(
        tmp_path / "raw.json",
        [
            {"qa_id": "a", "prediction": ["first-a", "second-a"]},
            {"qa_id": "b", "prediction": ["first-b", "second-b"]},
        ],
    )
    payload = materialize_single(source, tmp_path / "single.json", fallback_source=raw)

    assert [row["prediction"] for row in payload["predictions"]] == [
        ["selected"], ["first-b"]
    ]
    assert payload["manifest"]["fallback_qa_ids"] == ["b"]


def test_single_answer_rejects_mismatched_fallback_ids(tmp_path):
    source = _write(tmp_path / "gsa.json", [{"qa_id": "a", "error": {}}])
    raw = _write(tmp_path / "raw.json", [{"qa_id": "b", "prediction": ["x"]}])
    with pytest.raises(ValueError, match="different QA IDs"):
        materialize_single(source, tmp_path / "single.json", fallback_source=raw)


def test_single_answer_rejects_missing_qa_id(tmp_path):
    source = _write(tmp_path / "raw.json", [{"prediction": ["x"]}])
    with pytest.raises(ValueError, match="missing or duplicate qa_id"):
        materialize_single(source, tmp_path / "single.json")
