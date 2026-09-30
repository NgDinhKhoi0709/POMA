"""Nạp dữ liệu, dựng chuỗi bảng và truy hồi ví dụ train cùng bảng."""

from __future__ import annotations

import os
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from evaluation.io import load_qas_records
from evaluation.normalization import normalize_text
from preprocessing.loader import DatasetLoader
from preprocessing.representation import create_representation

ROOT = Path(__file__).resolve().parents[1]
# "cross": mô phỏng bảng chưa thấy, memory chỉ truy hồi câu train của các bảng khác.
MEMORY_SCOPE = os.environ.get("MAS_MEMORY_SCOPE", "same")


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


@lru_cache(maxsize=None)
def _toks(s: str) -> frozenset[str]:
    return frozenset(normalize_text(s).split())


def retrieve_same_table(qa: dict, k: int, exclude_ids: frozenset[str] = frozenset()) -> list[dict]:
    """k câu train cùng bảng giống câu hỏi nhất (Jaccard token), thứ tự từ ít đến nhiều giống.
    MEMORY_SCOPE="cross": lấy từ mọi bảng khác bảng của câu hỏi."""
    q = _toks(qa["question"])
    if MEMORY_SCOPE == "cross":
        pool = [r for tid, rs in train_by_table().items() if tid != qa["table_id"] for r in rs]
    else:
        pool = train_by_table().get(qa["table_id"], [])
    pool = [r for r in pool if r["qa_id"] not in exclude_ids and r["qa_id"] != qa["qa_id"]]
    scored = sorted(pool, key=lambda r: len(q & _toks(r["question"])) / max(1, len(q | _toks(r["question"]))))
    return scored[-k:]
