"""Dump experimental table encodings for one or more Open-ViTabQA tables.

Examples:

    python -m experiments.table_representation.run_encode \\
        --table-id 29_4 \\
        --output experiments/table_representation/samples

    python -m experiments.table_representation.run_encode \\
        --table-id 29_4 --methods flatten_v1,markdown,html --compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from preprocessing.loader import DatasetLoader

from .encodings import METHOD_NAMES, EncodedTable, compare_sizes, encode_all, rough_token_count


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", default="dataset/table.json", help="Path to table.json")
    parser.add_argument("--dataset-dir", default="dataset", help="Dataset directory for DatasetLoader")
    parser.add_argument("--table-id", action="append", dest="table_ids", default=[], help="Table id to encode; repeatable")
    parser.add_argument("--limit", type=int, default=0, help="If no table ids are given, encode the first N tables")
    parser.add_argument(
        "--methods",
        default="all",
        help="Comma-separated method names, or 'all'",
    )
    parser.add_argument("--output", default="", help="Directory to write per-method .txt files and a sizes.json summary")
    parser.add_argument("--compare", action="store_true", help="Print a size comparison table to stdout")
    return parser.parse_args(argv)


def _selected_methods(raw: str) -> List[str]:
    text = (raw or "all").strip()
    if text == "all":
        return list(METHOD_NAMES)
    methods = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [name for name in methods if name not in METHOD_NAMES]
    if unknown:
        raise ValueError(f"Unknown methods: {', '.join(unknown)}")
    return methods


def _load_tables(args: argparse.Namespace) -> Dict[str, Dict[str, Any]]:
    loader = DatasetLoader(dataset_dir=args.dataset_dir)
    tables_path = Path(args.tables)
    if tables_path.exists():
        return loader.load_tables_path(str(tables_path.resolve()))
    return loader.load_tables_path(args.tables)


def _choose_table_ids(tables: Dict[str, Dict[str, Any]], table_ids: List[str], limit: int) -> List[str]:
    if table_ids:
        missing = [table_id for table_id in table_ids if table_id not in tables]
        if missing:
            raise KeyError(f"Unknown table_id(s): {', '.join(missing)}")
        return table_ids
    ids = list(tables.keys())
    if limit > 0:
        return ids[:limit]
    raise ValueError("Pass --table-id or --limit to select tables")


def _write_outputs(output_dir: Path, encoded: Iterable[EncodedTable]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    items = list(encoded)
    if not items:
        raise ValueError("No encodings to write")
    table_id = items[0].table_id or "table"
    table_dir = output_dir / table_id
    table_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for item in items:
        path = table_dir / f"{item.method}.txt"
        path.write_text(item.text, encoding="utf-8")
        row = item.to_dict()
        row.pop("text", None)
        row["approx_tokens"] = rough_token_count(item.text)
        row["path"] = str(path)
        summary.append(row)
    summary_path = table_dir / "sizes.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary_path


def _print_compare(encoded: List[EncodedTable]) -> None:
    rows = compare_sizes(encoded)
    print(f"{'method':<16} {'chars':>8} {'lines':>7} {'~tok':>8}")
    print("-" * 42)
    for row in rows:
        method = row["method"]
        item = next(item for item in encoded if item.method == method)
        print(
            f"{method:<16} {row['n_chars']:>8} {row['n_lines']:>7} {rough_token_count(item.text):>8}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    methods = _selected_methods(args.methods)
    tables = _load_tables(args)
    table_ids = _choose_table_ids(tables, args.table_ids, args.limit)
    last_encoded: List[EncodedTable] = []
    for table_id in table_ids:
        encoded = encode_all(tables[table_id], methods)
        last_encoded = encoded
        if args.output:
            summary_path = _write_outputs(Path(args.output), encoded)
            print(f"Wrote {table_id} encodings to {summary_path.parent}")
        if args.compare or not args.output:
            print(f"\n# {table_id} {tables[table_id].get('table_title', '')}".rstrip())
            _print_compare(encoded)
    return 0 if last_encoded else 1


if __name__ == "__main__":
    sys.exit(main())
