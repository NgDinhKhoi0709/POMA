"""Reproducible manifests and append-only finalization artifacts."""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


class ArtifactError(RuntimeError):
    """Base error for an invalid or incompatible artifact."""


class ManifestMismatchError(ArtifactError):
    """An existing JSONL file belongs to a different run."""


class ArtifactRecordError(ArtifactError):
    """An incremental record violates the result contract."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactError(f"Value is not canonical JSON: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    """Hash a value using UTF-8 canonical sorted JSON."""
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file's exact bytes."""
    digest = sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ArtifactError(f"Cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _empty_counts() -> dict[str, int]:
    return {"dataset": 0, "successful": 0, "failed": 0, "attempts": 0}


def _empty_tokens() -> dict[str, int]:
    return {"prompt": 0, "completion": 0, "total": 0}


@dataclass(frozen=True)
class RunManifest:
    """Identity, configuration, and aggregate telemetry for one run."""

    source_kind: str
    source_sha256: str
    qas_sha256: str
    tables_sha256: str
    dataset_sha256: str
    git_commit: str
    model: str
    provider: str
    mode: str
    prompt_version: str
    schema_version: str
    finalizer: str
    generation_settings: dict[str, Any]
    configuration_fingerprint: str
    started_at: str
    completed_at: str | None = None
    counts: dict[str, int] = field(default_factory=_empty_counts)
    tokens: dict[str, int] = field(default_factory=_empty_tokens)
    cost_usd: float | None = None
    manifest_version: str = "finalization-run.v1"

    @classmethod
    def create(
        cls,
        *,
        source_path: Path,
        qas_path: Path,
        tables_path: Path,
        git_commit: str,
        source_kind: str,
        model: str,
        provider: str,
        mode: str,
        prompt_version: str,
        schema_version: str,
        finalizer: str,
        generation_settings: Mapping[str, Any],
        started_at: str,
    ) -> "RunManifest":
        """Build a manifest and its single canonical configuration identity."""
        source_hash = sha256_file(source_path)
        qas_hash = sha256_file(qas_path)
        tables_hash = sha256_file(tables_path)
        settings = dict(generation_settings)
        configuration = {
            "finalizer": finalizer,
            "generation_settings": settings,
            "git_commit": git_commit,
            "mode": mode,
            "model": model,
            "prompt_version": prompt_version,
            "provider": provider,
            "schema_version": schema_version,
            "source_kind": source_kind,
        }
        return cls(
            source_kind=source_kind,
            source_sha256=source_hash,
            qas_sha256=qas_hash,
            tables_sha256=tables_hash,
            dataset_sha256=canonical_sha256(
                {"qas_sha256": qas_hash, "tables_sha256": tables_hash}
            ),
            git_commit=git_commit,
            model=model,
            provider=provider,
            mode=mode,
            prompt_version=prompt_version,
            schema_version=schema_version,
            finalizer=finalizer,
            generation_settings=settings,
            configuration_fingerprint=canonical_sha256(configuration),
            started_at=started_at,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunManifest":
        """Rehydrate a serialized manifest, ignoring no required fields."""
        try:
            return cls(
                source_kind=value["source_kind"],
                source_sha256=value["source_sha256"],
                qas_sha256=value["qas_sha256"],
                tables_sha256=value["tables_sha256"],
                dataset_sha256=value["dataset_sha256"],
                git_commit=value["git_commit"],
                model=value["model"],
                provider=value["provider"],
                mode=value["mode"],
                prompt_version=value["prompt_version"],
                schema_version=value["schema_version"],
                finalizer=value["finalizer"],
                generation_settings=dict(value["generation_settings"]),
                configuration_fingerprint=value["configuration_fingerprint"],
                started_at=value["started_at"],
                completed_at=value.get("completed_at"),
                counts=dict(value.get("counts", _empty_counts())),
                tokens=dict(value.get("tokens", _empty_tokens())),
                cost_usd=value.get("cost_usd"),
                manifest_version=value.get(
                    "manifest_version",
                    "finalization-run.v1",
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ArtifactError(f"Invalid run manifest: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        """Serialize every manifest field without dropping unknown cost."""
        return asdict(self)


_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def _file_lock(target: Path) -> Iterator[None]:
    """Take a process and OS lock using a dedicated one-byte lock file."""
    lock_path = target.with_name(f"{target.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock(lock_path)
    with thread_lock:
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised on POSIX CI
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_usage(value: Any) -> None:
    if not isinstance(value, dict):
        raise ArtifactRecordError("usage must be an object")
    for field_name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        token_value = value.get(field_name, 0)
        if (
            isinstance(token_value, bool)
            or not isinstance(token_value, int)
            or token_value < 0
        ):
            raise ArtifactRecordError(f"usage.{field_name} must be non-negative")
    cost = value.get("cost_usd")
    if cost is not None and (
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(float(cost))
        or float(cost) < 0
    ):
        raise ArtifactRecordError("usage.cost_usd must be non-negative or null")


def _validated_record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(record)
    if not _non_empty_string(value.get("qa_id")):
        raise ArtifactRecordError("Result record requires a non-empty qa_id")
    if not _non_empty_string(value.get("table_id")):
        raise ArtifactRecordError("Result record requires a non-empty table_id")

    has_prediction = "prediction" in value
    has_error = "error" in value
    if has_prediction == has_error:
        raise ArtifactRecordError(
            "Result record requires exactly one of prediction or error"
        )
    if has_prediction:
        prediction = value["prediction"]
        if not isinstance(prediction, list) or not prediction or any(
            not _non_empty_string(answer) for answer in prediction
        ):
            raise ArtifactRecordError(
                "prediction must be a non-empty list of non-empty strings"
            )
        if not _non_empty_string(value.get("finalizer")):
            raise ArtifactRecordError(
                "Successful result record requires a finalizer"
            )
    else:
        error = value["error"]
        if not isinstance(error, dict) or not _non_empty_string(
            error.get("type")
        ) or not _non_empty_string(error.get("message")):
            raise ArtifactRecordError(
                "error must contain non-empty type and message strings"
            )
    if "usage" in value:
        _validate_usage(value["usage"])

    value.pop("record_type", None)
    _canonical_json(value)
    return value


def success_record(
    *,
    qa_id: str,
    table_id: str,
    prediction: list[str],
    finalizer: str,
    trace: Mapping[str, Any] | None = None,
    usage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate one successful incremental result."""
    record: dict[str, Any] = {
        "qa_id": qa_id,
        "table_id": table_id,
        "prediction": list(prediction),
        "finalizer": finalizer,
    }
    if trace is not None:
        record["trace"] = dict(trace)
    if usage is not None:
        record["usage"] = dict(usage)
    return _validated_record(record)


def failure_record(
    *,
    qa_id: str,
    table_id: str,
    error_type: str,
    message: str,
    usage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate one typed failed incremental result."""
    record: dict[str, Any] = {
        "qa_id": qa_id,
        "table_id": table_id,
        "error": {"type": error_type, "message": message},
    }
    if usage is not None:
        record["usage"] = dict(usage)
    return _validated_record(record)


def _load_lines(path: Path) -> tuple[RunManifest, list[dict[str, Any]]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ArtifactError(f"Cannot read artifact {path}: {exc}") from exc
    if not lines:
        raise ArtifactError(f"Artifact {path} has no manifest header")

    objects: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ArtifactError(
                f"Artifact {path} line {line_number} is invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise ArtifactError(
                f"Artifact {path} line {line_number} is not an object"
            )
        objects.append(value)
    if not objects:
        raise ArtifactError(f"Artifact {path} has no manifest header")

    header = objects[0]
    if header.get("record_type") != "manifest" or not isinstance(
        header.get("manifest"), dict
    ):
        raise ArtifactError(f"Artifact {path} has an invalid manifest header")
    manifest = RunManifest.from_dict(header["manifest"])
    records = [_validated_record(value) for value in objects[1:]]
    return manifest, records


def _assert_matching(existing: RunManifest, requested: RunManifest) -> None:
    identity_fields = (
        "source_sha256",
        "dataset_sha256",
        "configuration_fingerprint",
    )
    mismatches = [
        name
        for name in identity_fields
        if getattr(existing, name) != getattr(requested, name)
    ]
    if mismatches:
        raise ManifestMismatchError(
            "Cannot resume artifact with mismatched "
            + ", ".join(mismatches)
        )


def _usage_totals(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, int], float | None]:
    prompt = 0
    completion = 0
    total = 0
    costs: list[float] = []
    unknown_cost = False
    for record in records:
        usage = record.get("usage")
        if not isinstance(usage, dict):
            unknown_cost = True
            continue
        prompt += int(usage.get("prompt_tokens", 0))
        completion += int(usage.get("completion_tokens", 0))
        total += int(usage.get("total_tokens", 0))
        cost = usage.get("cost_usd")
        if cost is None:
            unknown_cost = True
        else:
            costs.append(float(cost))
    return (
        {"prompt": prompt, "completion": completion, "total": total},
        None if unknown_cost else sum(costs),
    )


class IncrementalArtifactStore:
    """A manifest-bound JSONL store with explicit resume semantics."""

    def __init__(self, path: Path, manifest: RunManifest) -> None:
        self.path = Path(path)
        self.manifest = manifest
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _file_lock(self.path):
            if self.path.exists() and self.path.stat().st_size > 0:
                existing, _ = _load_lines(self.path)
                _assert_matching(existing, manifest)
            else:
                header = {
                    "record_type": "manifest",
                    "manifest": manifest.to_dict(),
                }
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(_canonical_json(header) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())

    def append(self, record: Mapping[str, Any]) -> None:
        """Append one complete JSON object under the cross-platform lock."""
        value = _validated_record(record)
        with _file_lock(self.path):
            existing, _ = _load_lines(self.path)
            _assert_matching(existing, self.manifest)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(value) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def records(self) -> list[dict[str, Any]]:
        """Read and validate all incremental result records."""
        with _file_lock(self.path):
            existing, records = _load_lines(self.path)
            _assert_matching(existing, self.manifest)
            return records

    def pending_qa_ids(
        self,
        dataset_order: Sequence[str],
        *,
        retry_failed: bool = False,
    ) -> list[str]:
        """Return pending IDs; failed IDs require explicit retry permission."""
        ordered = [str(qa_id) for qa_id in dataset_order]
        if len(ordered) != len(set(ordered)):
            raise ArtifactRecordError("Dataset order contains duplicate qa_id values")

        records = self.records()
        successful = {
            str(record["qa_id"]) for record in records if "prediction" in record
        }
        failed = {
            str(record["qa_id"]) for record in records if "error" in record
        }.difference(successful)
        return [
            qa_id
            for qa_id in ordered
            if qa_id not in successful
            and (qa_id not in failed or retry_failed)
        ]

    def materialize(
        self,
        output_path: Path,
        *,
        dataset_order: Sequence[str],
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        """Write dataset-sorted official JSON while retaining typed failures."""
        ordered = [str(qa_id) for qa_id in dataset_order]
        if len(ordered) != len(set(ordered)):
            raise ArtifactRecordError("Dataset order contains duplicate qa_id values")
        order_set = set(ordered)
        records = self.records()
        unknown_ids = {
            str(record["qa_id"]) for record in records
        }.difference(order_set)
        if unknown_ids:
            raise ArtifactRecordError(
                f"Artifact contains qa_id outside dataset order: "
                f"{sorted(unknown_ids)[0]!r}"
            )

        by_qa: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_qa.setdefault(str(record["qa_id"]), []).append(record)

        missing_ids = [qa_id for qa_id in ordered if qa_id not in by_qa]
        if missing_ids:
            raise ArtifactRecordError(
                f"Dataset qa_id={missing_ids[0]!r} has no result record"
            )

        selected: list[dict[str, Any]] = []
        for qa_id in ordered:
            attempts = by_qa[qa_id]
            successes = [
                record for record in attempts if "prediction" in record
            ]
            if successes:
                selected.append(successes[-1])
            elif attempts:
                selected.append(attempts[-1])

        successful_count = sum(
            1 for record in selected if "prediction" in record
        )
        tokens, cost = _usage_totals(records)
        final_manifest = replace(
            self.manifest,
            completed_at=completed_at or _utc_now(),
            counts={
                "dataset": len(selected),
                "successful": successful_count,
                "failed": len(selected) - successful_count,
                "attempts": len(records),
            },
            tokens=tokens,
            cost_usd=cost,
        )
        payload = {
            "manifest": final_manifest.to_dict(),
            "predictions": selected,
        }
        _write_json_atomically(Path(output_path), payload)
        return payload


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json_atomically(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _file_lock(path):
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                newline="\n",
            ) as handle:
                temporary_name = handle.name
                json.dump(
                    value,
                    handle,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)


__all__ = [
    "ArtifactError",
    "ArtifactRecordError",
    "IncrementalArtifactStore",
    "ManifestMismatchError",
    "RunManifest",
    "canonical_sha256",
    "failure_record",
    "sha256_file",
    "success_record",
]
