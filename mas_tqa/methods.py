"""Các phương pháp: baseline (một lệnh gọi, self-consistency, cascade vote) và multi-agent MemXam.

Mọi vai dựa trên một solver dùng chung tiền tố prompt [hướng dẫn + bảng + memory] của solver đó,
chỉ khác phần đuôi (câu hỏi / nhiệm vụ), để vLLM tái dùng prefix cache.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from evaluation.normalization import normalize_text
from gap_tqa.nodes import YN_NEG, YN_POS, verbalize
from gap_tqa.router import route
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
        "Nếu hai đáp án cùng nội dung, chọn cách viết ngắn gọn giống phong cách các đáp án mẫu ở trên; "
        "không thêm chủ ngữ hay diễn giải.\n"
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


def valid(ans: str, question: str) -> bool:
    """Agent kiểm tra tất định: loại đáp án rỗng, và đáp án không phải Có/Không cho câu hỏi Có/Không."""
    a = normalize_text(ans or "")
    if not a:
        return False
    if route(question) == "yesno":
        return a in YN_POS | YN_NEG | {"null"}
    return True


def _pick_valid(answers: list[str], question: str) -> list[str]:
    ok = [x for x in answers if valid(x, question)]
    return ok or [x for x in answers if normalize_text(x or "")] or answers[:1]


def _judge(client: VLLMClient, qa: dict, cands: list[tuple[str, list[str]]], usage: Usage) -> tuple[int, str]:
    tj, u = client.chat(flat_prefix(qa) + _judge_suffix(qa, cands)); usage.add(u)
    obj = parse_json(tj[0]) or {}
    try:
        idx = int(obj.get("choice", 0))
    except (TypeError, ValueError):
        idx = 0
    return (idx if 0 <= idx < len(cands) else 0), cands[idx if 0 <= idx < len(cands) else 0][0]


def suite(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """Tầng đầu (A, B) chạy một lần; suy ra kNN-FS, evid, các ensemble đối chứng và MemXam trên cùng A, B.

    MemXam = memory cùng bảng + 2 solver dị thể + agent kiểm tra + đối chất 1 vòng + judge chỉ chọn.
    """
    q = qa["question"]
    ta, ua = client.chat(knn_prompt(qa))
    tb, ub = client.chat(evid_prompt(qa))
    (a, a_ev), (b, b_ev) = (final_answer(ta[0]), []), _parse_evid(tb[0])
    base = Usage(); base.add(ua); base.add(ub)
    out = {
        "knn_fs": {"prediction": [a], "usage": ua},
        "evid": {"prediction": [b], "trace": {"evidence": b_ev}, "usage": ub},
    }
    va, vb = valid(a, q), valid(b, q)
    first = {"A": a, "B": b, "A_valid": va, "B_valid": vb}
    if not (va and vb) or key(a, q) == key(b, q):
        # Đồng ý, hoặc agent kiểm tra loại bớt một bên: không có tranh chấp thật.
        pick = a if va or not vb else b
        r = "agree" if va and vb else "validator"
        for name in ("cascade3", "cascade3b", "judge_only", "memxam"):
            out[name] = {"prediction": [pick], "trace": {**first, "route": r}, "usage": base}
        return out

    # Đối chứng không tương tác (cùng agent kiểm tra): phiếu thứ ba họ A / họ B, đa số trên đáp án hợp lệ.
    for name, prompt, parse in (("cascade3", knn_prompt, final_answer), ("cascade3b", evid_prompt, lambda t: _parse_evid(t)[0])):
        uc = Usage(); uc.add(base)
        tc, u = client.chat(prompt(qa), temperature=0.7, top_p=0.95); uc.add(u)
        c = parse(tc[0])
        out[name] = {"prediction": [_majority(_pick_valid([a, b, c], q), q)], "trace": {**first, "C": c, "route": "vote"}, "usage": uc}

    # Ablation: bỏ đối chất, judge chọn thẳng giữa A và B.
    uj = Usage(); uj.add(base)
    j0, pj = _judge(client, qa, [(a, a_ev), (b, b_ev)], uj)
    out["judge_only"] = {"prediction": [pj], "trace": {**first, "route": "judge", "choice": j0}, "usage": uj}

    # MemXam: đối chất một vòng; đáp án sau đối chất không hợp lệ thì giữ đáp án cũ của solver đó.
    um = Usage(); um.add(base)
    ra, u = client.chat(flat_prefix(qa) + _rebut_suffix(qa, a, a_ev, b, b_ev)); um.add(u)
    rb, u = client.chat(grid_prefix(qa) + _rebut_suffix(qa, b, b_ev, a, a_ev)); um.add(u)
    (a2, a2_ev), (b2, b2_ev) = _parse_evid(ra[0]), _parse_evid(rb[0])
    if not valid(a2, q):
        a2, a2_ev = a, a_ev
    if not valid(b2, q):
        b2, b2_ev = b, b_ev
    trace = {**first, "A2": a2, "B2": b2, "B_ev": b_ev, "A2_ev": a2_ev, "B2_ev": b2_ev}
    if key(a2, q) == key(b2, q):
        out["memxam"] = {"prediction": [a2], "trace": {**trace, "route": "converged"}, "usage": um}
        return out
    idx, pm = _judge(client, qa, [(a2, a2_ev), (b2, b2_ev)], um)
    out["memxam"] = {"prediction": [pm], "trace": {**trace, "route": "judge", "choice": idx}, "usage": um}
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
}
