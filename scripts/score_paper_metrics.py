"""EM, F1, ROUGE-1 và METEOR cho các file dự đoán mas_tqa (bảng kết quả của paper).

- EM: mức "strict" của evaluation/lenient.py (cùng số với cột strict của scripts/score_lenient.py), dự đoán đi
  qua Verbalize như các script chấm khác.
- F1 (ký tự) và ROUGE-1: metric của repo.
- METEOR: bản chuẩn của nltk (có phạt phân mảnh), giống bài báo Open-ViTabQA; câu gold Null chấm như metric
  của repo (đúng khi dự đoán cũng là Null). Metric `evaluation.meteor` của repo không có phạt phân mảnh nên
  cho điểm cao hơn nhiều và không so được với bài báo.
BIF tính riêng bằng scripts/bif_all.py.

python scripts/score_paper_metrics.py --files memview_q.runv11test fs_qwen.runq2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nltk.translate.meteor_score import meteor_score  # noqa: E402

from evaluation import f1, rouge1  # noqa: E402
from evaluation.contracts import AlignedSample  # noqa: E402
from evaluation.lenient import lenient_match  # noqa: E402
from evaluation.normalization import is_unanswerable_reference, normalize_text, prediction_is_unanswerable  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402


def meteor(sample: AlignedSample) -> float:
    if is_unanswerable_reference(sample.reference):
        return float(prediction_is_unanswerable(sample.prediction))
    p, r = normalize_text(sample.prediction[0]).split(), normalize_text(sample.reference).split()
    return meteor_score([r], p) if p and r else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--files", nargs="+", required=True, help="Tên file trong --dir, không có .jsonl.")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    print(f"{'file':<28}{'n':>5}{'EM':>8}{'F1':>8}{'R1':>8}{'MET':>8}")
    for name in args.files:
        lines = (ROOT / args.dir / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        recs = {r["qa_id"]: r for r in map(json.loads, filter(str.strip, lines))}
        # Câu thiếu trong file dự đoán chấm là sai (dự đoán rỗng), để mọi hệ chấm trên cùng tập câu.
        samples = [AlignedSample(qa_id=i, prediction=[verbalize(q["question"], (recs.get(i, {}).get("prediction") or [""])[0])],
                                 reference=str(q["answer"])) for i, q in qas.items()]
        n = len(samples)
        em = sum(lenient_match(s.prediction[0], qas[s.qa_id]["answer"], qas[s.qa_id]["question"],
                               hints=qas[s.qa_id].get("hints"), level="strict") for s in samples)
        fs = sum(f1.score_sample(s).value for s in samples)
        r1 = sum(rouge1.score_sample(s).value for s in samples)
        met = sum(meteor(s) for s in samples)
        print(f"{name:<28}{n:5d}" + "".join(f"{100 * v / n:8.2f}" for v in (em, fs, r1, met)))


if __name__ == "__main__":
    main()
