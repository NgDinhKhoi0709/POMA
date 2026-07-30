import json
import multiprocessing

import pytest

from src.finalization.artifacts import (
    ArtifactError,
    ArtifactRecordError,
    IncrementalArtifactStore,
    ManifestMismatchError,
    RunManifest,
    canonical_sha256,
    failure_record,
    sha256_file,
    success_record,
)


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def _manifest(tmp_path, **overrides):
    source_path = overrides.pop("source_path", None)
    if source_path is None:
        source_path = _write(tmp_path / "source.json", '{"predictions": []}\n')
    qas_path = overrides.pop("qas_path", None)
    if qas_path is None:
        qas_path = _write(tmp_path / "qas.json", '{"qas": []}\n')
    tables_path = overrides.pop("tables_path", None)
    if tables_path is None:
        tables_path = _write(tmp_path / "tables.json", '{"table": []}\n')
    values = {
        "source_path": source_path,
        "qas_path": qas_path,
        "tables_path": tables_path,
        "git_commit": "abc123",
        "source_kind": "poma-specialists",
        "model": "qwen3-8b",
        "provider": "openai-compatible",
        "mode": "structured",
        "prompt_version": "gsa.v1",
        "schema_version": "grounded_answer.v1",
        "finalizer": "gsa",
        "generation_settings": {
            "temperature": 0,
            "max_tokens": 256,
            "provider_order": ["local"],
        },
        "started_at": "2026-07-30T00:00:00Z",
    }
    values.update(overrides)
    return RunManifest.create(**values)


def _append_in_process(path, manifest_dict, prefix, count):
    manifest = RunManifest.from_dict(manifest_dict)
    store = IncrementalArtifactStore(path, manifest)
    for index in range(count):
        store.append(
            success_record(
                qa_id=f"{prefix}-{index}",
                table_id="table",
                prediction=["answer"],
                finalizer="gsa",
            )
        )


def test_sha256_and_configuration_fingerprints_are_canonical_and_stable(tmp_path):
    """Catch input ordering or ambient metadata changing reproducibility hashes."""
    source_path = tmp_path / "source.json"
    source_path.write_bytes(b"same bytes\n")
    first = _manifest(
        tmp_path,
        source_path=source_path,
        generation_settings={"temperature": 0, "max_tokens": 256},
    )
    second = _manifest(
        tmp_path,
        source_path=source_path,
        generation_settings={"max_tokens": 256, "temperature": 0},
    )

    assert sha256_file(source_path) == (
        "abb7f0ae43ba52cc56233a5ecb4dfa11765f26b1282a18346d811b6a85af19c1"
    )
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256(
        {"a": 1, "b": 2}
    )
    assert first.configuration_fingerprint == second.configuration_fingerprint
    assert first.to_dict()["cost_usd"] is None
    assert first.to_dict()["completed_at"] is None
    assert first.to_dict()["counts"] == {
        "dataset": 0,
        "successful": 0,
        "failed": 0,
        "attempts": 0,
    }
    assert first.to_dict()["tokens"] == {
        "prompt": 0,
        "completion": 0,
        "total": 0,
    }


def test_manifest_deep_detaches_and_exposes_immutable_generation_settings(
    tmp_path,
):
    """Catch caller or exported nested mutation invalidating a frozen identity."""
    caller_settings = {
        "temperature": 0,
        "provider": {
            "only": ["local", "fallback"],
            "routing": {"allow_fallbacks": False},
        },
    }
    manifest = _manifest(
        tmp_path,
        generation_settings=caller_settings,
    )
    original_fingerprint = manifest.configuration_fingerprint
    original_serialized = manifest.to_dict()

    caller_settings["temperature"] = 1
    caller_settings["provider"]["only"].append("mutated")
    caller_settings["provider"]["routing"]["allow_fallbacks"] = True

    with pytest.raises(TypeError):
        manifest.generation_settings["temperature"] = 1
    with pytest.raises(TypeError):
        manifest.generation_settings["provider"]["only"][0] = "mutated"
    with pytest.raises(TypeError):
        manifest.generation_settings["provider"]["routing"][
            "allow_fallbacks"
        ] = True

    exported = manifest.to_dict()
    exported["generation_settings"]["provider"]["only"].append("export-only")

    assert manifest.configuration_fingerprint == original_fingerprint
    assert manifest.to_dict() == original_serialized
    assert json.loads(json.dumps(manifest.to_dict())) == original_serialized


