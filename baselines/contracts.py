"""Shared file and prediction contracts for vendored baseline adapters."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMON_FIELDS = {
    "qa_id",
    "table_id",
    "question",
    "prediction",
    "answer",
    "model",
    "method",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "api_calls",
    "cost_usd",
    "latency_s",
    "error",
}
COAGT_FIELDS = {"num_collectors", "temperatures", "max_chunk_tokens"}


@dataclass(frozen=True)
class RunPaths:
    root: Path
    results_jsonl: Path
    results_json: Path
    errors_jsonl: Path
    qas_subset: Path
    meta_json: Path
    eval_report: Path

    @classmethod
    def create(cls, output_dir: Path, method: str, run_id: str) -> "RunPaths":
        if method not in {"coagt", "coq"}:
            raise ValueError(f"unsupported baseline method: {method}")
        if not SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError(f"invalid run-id: {run_id!r}")
        root = output_dir.resolve() / method / run_id
        return cls(
            root=root,
            results_jsonl=root / "results.jsonl",
            results_json=root / "results.json",
            errors_jsonl=root / "errors.jsonl",
            qas_subset=root / "qas_subset.json",
            meta_json=root / "meta.json",
            eval_report=root / "eval" / "report.json",
        )

    def generated_files(self) -> tuple[Path, ...]:
        return (
            self.results_jsonl,
            self.results_json,
            self.errors_jsonl,
            self.qas_subset,
            self.meta_json,
            self.eval_report,
        )


def validate_prediction(record: Mapping[str, Any], method: str) -> None:
    missing = sorted(COMMON_FIELDS - record.keys())
    if missing:
        raise ValueError(f"missing prediction fields: {missing}")
    if str(record["method"]).lower() != method:
        raise ValueError(f"method mismatch: {record['method']!r} != {method!r}")
    for field in ("prompt_tokens", "completion_tokens", "total_tokens", "api_calls"):
        if not isinstance(record[field], int) or record[field] < 0:
            raise ValueError(f"{field} must be a non-negative int")
    for field in ("cost_usd", "latency_s"):
        if not isinstance(record[field], (int, float)) or record[field] < 0:
            raise ValueError(f"{field} must be non-negative")
    if method == "coagt":
        missing_coagt = sorted(COAGT_FIELDS - record.keys())
        if missing_coagt:
            raise ValueError(f"missing CoAgt fields: {missing_coagt}")
    elif method == "coq":
        if record.get("pipeline_mode") != "coq_base_sql_fallback":
            raise ValueError("CoQ pipeline_mode must be coq_base_sql_fallback")
        if not str(record.get("fallback_reason") or "").strip():
            raise ValueError("CoQ fallback_reason must be non-empty")
        for field in ("valid_sql", "final_sql"):
            if field not in record:
                raise ValueError(f"missing CoQ field: {field}")


def validate_run_records(
    records: Sequence[Mapping[str, Any]], method: str
) -> None:
    for record in records:
        validate_prediction(record, method)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
