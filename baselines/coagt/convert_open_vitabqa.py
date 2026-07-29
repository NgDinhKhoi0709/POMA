"""Convert Open_ViTabQA records to the CoAgt WikiTQ-style JSONL format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_records(path: Path, key: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"{path} must contain a list or a '{key}' list")


def select_qas(dataset_dir: Path, split: str, count: int | None) -> list[dict[str, Any]]:
    if split == "mixed":
        test_qas = load_records(dataset_dir / "qas_test.json", "qas")
        dev_qas = load_records(dataset_dir / "qas_dev.json", "qas")
        selected: list[dict[str, Any]] = []
        sources = [("test", test_qas), ("dev", dev_qas)]
        target = count or (len(test_qas) + len(dev_qas))
        index = 0
        while len(selected) < target:
            source_split, records = sources[index % len(sources)]
            source_index = index // len(sources)
            if source_index >= len(records):
                break
            qa = dict(records[source_index])
            qa["source_split"] = source_split
            selected.append(qa)
            index += 1
        return selected

    records = load_records(dataset_dir / f"qas_{split}.json", "qas")
    selected = records[:count] if count is not None else records
    return [{**qa, "source_split": split} for qa in selected]


def convert_record(qa: dict[str, Any], table: dict[str, Any]) -> dict[str, Any]:
    table_rows = table.get("table_dict", {}).get("table_rows")
    if not table_rows:
        raise ValueError(f"Missing table_dict.table_rows for table_id={qa.get('table_id')}")
    return {
        "ids": str(qa["qa_id"]),
        "title": str(table.get("table_title", "")),
        "statement": str(qa["question"]),
        "table_text": table_rows,
        "answer": [str(qa.get("answer", ""))],
        "source_split": qa.get("source_split"),
        "table_id": str(qa["table_id"]),
        "hints": qa.get("hints", []),
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def convert_open_vitabqa(
    qas_path: Path,
    tables_path: Path,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    qas = load_records(qas_path, "qas")
    tables = load_records(tables_path, "table")
    if limit is not None:
        qas = qas[:limit]
    table_by_id = {str(table["table_id"]): table for table in tables}
    converted: list[dict[str, Any]] = []
    for source_qa in qas:
        qa = {**source_qa, "source_split": source_qa.get("source_split", "test")}
        table = table_by_id.get(str(qa["table_id"]))
        if table is None:
            raise KeyError(
                f"Missing table_id={qa['table_id']} for qa_id={qa['qa_id']}"
            )
        converted.append(convert_record(qa, table))
    return converted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="../../Open_ViTabQA/dataset")
    parser.add_argument("--split", choices=("train", "dev", "test", "mixed"), default="mixed")
    parser.add_argument("--count", type=int, help="Number of records to convert. Omit or use 0 for all records.")
    parser.add_argument("--output", default="dataset_wtq/open_vitabqa_smoke_5.jsonl")
    parser.add_argument("--refs-output", default="outputs/open_vitabqa_smoke_5_refs.json")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    count = None if args.count in (None, 0) else args.count
    qas = select_qas(dataset_dir, args.split, count)
    tables = load_records(dataset_dir / "table.json", "table")
    table_by_id = {str(table["table_id"]): table for table in tables}

    converted: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    for qa in qas:
        table = table_by_id.get(str(qa["table_id"]))
        if table is None:
            raise ValueError(f"Missing table_id={qa['table_id']} for qa_id={qa['qa_id']}")
        converted.append(convert_record(qa, table))
        refs.append(qa)

    write_jsonl(Path(args.output), converted)
    refs_path = Path(args.refs_output)
    refs_path.parent.mkdir(parents=True, exist_ok=True)
    refs_path.write_text(json.dumps({"qas": refs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(converted), "output": args.output, "refs_output": args.refs_output}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
