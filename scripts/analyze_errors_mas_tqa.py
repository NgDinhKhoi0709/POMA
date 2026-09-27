"""Phân tích lỗi MemXam-SC-KV trên test đầy đủ: EM theo loại câu hỏi, loại bảng, kích thước bảng,
độ phủ memory, route; phân loại câu sai; so với FS.

python scripts/analyze_errors_mas_tqa.py [--method memxam_sckv.runv7full] [--ref fs.runfull]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.exact_match import score_sample  # noqa: E402
from evaluation.io import align_records, load_qas_records  # noqa: E402
from gap_tqa.nodes import verbalize  # noqa: E402
from mas_tqa.data import _toks, table_str, train_by_table  # noqa: E402

_NUM = re.compile(r"-?\d+(?:[.,]\d+)*")


def correct(pred: str, qa: dict) -> int:
    s, _ = align_records([{"qa_id": qa["qa_id"], "prediction": [verbalize(qa["question"], pred)]}], [qa], candidate_policy="first")
    return int(score_sample(s[0]).value)


def load(path: Path) -> dict[str, dict]:
    return {r["qa_id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}


def bucket(x: float, edges: list[float]) -> str:
    for lo, hi in zip(edges, edges[1:]):
        if lo <= x < hi:
            return f"[{lo:g}, {hi:g})"
    return f">= {edges[-1]:g}"


def error_kind(pred: str, gold: str, pool_ok: bool) -> str:
    p, g = pred.strip(), gold.strip()
    if not p or p.lower() in {"null", "none"}:
        return "rỗng / Null"
    if not pool_ok:
        pass  # vẫn phân loại hình thức bên dưới
    pt, gt = _toks(p), _toks(g)
    if pt and gt and (pt <= gt or gt <= pt):
        return "thừa/thiếu một phần (bao nhau)"
    if _NUM.search(g) and _NUM.search(p):
        return "sai số / sai giá trị số"
    if ("," in g or ";" in g) or ("," in p or ";" in p):
        return "liệt kê sai phần tử"
    if pt & gt:
        return "trùng một phần từ"
    return "sai hẳn (khác ô)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--method", default="memxam_sckv.runv7full")
    ap.add_argument("--ref", default="fs.runfull")
    ap.add_argument("--dump", default="outputs/mas_tqa/eval/errors_memxam_sckv_test.json")
    args = ap.parse_args()

    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / args.qas)}
    raw = {q["qa_id"]: q for q in json.loads((ROOT / args.qas).read_text(encoding="utf-8"))["qas"]}
    M, F = load(ROOT / args.dir / f"{args.method}.jsonl"), load(ROOT / args.dir / f"{args.ref}.jsonl")
    tab = {t["table_id"]: t for t in next(iter(json.loads((ROOT / "dataset/table.json").read_text(encoding="utf-8")).values()))}
    ids = sorted(set(M) & set(F))

    rows = []
    for i in ids:
        qa, tr = qas[i], M[i]["trace"]
        pred = M[i]["prediction"][0]
        cands = tr["samples"] + [tr["B"]] + [tr[k] for k in ("A2", "B2") if k in tr]
        t = tab[qa["table_id"]]
        train = train_by_table()[qa["table_id"]]
        qt = _toks(qa["question"])
        jac = max((len(qt & _toks(r["question"])) / max(1, len(qt | _toks(r["question"]))) for r in train), default=0.0)
        m_ok = correct(pred, qa)
        rows.append({
            "qa_id": i, "table_id": qa["table_id"], "question": qa["question"], "gold": raw[i]["answer"], "pred": pred,
            "hints": raw[i]["hints"], "table_type": "+".join(sorted(t["table_type"])), "domain": t["table_domain"],
            "n_rows": t["table_html"].count("<tr"), "flat_chars": len(table_str(qa["table_id"])), "n_train": len(train),
            "max_jac": jac, "route": tr["route"], "M": m_ok, "FS": correct(F[i]["prediction"][0], qa),
            "oracle": int(any(correct(c, qa) for c in cands)), "a_votes": sum(correct(c, qa) for c in tr["samples"]),
            "B": correct(tr["B"], qa), "gold_toks": len(_toks(raw[i]["answer"])),
        })

    n = len(rows)
    em = lambda s: 100 * sum(r["M"] for r in s) / max(1, len(s))  # noqa: E731
    fs = lambda s: 100 * sum(r["FS"] for r in s) / max(1, len(s))  # noqa: E731
    orc = lambda s: 100 * sum(r["oracle"] for r in s) / max(1, len(s))  # noqa: E731
    print(f"n={n}  MemXam EM {em(rows):.2f}  FS {fs(rows):.2f}  oracle ứng viên {orc(rows):.2f}\n")

    def table(title: str, key) -> None:
        g = defaultdict(list)
        for r in rows:
            for k in (key(r) if isinstance(key(r), list) else [key(r)]):
                g[k].append(r)
        print(f"== {title}")
        print(f"{'nhóm':<46}{'n':>5}{'MemXam':>8}{'FS':>7}{'gain':>7}{'oracle':>8}{'#sai':>6}")
        for k, s in sorted(g.items(), key=lambda kv: em(kv[1])):
            print(f"{str(k)[:45]:<46}{len(s):5d}{em(s):8.1f}{fs(s):7.1f}{em(s) - fs(s):+7.1f}{orc(s):8.1f}{sum(1 - r['M'] for r in s):6d}")
        print()

    table("Loại câu hỏi (hints; một câu có thể nhiều nhãn)", lambda r: [h.split(" (")[0][:45] for h in r["hints"]])
    table("Loại bảng", lambda r: r["table_type"])
    table("Số dòng bảng", lambda r: bucket(r["n_rows"], [0, 10, 20, 40, 80]))
    table("Độ dài Flatten V1 (ký tự)", lambda r: bucket(r["flat_chars"], [0, 2000, 4000, 8000, 16000]))
    table("Số QA train cùng bảng (memory)", lambda r: bucket(r["n_train"], [0, 10, 20, 40]))
    table("Jaccard lớn nhất với câu train cùng bảng", lambda r: bucket(r["max_jac"], [0, 0.3, 0.5, 0.8]))
    table("Độ dài đáp án gold (token)", lambda r: bucket(r["gold_toks"], [0, 2, 4, 8, 16]))
    table("Route", lambda r: r["route"])
    table("Số mẫu A đúng (/3) + B", lambda r: f"A {r['a_votes']}/3, B {'đúng' if r['B'] else 'sai'}")
    table("Lĩnh vực (domain)", lambda r: r["domain"])

    wrong = [r for r in rows if not r["M"]]
    print(f"== {len(wrong)} câu sai")
    print(f"  gold có trong ứng viên nhưng bị bỏ phiếu loại: {sum(r['oracle'] for r in wrong)}")
    print(f"  không ứng viên nào đúng:                      {sum(1 - r['oracle'] for r in wrong)}")
    print(f"  FS đúng mà MemXam sai (hồi quy):              {sum(r['FS'] for r in wrong)}")
    kinds = Counter(error_kind(r["pred"], r["gold"], r["oracle"]) for r in wrong)
    for k, c in kinds.most_common():
        print(f"  {k:<36}{c:5d}")
    tbl = Counter(r["table_id"] for r in wrong)
    tot = Counter(r["table_id"] for r in rows)
    print("\n== Bảng sai nhiều nhất (sai/tổng)")
    for t, c in tbl.most_common(12):
        tt = tab[t]
        print(f"  {t:<8}{c:3d}/{tot[t]:<3d} {tt['table_title'][:50]:<52}{'+'.join(tt['table_type']):<40}{tt['table_html'].count('<tr')} dòng")
    for r in wrong:
        r["kind"] = error_kind(r["pred"], r["gold"], r["oracle"])
    (ROOT / args.dump).write_text(json.dumps(wrong, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nĐã ghi {args.dump}")


if __name__ == "__main__":
    main()
