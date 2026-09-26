"""Gộp ứng viên từ nhiều arm đã lưu (0 lệnh gọi API): trần oracle, plurality vote, bộ chọn học được.

Bộ chọn = LogisticRegression trên đặc trưng của từng đáp án ứng viên (số arm ủng hộ, arm nào ủng hộ,
khớp nguyên văn/nằm trong một ô của bảng, độ dài, `Null`, lớp câu hỏi của router), đánh giá bằng
5-fold GroupKFold theo table_id. Vote hoà thì lấy arm đầu tiên của pool.

python scripts/pool_selector_pilot.py --pool A5 fs+v A2b
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.exact_match import score_sample  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from evaluation.normalization import normalize_text  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402
from gap_tqa.router import CLASSES, route  # noqa: E402
from preprocessing.loader import DatasetLoader  # noqa: E402
from preprocessing.variants import Grid  # noqa: E402

# '+v' = áp Verbalize tất định lên đáp án đã lưu (như scripts/compare_dev_arms.py).
# A5 đứng đầu để pool mặc định phá hoà bằng A5.
ARMS = {
    "A5": "outputs/gap_tqa/dev/A5_rule.json",
    "A0": "outputs/gap_tqa/dev/A0.json",
    "A1": "outputs/gap_tqa/dev/A1.json",
    "A2a": "outputs/gap_tqa/dev/A2a.json",
    "A2b": "outputs/gap_tqa/dev/A2b.json",
    "A3": "outputs/gap_tqa/dev/A3.json",
    "A4": "outputs/gap_tqa/dev/A4_rule.json",
    "fs+v": "outputs/baseline/dev_few_shot/openrouter_qwen_qwen3-8b.jsonl",
    "zs+v": "outputs/baseline/dev_zero_shot/openrouter_qwen_qwen3-8b.jsonl",
}


def load_arm(name: str, path: str, qas: dict, qas_list: list) -> dict[str, tuple[str, float]]:
    recs = [dict(r) for r in load_json_records(ROOT / path)]
    if name.endswith("+v"):
        for r in recs:
            r["prediction"] = [verbalize(qas[r["qa_id"]]["question"], (r.get("prediction") or [""])[0])]
    samples, _ = align_records(recs, qas_list, candidate_policy="first")
    return {s.qa_id: (normalize_text(s.prediction[0] if s.prediction else ""), score_sample(s).value) for s in samples}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qas", default="dataset/qas_dev.json")
    ap.add_argument("--pool", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--refs", nargs="+", default=["A5", "fs+v"], choices=list(ARMS))
    args = ap.parse_args()

    qas_list = load_qas_records(ROOT / args.qas)
    qas = {q["qa_id"]: q for q in qas_list}
    tables = DatasetLoader(str(ROOT / "dataset")).load_tables()
    names = list(dict.fromkeys(args.pool + args.refs))
    data = {n: load_arm(n, ARMS[n], qas, qas_list) for n in names}
    ids = sorted(set.intersection(*(set(v) for v in data.values())))
    cells: dict[str, set[str]] = {}

    rows, labels, owner, groups = [], [], [], []
    for i in ids:
        tid = qas[i]["table_id"]
        if tid not in cells:
            cells[tid] = {normalize_text(c) for row in Grid.from_table_data(tables[tid]).rows for c in row if c}
        support = defaultdict(list)
        for n in args.pool:
            support[data[n][i][0]].append(n)
        cls = route(qas[i]["question"])
        for ans, arms in support.items():
            rows.append([len(arms), float(ans in ("", "null")), min(len(ans.split()), 20) / 20,
                         float(ans in cells[tid]), float(any(ans and ans in c for c in cells[tid]))]
                        + [float(n in arms) for n in args.pool] + [float(cls == c) for c in CLASSES])
            labels.append(data[arms[0]][i][1])
            owner.append(i)
            groups.append(tid)
    X, y = np.array(rows), np.array(labels)
    prob = np.zeros(len(y))
    for train, test in GroupKFold(n_splits=5).split(X, y, np.array(groups)):
        prob[test] = LogisticRegression(max_iter=2000).fit(X[train], y[train]).predict_proba(X[test])[:, 1]
    best: dict[str, tuple[float, float]] = {}
    for p, i, em in zip(prob, owner, y):
        if i not in best or p > best[i][0]:
            best[i] = (p, em)
    selector = [best[i][1] for i in ids]

    vote = []
    for i in ids:
        counts = Counter(data[n][i][0] for n in args.pool)
        top, k = counts.most_common(1)[0]
        pick = data[args.pool[0]][i][0] if sum(v == k for v in counts.values()) > 1 else top
        vote.append(next(data[n][i][1] for n in args.pool if data[n][i][0] == pick))

    n = len(ids)
    print(f"n={n}  pool={'+'.join(args.pool)}")
    for name in names:
        print(f"  {name:>5}: EM {100 * sum(data[name][i][1] for i in ids) / n:.2f}")
    print(f"  oracle {100 * sum(any(data[m][i][1] for m in args.pool) for i in ids) / n:.2f}  "
          f"vote {100 * sum(vote) / n:.2f}  selector {100 * sum(selector) / n:.2f}")
    for label, base in [("vote", vote)] + [(r, [data[r][i][1] for i in ids]) for r in args.refs]:
        d = paired_bootstrap_ci(selector, base)["difference"]
        print(f"  selector - {label}: {100 * d['point_estimate']:+.2f} [{100 * d['lower']:+.2f}; "
              f"{100 * d['upper']:+.2f}]  W/L {sum(a > b for a, b in zip(selector, base))}/"
              f"{sum(a < b for a, b in zip(selector, base))}")
    for r in args.refs:
        d = paired_bootstrap_ci(vote, [data[r][i][1] for i in ids])["difference"]
        print(f"  vote - {r}: {100 * d['point_estimate']:+.2f} [{100 * d['lower']:+.2f}; {100 * d['upper']:+.2f}]")


if __name__ == "__main__":
    main()
