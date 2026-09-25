"""So ghép cặp EM giữa các file prediction trên cùng một split; '+v' sau tên thì áp Verbalize tất định.

python scripts/compare_dev_arms.py --base fs+v=outputs/baseline/dev_few_shot/openrouter_qwen_qwen3-8b.jsonl \
    zs=outputs/baseline/dev_zero_shot/openrouter_qwen_qwen3-8b.jsonl a5=outputs/gap_tqa/dev/A5_rule.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.io import load_json_records  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402
from gap_tqa.router import gold_class  # noqa: E402
from gap_tqa.run import score  # noqa: E402


def load(spec: str, qas_path: Path, questions: dict[str, str]) -> tuple[str, dict[str, float]]:
    name, path = spec.split("=", 1)
    if not name.endswith("+v"):
        return name, score(Path(path), qas_path)
    recs = [dict(r) for r in load_json_records(Path(path))]
    for r in recs:
        pred = r.get("prediction") or [""]
        r["prediction"] = [verbalize(questions[r["qa_id"]], pred[0])]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"predictions": recs}, f, ensure_ascii=False)
    return name, score(Path(f.name), qas_path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qas", default="dataset/qas_dev.json")
    ap.add_argument("--base", required=True)
    ap.add_argument("arms", nargs="+")
    args = ap.parse_args()

    qas_path = Path(args.qas)
    qas = {q["qa_id"]: q for q in json.load(open(qas_path, encoding="utf-8"))["qas"]}
    questions = {i: q["question"] for i, q in qas.items()}
    base_name, base = load(args.base, qas_path, questions)
    arms = dict(load(s, qas_path, questions) for s in args.arms)
    ids = sorted(set(base).intersection(*arms.values()))
    b = [base[i] for i in ids]
    print(f"n={len(ids)}  base {base_name}: EM {100 * sum(b) / len(ids):.2f}")
    for name, sc in arms.items():
        a = [sc[i] for i in ids]
        d = paired_bootstrap_ci(a, b)["difference"]
        by = defaultdict(list)
        for i in ids:
            by[gold_class(qas[i]["hints"])].append(sc[i])
        cls = " ".join(f"{k}:{100 * sum(v) / len(v):.1f}" for k, v in sorted(by.items()))
        print(f"{name:>10}: EM {100 * sum(a) / len(ids):.2f}  diff {100 * d['point_estimate']:+.2f} "
              f"[{100 * d['lower']:+.2f}; {100 * d['upper']:+.2f}]  W/L {sum(x > y for x, y in zip(a, b))}/"
              f"{sum(x < y for x, y in zip(a, b))}  | {cls}")


if __name__ == "__main__":
    main()
