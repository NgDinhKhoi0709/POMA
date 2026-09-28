"""BIF gốc và BIF mở rộng (4 nhãn và 3 nhãn) cho nhiều phương pháp trên cùng tập câu.

BIF mở rộng: câu nào EM mở rộng (evaluation/lenient.py) tính là đúng thì dùng chính gold làm dự đoán
(điểm của câu đó bằng trần gold-làm-dự-đoán). Mọi cặp (gold, dự đoán) duy nhất chỉ chấm một lần, lưu cache.
Tập câu chung của mọi file (bỏ câu thiếu và --exclude) để so sánh ghép cặp.

python scripts/bif_all.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bertscore import PhoBERTScoreConfig, PhoBERTScoreScorer  # noqa: E402
from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.lenient import lenient_match  # noqa: E402
from evaluation.vinliscore import ViNLIConfig, ViNLIScorer  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402

NLI4 = "outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best"
NLI3 = "checkpoints/vinli-xlmr-large-3label/checkpoint-best"
FILES = ["fs.runfull", "fs_fmt.runfull", "knn16_sc3.runv6full", "knn16_sc3.runv7full", "vote4.runv6full",
         "memxam_sc.runv6full", "vote4kv.runv7full", "memxam_sckv.runv7full", "memxam_sckv_fmt.runv7full"]
LEVELS = ("strict", "yn", "format")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--files", nargs="*", default=FILES)
    ap.add_argument("--ref", default="fs.runfull")
    ap.add_argument("--exclude", nargs="*", default=["62_3_178"], help="Câu làm PhoBERTScore crash (output JSON hỏng rất dài).")
    ap.add_argument("--cache", default="outputs/mas_tqa/eval/bif_pairs_cache.json")
    args = ap.parse_args()

    qas = {q["qa_id"]: q for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    preds = {}
    for f in args.files:
        recs = [json.loads(x) for x in (ROOT / args.dir / f"{f}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        preds[f] = {r["qa_id"]: verbalize(qas[r["qa_id"]]["question"], (r.get("prediction") or [""])[0]) or "Null" for r in recs}
    ids = sorted(set.intersection(*[set(p) for p in preds.values()]) - set(args.exclude))

    def cand(f: str, i: str, lv: str) -> str:
        q, p = qas[i], preds[f][i]
        return q["answer"] if lv != "strict" and lenient_match(p, q["answer"], q["question"], hints=q.get("hints"), level=lv) else p

    table = {(f, lv): {i: cand(f, i, lv) for i in ids} for f in args.files for lv in LEVELS}
    table[("gold", "strict")] = {i: qas[i]["answer"] for i in ids}

    cache_path = ROOT / args.cache
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    pairs = sorted({json.dumps([qas[i]["answer"], c], ensure_ascii=False) for col in table.values() for i, c in col.items()} - set(cache))
    print(f"{len(ids)} câu chung, {len(pairs)} cặp mới cần chấm (cache {len(cache)})", flush=True)
    if pairs:
        refs, cands = zip(*[json.loads(p) for p in pairs])
        pho = PhoBERTScoreScorer(PhoBERTScoreConfig(device="cuda")).score_pairs(list(cands), list(refs))
        e4 = ViNLIScorer(ViNLIConfig(model_path=str(ROOT / NLI4), entailment_id=0, device="cuda")).entailment_scores(list(refs), list(cands))
        e3 = ViNLIScorer(ViNLIConfig(model_path=str(ROOT / NLI3), entailment_id=0, device="cuda")).entailment_scores(list(refs), list(cands))
        for p, a, b, c in zip(pairs, pho, e4, e3):
            cache[p] = [a, b, c]
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    def bif(col: dict[str, str], nli: int) -> dict[str, float]:
        return {i: 0.5 * cache[json.dumps([qas[i]["answer"], c], ensure_ascii=False)][0]
                + 0.5 * cache[json.dumps([qas[i]["answer"], c], ensure_ascii=False)][nli] for i, c in col.items()}

    pct = lambda d: 100 * fmean(d.values())  # noqa: E731
    g = table[("gold", "strict")]
    print(f"\nTrần (gold làm dự đoán): BIF4 {pct(bif(g, 1)):.2f}  BIF3 {pct(bif(g, 2)):.2f}  PhoBERT {100 * fmean(cache[json.dumps([qas[i]['answer'], c], ensure_ascii=False)][0] for i, c in g.items()):.2f}\n")
    head = f"{'phương pháp':<28}{'PhoBERT':>8}" + "".join(f"{'BIF4-' + lv:>13}" for lv in LEVELS) + "".join(f"{'BIF3-' + lv:>13}" for lv in LEVELS)
    print(head + f"   Δ BIF4 / BIF3 so với {args.ref} (gốc) [95% CI]")
    ref4, ref3 = bif(table[(args.ref, "strict")], 1), bif(table[(args.ref, "strict")], 2)
    rows = []
    for f in args.files:
        s4 = {lv: bif(table[(f, lv)], 1) for lv in LEVELS}
        s3 = {lv: bif(table[(f, lv)], 2) for lv in LEVELS}
        pho = 100 * fmean(cache[json.dumps([qas[i]["answer"], c], ensure_ascii=False)][0] for i, c in table[(f, "strict")].items())
        line = f"{f:<28}{pho:8.2f}" + "".join(f"{pct(s4[lv]):13.2f}" for lv in LEVELS) + "".join(f"{pct(s3[lv]):13.2f}" for lv in LEVELS)
        if f != args.ref:
            c4 = paired_bootstrap_ci([s4["strict"][i] for i in ids], [ref4[i] for i in ids], samples=5000)
            c3 = paired_bootstrap_ci([s3["strict"][i] for i in ids], [ref3[i] for i in ids], samples=5000)
            line += (f"   {100 * c4['point_estimate']:+.2f} [{100 * c4['lower']:+.2f}; {100 * c4['upper']:+.2f}]"
                     f" / {100 * c3['point_estimate']:+.2f} [{100 * c3['lower']:+.2f}; {100 * c3['upper']:+.2f}]")
        print(line)
        rows.append({"file": f, "n": len(ids), "phobert": pho, **{f"bif4_{lv}": pct(s4[lv]) for lv in LEVELS},
                     **{f"bif3_{lv}": pct(s3[lv]) for lv in LEVELS}})
    (ROOT / "outputs/mas_tqa/eval/bif_all_test.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
