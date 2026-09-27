"""Chấm EM/F1/BIF cho một file mas_tqa bằng run_eval.py (đáp án đã áp Verbalize như khi chấm EM).

python scripts/bif_mas_tqa.py outputs/mas_tqa/qas_dev_200/knn_fs.run1.jsonl [--qas outputs/mas_tqa/qas_dev_200.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402

NLI = "outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pred")
    ap.add_argument("--qas", default="outputs/mas_tqa/qas_dev_200.json")
    ap.add_argument("--nli", default=NLI, help="Checkpoint ViNLI (mặc định: bản 4 nhãn); entailment luôn là index 0.")
    ap.add_argument("--tag", default="", help="Hậu tố tên file báo cáo, vd. '.3label', để không ghi đè bản 4 nhãn.")
    args = ap.parse_args()

    pred = Path(args.pred)
    recs = [json.loads(line) for line in pred.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {r["qa_id"] for r in recs}
    qas = [q for q in load_qas_records(ROOT / args.qas) if q["qa_id"] in ids]
    out_dir = ROOT / "outputs/mas_tqa/eval" / pred.parent.name
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pred.stem
    vpred = out_dir / f"{stem}.v.jsonl"
    vpred.write_text(
        "".join(
            json.dumps({"qa_id": r["qa_id"], "prediction": [verbalize(r["question"], (r["prediction"] or [""])[0]) or "Null"]}, ensure_ascii=False) + "\n"
            for r in recs
        ),
        encoding="utf-8",
    )
    qpath = out_dir / f"{stem}.qas.json"
    qpath.write_text(json.dumps(qas, ensure_ascii=False), encoding="utf-8")
    cmd = [
        sys.executable, str(ROOT / "run_eval.py"), "--pred", str(vpred), "--qas", str(qpath),
        "--metrics", "em,f1,bif", "--candidate-policy", "first",
        "--bif-nli-model", str(ROOT / args.nli), "--bif-entailment-id", "0", "--bif-device", "cuda",
        "--bif-details", str(out_dir / f"{stem}{args.tag}.bif_details.json"),
        "--output", str(out_dir / f"{stem}{args.tag}.report.json"),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
