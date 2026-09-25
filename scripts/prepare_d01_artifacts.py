"""Adapt archived predictions and materialize one-answer D01 evaluation inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("predictions") if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ValueError(f"{path} has no predictions array")
    ids = [
        str(row["qa_id"]).strip() if row.get("qa_id") is not None else ""
        for row in records
    ]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{path} has missing or duplicate qa_id values")
    return records


def _first_answer(row: dict[str, Any]) -> str:
    raw = row.get("prediction", row.get("predicted_answer"))
    values = raw if isinstance(raw, list) else [raw]
    if not values or not isinstance(values[0], str) or not values[0].strip():
        raise ValueError(f"qa_id={row['qa_id']!r} has no non-empty first answer")
    return values[0].strip()


def adapt_baseline(source: Path, output: Path) -> dict[str, Any]:
    """Convert archived predicted_answer to the finalizer's prediction schema."""
    records = _records(source)
    converted = []
    for row in records:
        raw = row.get("predicted_answer")
        if not isinstance(raw, list) or len(raw) != 1:
            raise ValueError(f"qa_id={row['qa_id']!r} is not a one-answer baseline")
        converted.append(
            {
                "qa_id": row["qa_id"],
                "table_id": row.get("table_id"),
                "prediction": [_first_answer(row)],
            }
        )
    payload = {
        "manifest": {
            "transform": "legacy-baseline-to-canonical.v1",
            "source": str(source),
            "source_sha256": _sha256(source),
            "count": len(converted),
            "source_parse_failures": sum(not row.get("parse_ok", True) for row in records),
        },
        "predictions": converted,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def materialize_single(
    source: Path, output: Path, *, fallback_source: Path | None = None
) -> dict[str, Any]:
    """Keep the first output, falling back to the raw first answer on failure."""
    records = _records(source)
    fallback = {}
    if fallback_source is not None:
        fallback_records = _records(fallback_source)
        fallback = {str(row["qa_id"]): row for row in fallback_records}
        if set(fallback) != {str(row["qa_id"]) for row in records}:
            raise ValueError("Finalizer and fallback source have different QA IDs")
    converted = []
    fallback_ids = []
    for row in records:
        qa_id = str(row["qa_id"])
        try:
            answer = _first_answer(row)
        except ValueError:
            if not fallback:
                raise
            answer = _first_answer(fallback[qa_id])
            fallback_ids.append(qa_id)
        converted.append(
            {
                "qa_id": qa_id,
                "table_id": row.get("table_id"),
                "prediction": [answer],
            }
        )
    payload = {
        "manifest": {
            "transform": "single-first-with-optional-fallback.v1",
            "source": str(source),
            "source_sha256": _sha256(source),
            "fallback_source": str(fallback_source) if fallback_source else None,
            "fallback_source_sha256": _sha256(fallback_source) if fallback_source else None,
            "count": len(converted),
            "fallback_count": len(fallback_ids),
            "fallback_qa_ids": fallback_ids,
        },
        "predictions": converted,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("adapt-baseline", "single-answer"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fallback-source", type=Path)
    args = parser.parse_args()
    if args.operation == "adapt-baseline":
        if args.fallback_source is not None:
            parser.error("--fallback-source is only valid for single-answer")
        payload = adapt_baseline(args.source, args.output)
    else:
        payload = materialize_single(
            args.source, args.output, fallback_source=args.fallback_source
        )
    print(json.dumps(payload["manifest"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
