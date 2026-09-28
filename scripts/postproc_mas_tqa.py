"""Chấm các luật hậu xử lý tất định trên file dự đoán mas_tqa: số câu sửa đúng / làm hỏng, EM trước–sau.

- style: agent định dạng theo phong cách gold của câu train cùng bảng (mas_tqa/style.py).
- null: đáp án cuối là Null mà trong các ứng viên có đáp án hợp lệ khác Null → lấy đáp án đó
  (cần ≥ --null-min phiếu).

Chọn luật trên dev, rồi áp đúng một lần lên test.
python scripts/postproc_mas_tqa.py --dir outputs/mas_tqa/qas_dev --qas dataset/qas_dev.json --file memxam_sckv.runv8dev
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
from evaluation.normalization import is_unanswerable_prediction  # noqa: E402
from mas_tqa.methods import _top  # noqa: E402
from mas_tqa.style import RULES, harmonize  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402


def null_fix(pred: str, trace: dict, question: str, min_votes: int) -> str:
    if not is_unanswerable_prediction(pred) or not trace:
        return pred
    pool = list(trace.get("samples", [])) + [trace.get(k, "") for k in ("B", "A2", "B2") if trace.get(k)]
    ranked = [(x, c) for x, c in _top(pool, question) if not is_unanswerable_prediction(x)]
    return ranked[0][0] if ranked and ranked[0][1] >= min_votes else pred


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_dev")
    ap.add_argument("--qas", default="dataset/qas_dev.json")
    ap.add_argument("--file", default="memxam_sckv.runv8dev")
    ap.add_argument("--null-min", type=int, default=1)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / args.qas)}
    recs = [json.loads(line) for line in (ROOT / args.dir / f"{args.file}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["qa_id"] for r in recs]
    base = {r["qa_id"]: correct(r["prediction"][0], qas[r["qa_id"]]) for r in recs}
    rules = {name: (lambda f: lambda r: f(r["prediction"][0], qas[r["qa_id"]]))(f) for name, f in RULES.items()}
    rules["style (tất cả)"] = lambda r: harmonize(r["prediction"][0], qas[r["qa_id"]])
    rules["null"] = lambda r: null_fix(r["prediction"][0], r.get("trace") or {}, r["question"], args.null_min)
    n = len(ids)
    print(f"{args.file}: n={n}  EM gốc {100 * sum(base.values()) / n:.2f}\n")
    print(f"{'luật':<14}{'đổi':>6}{'sửa đúng':>10}{'làm hỏng':>10}{'EM':>8}   Δ [95% CI]")
    for name, f in rules.items():
        new = {r["qa_id"]: f(r) for r in recs}
        ok = {r["qa_id"]: correct(new[r["qa_id"]], qas[r["qa_id"]]) for r in recs}
        changed = [i for i, r in zip(ids, recs) if new[i] != r["prediction"][0]]
        fix = sum(ok[i] and not base[i] for i in changed)
        brk = sum(base[i] and not ok[i] for i in changed)
        ci = paired_bootstrap_ci([ok[i] for i in ids], [base[i] for i in ids], samples=5000)
        print(f"{name:<14}{len(changed):6d}{fix:10d}{brk:10d}{100 * sum(ok.values()) / n:8.2f}   "
              f"{100 * ci['point_estimate']:+.2f} [{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]")
        if args.show:
            for i, r in zip(ids, recs):
                if i in changed:
                    tag = "+" if ok[i] and not base[i] else "-" if base[i] and not ok[i] else "="
                    print(f"    {tag} {r['prediction'][0][:40]!r} -> {new[i][:40]!r}  gold={r['groundtruth'][:40]!r}")


if __name__ == "__main__":
    main()
