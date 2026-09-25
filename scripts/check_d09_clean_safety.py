"""D09: does the cleaning layer ever delete a gold answer from the table text?

Uses only gold answers and table text (no model output). For every QA whose gold answer is present in
the raw grid, report whether it is still present after each cleaning rule alone and after all rules.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing.variants import Grid  # noqa: E402

RULES = {
    "strip_citations": dict(drop_empty_columns=False, drop_link_columns=False, drop_empty_rows=False),
    "drop_empty_columns": dict(strip_citations=False, drop_link_columns=False, drop_empty_rows=False),
    "drop_link_columns": dict(strip_citations=False, drop_empty_columns=False, drop_empty_rows=False),
    "drop_empty_rows": dict(strip_citations=False, drop_empty_columns=False, drop_link_columns=False),
    "all_rules": {},
}


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", str(text)).lower().split())


def _cells(grid: Grid) -> list[str]:
    return [_norm(v) for row in grid.rows for v in row if v]


def _present(gold: str, cells: list[str]) -> tuple[bool, bool]:
    """(gold equals a whole cell, gold is a substring of the table text)."""
    g = _norm(gold)
    return g in cells, any(g in c for c in cells)


def check(qas: list[dict], tables: dict[str, dict]) -> dict:
    grids = {tid: Grid.from_table_data(t) for tid, t in tables.items()}
    cleaned = {rule: {tid: g.cleaned(**kw) for tid, g in grids.items()} for rule, kw in RULES.items()}
    report = {rule: {"whole_cell_present_raw": 0, "whole_cell_lost": 0, "substring_present_raw": 0, "substring_lost": 0, "examples": []}
              for rule in RULES}
    for qa in qas:
        tid = str(qa["table_id"])
        gold = str(qa["answer"])
        if not gold.strip() or tid not in grids:
            continue
        raw_cell, raw_sub = _present(gold, _cells(grids[tid]))
        for rule in RULES:
            new_cell, new_sub = _present(gold, _cells(cleaned[rule][tid]))
            row = report[rule]
            row["whole_cell_present_raw"] += raw_cell
            row["substring_present_raw"] += raw_sub
            if raw_cell and not new_cell:
                row["whole_cell_lost"] += 1
                row["examples"].append({"qa_id": qa["qa_id"], "gold": gold, "kind": "whole_cell"})
            if raw_sub and not new_sub:
                row["substring_lost"] += 1
                if len(row["examples"]) < 12:
                    row["examples"].append({"qa_id": qa["qa_id"], "gold": gold, "kind": "substring"})
    for row in report.values():
        row["examples"] = row["examples"][:12]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--subset", type=Path, default=PROJECT_ROOT / "outputs/d04/qas_test_200.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}
    splits = {name: json.loads((PROJECT_ROOT / f"dataset/qas_{name}.json").read_text(encoding="utf-8"))["qas"]
              for name in ("train", "dev", "test")}
    scopes = {
        "subset_200": json.loads(args.subset.read_text(encoding="utf-8"))["qas"],
        "test_992": splits["test"],
        "all_splits": [qa for qas in splits.values() for qa in qas],
    }
    result = {name: check(qas, tables) for name, qas in scopes.items()}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for scope, report in result.items():
        print(f"== {scope}")
        for rule, row in report.items():
            print(f"{rule:20} whole-cell raw={row['whole_cell_present_raw']:5} lost={row['whole_cell_lost']:3} | "
                  f"substring raw={row['substring_present_raw']:5} lost={row['substring_lost']:3}")


if __name__ == "__main__":
    main()
