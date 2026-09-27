"""Phân tích suite v8: độ chính xác có điều kiện của agent C (code), luật dừng, và luật tổng hợp offline.

Mọi luật dùng chung lệnh gọi của một lần chạy nên so sánh là ghép cặp (paired bootstrap).

python scripts/analyze_v8.py --dir outputs/mas_tqa/qas_dev --qas dataset/qas_dev.json --run v8dev
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
from mas_tqa.methods import _majority, _pick_valid, _top, key, valid  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_dev")
    ap.add_argument("--qas", default="dataset/qas_dev.json")
    ap.add_argument("--run", default="v8dev")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / args.qas)}
    hints = {q["qa_id"]: q["hints"] for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    d = ROOT / args.dir
    files = {m: d / f"{m}.run{args.run}.jsonl" for m in
             ["knn16_sc3", "vote4kv", "code_c", "vote5", "memxam_sckv", "memxam_veto", "memxam_c5"]}
    recs = {m: {r["qa_id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines()) if r}
            for m, p in files.items() if p.exists()}
    ids = sorted(set.intersection(*[set(v) for v in recs.values()]))
    tr = {i: recs["memxam_c5"][i]["trace"] for i in ids}

    ok = {m: {i: correct(recs[m][i]["prediction"][0], qas[i]) for i in ids} for m in recs}

    # Luật offline trên cùng trace (chỉ dùng A2/B2 khi đối chất đã chạy, tức 5 đáp án chưa đồng nhất).
    def rule(i: str, pool_c: bool, need: int, veto: bool, w_c: int = 1) -> str:
        t, q = tr[i], qas[i]["question"]
        pool = t["samples"] + [t["B"]] + ([t["C"]] * w_c if pool_c else [])
        r = _top(pool, q)
        stop = not r or len(r) == 1 or r[0][1] >= need
        if veto and r and valid(t["B"], q) and key(t["B"], q) != key(r[0][0], q):
            stop = False
        if stop or "A2" not in t:
            return r[0][0] if r else t["samples"][0]
        return _majority(_pick_valid([t["A2"], t["B2"]] + pool, q), q)

    offline = {
        "off_c5_need4": lambda i: rule(i, True, 4, False),
        "off_c5_need5": lambda i: rule(i, True, 5, False),
        "off_c5_veto": lambda i: rule(i, True, 4, True),
        "off_c2w_need4": lambda i: rule(i, True, 4, False, 2),
        "off_v7_need4": lambda i: rule(i, False, 4, False),
    }
    for name, f in offline.items():
        ok[name] = {i: correct(f(i), qas[i]) for i in ids}

    n = len(ids)
    print(f"n={n}  run={args.run}\n")
    base = ok["memxam_sckv"]
    print(f"{'luật':<16}{'EM':>7}   Δ vs memxam_sckv [95% CI]")
    for m, v in ok.items():
        em = 100 * sum(v.values()) / n
        ci = paired_bootstrap_ci([v[i] for i in ids], [base[i] for i in ids], samples=5000)
        print(f"{m:<16}{em:7.2f}   {100 * ci['point_estimate']:+.2f} [{100 * ci['lower']:+.2f}, {100 * ci['upper']:+.2f}]")

    # Độ chính xác có điều kiện của C (bài học Headroom).
    pool4_ok = {i: any(correct(x, qas[i]) for x in tr[i]["samples"] + [tr[i]["B"]]) for i in ids}
    v4 = ok["vote4kv"]
    c = ok["code_c"]
    err = Counter(("lỗi chạy" if tr[i].get("C_error") else ("rỗng" if not tr[i]["C"] else "có đáp án")) for i in ids)
    print(f"\nC: EM {100 * sum(c.values()) / n:.2f}; trạng thái {dict(err)}")
    miss = [i for i in ids if not pool4_ok[i]]
    print(f"  pool v7 sai hết: {len(miss)} câu, C đúng {sum(c[i] for i in miss)}")
    right = [i for i in ids if v4[i]]
    print(f"  vote4 đúng: {len(right)} câu, C sai {sum(1 - c[i] for i in right)}")
    for h in sorted({h for i in ids for h in hints[i]}):
        s = [i for i in ids if h in hints[i]]
        print(f"  {h.split(' (')[0][:40]:<42}n={len(s):4d}  C {100 * sum(c[i] for i in s) / len(s):5.1f}  "
              f"vote4 {100 * sum(v4[i] for i in s) / len(s):5.1f}  c5 {100 * sum(ok['memxam_c5'][i] for i in s) / len(s):5.1f}")

    # Veto: A 3/3 đồng nhất, B bất đồng → A có nhượng bộ trong đối chất không?
    vt = [i for i in ids if recs["memxam_veto"][i]["trace"]["route"] == "debate"
          and recs["memxam_sckv"][i]["trace"]["route"] == "consensus"]
    conc = sum(key(tr[i]["A2"], qas[i]["question"]) != key(tr[i]["A_pos"], qas[i]["question"]) for i in vt)
    print(f"\nVeto thêm {len(vt)} câu đối chất; A đổi lập trường {conc}; "
          f"veto đúng {sum(ok['memxam_veto'][i] for i in vt)} vs v7 đúng {sum(base[i] for i in vt)}")


if __name__ == "__main__":
    main()
