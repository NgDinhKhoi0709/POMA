"""Nạp dữ liệu, dựng chuỗi bảng và truy hồi ví dụ train cùng bảng."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from evaluation.io import load_qas_records
from evaluation.normalization import normalize_text
from preprocessing.loader import DatasetLoader
from preprocessing.representation import create_representation

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def tables() -> dict:
    return DatasetLoader(str(ROOT / "dataset")).load_tables()


@lru_cache(maxsize=None)
def table_str(table_id: str) -> str:
    return str(create_representation(tables()[table_id]).to_string() or "").strip()


@lru_cache(maxsize=1)
def train_by_table() -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = defaultdict(list)
    for r in load_qas_records(ROOT / "dataset/qas_train.json"):
        by[r["table_id"]].append(r)
    return by


def _toks(s: str) -> set[str]:
    return set(normalize_text(s).split())


def retrieve_same_table(qa: dict, k: int, exclude_ids: frozenset[str] = frozenset()) -> list[dict]:
    """k câu train cùng bảng giống câu hỏi nhất (Jaccard token), thứ tự từ ít đến nhiều giống."""
    q = _toks(qa["question"])
    pool = [r for r in train_by_table().get(qa["table_id"], []) if r["qa_id"] not in exclude_ids and r["qa_id"] != qa["qa_id"]]
    scored = sorted(pool, key=lambda r: len(q & _toks(r["question"])) / max(1, len(q | _toks(r["question"]))))
    return scored[-k:]
