"""Bỏ phiếu bằng LLM: agent chấm điểm cho từng ứng viên, điểm là xác suất đúng, tổng bằng 1.

Chỉ chạy trên câu có ≥ 2 ứng viên hợp lệ khác nhau (lấy từ trace MemView: 3 mẫu A, B, A2, B2).
Hai agent chấm, mỗi agent đọc bảng theo một view (Flatten V1, Markdown-KV) + 8 câu mẫu cùng bảng.
Không cho agent biết số phiếu, để điểm của nó độc lập với bỏ phiếu; thứ tự ứng viên xáo theo qa_id.
"""

from __future__ import annotations

import json
import os
import random
from collections import Counter

from .client import Usage, VLLMClient, parse_json
from .data import table_str
from .methods import key, valid

_TASK = (
    "NHIỆM VỤ: dưới đây là các đáp án ứng viên cho câu hỏi, do các chuyên gia khác đưa ra; có thể có một "
    "ứng viên đúng hoặc tất cả đều sai. Đối chiếu từng ứng viên với bảng thật cẩn thận, rồi cho mỗi ứng viên "
    "một điểm là xác suất ứng viên đó là đáp án đúng. Tổng các điểm phải bằng 1. Đáp án đúng phải khớp nội "
    "dung với bảng và viết theo đúng phong cách các đáp án mẫu ở trên.\n"
    "ĐẦU RA: đúng một JSON {\"scores\": [{\"id\": <số thứ tự>, \"p\": <điểm từ 0 đến 1>}, ...]}.\n"
)


def prefix_flat(qa: dict, memory: bool = True) -> str:
    from .math_agent import demo_block

    return (
        "Bạn là chuyên gia đọc bảng. Bảng dưới đây ở dạng chuỗi Flatten V1. CHỈ được dùng thông tin trong bảng.\n\n"
        f"BẢNG:\n{table_str(qa['table_id'])}\n\n{demo_block(qa, memory)}\n\n"
    )


def prefix_kv(qa: dict, memory: bool = True) -> str:
    from .math_agent import prefix

    return prefix(qa, memory)


def candidates(trace: dict, question: str) -> tuple[list[str], list[int]]:
    """Các đáp án hợp lệ khác nhau (theo key) cùng số phiếu của chúng trong pool MemView."""
    pool = list(trace.get("samples", [])) + [trace.get("B", "")] + [trace[k] for k in ("A2", "B2") if trace.get(k)]
    ok = [x for x in pool if valid(x, question)]
    votes = Counter(key(x, question) for x in ok)
    seen, cands = set(), []
    for x in ok:
        if key(x, question) not in seen:
            seen.add(key(x, question))
            cands.append(x)
    return cands, [votes[key(x, question)] for x in cands]


def parse_scores(text: str, n: int) -> list[float]:
    """Điểm theo đúng thứ tự ứng viên đã hiển thị; chuẩn hoá tổng = 1; lỗi → chia đều."""
    obj = parse_json(text) or {}
    raw = obj.get("scores")
    p = [0.0] * n
    if isinstance(raw, dict):
        raw = [{"id": k, "p": v} for k, v in raw.items()]
    for item in raw if isinstance(raw, list) else []:
        try:
            i, v = int(item.get("id")), float(item.get("p"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 0 <= i < n:
            p[i] = max(0.0, v)
    s = sum(p)
    return [x / s for x in p] if s > 0 else [1.0 / n] * n


def score(client: VLLMClient, qa: dict, prefix: str, cands: list[str],
          notes: list[str] | None = None, **sampling) -> tuple[list[float], Usage]:
    """notes[i]: lý do (và bằng chứng) các agent đưa ra cho ứng viên i; None = chỉ cho xem đáp án."""
    order = list(range(len(cands)))
    random.Random(qa["qa_id"]).shuffle(order)
    listing = "\n".join(f"[{j}] {cands[i]}" + (f"\n    Lý do của agent: {notes[i]}" if notes and notes[i] else "")
                        for j, i in enumerate(order))
    t, u = client.chat(prefix + _TASK + f"\nCÂU HỎI: {qa['question']}\nCÁC ỨNG VIÊN:\n{listing}\nĐẦU RA: ", **sampling)
    shown = parse_scores(t[0], len(cands))
    p = [0.0] * len(cands)
    for j, i in enumerate(order):
        p[i] = shown[j]
    return p, u


_TRACES: dict[str, dict] = {}


def trace_for(qa_id: str) -> dict | None:
    path = os.environ["MAS_SCORE_TRACE"]
    if not _TRACES:
        for line in open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                _TRACES[r["qa_id"]] = r
    return _TRACES.get(qa_id)


def llm_score(client: VLLMClient, qa: dict) -> dict:
    rec = trace_for(qa["qa_id"])
    base = rec["prediction"][0] if rec else ""
    cands, votes = candidates(rec["trace"], qa["question"]) if rec else ([], [])
    usage = Usage()
    if len(cands) < 2:
        return {"prediction": [base or "Null"], "trace": {"cands": cands, "votes": votes, "skipped": True}, "usage": usage}
    p_flat, u = score(client, qa, prefix_flat(qa), cands); usage.add(u)
    p_kv, u = score(client, qa, prefix_kv(qa), cands); usage.add(u)
    mean = [(a + b) / 2 for a, b in zip(p_flat, p_kv)]
    return {"prediction": [cands[max(range(len(cands)), key=mean.__getitem__)]],
            "trace": {"cands": cands, "votes": votes, "p_flat": p_flat, "p_kv": p_kv, "base": base}, "usage": usage}
