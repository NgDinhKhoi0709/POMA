"""Append-only JSONL utilities used by resumable Kaggle evaluation."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping

_WRITE_LOCK = threading.Lock()


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSONL in {path} at line {line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL record in {path} at line {line_number} must be an object")
        records.append(record)
    return records


def completed_qa_ids(predictions_path: Path, errors_path: Path) -> set[str]:
    completed = {
        str(record["qa_id"]).strip()
        for record in load_jsonl(predictions_path)
        if str(record.get("qa_id", "")).strip()
    }
    completed.update(
        str(record["qa_id"]).strip()
        for record in load_jsonl(errors_path)
        if record.get("terminal") is True and str(record.get("qa_id", "")).strip()
    )
    return completed
