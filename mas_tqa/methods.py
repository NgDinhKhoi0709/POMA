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


def flat_prefix(qa: dict, k: int = KNN_K) -> str:
    return f"{_KNN_HEADER}\nBẢNG (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{knn_block(qa, k)}\n\n"


def knn_prompt(qa: dict, k: int = KNN_K) -> str:
    return flat_prefix(qa, k) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


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


def grid_prefix(qa: dict, k: int = KNN_K) -> str:
    return f"{_GRID_HEADER}\nBẢNG:\n{grid_str(qa['table_id'])}\n\n{knn_block(qa, k)}\n\n"


def evid_prompt(qa: dict, k: int = KNN_K) -> str:
    return grid_prefix(qa, k) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


def _parse_evid(text: str) -> tuple[str, list[str]]:
    obj = parse_json(text) or {}
    ev = obj.get("evidence") or []
    if "final_answer" in obj:
        ans = "Null" if obj["final_answer"] is None else str(obj["final_answer"]).strip()
    else:
        ans = final_answer(text)
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

    MemXam = memory cùng bảng + 2 solver dị thể + agent kiểm tra + đối chất 1 vòng; không hội tụ thì
    bỏ phiếu {A2, B2, C} (C là phiếu độc lập họ A, dùng chung với cascade3). `memxam_judge` = bản dùng judge.
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
        for name in ("cascade3", "cascade3b", "judge_only", "memxam", "memxam_judge"):
            out[name] = {"prediction": [pick], "trace": {**first, "route": r}, "usage": base}
        return out

    # Đối chứng không tương tác (cùng agent kiểm tra): phiếu thứ ba họ A / họ B, đa số trên đáp án hợp lệ.
    third = {}
    for name, prompt, parse in (("cascade3", knn_prompt, final_answer), ("cascade3b", evid_prompt, lambda t: _parse_evid(t)[0])):
        uc = Usage(); uc.add(base)
        tc, u = client.chat(prompt(qa), temperature=0.7, top_p=0.95); uc.add(u)
        c = parse(tc[0])
        third[name] = (c, u)
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
        for name in ("memxam", "memxam_judge"):
            out[name] = {"prediction": [a2], "trace": {**trace, "route": "converged"}, "usage": um}
        return out
    # Không hội tụ: bỏ phiếu với phiếu độc lập C (hoà thì lấy A2).
    c, uc = third["cascade3"]
    uv = Usage(); uv.add(um); uv.add(uc)
    pv = _majority(_pick_valid([a2, b2, c], q), q)
    out["memxam"] = {"prediction": [pv], "trace": {**trace, "C": c, "route": "vote"}, "usage": uv}
    # Ablation: bản dùng judge thay vì bỏ phiếu.
    uj2 = Usage(); uj2.add(um)
    idx, pm = _judge(client, qa, [(a2, a2_ev), (b2, b2_ev)], uj2)
    out["memxam_judge"] = {"prediction": [pm], "trace": {**trace, "route": "judge", "choice": idx}, "usage": uj2}
    return out


# ---------- v5: ba solver dị thể (thêm view Markdown-KV) ----------

@lru_cache(maxsize=None)
def kv_str(table_id: str) -> str:
    return render_table(tables()[table_id], "markdown_kv_clean")


_KV_HEADER = (
    "Bạn là chuyên gia đọc bảng. Bảng dưới đây được viết thành từng khối, mỗi khối là một hàng "
    "(\"## Hàng i\"), mỗi dòng trong khối có dạng \"Tên cột: giá trị\". CHỈ được dùng thông tin trong bảng.\n"
    + _GRID_HEADER.split("\n", 1)[1]
)


def kv_prefix(qa: dict, k: int = KNN_K) -> str:
    return f"{_KV_HEADER}\nBẢNG:\n{kv_str(qa['table_id'])}\n\n{knn_block(qa, k)}\n\n"


def kv_prompt(qa: dict, k: int = KNN_K) -> str:
    return kv_prefix(qa, k) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


