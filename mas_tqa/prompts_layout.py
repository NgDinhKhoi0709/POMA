"""Phần dữ liệu dùng chung: tên bảng, ví dụ, câu hỏi. Mỗi dòng model tự chọn cách bọc."""

from __future__ import annotations

import re

from .data import MEMORY_SCOPE, retrieve_same_table, table_str, tables


def title_name(qa: dict) -> str:
    return re.sub(r"_\d+$", "", str(tables()[qa["table_id"]].get("table_title") or "")).strip()


def example_rows(qa: dict, k: int, memory: bool) -> str:
    if not memory:
        from .prompts_fs import _few_shot_examples_vi

        return _few_shot_examples_vi().strip()
    return "\n".join(f"Câu hỏi: {d['question']}\nĐáp án: {d['answer']}" for d in retrieve_same_table(qa, k))


def examples_block(qa: dict, k: int, memory: bool, wrap: str) -> str:
    """wrap là 'xml' hoặc 'markdown'."""
    if not memory:
        body = example_rows(qa, k, False)
        if wrap == "xml":
            return f"<ví_dụ_chung>\n{body}\n</ví_dụ_chung>\n"
        return f"# Ví dụ chung\n{body}\n"
    body = example_rows(qa, k, True)
    if MEMORY_SCOPE == "cross":
        tag, heading = "ví_dụ_từ_bảng_khác", "Ví dụ từ bảng khác"
    else:
        tag, heading = "ví_dụ_cùng_bảng", "Ví dụ cùng bảng"
    if wrap == "xml":
        return f"<{tag}>\n{body}\n</{tag}>\n"
    return f"# {heading}\n{body}\n"


def title_block(qa: dict, wrap: str) -> str:
    name = title_name(qa)
    if not name:
        return ""
    if wrap == "xml":
        return f"<tên_bảng>{name}</tên_bảng>\n"
    return f"# Tên bảng\n{name}\n\n"


def table_block(qa: dict, kind: str, wrap: str) -> str:
    if kind == "kv":
        from .methods import kv_str

        body = kv_str(qa["table_id"])
    else:
        body = table_str(qa["table_id"])
    if wrap == "xml":
        return f"<bảng>\n{body}\n</bảng>\n"
    return f"# Bảng\n{body}\n\n"


def messages(
    system: str,
    qa: dict,
    k: int,
    memory: bool,
    remind: str,
    *,
    table: str,
    wrap: str = "xml",
    force_generic: bool = False,
    skip_examples: bool = False,
) -> list[dict]:
    demos = ""
    if not skip_examples:
        demos = examples_block(qa, k, memory and not force_generic, wrap)
    if wrap == "xml":
        question = f"<câu_hỏi>\n{qa['question']}\n</câu_hỏi>\n<nhắc_lại>\n{remind}\n</nhắc_lại>"
    else:
        question = f"# Câu hỏi\n{qa['question']}\n\n# Nhắc lại\n{remind}"
    user = f"{title_block(qa, wrap)}{table_block(qa, table, wrap)}\n{demos}\n{question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
