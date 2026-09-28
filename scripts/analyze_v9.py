"""v9: A/B trả kèm lý do; LLM validator chấm điểm (tổng = 1). So các luật trên cùng các lần gọi.

Luật "A = 1 phiếu": 3 mẫu A trùng nhau chỉ tính là một ý kiến; dừng sớm chỉ khi A nhất trí và B đồng ý,
còn lại để LLM validator chọn trong các ứng viên. Chọn luật trên dev, áp đúng một lần lên test.

python scripts/analyze_v9.py --split dev --run v9dev
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
from mas_tqa.methods import key, valid  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402


def argmax(xs: list[float]) -> int:
    return max(range(len(xs)), key=xs.__getitem__)


def decide(rec: dict, q: str, rule: str) -> str:
    """rec = bản ghi score_r (trace đầy đủ); trả đáp án theo luật."""
    t = rec["trace"]
    base = rec["prediction"][0] if not t.get("scored") else None
    v7 = t.get("_v7")
    s, b = t["samples"], t["B"]
    a_keys = {key(x, q) for x in s if valid(x, q)}
    a_unan = len(a_keys) == 1
    b_agree = (not valid(b, q)) or (a_unan and key(b, q) in a_keys)
    if not t.get("scored"):
        return v7 or base
    c = t["cands"]
    p = {tag: [(x + y) / 2 for x, y in zip(t[f"p_flat_{tag}"], t[f"p_kv_{tag}"])] for tag in ("plain", "reason")}
    if rule == "v7":
        return v7
    if rule.startswith("llm_all_"):  # LLM chọn ở mọi câu có ≥ 2 ứng viên
        return c[argmax(p[rule.split("_")[-1]])]
    if rule.startswith("a1_"):  # A = 1 phiếu: dừng khi A nhất trí và B đồng ý; còn lại LLM chọn
        tag = rule.split("_")[-1]
        return v7 if (a_unan and b_agree) else c[argmax(p[tag])]
    if rule.startswith("a1v7_"):  # A = 1 phiếu chỉ ở ca A 3/3 vs B; ca khác giữ luật v7 (đối chất)
        tag = rule.split("_")[-1]
        return c[argmax(p[tag])] if (a_unan and not b_agree) else v7
    raise ValueError(rule)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--run", default="v9dev")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"dataset/qas_{args.split}.json")}
    load = lambda n: {json.loads(x)["qa_id"]: json.loads(x) for x in (ROOT / f"outputs/mas_tqa/qas_{args.split}/{n}.run{args.run}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}  # noqa: E731
    sc, mv, sc3 = load("score_r"), load("memview_r"), load("knn16_sc3r")
    ids = sorted(set(sc) & set(mv))
    for i in ids:
        sc[i]["trace"]["_v7"] = mv[i]["prediction"][0]
    rules = {"MemView (luật v7, bản có lý do)": "v7",
             "LLM validator chọn mọi câu ≥ 2 ứng viên, không lý do": "llm_all_plain",
             "LLM validator chọn mọi câu ≥ 2 ứng viên, có lý do": "llm_all_reason",
             "A = 1 phiếu + LLM validator, không lý do": "a1_plain",
             "A = 1 phiếu + LLM validator, có lý do": "a1_reason",
             "chỉ ca A 3/3 vs B → LLM validator (có lý do)": "a1v7_reason"}
    ok = lambda a, i: correct(a, qas[i]) if a else 0  # noqa: E731
    ref = {i: ok(mv[i]["prediction"][0], i) for i in ids}
    scored = [i for i in ids if sc[i]["trace"].get("scored")]
    orc = sum(any(ok(c, i) for c in sc[i]["trace"]["cands"]) for i in scored)
    print(f"{args.split} {args.run}: {len(ids)} câu; chỉ agent A {100 * sum(ok(sc3[i]['prediction'][0], i) for i in ids if i in sc3) / len(ids):.2f}; "
          f"{len(scored)} câu ≥ 2 ứng viên (oracle {orc}, MemView đúng {sum(ref[i] for i in scored)})\n")
    for name, r in rules.items():
        v = {i: ok(decide(sc[i], qas[i]["question"], r), i) for i in ids}
        ci = paired_bootstrap_ci([v[i] for i in ids], [ref[i] for i in ids], samples=5000)
        print(f"{name:<52}{100 * sum(v.values()) / len(ids):7.2f}   {100 * ci['point_estimate']:+.2f} "
              f"[{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]   sửa {sum(v[i] and not ref[i] for i in ids)} / hỏng {sum(ref[i] and not v[i] for i in ids)}")


if __name__ == "__main__":
    main()