def _rebut3_suffix(qa: dict, mine: tuple[str, list[str]], others: list[tuple[str, list[str]]]) -> str:
    lines = "\n".join(
        f"- Chuyên gia {i + 1}: {a}  (bằng chứng: {json.dumps(ev, ensure_ascii=False)})" for i, (a, ev) in enumerate(others)
    )
    return (
        "NHIỆM VỤ LÚC NÀY KHÁC: bạn và các chuyên gia khác đã trả lời câu hỏi dưới đây nhưng chưa thống nhất.\n"
        "Hãy đối chiếu lại mọi đáp án với bảng thật cẩn thận. Giữ đáp án của bạn nếu nó đúng; "
        "đổi sang đáp án khác nếu đáp án đó đúng hơn (kể cả chỉ đúng hơn về cách viết).\n"
        "Nếu các đáp án cùng nội dung, chọn cách viết ngắn gọn giống phong cách các đáp án mẫu ở trên; "
        "không thêm chủ ngữ hay diễn giải.\n"
        "ĐẦU RA: đúng một JSON {\"decision\": \"giu\" hoặc \"doi\", \"evidence\": [\"<ô bảng>\"], \"final_answer\": \"...\"}.\n\n"
        f"CÂU HỎI: {qa['question']}\n"
        f"ĐÁP ÁN CỦA BẠN: {mine[0]}\nBẰNG CHỨNG CỦA BẠN: {json.dumps(mine[1], ensure_ascii=False)}\n"
        f"ĐÁP ÁN CỦA CÁC CHUYÊN GIA KHÁC:\n{lines}\n"
    )


V5_K = KNN_K