@pytest.mark.parametrize("tampered_field", ["model", "generation_settings"])
def test_resume_rejects_header_with_tampered_serialized_configuration(
    tmp_path,
    tampered_field,
):
    """Catch a stale stored fingerprint blessing modified configuration."""
    manifest = _manifest(
        tmp_path,
        generation_settings={
            "temperature": 0,
            "provider": {"only": ["local"]},
        },
    )
    jsonl_path = tmp_path / "run.jsonl"
    IncrementalArtifactStore(jsonl_path, manifest)
    header = json.loads(jsonl_path.read_text(encoding="utf-8"))
    if tampered_field == "model":
        header["manifest"]["model"] = "tampered-model"
    else:
        header["manifest"]["generation_settings"]["provider"]["only"].append(
            "tampered-provider"
        )
    jsonl_path.write_text(
        json.dumps(header, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ArtifactError, match="fingerprint"):
        IncrementalArtifactStore(jsonl_path, manifest)


def test_resume_skips_success_and_retries_failure_only_when_explicit(tmp_path):
    """Catch successful reruns or implicit retry of failed dataset items."""
    manifest = _manifest(tmp_path)
    jsonl_path = tmp_path / "run.jsonl"
    store = IncrementalArtifactStore(jsonl_path, manifest)
    store.append(
        success_record(
            qa_id="q1",
            table_id="t1",
            prediction=["Hà Nội"],
            finalizer="gsa",
        )
    )
    store.append(
        failure_record(
            qa_id="q2",
            table_id="t2",
            error_type="ProviderTimeout",
            message="timed out",
        )
    )

    assert store.pending_qa_ids(["q1", "q2", "q3"]) == ["q3"]
    assert store.pending_qa_ids(
        ["q1", "q2", "q3"],
        retry_failed=True,
    ) == ["q2", "q3"]


def test_matching_resume_is_append_only_and_never_truncates(tmp_path):
    """Catch reopening a matching run destroying already completed records."""
    manifest = _manifest(tmp_path)
    jsonl_path = tmp_path / "run.jsonl"
    first_store = IncrementalArtifactStore(jsonl_path, manifest)
    first_store.append(
        success_record(
            qa_id="q1",
            table_id="t1",
            prediction=["Hà Nội"],
            finalizer="gsa",
        )
    )
    before = jsonl_path.read_bytes()

    resumed_store = IncrementalArtifactStore(jsonl_path, manifest)
    resumed_store.append(
        success_record(
            qa_id="q2",
            table_id="t2",
            prediction=["Huế"],
            finalizer="gsa",
        )
    )

    after = jsonl_path.read_bytes()
    assert after.startswith(before)
    assert resumed_store.pending_qa_ids(["q1", "q2"]) == []


@pytest.mark.parametrize("mismatch", ["source", "dataset", "config"])
def test_resume_rejects_source_dataset_or_configuration_mismatch(
    tmp_path,
    mismatch,
):
    """Catch incompatible runs being silently mixed in one JSONL artifact."""
    jsonl_path = tmp_path / "run.jsonl"
    original = _manifest(tmp_path)
    IncrementalArtifactStore(jsonl_path, original)
    if mismatch == "source":
        replacement = _manifest(
            tmp_path,
            source_path=_write(tmp_path / "other-source.json", "{}\n"),
        )
    elif mismatch == "dataset":
        replacement = _manifest(
            tmp_path,
            qas_path=_write(tmp_path / "other-qas.json", "[]\n"),
        )
    else:
        replacement = _manifest(tmp_path, model="different-model")

    with pytest.raises(ManifestMismatchError):
        IncrementalArtifactStore(jsonl_path, replacement)


def test_materialization_sorts_by_dataset_and_retains_typed_failures(tmp_path):
    """Catch completion-order output or failure removal changing the denominator."""
    manifest = _manifest(tmp_path)
    store = IncrementalArtifactStore(tmp_path / "run.jsonl", manifest)
    store.append(
        failure_record(
            qa_id="q2",
            table_id="t2",
            error_type="SchemaValidationError",
            message="invalid output",
            usage={
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
                "cost_usd": None,
            },
        )
    )
    store.append(
        success_record(
            qa_id="q1",
            table_id="t1",
            prediction=["Hà Nội"],
            finalizer="gsa",
            trace={"decision": "selected"},
            usage={
                "prompt_tokens": 7,
                "completion_tokens": 1,
                "total_tokens": 8,
                "cost_usd": 0.01,
            },
        )
    )

    payload = store.materialize(
        tmp_path / "run.json",
        dataset_order=["q1", "q2"],
        completed_at="2026-07-30T00:01:00Z",
    )

    assert payload["predictions"] == [
        {
            "qa_id": "q1",
            "table_id": "t1",
            "prediction": ["Hà Nội"],
            "finalizer": "gsa",
            "trace": {"decision": "selected"},
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 1,
                "total_tokens": 8,
                "cost_usd": 0.01,
            },
        },
        {
            "qa_id": "q2",
            "table_id": "t2",
            "error": {
                "type": "SchemaValidationError",
                "message": "invalid output",
            },
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
                "cost_usd": None,
            },
        },
    ]
    assert payload["manifest"]["counts"] == {
        "dataset": 2,
        "successful": 1,
        "failed": 1,
        "attempts": 2,
    }
    assert payload["manifest"]["tokens"] == {
        "prompt": 10,
        "completion": 3,
        "total": 13,
    }
    assert payload["manifest"]["cost_usd"] is None
    assert payload["manifest"]["completed_at"] == "2026-07-30T00:01:00Z"
    assert json.loads((tmp_path / "run.json").read_text(encoding="utf-8")) == payload


