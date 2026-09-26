"""Chấm EM các file mas_tqa (candidate đầu), so ghép cặp với một file tham chiếu.

Nhiều file của cùng phương pháp (run1, run2, ...) được báo từng lần chạy và trung bình.
`+v` = áp Verbalize tất định của GaP-TQA lên đáp án (như baseline FS+v trong repo).

python scripts/score_mas_tqa.py --ref fs --dir outputs/mas_tqa/qas_dev_200 [--verbalize]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.exact_match import score_sample  # noqa: E402
from evaluation.io import align_records, load_qas_records  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402
from mas_tqa.data import train_by_table, _toks  # noqa: E402

_RUN_RE = re.compile(r"^(?P<method>.+)\.run(?P<run>[^.]+)\.jsonl$")


def near_twins(qas: list[dict], thr: float = 0.8) -> set[str]:
    """Câu có câu train cùng bảng với Jaccard token ≥ thr (kiểm tra độ nhạy rò rỉ)."""
    out = set()
    for q in qas:
        t = _toks(q["question"])
        if any(len(t & _toks(r["question"])) / max(1, len(t | _toks(r["question"]))) >= thr for r in train_by_table()[q["table_id"]]):
            out.add(q["qa_id"])
    return out


def em_vector(path: Path, qas: list[dict], use_v: bool) -> dict[str, float]:
    recs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    byq = {q["qa_id"]: q for q in qas}
    if use_v:
        for r in recs:
            r["prediction"] = [verbalize(byq[r["qa_id"]]["question"], (r.get("prediction") or [""])[0])]
    ids = {r["qa_id"] for r in recs}
    samples, _ = align_records(recs, [q for q in qas if q["qa_id"] in ids], candidate_policy="first")
    return {s.qa_id: score_sample(s).value for s in samples}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_dev_200")
    ap.add_argument("--qas", help="Mặc định suy từ tên thư mục.")
    ap.add_argument("--ref", default="fs")
    ap.add_argument("--verbalize", action="store_true")
    args = ap.parse_args()

    d = ROOT / args.dir
    qas = load_qas_records(ROOT / (args.qas or f"outputs/mas_tqa/{d.name}.json"))
    twins = near_twins(qas)
    runs: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for p in sorted(d.glob("*.jsonl")):
        m = _RUN_RE.match(p.name)
        if m and p.stat().st_size:
            runs[m["method"]][m["run"]] = em_vector(p, qas, args.verbalize)
    full = {q["qa_id"] for q in qas}
    ref = runs.get(args.ref, {})
    print(f"{len(qas)} câu, {len(twins)} câu có sinh đôi trong train; verbalize={args.verbalize}\n")
    print(f"{'method':<24}{'run':>5}{'n':>5}{'EM':>8}{'EM-twin':>9}   diff vs {args.ref} [95% CI]")
    for method, rr in sorted(runs.items()):
        ems = []
        for run, v in sorted(rr.items()):
            ids = sorted(v)
            em = 100 * fmean(v[i] for i in ids)
            nt = [i for i in ids if i not in twins]
            em_nt = 100 * fmean(v[i] for i in nt) if nt else float("nan")
            ems.append(em)
            cmp = ""
            r = ref.get(run) or (next(iter(ref.values())) if ref else None)
            if r and method != args.ref:
                common = sorted(set(v) & set(r))
                ci = paired_bootstrap_ci([v[i] for i in common], [r[i] for i in common], samples=5000)
                cmp = f"{100 * ci['point_estimate']:+.2f} [{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}] n={len(common)}"
            flag = "" if len(v) == len(full) else " (thiếu)"
            print(f"{method:<24}{run:>5}{len(v):>5}{em:8.2f}{em_nt:9.2f}   {cmp}{flag}")
        if len(ems) > 1:
            print(f"{method:<24}{'mean':>5}{'':>5}{fmean(ems):8.2f}")


if __name__ == "__main__":
    main()
