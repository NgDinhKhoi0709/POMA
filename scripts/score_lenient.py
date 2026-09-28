"""Chấm EM gốc và EM mở rộng (evaluation/lenient.py) cho mọi file dự đoán trong một thư mục mas_tqa.

Dự đoán đi qua Verbalize như EM gốc của repo. In chênh lệch ghép cặp so với --ref ở từng mức, và
(--show) các cặp chỉ đúng ở mức mở rộng để kiểm tra bằng mắt.

python scripts/score_lenient.py --dir outputs/mas_tqa/qas_test --qas dataset/qas_test.json --ref fs.runfull
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
from evaluation.lenient import LEVELS, lenient_match  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--ref", default="fs.runfull")
    ap.add_argument("--files", nargs="*", help="Tên file (không .jsonl); mặc định mọi file trong --dir.")
    ap.add_argument("--show", help="In các cặp chỉ đúng ở mức mở rộng của file này.")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    d = ROOT / args.dir
    names = args.files or sorted(p.stem for p in d.glob("*.jsonl"))

    def score(name: str) -> dict[str, dict[str, int]]:
        recs = [json.loads(x) for x in (d / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        out: dict[str, dict[str, int]] = {lv: {} for lv in LEVELS}
        for r in recs:
            q = qas[r["qa_id"]]
            pred = verbalize(q["question"], (r.get("prediction") or [""])[0])
            for lv in LEVELS:
                out[lv][r["qa_id"]] = int(lenient_match(pred, q["answer"], q["question"], hints=q.get("hints"), level=lv))
        return out

    ref = score(args.ref)
    print(f"{'file':<30}{'n':>5}" + "".join(f"{lv:>9}" for lv in LEVELS) + f"   Δ so với {args.ref} [95% CI] theo mức")
    for name in names:
        s = score(name)
        ids = sorted(s["strict"])
        row = f"{name:<30}{len(ids):5d}" + "".join(f"{100 * sum(s[lv].values()) / len(ids):9.2f}" for lv in LEVELS)
        if name != args.ref:
            common = [i for i in ids if i in ref["strict"]]
            cis = []
            for lv in LEVELS:
                ci = paired_bootstrap_ci([s[lv][i] for i in common], [ref[lv][i] for i in common], samples=5000)
                cis.append(f"{100 * ci['point_estimate']:+.2f} [{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]")
            row += "   " + " | ".join(cis)
        print(row)

    if args.show:
        s = score(args.show)
        recs = {json.loads(x)["qa_id"]: json.loads(x) for x in (d / f"{args.show}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
        kinds = Counter()
        print(f"\nCác cặp chỉ đúng ở mức mở rộng ({args.show}):")
        for i in sorted(s["strict"]):
            lv = next((lv for lv in LEVELS if s[lv][i]), None)
            if lv and lv != "strict":
                kinds[lv] += 1
                print(f"  [{lv}] pred={recs[i]['prediction'][0][:50]!r}  gold={qas[i]['answer'][:50]!r}  | {qas[i]['question'][:60]}")
        print(dict(kinds))


if __name__ == "__main__":
    main()
