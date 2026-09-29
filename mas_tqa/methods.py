"""Các phương pháp: baseline (một lệnh gọi, self-consistency, cascade vote) và multi-agent MemXam.

Mọi vai dựa trên một solver dùng chung tiền tố prompt [hướng dẫn + bảng + memory] của solver đó,
chỉ khác phần đuôi (câu hỏi / nhiệm vụ), để vLLM tái dùng prefix cache.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache

import requests

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


_REUSE: dict[str, list[str]] = {}


def _reused_a_samples(qa_id: str) -> list[str] | None:
    """Mẫu A (kNN16, n=3) đọc từ file knn16_sc3 của lần chạy khác, chỉ định bằng MAS_REUSE_A_FILE."""
    path = os.environ.get("MAS_REUSE_A_FILE")
    sidecar = os.path.join(os.path.dirname(__file__), "..", "outputs", "mas_tqa", ".reuse_a_file")
    if not path and os.path.exists(sidecar):  # cho tiến trình đã khởi chạy trước khi đặt biến môi trường
        path = open(sidecar, encoding="utf-8").read().strip()
    if not path:
        return None
    if qa_id not in _REUSE and os.path.exists(path):  # file còn đang được ghi: đọc lại khi thiếu
        for line in open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                _REUSE[r["qa_id"]] = r["trace"]["samples"]
    return _REUSE.get(qa_id)


def suite_sc(client: VLLMClient, qa: dict, b_view: str = "grid") -> dict[str, dict]:
    """A (k=16) lấy 3 mẫu, B lấy 1 mẫu; đồng thuận ≥3/4 → dừng; tranh chấp → đối chất một vòng → bỏ phiếu.

    `b_view`: cách nhìn bảng của agent B ("grid" = v6, "kv" = Markdown-KV, v7).
    """
    q = qa["question"]
    fa, fb = flat_prefix(qa, V6_KA), (grid_prefix(qa) if b_view == "grid" else kv_prefix(qa))
    tail = f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {q}\nĐẦU RA: "
    reused = _reused_a_samples(qa["qa_id"])
    if reused is not None:  # dùng lại 3 mẫu A độc lập của lần chạy khác (cùng prompt), không gọi lại
        samples, ua = reused, Usage()
    else:
        ta, ua = client.chat(fa + tail, n=3, temperature=0.7, top_p=0.95)
        samples = [final_answer(t) for t in ta]
    tb, ub = client.chat(fb + tail)
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


def suite_sckv(client: VLLMClient, qa: dict) -> dict[str, dict]:
    out = suite_sc(client, qa, b_view="kv")
    return {"knn16_sc3": out["knn16_sc3"], "vote4kv": out["vote4"], "memxam_sckv": out["memxam_sc"]}


SUITES = {"suite": suite, "suite3": suite3, "suite_sc": suite_sc, "suite_sckv": suite_sckv}

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


# ---------- Parse-Critic: ghi chú cấu trúc bảng do LLM tự nhận xét cách parse HTML ----------

def knn_pnotes_prompt(qa: dict, k: int = KNN_K) -> str:
    from .parse_critic import notes_for

    notes = notes_for(qa["table_id"])
    block = f"GHI CHÚ CẤU TRÚC BẢNG (do agent kiểm tra parse viết):\n{notes}\n\n" if notes else ""
    return (
        f"{_KNN_HEADER}\nBẢNG (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{block}{knn_block(qa, k)}\n\n"
        f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "
    )


METHODS["knn_fs_pnotes"] = single(knn_pnotes_prompt)


# ---------- Memory-Curator: agent chọn ví dụ train cùng bảng thay cho Jaccard ----------

CURATE_K = 8


def curate(client: VLLMClient, qa: dict) -> tuple[list[dict], Usage]:
    from .data import train_by_table

    pool = [r for r in train_by_table().get(qa["table_id"], []) if r["qa_id"] != qa["qa_id"]][:40]
    if len(pool) <= CURATE_K:
        return pool, Usage()
    listing = "\n".join(f"[{i}] {r['question']} → {r['answer']}" for i, r in enumerate(pool))
    prompt = (
        "Bạn là agent quản lý bộ nhớ cho một hệ hỏi–đáp trên bảng. Dưới đây là các câu hỏi đã được trả lời đúng "
        "trên cùng một bảng. Hãy chọn tối đa 8 ví dụ hữu ích nhất để trả lời CÂU HỎI MỚI: ưu tiên ví dụ cùng kiểu "
        "câu hỏi, cùng kiểu đáp án (số, tên, Có/Không, danh sách...) hoặc cùng hàng/cột liên quan.\n"
        "ĐẦU RA: đúng một JSON {\"chon\": [<các số thứ tự>]}.\n\n"
        f"CÁC VÍ DỤ:\n{listing}\n\nCÂU HỎI MỚI: {qa['question']}\n"
    )
    t, u = client.chat(prompt, thinking=False, max_tokens=200)
    obj = parse_json(t[0]) or {}
    idx = [i for i in obj.get("chon") or [] if isinstance(i, int) and 0 <= i < len(pool)]
    picked = [pool[i] for i in dict.fromkeys(idx)][:CURATE_K]
    if not picked:  # agent lỗi → quay về truy hồi Jaccard
        picked = retrieve_same_table(qa, CURATE_K)
    return picked, u


def curated_fs(client: VLLMClient, qa: dict) -> dict:
    demos, u0 = curate(client, qa)
    lines = [f'CÂU HỎI: {d["question"]}\nĐẦU RA: {{"final_answer": "{d["answer"]}"}}' for d in demos]
    block = (
        "CÁC CÂU HỎI KHÁC ĐÃ ĐƯỢC TRẢ LỜI ĐÚNG TRÊN CHÍNH BẢNG NÀY "
        "(tham khảo cách viết đáp án ngắn gọn, đúng định dạng):\n\n" + "\n\n".join(lines)
    )
    prompt = (
        f"{_KNN_HEADER}\nBẢNG (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{block}\n\n"
        f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "
    )
    texts, u1 = client.chat(prompt)
    usage = Usage(); usage.add(u0); usage.add(u1)
    return {"prediction": [final_answer(texts[0])], "trace": {"demos": [d["qa_id"] for d in demos]}, "usage": usage}


METHODS["curated_fs"] = curated_fs
METHODS["kv_fs"] = single(lambda qa: kv_prompt(qa))
METHODS["kv16_fs"] = single(lambda qa: kv_prompt(qa, 16))


# ---------- Prompt tiếng Anh (dịch sát kNN-FS; bảng, câu hỏi, đáp án mẫu giữ nguyên tiếng Việt) ----------

_KNN_HEADER_EN = (
    "You are a table question answering system.\n"
    "The table is given as a Flatten V1 string in TABLE_STR.\n"
    "Use ONLY the information in TABLE_STR to answer.\n\n"
    "TABLE_STR FORMAT NOTES (FLATTEN V1):\n"
    "- Each line has the form: row_header|column_header|value.\n"
    "- Row and column headers always carry the suffix '<header>'.\n"
    "- The data cell value is the third component of each line.\n\n"
    "OUTPUT (REQUIRED): a single valid JSON object (it may be wrapped in a ```json ... ``` block).\n"
    "Do not add any text outside the JSON (or outside the ```json block).\n"
    "Schema:\n"
    '  {"final_answer": "<one short value; or the string Null if the table does not contain enough information>"}\n'
    "Do not output reasoning. Do not output internal thoughts.\n"
    "Never use <think> or </think> tags.\n"
    "final_answer rules (short, suited to exact-match evaluation):\n"
    "- Base it only on TABLE_STR; do not make things up; do not repeat the question.\n"
    "- One short value (number, name, Có/Không, ...); use Null (string) if it cannot be answered.\n"
    "- No Markdown in final_answer.\n"
    "- Write final_answer in Vietnamese, in exactly the same style as the example answers below.\n"
    'One-line example: {"final_answer":"42"}\n'
)


def knn_prompt_en(qa: dict, k: int = KNN_K) -> str:
    demos = retrieve_same_table(qa, k)
    lines = [f'QUESTION: {d["question"]}\nOUTPUT: {{"final_answer": "{d["answer"]}"}}' for d in demos]
    block = (
        "OTHER QUESTIONS ALREADY ANSWERED CORRECTLY ON THIS SAME TABLE "
        "(follow how their answers are written: short, same format):\n\n" + "\n\n".join(lines)
    )
    return (
        f"{_KNN_HEADER_EN}\nTABLE (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{block}\n\n"
        f"NOW ANSWER THE FOLLOWING QUESTION.\nQUESTION: {qa['question']}\nOUTPUT: "
    )


METHODS["knn16_fs_en"] = single(lambda qa: knn_prompt_en(qa, 16))


# ---------- Sửa ghi chú định dạng: Flatten V1 thực tế là lưới (dòng đầu = tên cột), không phải bộ ba ----------

_FLAT_NOTES_FIXED_VI = (
    "GHI CHÚ ĐỊNH DẠNG TABLE_STR:\n"
    "- Dòng đầu tiên là tên các cột (mỗi tên có hậu tố '<header>'); mỗi dòng tiếp theo là một hàng của bảng.\n"
    "- Các ô trong một dòng cách nhau bởi dấu |, theo đúng thứ tự cột của dòng đầu; ô trống vẫn được giữ chỗ.\n"
    "- Ô đầu của một hàng có hậu tố '<header>' là tiêu đề của hàng đó.\n"
)
_KNN_HEADER_FIXED = _KNN_HEADER.replace(_flatten_v1_notes_vi(), _FLAT_NOTES_FIXED_VI)
assert _KNN_HEADER_FIXED != _KNN_HEADER


def knn_prompt_fixed(qa: dict, k: int = KNN_K) -> str:
    return (
        f"{_KNN_HEADER_FIXED}\nBẢNG (TABLE_STR):\n{table_str(qa['table_id'])}\n\n{knn_block(qa, k)}\n\n"
        f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "
    )


METHODS["knn16_fs_fix"] = single(lambda qa: knn_prompt_fixed(qa, 16))


# ---------- v8: agent C viết code pandas; tầng đầu dùng chung, xuất nhiều luật dừng từ cùng lệnh gọi ----------

_CODE_HEADER = (
    "Bạn là chuyên gia phân tích bảng bằng Python. Bảng đã được nạp sẵn vào biến `df` (pandas DataFrame): "
    "dòng \"cột\" dưới đây là tên cột, mỗi dòng đánh số là một hàng (chỉ số 0, 1, ...). Mọi ô là chuỗi (str); "
    "số có thể dùng dấu chấm phân cách hàng nghìn và dấu phẩy thập phân kiểu Việt Nam, có thể kèm chú thích như [10]; "
    "ô rỗng là ''. Nếu tên cột trùng nhau, cột sau có hậu tố \" (2)\".\n"
    "Viết code Python dùng `df` để tìm đáp án và gán vào biến `answer` (chuỗi), viết đúng phong cách các đáp án mẫu: "
    "ngắn gọn, số thập phân dùng dấu phẩy, liệt kê cách nhau bởi dấu phẩy, câu hỏi Có/Không thì trả lời như đáp án mẫu. "
    "Câu hỏi chỉ cần tra một ô thì vẫn viết code tra ô đó. Được import: math, re, datetime, statistics, pandas, numpy, "
    "collections, itertools, unicodedata. Không đọc/ghi file. Bảng không đủ thông tin thì gán answer = \"Null\".\n"
    "ĐẦU RA: chỉ một khối ```python ... ```.\n"
)


def code_prompt(qa: dict, k: int = KNN_K) -> str:
    from .code_agent import df_view

    demos = "\n".join(f"CÂU HỎI: {d['question']}\nĐÁP ÁN: {d['answer']}" for d in retrieve_same_table(qa, k))
    return (
        f"{_CODE_HEADER}\nBẢNG (df):\n{df_view(qa['table_id'])}\n\n"
        f"CÁC CÂU HỎI KHÁC ĐÃ ĐƯỢC TRẢ LỜI ĐÚNG TRÊN CHÍNH BẢNG NÀY (tham khảo cách viết đáp án):\n{demos}\n\n"
        f"BÂY GIỜ VIẾT CODE CHO CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\n"
    )


def code_agent(client: VLLMClient, qa: dict) -> tuple[str, dict, Usage]:
    """Agent C: sinh code rồi chạy trong sandbox; đáp án rỗng nếu code lỗi (validator sẽ loại)."""
    from .code_agent import extract_code, run_code, table_rows

    t, u = client.chat(code_prompt(qa))
    code = extract_code(strip_think(t[0]))
    ans, err = run_code(table_rows(qa["table_id"]), code)
    return ans or "", {"code": code[-1500:], "error": err}, u


def _stop(ranked: list[tuple[str, int]], need: int) -> bool:
    return not ranked or len(ranked) == 1 or ranked[0][1] >= need


def suite_v8(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """A (k=16, 3 mẫu) + B (Markdown-KV, bằng chứng) + C (code). Đối chất chạy khi 5 đáp án chưa đồng nhất,
    rồi mọi luật dừng được tính trên cùng các lệnh gọi (so sánh ghép cặp trong một lần chạy):

    - memxam_sckv: luật v7 (≥3/4 trên A×3+B, bỏ qua C).
    - memxam_veto: như v7 nhưng A 3/3 mà B hợp lệ và bất đồng → vẫn đối chất.
    - memxam_c5: bỏ phiếu 5 (A×3+B+C), dừng khi ≥4/5; tranh chấp → đối chất → bỏ phiếu trên [A2, B2]+5.
    """
    q = qa["question"]
    fa, fb = flat_prefix(qa, V6_KA), kv_prefix(qa)
    tail = f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {q}\nĐẦU RA: "
    ta, ua = client.chat(fa + tail, n=3, temperature=0.7, top_p=0.95)
    samples = [final_answer(t) for t in ta]
    tb, ub = client.chat(fb + tail)
    b, b_ev = _parse_evid(tb[0])
    if os.environ.get("MAS_V8_NO_C"):  # luật được chọn không dùng C: bỏ lệnh gọi C (memxam_veto/sckv không đổi)
        c, c_info, uc = "", {"code": "", "error": "tắt"}, Usage()
    else:
        c, c_info, uc = code_agent(client, qa)
    base = Usage(); base.add(ua); base.add(ub)
    pool4, pool5 = samples + [b], samples + [b, c]
    r4, r5 = _top(pool4, q), _top(pool5, q)
    trace = {"samples": samples, "B": b, "B_ev": b_ev[:20], "C": c, **{f"C_{k}": v for k, v in c_info.items()}}
    full = Usage(); full.add(base); full.add(uc)
    out = {
        "knn16_sc3": {"prediction": [_majority(_pick_valid(samples, q), q)], "trace": {"samples": samples}, "usage": ua},
        "vote4kv": {"prediction": [_majority(_pick_valid(pool4, q), q)], "trace": trace, "usage": base},
        "code_c": {"prediction": [c or "Null"], "trace": c_info, "usage": uc},
        "vote5": {"prediction": [_majority(_pick_valid(pool5, q), q)], "trace": trace, "usage": full},
    }
    top4 = r4[0][0] if r4 else (pool4[0] if normalize_text(pool4[0]) else b)
    top5 = r5[0][0] if r5 else top4
    if len(r5) <= 1:  # 5 đáp án hợp lệ đồng nhất: mọi luật dừng
        for name, pick, u in (("memxam_sckv", top4, base), ("memxam_veto", top4, base), ("memxam_c5", top5, full)):
            out[name] = {"prediction": [pick], "trace": {**trace, "route": "consensus"}, "usage": u}
        return out
    # Đối chất chuẩn: A bảo vệ đáp án mạnh nhất của họ A; B bảo vệ đáp án của mình, nếu trùng A thì ứng viên
    # mạnh nhất còn lại (ưu tiên pool v7, rồi tới C).
    a_top = _top(samples, q)
    a_pos = a_top[0][0] if a_top else (r4 or r5)[0][0]
    others = [x for x, _ in r4 + r5 if key(x, q) != key(a_pos, q)]
    b_pos = b if valid(b, q) and key(b, q) != key(a_pos, q) else (others[0] if others else a_pos)
    ud = Usage()
    ra, u = client.chat(fa + _rebut_suffix(qa, a_pos, [], b_pos, b_ev)); ud.add(u)
    rb, u = client.chat(fb + _rebut_suffix(qa, b_pos, b_ev, a_pos, [])); ud.add(u)
    a2, b2 = _parse_evid(ra[0])[0], _parse_evid(rb[0])[0]
    a2 = a2 if valid(a2, q) else a_pos
    b2 = b2 if valid(b2, q) else b_pos
    dtrace = {**trace, "A_pos": a_pos, "B_pos": b_pos, "A2": a2, "B2": b2}

    def with_debate(u0: Usage) -> Usage:
        u1 = Usage(); u1.add(u0); u1.add(ud)
        return u1

    b_dissents = valid(b, q) and bool(r4) and key(b, q) != key(r4[0][0], q)
    rules = {
        "memxam_sckv": (_stop(r4, 3), top4, pool4, base),
        "memxam_veto": (_stop(r4, 3) and not (r4 and r4[0][1] >= 3 and b_dissents), top4, pool4, base),
        "memxam_c5": (_stop(r5, 4), top5, pool5, full),
    }
    for name, (stop, top, pool, u0) in rules.items():
        if stop:
            out[name] = {"prediction": [top], "trace": {**dtrace, "route": "consensus"}, "usage": u0}
        else:
            final = _majority(_pick_valid([a2, b2] + pool, q), q)
            out[name] = {"prediction": [final], "trace": {**dtrace, "route": "debate"}, "usage": with_debate(u0)}
    return out


SUITES["suite_v8"] = suite_v8


# ---------- Agent M (toán) + agent V (kiểm tra): chỉ chạy trên câu router gán "compute" ----------

def math_mv(client: VLLMClient, qa: dict) -> dict:
    from .math_agent import prefix, solve

    res = solve(client, qa, prefix(qa), kv_str(qa["table_id"]))
    usage = res.pop("usage")
    return {"prediction": [res["V"] or res["M"] or "Null"], "trace": res, "usage": usage}


METHODS["math_mv"] = math_mv


# ---------- Bỏ phiếu bằng LLM: điểm xác suất cho từng ứng viên (mas_tqa/scorer.py) ----------

def _llm_score(client: VLLMClient, qa: dict) -> dict:
    from .scorer import llm_score

    return llm_score(client, qa)


METHODS["llm_score"] = _llm_score


# ---------- v9: A và B trả thêm lý do; agent chấm điểm (tổng = 1) thấy đáp án kèm lý do ----------

_REASON_TAIL = (
    "BÂY GIỜ TRẢ LỜI CÂU HỎI SAU. Trong JSON đầu ra, thêm trường \"reason\" đặt trước \"final_answer\": "
    "tối đa 2 câu, nêu dùng hàng/cột/ô nào và suy ra đáp án thế nào.\nCÂU HỎI: {q}\nĐẦU RA: "
)


def _reason(text: str) -> str:
    obj = parse_json(text) or {}
    return str(obj.get("reason") or "").strip()[:300]


def suite_v9(client: VLLMClient, qa: dict) -> dict[str, dict]:
    """Tầng đầu như v7 (A: Flatten V1 + 16 câu mẫu, 3 mẫu; B: Markdown-KV) nhưng mỗi đáp án kèm lý do.
    Luật v7 (đồng thuận ≥ 3/4, nếu không thì đối chất + bỏ phiếu) cho memview_r. Câu còn ≥ 2 ứng viên:
    agent chấm điểm hai view, mỗi view chấm hai lần (không lý do / có lý do) để so ghép cặp."""
    from .scorer import candidates, prefix_flat, prefix_kv, score

    q = qa["question"]
    fa, fb = flat_prefix(qa, V6_KA), kv_prefix(qa)
    tail = _REASON_TAIL.format(q=q)
    ta, ua = client.chat(fa + tail, n=3, temperature=0.7, top_p=0.95)
    samples, a_reasons = [final_answer(t) for t in ta], [_reason(t) for t in ta]
    try:
        tb, ub = client.chat(fb + tail)
    except requests.HTTPError:  # bảng Markdown-KV vượt ngữ cảnh: chỉ dùng kết quả của agent A
        a_only = _majority(_pick_valid(samples, q), q)
        tr = {"samples": samples, "A_reasons": a_reasons, "route": "a_only", "scored": False}
        return {name: {"prediction": [a_only], "trace": tr, "usage": ua}
                for name in ("knn16_sc3r", "vote4r", "memview_r", "score_r")}
    b, b_ev = _parse_evid(tb[0])
    b_reason = _reason(tb[0])
    base = Usage(); base.add(ua); base.add(ub)
    pool = samples + [b]
    trace = {"samples": samples, "A_reasons": a_reasons, "B": b, "B_ev": b_ev[:20], "B_reason": b_reason}
    out = {"knn16_sc3r": {"prediction": [_majority(_pick_valid(samples, q), q)], "trace": {"samples": samples}, "usage": ua},
           "vote4r": {"prediction": [_majority(_pick_valid(pool, q), q)], "trace": trace, "usage": base}}
    ranked = _top(pool, q)
    um = Usage(); um.add(base)
    if not ranked or ranked[0][1] >= 3 or len(ranked) == 1:
        final = ranked[0][0] if ranked else (pool[0] if normalize_text(pool[0]) else b)
        trace["route"] = "consensus"
    else:
        a_top = _top(samples, q)
        a_pos = a_top[0][0] if a_top else ranked[0][0]
        b_pos = b if valid(b, q) and key(b, q) != key(a_pos, q) else next(
            (x for x, _ in ranked if key(x, q) != key(a_pos, q)), ranked[-1][0])
        ra, u = client.chat(fa + _rebut_suffix(qa, a_pos, [], b_pos, b_ev)); um.add(u)
        rb, u = client.chat(fb + _rebut_suffix(qa, b_pos, b_ev, a_pos, [])); um.add(u)
        a2, b2 = _parse_evid(ra[0])[0], _parse_evid(rb[0])[0]
        a2 = a2 if valid(a2, q) else a_pos
        b2 = b2 if valid(b2, q) else b_pos
        final = _majority(_pick_valid([a2, b2] + pool, q), q)
        trace.update({"A_pos": a_pos, "B_pos": b_pos, "A2": a2, "B2": b2, "route": "debate"})
    out["memview_r"] = {"prediction": [final], "trace": trace, "usage": um}
    cands, votes = candidates(trace, q)
    trace["cands"], trace["votes"] = cands, votes
    if len(cands) < 2:
        out["score_r"] = {"prediction": [final], "trace": {**trace, "scored": False}, "usage": um}
        return out
    notes = []
    for c in cands:
        why = [r for s, r in zip(samples, a_reasons) if r and valid(s, q) and key(s, q) == key(c, q)]
        if valid(b, q) and key(b, q) == key(c, q) and (b_reason or b_ev):
            why.append((b_reason + (" Bằng chứng: " + "; ".join(b_ev[:5]) if b_ev else "")).strip())
        notes.append(" | ".join(why)[:600])
    us = Usage(); us.add(um)
    ps = {}
    for view, pre in (("flat", prefix_flat(qa)), ("kv", prefix_kv(qa))):
        for tag, nt in (("plain", None), ("reason", notes)):
            ps[f"p_{view}_{tag}"], u = score(client, qa, pre, cands, nt); us.add(u)
    mean = [(a + bb) / 2 for a, bb in zip(ps["p_flat_reason"], ps["p_kv_reason"])]
    trace.update({"notes": notes, **ps, "scored": True})
    out["score_r"] = {"prediction": [cands[max(range(len(cands)), key=mean.__getitem__)]], "trace": trace, "usage": us}
    return out


SUITES["suite_v9"] = suite_v9


# ---------- Agent C phát hiện Null cho câu giải thích; ghi chú câu giải thích cho A/B (mas_tqa/null_agent.py) ----------

def _null_detect(client: VLLMClient, qa: dict) -> dict:
    from .math_agent import prefix
    from .null_agent import detect

    answerable, info, u = detect(client, qa, prefix(qa))
    return {"prediction": ["ANSWERABLE" if answerable else "Null"], "trace": {"answerable": answerable, **info}, "usage": u}


def _explain_single(prefix_fn, note: bool):
    """Một lần gọi A (Flatten, 16 câu mẫu) hoặc B (Markdown-KV); có/không ghi chú câu giải thích ở đuôi prompt."""
    from .null_agent import EXPLAIN_NOTE

    def run(client: VLLMClient, qa: dict) -> dict:
        tail = (EXPLAIN_NOTE if note else "") + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "
        t, u = client.chat(prefix_fn(qa) + tail, temperature=0.6, top_p=0.95)
        return {"prediction": [_parse_evid(t[0])[0] if prefix_fn is kv_prefix else final_answer(t[0])], "raw": t[0][-300:], "usage": u}

    return run


METHODS["null_detect"] = _null_detect
METHODS["a_explain_plain"] = _explain_single(lambda qa: flat_prefix(qa, V6_KA), False)
METHODS["a_explain_note"] = _explain_single(lambda qa: flat_prefix(qa, V6_KA), True)
METHODS["b_explain_plain"] = _explain_single(kv_prefix, False)
METHODS["b_explain_note"] = _explain_single(kv_prefix, True)


# ---------- Prompt theo Best Practices của Qwen3-8B (mas_tqa/prompts_qwen.py) ----------

def _qwen_agent(which: str, n: int):
    """Agent A (Flatten V1, 16 câu mẫu) hoặc B (Markdown-KV, 8 câu mẫu, bằng chứng) với system prompt mới và tham số
    lấy mẫu Qwen3 cho thinking; n mẫu thì lấy đáp án đa số."""
    from .prompts_qwen import QWEN_THINKING, messages_a, messages_b

    def run(client: VLLMClient, qa: dict) -> dict:
        msgs = messages_a(qa) if which == "A" else messages_b(qa)
        t, u = client.chat(msgs, n=n, **QWEN_THINKING)
        answers = [(_parse_evid(x)[0] if which == "B" else final_answer(x)) for x in t]
        pred = _majority(_pick_valid(answers, qa["question"]), qa["question"]) if n > 1 else answers[0]
        return {"prediction": [pred], "trace": {"samples": answers, "reasons": [_reason(x) for x in t]}, "usage": u}

    return run


METHODS["a_qwen"] = _qwen_agent("A", 1)
METHODS["a_qwen_sc3"] = _qwen_agent("A", 3)
METHODS["b_qwen"] = _qwen_agent("B", 1)
