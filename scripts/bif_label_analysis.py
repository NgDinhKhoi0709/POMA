"""Tách BIF: PhoBERT-F1 riêng, khối xác suất OTHER của ViNLI 4 nhãn, và xấp xỉ 3 nhãn.

Xấp xỉ 3 nhãn = P(E) / (P(E) + P(C) + P(N)), tức bỏ OTHER rồi chuẩn hoá lại. Đây KHÔNG phải một
mô hình 3 nhãn được huấn luyện riêng; chỉ cho biết OTHER đang hút bao nhiêu xác suất.
Đọc các file *.bif_details.json do scripts/bif_mas_tqa.py sinh ra.

python scripts/bif_label_analysis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from evaluation.vinliscore import ViNLIConfig, ViNLIScorer  # noqa: E402

NLI = ROOT / "outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best"
NLI3 = ROOT / "checkpoints/vinli-xlmr-large-3label/checkpoint-best"  # huấn luyện 3 nhãn thật (không OTHER)
EVAL = ROOT / "outputs/mas_tqa/eval"
RUNS = {
    "dev": ["fs.run1", "fs.run2", "fs.run3", "knn_fs.runv4r1", "knn_sc3.run1", "knn_sc3.run2",
            "memxam.runv4r1", "knn16_fs.run1", "vote4.runv6r1", "memxam_sc.runv6r1", "vote4kv.runv7r1", "memxam_sckv.runv7r1"],
    "test": ["fs.runt1", "knn_fs.runv4t1", "knn16_sc3.runv6t1", "vote4.runv6t1", "memxam_sc.runv6t1",
             "memxam.runv4t1", "cascade3b.runv4t1", "judge_only.runv4t1", "vote4kv.runv7t1", "memxam_sckv.runv7t1"],
}


def probs(scorer: ViNLIScorer, pairs: list[tuple[str, str]]) -> list[list[float]]:
    torch, out = scorer._torch, []
    for s in range(0, len(pairs), 32):
        batch = pairs[s: s + 32]
        inputs = scorer.tokenizer([a for a, _ in batch], [b for _, b in batch], truncation=True, padding=True,
                                  max_length=128, return_tensors="pt")
        inputs = {k: v.to(scorer.device) for k, v in inputs.items()}
        with torch.no_grad():
            out.extend(torch.softmax(scorer.model(**inputs).logits, dim=-1).cpu().tolist())
    return out


def summarize(details: list[dict], p: list[list[float]], p3: list[list[float]]) -> dict[str, float]:
    pho = [d["phobert_f1"] for d in details]
    t3 = [x[0] for x in p3]
    e4 = [x[0] for x in p]
    other = [x[3] for x in p]
    e3 = [x[0] / max(1e-9, x[0] + x[1] + x[2]) for x in p]
    return {
        "n": len(details),
        "PhoBERT": 100 * fmean(pho),
        "P(E)_4": 100 * fmean(e4),
        "P(OTHER)": 100 * fmean(other),
        "BIF_4": 100 * fmean(0.5 * a + 0.5 * b for a, b in zip(pho, e4)),
        "BIF_3~": 100 * fmean(0.5 * a + 0.5 * b for a, b in zip(pho, e3)),
        "P(E)_3": 100 * fmean(t3),
        "BIF_3": 100 * fmean(0.5 * a + 0.5 * b for a, b in zip(pho, t3)),
    }


def main() -> None:
    scorer = ViNLIScorer(ViNLIConfig(model_path=str(NLI), entailment_id=0, device="cuda", batch_size=32))
    scorer3 = ViNLIScorer(ViNLIConfig(model_path=str(NLI3), entailment_id=0, device="cuda", batch_size=32))
    rows = []
    for split, runs in RUNS.items():
        ids = {q["qa_id"] for q in load_qas_records(ROOT / f"outputs/mas_tqa/qas_{split}_200.json")}
        gold = [d for d in json.loads((ROOT / f"outputs/mas_tqa/ceiling/gold_{split}.bif_details.json").read_text(encoding="utf-8")) if d["qa_id"] in ids]
        full = json.loads((ROOT / f"outputs/mas_tqa/ceiling/gold_{split}.bif_details.json").read_text(encoding="utf-8"))
        for name, det in [("gold toàn split", full), ("gold (trần)", gold)] + [
            (r, json.loads((EVAL / f"qas_{split}_200" / f"{r}.bif_details.json").read_text(encoding="utf-8"))) for r in runs
        ]:
            pairs = [(d["reference"], d["candidate"]) for d in det]
            rows.append((split, name, summarize(det, probs(scorer, pairs), probs(scorer3, pairs))))
    head = f"{'split':5s} {'method':22s}{'n':>5}{'PhoBERT':>9}{'P(E)4':>8}{'P(OTH)':>8}{'BIF_4':>8}{'BIF_3~':>8}{'P(E)3':>8}{'BIF_3':>8}"
    print(head)
    for split, name, s in rows:
        print(f"{split:5s} {name:22s}{s['n']:5d}{s['PhoBERT']:9.2f}{s['P(E)_4']:8.2f}{s['P(OTHER)']:8.2f}{s['BIF_4']:8.2f}{s['BIF_3~']:8.2f}{s['P(E)_3']:8.2f}{s['BIF_3']:8.2f}")
    (ROOT / "outputs/mas_tqa/eval/bif_label_analysis.json").write_text(
        json.dumps([{"split": a, "method": b, **c} for a, b, c in rows], ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
