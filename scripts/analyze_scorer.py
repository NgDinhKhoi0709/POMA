"""Bỏ phiếu bằng LLM (điểm xác suất, tổng = 1): so các luật ghép với luật MemView trên cùng trace.

python scripts/analyze_scorer.py --split dev --base memxam_sckv.runv8dev --score llm_score.runs1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.io import load_qas_records  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402


def argmax(xs: list[float]) -> int:
    return max(range(len(xs)), key=xs.__getitem__)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--base", default="memxam_sckv.runv8dev")
    ap.add_argument("--score", default="llm_score.runs1")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"dataset/qas_{args.split}.json")}
    load = lambda p: {json.loads(x)["qa_id"]: json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()}  # noqa: E731
    base = load(ROOT / f"outputs/mas_tqa/qas_{args.split}/{args.base}.jsonl")
    sc = {i: r for i, r in load(ROOT / f"outputs/mas_tqa/qas_{args.split}_multi/{args.score}.jsonl").items()
          if not r["trace"].get("skipped")}
    ids = sorted(base)
    ok = lambda a, i: correct(a, qas[i]) if a else 0  # noqa: E731

    def pick(i: str, how: str, tau: float = 0.0) -> str:
        b = base[i]["prediction"][0]
        if i not in sc:
            return b
        t = sc[i]["trace"]
        c, v = t["cands"], t["votes"]
        mean = [(a + bb) / 2 for a, bb in zip(t["p_flat"], t["p_kv"])]
        if how == "llm":
            return c[argmax(mean)]
        if how == "flat":
            return c[argmax(t["p_flat"])]
        if how == "kv":
            return c[argmax(t["p_kv"])]
        if how == "vote+llm":
            share = [x / sum(v) for x in v]
            return c[argmax([s + m for s, m in zip(share, mean)])]
        if how == "tau":
            return c[argmax(mean)] if max(mean) >= tau else b
        raise ValueError(how)

    rules = {"MemView (bỏ phiếu + đối chất)": lambda i: base[i]["prediction"][0],
             "LLM chấm (trung bình 2 view)": lambda i: pick(i, "llm"),
             "LLM chấm, chỉ view Flatten": lambda i: pick(i, "flat"),
             "LLM chấm, chỉ view KV": lambda i: pick(i, "kv"),
             "phiếu + điểm LLM": lambda i: pick(i, "vote+llm")}
    for tau in (0.6, 0.7, 0.8, 0.9):
        rules[f"LLM chỉ khi điểm cao nhất ≥ {tau}"] = (lambda t: lambda i: pick(i, "tau", t))(tau)

    ref = {i: ok(base[i]["prediction"][0], i) for i in ids}
    orc = sum(any(ok(c, i) for c in sc[i]["trace"]["cands"]) for i in sc)
    print(f"{args.split}: {len(ids)} câu; {len(sc)} câu có ≥ 2 ứng viên; oracle trong nhóm đó {orc}, "
          f"MemView đúng {sum(ref[i] for i in sc)}\n")
    print(f"{'luật':<34}{'EM':>7}   Δ [95% CI]            sửa / hỏng")
    for name, f in rules.items():
        v = {i: ok(f(i), i) for i in ids}
        ci = paired_bootstrap_ci([v[i] for i in ids], [ref[i] for i in ids], samples=5000)
        print(f"{name:<34}{100 * sum(v.values()) / len(ids):7.2f}   {100 * ci['point_estimate']:+.2f} "
              f"[{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]   {sum(v[i] and not ref[i] for i in ids)} / "
              f"{sum(ref[i] and not v[i] for i in ids)}")

    # hiệu chuẩn: độ chính xác của lựa chọn LLM theo điểm cao nhất
    print("\nHiệu chuẩn (lựa chọn của LLM, trên câu có ≥ 2 ứng viên):")
    for lo, hi in ((0, .5), (.5, .7), (.7, .9), (.9, 1.01)):
        s = [i for i in sc if lo <= max((a + b) / 2 for a, b in zip(sc[i]["trace"]["p_flat"], sc[i]["trace"]["p_kv"])) < hi]
        if s:
            acc = sum(ok(pick(i, "llm"), i) for i in s) / len(s)
            print(f"  điểm [{lo}, {min(hi, 1)}): {len(s):3d} câu, LLM đúng {100 * acc:.1f}%, MemView đúng {100 * sum(ref[i] for i in s) / len(s):.1f}%")


if __name__ == "__main__":
    main()
