"""Bộ chọn học được thay bước bỏ phiếu cuối: logistic regression trên đặc trưng tất định của từng ứng viên.

Ứng viên = các đáp án khác nhau (theo key) trong {3 mẫu A, B, A2, B2}. Đặc trưng chỉ dùng thứ có
trong trace v7 (không dùng C) để áp được lên test. Huấn luyện/chọn trên dev (cross-validation theo
bảng), rồi áp đúng một lần lên test.

python scripts/selector_mas_tqa.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.io import load_qas_records  # noqa: E402
from evaluation.normalization import is_unanswerable_prediction, normalize_text  # noqa: E402
from mas_tqa.code_agent import table_rows  # noqa: E402
from mas_tqa.data import retrieve_same_table  # noqa: E402
from mas_tqa.methods import key, valid  # noqa: E402
from mas_tqa.style import harmonize  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402

FEATS = ["a_votes", "b", "a2", "b2", "debated", "is_top", "cell_exact", "cell_sub", "len_ratio", "null", "a_first"]


def cells(table_id: str, _cache: dict = {}) -> set[str]:  # noqa: B006
    if table_id not in _cache:
        _cache[table_id] = {normalize_text(c) for r in table_rows(table_id) for c in r if c.strip()}
    return _cache[table_id]


def candidates(rec: dict, qa: dict) -> list[dict]:
    t, q = rec["trace"], qa["question"]
    pool = [("A", x) for x in t["samples"]] + [("B", t["B"])]
    pool += [(r, t[r]) for r in ("A2", "B2") if t.get(r)]
    groups: dict[str, dict] = {}
    for role, ans in pool:
        if not valid(ans, q):
            continue
        g = groups.setdefault(key(ans, q), {"text": ans, "a_votes": 0, "b": 0, "a2": 0, "b2": 0})
        g["a_votes" if role == "A" else role.lower()] += 1
    if not groups:
        return []
    top = max(groups.values(), key=lambda g: g["a_votes"] + g["b"])
    demo_len = median([len(d["answer"]) for d in retrieve_same_table(qa, 16)] or [10])
    first = key(t["samples"][0], q) if t["samples"] else ""
    C = cells(qa["table_id"])
    out = []
    for k, g in groups.items():
        n = normalize_text(g["text"])
        out.append({
            **g, "debated": int("A2" in t), "is_top": int(g is top), "cell_exact": int(n in C),
            "cell_sub": int(n not in C and any(n in c for c in C if len(c) < 200)),
            "len_ratio": min(4.0, len(g["text"]) / max(1.0, demo_len)), "null": int(is_unanswerable_prediction(g["text"])),
            "a_first": int(k == first),
        })
    return out


def load(split: str, file: str) -> tuple[list[str], dict, dict]:
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"dataset/qas_{split}.json")}
    recs = {r["qa_id"]: r for r in map(json.loads, (ROOT / f"outputs/mas_tqa/qas_{split}/{file}.jsonl").read_text(encoding="utf-8").splitlines()) if r}
    return sorted(recs), qas, recs


def build(ids, qas, recs):
    X, y, grp, qid, texts = [], [], [], [], []
    for i in ids:
        for c in candidates(recs[i], qas[i]):
            X.append([c[f] for f in FEATS])
            y.append(correct(harmonize(c["text"], qas[i]), qas[i]))
            grp.append(qas[i]["table_id"]); qid.append(i); texts.append(c["text"])
    return np.array(X, float), np.array(y), np.array(grp), qid, texts


def pick(scores, qid, texts):
    best: dict[str, tuple[float, str]] = {}
    for s, i, t in zip(scores, qid, texts):
        if i not in best or s > best[i][0]:
            best[i] = (s, t)
    return {i: t for i, (_, t) in best.items()}


def evaluate(name, ids, qas, recs, chosen):
    base = {i: correct(harmonize(recs[i]["prediction"][0], qas[i]), qas[i]) for i in ids}
    new = {i: correct(harmonize(chosen.get(i, recs[i]["prediction"][0]), qas[i]), qas[i]) for i in ids}
    ci = paired_bootstrap_ci([new[i] for i in ids], [base[i] for i in ids], samples=5000)
    fix = sum(new[i] and not base[i] for i in ids)
    brk = sum(base[i] and not new[i] for i in ids)
    print(f"{name:<34} EM {100 * sum(new.values()) / len(ids):.2f} (gốc+định dạng {100 * sum(base.values()) / len(ids):.2f})  "
          f"Δ {100 * ci['point_estimate']:+.2f} [{100 * ci['lower']:+.2f}; {100 * ci['upper']:+.2f}]  sửa {fix} / hỏng {brk}")


def main() -> None:
    ids, qas, recs = load("dev", "memxam_sckv.runv8dev")
    X, y, grp, qid, texts = build(ids, qas, recs)
    print(f"dev: {len(ids)} câu, {len(y)} ứng viên, oracle {100 * len({i for i, v in zip(qid, y) if v}) / len(ids):.2f}")
    for C in (0.1, 1.0, 10.0):
        scores = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X, y, grp):
            m = LogisticRegression(C=C, max_iter=2000).fit(X[tr], y[tr])
            scores[te] = m.predict_proba(X[te])[:, 1]
        evaluate(f"dev CV 5-fold theo bảng, C={C}", ids, qas, recs, pick(scores, qid, texts))
    m = LogisticRegression(C=1.0, max_iter=2000).fit(X, y)
    print("hệ số:", {f: round(w, 2) for f, w in zip(FEATS, m.coef_[0])})
    if "--test" in sys.argv:  # áp một lần lên test, mô hình huấn luyện trên toàn bộ dev
        tids, tqas, trecs = load("test", "memxam_sckv.runv7full")
        TX, _, _, tqid, ttexts = build(tids, tqas, trecs)
        evaluate("TEST (huấn luyện trên dev)", tids, tqas, trecs, pick(m.predict_proba(TX)[:, 1], tqid, ttexts))


if __name__ == "__main__":
    main()
