"""Phân tích trace MemXam/cascade3: bất đồng, oracle {A,B}, và độ chính xác có điều kiện của từng tầng.

python scripts/analyze_memxam.py --run 1
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.exact_match import score_sample  # noqa: E402
from evaluation.io import align_records, load_qas_records  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402


def correct(pred: str, qa: dict) -> int:
    s, _ = align_records([{"qa_id": qa["qa_id"], "prediction": [verbalize(qa["question"], pred)]}], [qa], candidate_policy="first")
    return int(score_sample(s[0]).value)


def load(d: Path, name: str, run: str) -> dict[str, dict]:
    p = d / f"{name}.run{run}.jsonl"
    return {r["qa_id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines())} if p.exists() else {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_dev_200")
    ap.add_argument("--run", default="1")
    ap.add_argument("--show", action="store_true", help="In từng câu bất đồng.")
    args = ap.parse_args()
    d = ROOT / args.dir
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"outputs/mas_tqa/{d.name}.json")}
    mx, cc = load(d, "memxam", args.run), load(d, "cascade3", args.run)
    ids = sorted(set(mx) & set(cc))
    n = len(ids)
    A = {i: correct(mx[i]["trace"]["A"], qas[i]) for i in ids}
    B = {i: correct(mx[i]["trace"]["B"], qas[i]) for i in ids}
    M = {i: correct(mx[i]["prediction"][0], qas[i]) for i in ids}
    C = {i: correct(cc[i]["prediction"][0], qas[i]) for i in ids}
    dis = [i for i in ids if mx[i]["trace"]["route"] != "agree"]
    agree = [i for i in ids if i not in dis]
    pct = lambda v, s: 100 * sum(v[i] for i in s) / max(1, len(s))  # noqa: E731
    print(f"n={n}  A(kNN-FS)={pct(A, ids):.1f}  B(evid)={pct(B, ids):.1f}  oracle(A,B)={100 * sum(A[i] or B[i] for i in ids) / n:.1f}")
    print(f"MemXam={pct(M, ids):.1f}  cascade3={pct(C, ids):.1f}")
    print(f"đồng ý {len(agree)} câu, EM {pct(A, agree):.1f};  bất đồng {len(dis)} câu")
    kinds = Counter(("A" if A[i] else "-") + ("B" if B[i] else "-") for i in dis)
    print("  trên câu bất đồng (A đúng/B đúng):", dict(kinds))
    routes = Counter(mx[i]["trace"]["route"] for i in dis)
    for r in routes:
        s = [i for i in dis if mx[i]["trace"]["route"] == r]
        print(f"  route {r}: {len(s)} câu  MemXam {pct(M, s):.1f}  cascade3 {pct(C, s):.1f}  A {pct(A, s):.1f}  B {pct(B, s):.1f}")
    for label, v in [("MemXam", M), ("cascade3", C)]:
        fix = sum(v[i] and not A[i] for i in dis)
        brk = sum(A[i] and not v[i] for i in dis)
        print(f"  {label} so với chỉ dùng A trên câu bất đồng: sửa {fix}, phá {brk}")
    if args.show:
        for i in dis:
            t = mx[i]["trace"]
            print(f"\n{i} gold={qas[i]['answer']!r} route={t['route']} M={M[i]} C={C[i]}\n  A={t['A']!r} B={t['B']!r} A2={t.get('A2')!r} B2={t.get('B2')!r} C3={cc[i]['trace'].get('C')!r}")


if __name__ == "__main__":
    main()
