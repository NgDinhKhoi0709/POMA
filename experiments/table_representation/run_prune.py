"""Prune an Open-ViTabQA table to question-relevant rows and columns.

Examples:

    python -m experiments.table_representation.run_prune \\
        --table-id 37_1 \\
        --question "Album có tựa đề album1 xếp hạng thứ mấy trên bảng xếp hạng US Heat?" \\
        --compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from preprocessing.loader import DatasetLoader

from .pruning import PRUNE_METHODS, PrunedTable, prune_all


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", default="dataset/table.json")
    parser.add_argument("--dataset-dir", default="dataset")
    parser.add_argument("--qas", default="dataset/qas_test.json")
    parser.add_argument("--table-id", default="")
    parser.add_argument("--qa-id", default="")
    parser.add_argument("--question", default="")
    parser.add_argument("--methods", default="all")
    parser.add_argument("--max-rows", type=int, default=8)
    parser.add_argument("--max-cols", type=int, default=6)
    parser.add_argument("--output", default="")
    parser.add_argument("--compare", action="store_true")
    return parser.parse_args(argv)


def _selected_methods(raw: str) -> List[str]:
    text = (raw or "all").strip()
    if text == "all":
        return list(PRUNE_METHODS)
    methods = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [name for name in methods if name not in PRUNE_METHODS]
    if unknown:
        raise ValueError(f"Unknown methods: {', '.join(unknown)}")
    return methods


def _load_tables(args: argparse.Namespace) -> Dict[str, Dict[str, Any]]:
    loader = DatasetLoader(dataset_dir=args.dataset_dir)
    tables_path = Path(args.tables)
    if tables_path.exists():
        return loader.load_tables_path(str(tables_path.resolve()))
    return loader.load_tables_path(args.tables)


def _load_qas(path: str) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("qas", payload)
        if isinstance(items, dict):
            items = list(items.values())
        return list(items)
    return list(payload)


def _resolve_question(args: argparse.Namespace, tables: Dict[str, Dict[str, Any]]) -> tuple[str, str, Dict[str, Any]]:
    question = args.question.strip()
    table_id = args.table_id.strip()
    if args.qa_id:
        matches = [item for item in _load_qas(args.qas) if str(item.get("qa_id")) == args.qa_id]
        if not matches:
            raise KeyError(f"Unknown qa_id: {args.qa_id}")
        item = matches[0]
        table_id = str(item.get("table_id") or table_id)
        question = question or str(item.get("question") or "")
    if not table_id:
        raise ValueError("Pass --table-id or --qa-id")
    if table_id not in tables:
        raise KeyError(f"Unknown table_id: {table_id}")
    if not question:
        raise ValueError("Pass --question or --qa-id")
    return table_id, question, tables[table_id]


def _print_compare(results: List[PrunedTable]) -> None:
    print(f"{'method':<18} {'chars':>8} {'save':>7} {'rows':>9} {'cols':>9}")
    print("-" * 54)
    for item in results:
        rows = f"{item.n_rows_after}/{item.n_rows_before}"
        cols = f"{item.n_cols_after}/{item.n_cols_before}"
        print(
            f"{item.method:<18} {item.n_chars_after:>8} {item.char_save_ratio:6.0%} "
            f"{rows:>9} {cols:>9}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    tables = _load_tables(args)
    table_id, question, table = _resolve_question(args, tables)
    results = prune_all(
        table,
        question,
        methods=_selected_methods(args.methods),
        max_rows=args.max_rows,
        max_cols=args.max_cols,
    )
    print(f"# {table_id}")
    print(f"Q: {question}")
    if args.compare or not args.output:
        _print_compare(results)
        target = next(item for item in results if item.method == "lexical_subtable")
        print("\n--- lexical_subtable ---\n" + target.text)
    if args.output:
        output_dir = Path(args.output) / table_id
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = []
        for item in results:
            path = output_dir / f"{item.method}.txt"
            path.write_text(item.text, encoding="utf-8")
            row = item.to_dict()
            row.pop("text", None)
            row["path"] = str(path)
            summary.append(row)
        (output_dir / "sizes.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote encodings to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