def suite3(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """Ba solver dị thể + agent kiểm tra; không đồng thuận 3/3 → đối chất một vòng (mỗi solver thấy hai bên kia) → đa số."""
    q, k = qa["question"], V5_K
    prefixes = [flat_prefix(qa, k), grid_prefix(qa, k), kv_prefix(qa, k)]
    tail = f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {q}\nĐẦU RA: "
    usage, sols, out = Usage(), [], {}
    for name, pre in zip(("knn_fs", "evid", "kv"), prefixes):
        t, u = client.chat(pre + tail); usage.add(u)
        ans = _parse_evid(t[0]) if name != "knn_fs" else (final_answer(t[0]), [])
        sols.append(ans)
        out[f"{name}_k{k}"] = {"prediction": [ans[0]], "usage": u}
    answers = [a for a, _ in sols]
    ok = [x for x in answers if valid(x, q)]
    first = {"A": answers[0], "B": answers[1], "C": answers[2]}
    vote = _majority(_pick_valid(answers, q), q)
    out["vote3"] = {"prediction": [vote], "trace": first, "usage": usage}
    if len(ok) == 3 and len({key(x, q) for x in ok}) == 1:
        out["memxam3"] = {"prediction": [ok[0]], "trace": {**first, "route": "agree"}, "usage": usage}
        return out
    um = Usage(); um.add(usage)
    revised = []
    for i, pre in enumerate(prefixes):
        mine = sols[i] if valid(sols[i][0], q) else ("(không có)", [])
        others = [s for j, s in enumerate(sols) if j != i and valid(s[0], q)]
        t, u = client.chat(pre + _rebut3_suffix(qa, mine, others)); um.add(u)
        r = _parse_evid(t[0])
        revised.append(r[0] if valid(r[0], q) else sols[i][0])
    pick = _majority(_pick_valid(revised, q), q)
    out["memxam3"] = {"prediction": [pick], "trace": {**first, "revised": revised, "route": "debate"}, "usage": um}
    return out


# ---------- v6: agent có độ tin cậy từ nhiều mẫu (SC bên trong agent) ----------

V6_KA = 16  # ablation memory: k=16 tốt nhất cho solver A, không lợi cho B


def _top(answers: list[str], question: str) -> list[tuple[str, int]]:
    """Các đáp án hợp lệ theo số phiếu giảm dần (giữ thứ tự xuất hiện khi hoà)."""
    ok = [x for x in answers if valid(x, question)]
    votes = Counter(key(x, question) for x in ok)
    seen, out = set(), []
    for x in ok:
        kx = key(x, question)
        if kx not in seen:
            seen.add(kx)
            out.append((x, votes[kx]))
    return sorted(out, key=lambda t: -t[1])


def suite_sc(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """A (k=16) lấy 3 mẫu, B lấy 1 mẫu; đồng thuận ≥3/4 → dừng; tranh chấp → đối chất một vòng → bỏ phiếu."""
    q = qa["question"]
    fa, fb = flat_prefix(qa, V6_KA), grid_prefix(qa)
    tail = f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {q}\nĐẦU RA: "
    ta, ua = client.chat(fa + tail, n=3, temperature=0.7, top_p=0.95)
    tb, ub = client.chat(fb + tail)
    samples = [final_answer(t) for t in ta]
    b, b_ev = _parse_evid(tb[0])
    base = Usage(); base.add(ua); base.add(ub)
    pool = samples + [b]
    out = {
        "knn16_sc3": {"prediction": [_majority(_pick_valid(samples, q), q)], "trace": {"samples": samples}, "usage": ua},
        "vote4": {"prediction": [_majority(_pick_valid(pool, q), q)], "trace": {"samples": samples, "B": b}, "usage": base},
    }
    ranked = _top(pool, q)
    trace = {"samples": samples, "B": b}
    if not ranked or ranked[0][1] >= 3 or len(ranked) == 1:
        pick = ranked[0][0] if ranked else (pool[0] if normalize_text(pool[0]) else b)
        out["memxam_sc"] = {"prediction": [pick], "trace": {**trace, "route": "consensus"}, "usage": base}
        return out
    # Tranh chấp: A bảo vệ đáp án được họ A ủng hộ nhiều nhất, B bảo vệ đáp án của mình (hoặc ứng viên còn lại).
    a_top = _top(samples, q)
    a_pos = a_top[0][0] if a_top else ranked[0][0]
    b_pos = b if valid(b, q) and key(b, q) != key(a_pos, q) else next(
        (x for x, _ in ranked if key(x, q) != key(a_pos, q)), ranked[-1][0])
    um = Usage(); um.add(base)
    ra, u = client.chat(fa + _rebut_suffix(qa, a_pos, [], b_pos, b_ev)); um.add(u)
    rb, u = client.chat(fb + _rebut_suffix(qa, b_pos, b_ev, a_pos, [])); um.add(u)
    a2, b2 = _parse_evid(ra[0])[0], _parse_evid(rb[0])[0]
    a2 = a2 if valid(a2, q) else a_pos
    b2 = b2 if valid(b2, q) else b_pos
    final = _majority(_pick_valid([a2, b2] + pool, q), q)
    out["memxam_sc"] = {"prediction": [final], "trace": {**trace, "A_pos": a_pos, "B_pos": b_pos, "A2": a2, "B2": b2, "route": "debate"}, "usage": um}
    return out


SUITES = {"suite": suite, "suite3": suite3, "suite_sc": suite_sc}

METHODS = {
    "fs": single(fs_prompt),
    "fs_nothink": single(fs_prompt, thinking=False),
    "knn_fs": single(knn_prompt),
    "knn_fs_nothink": single(knn_prompt, thinking=False),
    "evid": single(evid_prompt),
    # Ablation kích thước memory (k câu train cùng bảng).
    "knn4_fs": single(lambda qa: knn_prompt(qa, 4)),
    "knn16_fs": single(lambda qa: knn_prompt(qa, 16)),
    "knn30_fs": single(lambda qa: knn_prompt(qa, 30)),
    "evid16": single(lambda qa: evid_prompt(qa, 16)),
    "knn_sc3": self_consistency(knn_prompt, 3),
    "fs_sc3": self_consistency(fs_prompt, 3),
}