def test_success_after_explicit_retry_replaces_failure_in_materialization(tmp_path):
    """Catch a recovered QA remaining failed or appearing twice officially."""
    manifest = _manifest(tmp_path)
    store = IncrementalArtifactStore(tmp_path / "run.jsonl", manifest)
    store.append(
        failure_record(
            qa_id="q1",
            table_id="t1",
            error_type="ProviderTimeout",
            message="first attempt",
        )
    )
    store.append(
        success_record(
            qa_id="q1",
            table_id="t1",
            prediction=["Hà Nội"],
            finalizer="gsa",
        )
    )

    payload = store.materialize(
        tmp_path / "run.json",
        dataset_order=["q1"],
    )

    assert len(payload["predictions"]) == 1
    assert payload["predictions"][0]["prediction"] == ["Hà Nội"]
    assert payload["manifest"]["counts"] == {
        "dataset": 1,
        "successful": 1,
        "failed": 0,
        "attempts": 2,
    }


def test_materialization_rejects_missing_dataset_results(tmp_path):
    """Catch an incomplete run silently shrinking the official denominator."""
    store = IncrementalArtifactStore(
        tmp_path / "run.jsonl",
        _manifest(tmp_path),
    )
    store.append(
        success_record(
            qa_id="q1",
            table_id="t1",
            prediction=["Hà Nội"],
            finalizer="gsa",
        )
    )

    with pytest.raises(ArtifactRecordError, match="no result"):
        store.materialize(
            tmp_path / "run.json",
            dataset_order=["q1", "q2"],
        )


def test_artifact_records_require_prediction_or_typed_error(tmp_path):
    """Catch malformed failure strings or missing outcomes entering the log."""
    store = IncrementalArtifactStore(tmp_path / "run.jsonl", _manifest(tmp_path))

    with pytest.raises(ArtifactRecordError):
        store.append({"qa_id": "q1", "table_id": "t1", "error": "boom"})
    with pytest.raises(ArtifactRecordError):
        store.append({"qa_id": "q1", "table_id": "t1"})


def test_processes_append_complete_json_lines_under_cross_platform_lock(tmp_path):
    """Catch interleaved writes corrupting concurrent incremental records."""
    manifest = _manifest(tmp_path)
    jsonl_path = tmp_path / "run.jsonl"
    IncrementalArtifactStore(jsonl_path, manifest)
    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_append_in_process,
            args=(jsonl_path, manifest.to_dict(), prefix, 8),
        )
        for prefix in ("a", "b")
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)

    assert [process.exitcode for process in processes] == [0, 0]
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    objects = [json.loads(line) for line in lines]
    assert len(objects) == 17
    assert objects[0]["record_type"] == "manifest"
    assert {item["qa_id"] for item in objects[1:]} == {
        *(f"a-{index}" for index in range(8)),
        *(f"b-{index}" for index in range(8)),
    }
