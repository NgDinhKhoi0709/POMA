"""EM theo nhóm câu (hint của dataset, độ dài bảng, độ dài gold, ô gộp, độ phủ memory) cho một hệ so với một hệ
đối chứng, và các số của slide "vì sao hai view" (từng agent riêng lẻ, bù lỗi) và "agent V" từ trace suite_v10.

EM ở đây là mức "mọi cách viết" của evaluation/lenient.py (mặc định) hoặc mức chặt (--level strict).

python scripts/analyze_weak_groups.py --method memview_q.runv11test --ref fs_qwen.runq2 --vote vote4_q.runv11test
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.lenient import LEVELS, lenient_match  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402
from mas_tqa.data import _toks, table_str, train_by_table  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--method", default="memview_q.runv11test")
    ap.add_argument("--ref", default="fs_qwen.runq2")
    ap.add_argument("--vote", default="vote4_q.runv11test", help="Bỏ phiếu A+B cùng lần chạy, để so với agent V.")
    ap.add_argument("--level", default=LEVELS[-1], choices=LEVELS)
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    tab = {t["table_id"]: t for t in next(iter(json.loads((ROOT / "dataset/table.json").read_text(encoding="utf-8")).values()))}

    def load(name: str) -> dict[str, dict]:
        lines = (ROOT / args.dir / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        return {r["qa_id"]: r for r in map(json.loads, filter(str.strip, lines))}

    def ok(r: dict, q: dict) -> int:
        pred = verbalize(q["question"], (r.get("prediction") or [""])[0])
        return int(lenient_match(pred, q["answer"], q["question"], hints=q.get("hints"), level=args.level))

    M, F = load(args.method), load(args.ref)
    rows = []
    for i, q in qas.items():
        train = train_by_table()[q["table_id"]]
        qt = _toks(q["question"])
        jac = max((len(qt & _toks(r["question"])) / max(1, len(qt | _toks(r["question"]))) for r in train), default=0.0)
        rows.append({"M": ok(M.get(i, {}), q), "F": ok(F.get(i, {}), q), "flat": len(table_str(q["table_id"])),
                     "gold": len(_toks(q["answer"])), "types": tab[q["table_id"]]["table_type"], "jac": jac,
                     "hints": [h.split(" (")[0] for h in q.get("hints", [])], "n_train": len(train)})

    def show(name: str, pred) -> None:
        s = [r for r in rows if pred(r)]
        if s:
            m, f = 100 * sum(r["M"] for r in s) / len(s), 100 * sum(r["F"] for r in s) / len(s)
            print(f"{name[:44]:<45}{len(s):5d}{m:8.1f}{f:8.1f}{m - f:+8.1f}{sum(1 - r['M'] for r in s):6d}")

    print(f"mức EM: {args.level}\n{'nhóm':<45}{'n':>5}{'hệ':>8}{'ref':>8}{'hơn':>8}{'sai':>6}")
    show("tất cả", lambda r: True)
    show("Flatten V1 >= 16.000 ký tự", lambda r: r["flat"] >= 16000)
    show("gold >= 8 token", lambda r: r["gold"] >= 8)
    show("bảng có ô gộp giá trị", lambda r: "contain_merged_value" in r["types"])
    for h, _ in Counter(h for r in rows for h in r["hints"]).most_common():
        show(f"hint: {h}", lambda r, h=h: h in r["hints"])
    show("Jaccard >= 0.8 với câu train cùng bảng", lambda r: r["jac"] >= 0.8)
    show("bảng có < 10 câu train", lambda r: r["n_train"] < 10)

    # Từng agent riêng lẻ và bù lỗi (trace suite_v10: samples = 3 mẫu A, B = đáp án B).
    a1 = b1 = any_ok = nb = 0
    for i, q in qas.items():
        tr = M.get(i, {}).get("trace", {})
        s = tr.get("samples") or []
        a_ok = ok({"prediction": [s[0] if s else ""]}, q)
        a1 += a_ok
        if "B" in tr:
            nb += 1
            b_ok = ok({"prediction": [tr["B"]]}, q)
            b1 += b_ok
            any_ok += int(a_ok or b_ok)
    if nb:
        print(f"\nA một mẫu {100 * a1 / len(qas):.2f}  B {100 * b1 / nb:.2f} (n={nb})  ít nhất một đúng {100 * any_ok / nb:.2f}")

    # Agent V so với bỏ phiếu ở các câu agent V được gọi.
    V = load(args.vote)
    routed = [i for i in qas if M.get(i, {}).get("trace", {}).get("route") == "agent_v"]
    if routed:
        mv = sum(ok(M[i], qas[i]) for i in routed)
        vv = sum(ok(V[i], qas[i]) for i in routed)
        fix = sum(ok(M[i], qas[i]) and not ok(V[i], qas[i]) for i in routed)
        hurt = sum(ok(V[i], qas[i]) and not ok(M[i], qas[i]) for i in routed)
        print(f"agent V chạy {len(routed)} câu: V đúng {mv}, bỏ phiếu đúng {vv}, sửa {fix}, làm hỏng {hurt}")
    print("route:", dict(Counter(M.get(i, {}).get("trace", {}).get("route") for i in qas)))


if __name__ == "__main__":
    main()
