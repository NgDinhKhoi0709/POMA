"""Các phương pháp: baseline (một lệnh gọi, self-consistency, cascade vote) và multi-agent MemXam.

Mọi vai dựa trên một solver dùng chung tiền tố prompt [hướng dẫn + bảng + memory] của solver đó,
chỉ khác phần đuôi (câu hỏi / nhiệm vụ), để vLLM tái dùng prefix cache.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from evaluation.normalization import normalize_text
from gap_tqa.nodes import verbalize
from preprocessing.variants import render_table

from .client import Usage, VLLMClient, final_answer, parse_json, strip_think
from .data import retrieve_same_table, table_str, tables
from .prompts_fs import _build_few_shot, _flatten_v1_notes_vi, _json_schema_instructions_vi

KNN_K = 8

_KNN_HEADER = (
    "Bạn là hệ thống hỏi–đáp dựa trên bảng.\n"
    "Bảng được cung cấp dưới dạng chuỗi Flatten V1 trong TABLE_STR.\n"
    "CHỈ được dùng thông tin trong TABLE_STR để trả lời.\n\n"
    + _flatten_v1_notes_vi()
    + "\n"
    + _json_schema_instructions_vi()
)


def knn_block(qa: dict, k: int = KNN_K) -> str:
    demos = retrieve_same_table(qa, k)
    lines = [f'CÂU HỎI: {d["question"]}\nĐẦU RA: {{"final_answer": "{d["answer"]}"}}' for d in demos]
    return (
        "CÁC CÂU HỎI KHÁC ĐÃ ĐƯỢC TRẢ LỜI ĐÚNG TRÊN CHÍNH BẢNG NÀY "
        "(tham khảo cách viết đáp án ngắn gọn, đúng định dạng):\n\n" + "\n\n".join(lines)
    )


def flat_prefix(qa: dict) -> str:
    return f"{_KNN_HEADER}\nBẢNG (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{knn_block(qa)}\n\n"


def knn_prompt(qa: dict) -> str:
    return flat_prefix(qa) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


def fs_prompt(qa: dict) -> str:
    return _build_few_shot(qa["question"], table_str(qa["table_id"]), True)


# ---------- Solver B: họ prompt khác (bảng dạng lưới, bằng chứng trước) ----------

@lru_cache(maxsize=None)
def grid_str(table_id: str) -> str:
    return render_table(tables()[table_id], "pipe_path_clean")


_GRID_HEADER = (
    "Bạn là chuyên gia đọc bảng. Bảng dưới đây ở dạng lưới: dòng đầu là tên cột, mỗi dòng sau là một hàng, "
    "các ô cách nhau bởi dấu |. CHỈ được dùng thông tin trong bảng.\n"
    "ĐẦU RA: đúng một JSON {\"evidence\": [\"<các ô bảng dùng để trả lời, chép nguyên văn>\"], "
    "\"final_answer\": \"<đáp án ngắn gọn, viết theo đúng phong cách các đáp án mẫu; Null nếu bảng không đủ thông tin>\"}.\n"
    "Trước hết tìm hàng và cột liên quan, chép các ô đó vào evidence, rồi mới kết luận final_answer.\n"
)


def grid_prefix(qa: dict) -> str:
    return f"{_GRID_HEADER}\nBẢNG:\n{grid_str(qa['table_id'])}\n\n{knn_block(qa)}\n\n"


def evid_prompt(qa: dict) -> str:
    return grid_prefix(qa) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


def _parse_evid(text: str) -> tuple[str, list[str]]:
    obj = parse_json(text) or {}
    ev = obj.get("evidence") or []
    if "final_answer" in obj:
        ans = "Null" if obj["final_answer"] is None else str(obj["final_answer"]).strip()
    else:
        ans = strip_think(text)
    return ans, [str(e) for e in ev] if isinstance(ev, list) else [str(ev)]


def key(ans: str, question: str) -> str:
    return normalize_text(verbalize(question, ans))


# ---------- Đối chất (một vòng) và Judge: đuôi prompt đặt sau tiền tố của solver ----------

def _rebut_suffix(qa: dict, mine: str, my_ev: list[str], other: str, other_ev: list[str]) -> str:
    return (
        "NHIỆM VỤ LÚC NÀY KHÁC: bạn và một chuyên gia khác đã trả lời câu hỏi dưới đây nhưng ra đáp án khác nhau.\n"
        "Hãy đối chiếu lại cả hai đáp án với bảng thật cẩn thận. Giữ đáp án của bạn nếu nó đúng; "
        "đổi sang đáp án của chuyên gia kia nếu đáp án đó đúng hơn (kể cả chỉ đúng hơn về cách viết).\n"
        "ĐẦU RA: đúng một JSON {\"decision\": \"giu\" hoặc \"doi\", \"evidence\": [\"<ô bảng>\"], \"final_answer\": \"...\"}.\n\n"
        f"CÂU HỎI: {qa['question']}\n"
        f"ĐÁP ÁN CỦA BẠN: {mine}\nBẰNG CHỨNG CỦA BẠN: {json.dumps(my_ev, ensure_ascii=False)}\n"
        f"ĐÁP ÁN CỦA CHUYÊN GIA KIA: {other}\nBẰNG CHỨNG CỦA HỌ: {json.dumps(other_ev, ensure_ascii=False)}\n"
    )


def _judge_suffix(qa: dict, cands: list[tuple[str, list[str]]]) -> str:
    opts = "\n".join(
        f"[{i}] {a}  (bằng chứng: {json.dumps(ev, ensure_ascii=False)})" for i, (a, ev) in enumerate(cands)
    )
    return (
        "NHIỆM VỤ LÚC NÀY KHÁC: bạn là trọng tài. Các chuyên gia vẫn bất đồng về câu hỏi dưới đây. "
        "Đối chiếu từng đáp án với bảng và với phong cách các đáp án mẫu, rồi CHỌN một đáp án "
        "(không được viết đáp án mới).\n"
        "ĐẦU RA: đúng một JSON {\"choice\": <số thứ tự>}.\n\n"
        f"CÂU HỎI: {qa['question']}\nCÁC ĐÁP ÁN:\n{opts}\n"
    )


def _solvers(client: VLLMClient, qa: dict, usage: Usage) -> tuple[tuple[str, list[str]], tuple[str, list[str]]]:
    ta, u = client.chat(knn_prompt(qa)); usage.add(u)
    tb, u = client.chat(evid_prompt(qa)); usage.add(u)
    return (final_answer(ta[0]), []), _parse_evid(tb[0])


def memxam(client: VLLMClient, qa: dict) -> dict:
    """Memory + 2 solver dị thể ngang sức; bất đồng → đối chất 1 vòng; vẫn bất đồng → judge chọn."""
    usage, q = Usage(), qa["question"]
    (a, a_ev), (b, b_ev) = _solvers(client, qa, usage)
    trace = {"A": a, "B": b}
    if key(a, q) == key(b, q):
        return {"prediction": [a], "trace": {**trace, "route": "agree"}, "usage": usage}

    ra, u = client.chat(flat_prefix(qa) + _rebut_suffix(qa, a, a_ev, b, b_ev)); usage.add(u)
    rb, u = client.chat(grid_prefix(qa) + _rebut_suffix(qa, b, b_ev, a, a_ev)); usage.add(u)
    (a2, a2_ev), (b2, b2_ev) = _parse_evid(ra[0]), _parse_evid(rb[0])
    trace.update({"A2": a2, "B2": b2})
    if key(a2, q) == key(b2, q):
        return {"prediction": [a2], "trace": {**trace, "route": "converged"}, "usage": usage}

    cands = [(a2, a2_ev), (b2, b2_ev)]
    tj, u = client.chat(flat_prefix(qa) + _judge_suffix(qa, cands)); usage.add(u)
    obj = parse_json(tj[0]) or {}
    try:
        idx = int(obj.get("choice", 0))
    except (TypeError, ValueError):
        idx = 0
    idx = idx if 0 <= idx < len(cands) else 0
    return {"prediction": [cands[idx][0]], "trace": {**trace, "route": "judge", "choice": idx}, "usage": usage}


# ---------- Baseline ----------

def single(prompt_fn, *, thinking: bool = True):
    def run(client: VLLMClient, qa: dict) -> dict:
        texts, usage = client.chat(prompt_fn(qa), thinking=thinking)
        return {"prediction": [final_answer(texts[0])], "raw": texts[0][-400:], "usage": usage}

    return run


def _majority(answers: list[str], question: str) -> str:
    votes = Counter(key(x, question) for x in answers)
    top, cnt = votes.most_common(1)[0]
    return next(x for x in answers if key(x, question) == top) if cnt > 1 else answers[0]


def self_consistency(prompt_fn, n: int, *, thinking: bool = True):
    """n mẫu (temperature 0.7) trong một request, bỏ phiếu đa số; không có đa số thì lấy mẫu đầu."""
    def run(client: VLLMClient, qa: dict) -> dict:
        texts, usage = client.chat(prompt_fn(qa), thinking=thinking, n=n, temperature=0.7, top_p=0.95)
        answers = [final_answer(t) for t in texts]
        return {"prediction": [_majority(answers, qa["question"])], "trace": {"samples": answers}, "usage": usage}

    return run


def cascade3(client: VLLMClient, qa: dict) -> dict:
    """Đối chứng không tương tác của MemXam: cùng A, B; bất đồng → thêm một phiếu kNN (mẫu T=0.7), đa số; hoà lấy A."""
    usage, q = Usage(), qa["question"]
    (a, _), (b, _) = _solvers(client, qa, usage)
    if key(a, q) == key(b, q):
        return {"prediction": [a], "trace": {"A": a, "B": b, "route": "agree"}, "usage": usage}
    tc, u = client.chat(knn_prompt(qa), temperature=0.7, top_p=0.95); usage.add(u)
    c = final_answer(tc[0])
    return {"prediction": [_majority([a, b, c], q)], "trace": {"A": a, "B": b, "C": c, "route": "vote"}, "usage": usage}


def suite(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """Chạy tầng đầu (A, B) một lần rồi suy ra kNN-FS, evid, cascade3 và MemXam trên cùng A, B."""
    q = qa["question"]
    ta, ua = client.chat(knn_prompt(qa))
    tb, ub = client.chat(evid_prompt(qa))
    (a, a_ev), (b, b_ev) = (final_answer(ta[0]), []), _parse_evid(tb[0])
    base = Usage(); base.add(ua); base.add(ub)
    out = {
        "knn_fs": {"prediction": [a], "usage": ua},
        "evid": {"prediction": [b], "usage": ub},
    }
    if key(a, q) == key(b, q):
        agree = {"A": a, "B": b, "route": "agree"}
        out["cascade3"] = {"prediction": [a], "trace": agree, "usage": base}
        out["memxam"] = {"prediction": [a], "trace": agree, "usage": base}
        return out

    uc = Usage(); uc.add(base)
    tc, u = client.chat(knn_prompt(qa), temperature=0.7, top_p=0.95); uc.add(u)
    c = final_answer(tc[0])
    out["cascade3"] = {"prediction": [_majority([a, b, c], q)], "trace": {"A": a, "B": b, "C": c, "route": "vote"}, "usage": uc}

    um = Usage(); um.add(base)
    ra, u = client.chat(flat_prefix(qa) + _rebut_suffix(qa, a, a_ev, b, b_ev)); um.add(u)
    rb, u = client.chat(grid_prefix(qa) + _rebut_suffix(qa, b, b_ev, a, a_ev)); um.add(u)
    (a2, a2_ev), (b2, b2_ev) = _parse_evid(ra[0]), _parse_evid(rb[0])
    trace = {"A": a, "B": b, "A2": a2, "B2": b2}
    if key(a2, q) == key(b2, q):
        out["memxam"] = {"prediction": [a2], "trace": {**trace, "route": "converged"}, "usage": um}
        return out
    cands = [(a2, a2_ev), (b2, b2_ev)]
    tj, u = client.chat(flat_prefix(qa) + _judge_suffix(qa, cands)); um.add(u)
    obj = parse_json(tj[0]) or {}
    try:
        idx = int(obj.get("choice", 0))
    except (TypeError, ValueError):
        idx = 0
    idx = idx if 0 <= idx < len(cands) else 0
    out["memxam"] = {"prediction": [cands[idx][0]], "trace": {**trace, "route": "judge", "choice": idx}, "usage": um}
    return out


SUITES = {"suite": suite}

METHODS = {
    "fs": single(fs_prompt),
    "fs_nothink": single(fs_prompt, thinking=False),
    "knn_fs": single(knn_prompt),
    "knn_fs_nothink": single(knn_prompt, thinking=False),
    "evid": single(evid_prompt),
    "knn_sc3": self_consistency(knn_prompt, 3),
    "fs_sc3": self_consistency(fs_prompt, 3),
    "cascade3": cascade3,
    "memxam": memxam,
}
