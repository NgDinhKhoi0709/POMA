"""Phân tích agent M (toán) + V (kiểm tra) và các cách ghép vào MemXam-SC-KV.

Mọi so sánh ghép cặp trên cùng tập câu; đáp án đều qua agent định dạng (mas_tqa/style.py) như pipeline cuối.
Chọn luật trên dev, rồi áp đúng một lần lên test.

python scripts/analyze_math.py --split dev --math math_mv.runor1 --base memxam_sckv.runv8dev
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.io import load_qas_records  # noqa: E402
from mas_tqa.methods import _majority, _pick_valid, _top, key  # noqa: E402
from mas_tqa.style import harmonize  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402


def math_answer(t: dict, need_verified: bool) -> str:
    """Đáp án của nhánh toán: V xác nhận → M; V sửa → bản sửa; còn lại rỗng (hoặc M nếu không cần V)."""
    if not t["M"]:
        return ""
    if t["V_ok"] is True:
        return t["M"]
    if t["V_ok"] is False:
        return t["V"]
    return "" if need_verified else t["M"]


def rules(r: dict, m: dict | None, q: str) -> dict[str, str]:
    base = r["prediction"][0]
    t = r["trace"]
    pool = list(t["samples"]) + [t["B"]] + [t[k] for k in ("A2", "B2") if t.get(k)]
    out = {"MemXam": base}
    if m is None:
        return {k: base for k in ("MemXam", "thay_nếu_V_xác_nhận", "thay_theo_M+V", "thay_nếu_V_ok_và_grounded",
                                  "phiếu_w1", "phiếu_w2", "trọng_tài_khi_tranh_chấp", "thay_nếu_trùng_ứng_viên")}
    mt = m["trace"]
    verified = mt["M"] if mt["V_ok"] is True else ""
    mv = math_answer(mt, need_verified=True)
    out["thay_nếu_V_xác_nhận"] = verified or base
    out["thay_theo_M+V"] = mv or base
    out["thay_nếu_V_ok_và_grounded"] = verified if verified and mt["M_grounded"] else base
    for w in (1, 2):
        out[f"phiếu_w{w}"] = _majority(_pick_valid([base] + pool + [mv] * w if mv else [base] + pool, q), q)
    disputed = len(_top(pool, q)) > 1
    out["trọng_tài_khi_tranh_chấp"] = mv if (mv and disputed) else base
    in_pool = mv and any(key(mv, q) == key(x, q) for x in pool)
    out["thay_nếu_trùng_ứng_viên"] = mv if in_pool else base
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--math", default="math_mv.runor1")
    ap.add_argument("--base", default="memxam_sckv.runv8dev")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"dataset/qas_{args.split}.json")}
    load = lambda p: {json.loads(x)["qa_id"]: json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()}  # noqa: E731
    base = load(ROOT / f"outputs/mas_tqa/qas_{args.split}/{args.base}.jsonl")
    math = load(ROOT / f"outputs/mas_tqa/qas_{args.split}_compute/{args.math}.jsonl")
    ok = lambda a, i: correct(harmonize(a, qas[i]), qas[i]) if a else 0  # noqa: E731
    ids = sorted(base)
    cmp_ids = [i for i in ids if i in math]
    print(f"{args.split}: {len(ids)} câu, {len(cmp_ids)} câu gán 'compute' có kết quả M+V\n")

    # --- độ chính xác có điều kiện ---
    kinds = Counter(str(math[i]["trace"]["M_plan"].get("type", "?")) if math[i]["trace"]["M"] or math[i]["trace"]["M_err"] == "lookup"
                    else f"lỗi: {math[i]['trace']['M_err'][:20]}" for i in cmp_ids)
    print("Loại M chọn:", dict(kinds))
    act = [i for i in cmp_ids if math[i]["trace"]["M"]]
    mx = {i: ok(base[i]["prediction"][0], i) for i in cmp_ids}
    m_ok = {i: ok(math[i]["trace"]["M"], i) for i in act}
    print(f"M trả lời {len(act)}/{len(cmp_ids)} câu; M đúng {sum(m_ok.values())} ({100 * sum(m_ok.values()) / max(1, len(act)):.1f}%), "
          f"MemXam đúng trên cùng câu {sum(mx[i] for i in act)}")
    print(f"  khi MemXam sai ({sum(1 - mx[i] for i in act)} câu): M đúng {sum(m_ok[i] for i in act if not mx[i])}")
    print(f"  khi MemXam đúng ({sum(mx[i] for i in act)} câu): M sai {sum(1 - m_ok[i] for i in act if mx[i])}")
    for v in (True, False, None):
        s = [i for i in act if math[i]["trace"]["V_ok"] is v]
        extra = ""
        if v is False:
            fixed = [i for i in s if math[i]["trace"]["V"]]
            extra = f"; V đưa bản sửa {len(fixed)} câu, bản sửa đúng {sum(ok(math[i]['trace']['V'], i) for i in fixed)}"
        print(f"  V_ok={v!s:<5}: {len(s):3d} câu, M đúng {sum(m_ok[i] for i in s)}, MemXam đúng {sum(mx[i] for i in s)}{extra}")
    g = [i for i in act if not math[i]["trace"]["M_grounded"]]
    print(f"  ô trích không có trong bảng: {len(g)} câu, M đúng {sum(m_ok[i] for i in g)}")

    # --- luật ghép ---
    res = {i: rules(base[i], math.get(i), qas[i]["question"]) for i in ids}
    names = list(next(iter(res.values())))
    ref = {i: ok(res[i]["MemXam"], i) for i in ids}
    print(f"\n{'luật':<28}{'EM':>7}   Δ [95% CI]   sửa / hỏng")
    for n in names:
        v = {i: ok(res[i][n], i) for i in ids}
        ci = paired_bootstrap_ci([v[i] for i in ids], [ref[i] for i in ids], samples=5000)
        fix = sum(v[i] and not ref[i] for i in ids)
        brk = sum(ref[i] and not v[i] for i in ids)
        print(f"{n:<28}{100 * sum(v.values()) / len(ids):7.2f}   {100 * ci['point_estimate']:+.2f} "
              f"[{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]   {fix} / {brk}")


if __name__ == "__main__":
    main()
