"""Verifier agent cho các câu phiếu phân tán (sparse): chấm từng ứng viên thay cho bỏ phiếu đa số.

Pool ứng viên lấy từ các lần gọi độc lập đã lưu (mặc định: 3 mẫu kNN-SC3 + solver B + kNN k=16).
Câu "sparse" = không có đáp án hợp lệ nào đạt ≥ `--min-votes` phiếu. Chỉ các câu này gọi verifier.

python scripts/verify_sparse.py --run 1
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from mas_tqa.client import VLLMClient, parse_json  # noqa: E402
from mas_tqa.methods import _majority, _pick_valid, _top, flat_prefix, key  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402

D = ROOT / "outputs/mas_tqa/qas_dev_200"


def verify_suffix(question: str, cand: str) -> str:
    return (
        "NHIỆM VỤ LÚC NÀY KHÁC: bạn là người kiểm định. Hãy kiểm tra xem ĐÁP ÁN ĐỀ XUẤT dưới đây có trả lời "
        "đúng câu hỏi theo bảng hay không: tìm các ô bảng liên quan, đối chiếu nội dung, và xét cả cách viết "
        "so với phong cách các đáp án mẫu ở trên.\n"
        "ĐẦU RA: đúng một JSON {\"evidence\": [\"<ô bảng>\"], \"verdict\": \"dung\" hoặc \"sai\", "
        "\"score\": <số nguyên 0-100, mức tin rằng đáp án đúng>}.\n\n"
        f"CÂU HỎI: {question}\nĐÁP ÁN ĐỀ XUẤT: {cand}\n"
    )


def load(name: str) -> dict[str, dict]:
    return {r["qa_id"]: r for r in map(json.loads, (D / f"{name}.jsonl").read_text(encoding="utf-8").splitlines())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="1")
    ap.add_argument("--min-votes", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / "outputs/mas_tqa/qas_dev_200.json")}
    sc, b, a16 = load("knn_sc3.run1"), load("evid.runv4r1"), load("knn16_fs.run1")
    ids = [i for i in qas if i in sc and i in b and i in a16]
    pools = {i: sc[i]["trace"]["samples"] + [b[i]["prediction"][0], a16[i]["prediction"][0]] for i in ids}
    sparse = [i for i in ids if (lambda r: r and r[0][1] < args.min_votes)(_top(pools[i], qas[i]["question"]))]
    print(f"{len(ids)} câu, {len(sparse)} câu sparse (không ứng viên nào ≥ {args.min_votes}/5 phiếu)", flush=True)

    out = D / f"verify_sparse.run{args.run}.jsonl"
    done = {json.loads(line)["qa_id"] for line in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    client = VLLMClient()

    def one(i: str) -> dict:
        qa = qas[i]
        cands = _top(pools[i], qa["question"])
        scored = []
        for cand, votes in cands:
            t, _ = client.chat(flat_prefix(qa) + verify_suffix(qa["question"], cand))
            obj = parse_json(t[0]) or {}
            try:
                s = float(obj.get("score", 0))
            except (TypeError, ValueError):
                s = 0.0
            ok = str(obj.get("verdict", "")).strip().lower().startswith("d")
            scored.append({"cand": cand, "votes": votes, "verdict": ok, "score": s})
        return {"qa_id": i, "scored": scored}

    with ThreadPoolExecutor(args.workers) as ex, out.open("a", encoding="utf-8") as fh:
        for rec in ex.map(one, [i for i in sparse if i not in done]):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()

    res = {r["qa_id"]: r["scored"] for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    tot = {"vote5": 0, "verifier": 0}
    fix = brk = 0
    for i in ids:
        q = qas[i]["question"]
        v = _majority(_pick_valid(pools[i], q), q)
        pick = v
        if i in res and res[i]:
            best = max(res[i], key=lambda s: (s["verdict"], s["score"], s["votes"]))
            pick = best["cand"]
        cv, cp = correct(v, qas[i]), correct(pick, qas[i])
        tot["vote5"] += cv
        tot["verifier"] += cp
        fix += cp and not cv
        brk += cv and not cp
    n = len(ids)
    print({k: round(100 * x / n, 2) for k, x in tot.items()}, f"trên câu sparse: sửa {fix}, phá {brk}")
    orc = sum(any(correct(c, qas[i]) for c in pools[i]) for i in sparse)
    print(f"oracle trong nhóm sparse: {orc}/{len(sparse)}; vote đúng {sum(correct(_majority(_pick_valid(pools[i], qas[i]['question']), qas[i]['question']), qas[i]) for i in sparse)}")


if __name__ == "__main__":
    main()
