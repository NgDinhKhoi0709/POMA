from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BASELINE_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = BASELINE_ROOT.parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from Open_ViTabQA.preprocessing.parser import HTMLTableParser


def _load_records(path: Path, key: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    raise ValueError(f"{path} must contain a JSON list or a '{key}' list")


def _coq_table_from_open_table(table: dict[str, Any]) -> dict[str, Any]:
    parsed = HTMLTableParser().parse(str(table.get("table_html") or ""))
    header_rows = [[cell.value for cell in row] for row in parsed.headers]
    data_rows = [[cell.value for cell in row] for row in parsed.rows]

    if header_rows:
        max_cols = max((len(row) for row in header_rows + data_rows), default=0)
        header = []
        for col_idx in range(max_cols):
            parts = []
            for row in header_rows:
                if col_idx < len(row):
                    value = str(row[col_idx] or "").strip()
                    if value and value not in parts:
                        parts.append(value)
            header.append(" / ".join(parts) if parts else f"column_{col_idx + 1}")
    elif data_rows:
        header = [f"column_{idx + 1}" for idx in range(max(len(row) for row in data_rows))]
    else:
        header = []

    width = len(header)
    normalized_rows = []
    for row in data_rows:
        out_row = [str(cell or "").strip() for cell in row[:width]]
        if len(out_row) < width:
            out_row.extend([""] * (width - len(out_row)))
        normalized_rows.append(out_row)

    return {
        "title": table.get("table_title") or table.get("table_id") or "table_name",
        "table": {
            "header": header,
            "rows": normalized_rows,
        },
    }


def convert_open_vitabqa(
    qas_path: Path,
    tables_path: Path,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    qas = _load_records(qas_path, "qas")
    tables = _load_records(tables_path, "table")
    table_by_id = {str(table.get("table_id")): table for table in tables if table.get("table_id") is not None}

    converted: list[dict[str, Any]] = []
    selected_qas = qas[:limit] if limit is not None else qas
    for qa in selected_qas:
        table_id = str(qa.get("table_id", ""))
        if table_id not in table_by_id:
            raise KeyError(f"Missing table_id {table_id!r} for qa_id {qa.get('qa_id')!r}")
        source_table = table_by_id[table_id]
        coq_table = _coq_table_from_open_table(source_table)
        converted.append(
            {
                "qa_id": str(qa.get("qa_id", "")),
                "table_id": table_id,
                "source_split": "test",
                "question": str(qa.get("question", "")),
                "answer": qa.get("answer", ""),
                "hints": qa.get("hints", []) or [],
                "table": coq_table,
                "source_table_type": source_table.get("table_type", []),
                "source_table_domain": source_table.get("table_domain", ""),
            }
        )
    return converted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Open_ViTabQA records to ChainofQuery local JSON.")
    parser.add_argument("--qas", required=True, type=Path, help="Path to Open_ViTabQA qas JSON.")
    parser.add_argument("--tables", required=True, type=Path, help="Path to Open_ViTabQA table JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path.")
    parser.add_argument("--limit", type=int, default=None, help="Keep only the first N QA records.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    records = convert_open_vitabqa(args.qas, args.tables, limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
