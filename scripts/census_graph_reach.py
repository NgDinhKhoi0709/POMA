"""Điều tra độ phủ (reach) của hướng typed-graph trên Open-ViTabQA, không gọi API.

Trả lời ba câu hỏi trước khi chi tiền cho đề xuất GRAPH:
1. Đáp án gold thuộc dạng nào (ô nguyên văn, đoạn trong ô, số suy ra, Yes/No, Null, ...)
   và bao nhiêu phần trăm biểu diễn được bằng graph thao tác bảng có kiểu.
2. Bao nhiêu câu có >= 2 "đoạn" (proxy: >= 2 nhãn hint) để tách cho nhiều Skill Agent.
3. Chọn đáp án bằng vote + neo vào ô bảng (tất định) trên 6 artifact có sẵn có hơn FS+GSA không.
4. Node Verbalize (đổi từ Yes/No theo đuôi câu hỏi) trên đáp án đã lưu: EM ghép cặp và tỉ lệ tái tạo gold.

Mục 3 là phân tích hậu nghiệm trên test, chỉ để định hướng, không dùng chọn phương pháp.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import exact_match  # noqa: E402
from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from evaluation.normalization import normalize_text, parse_list_items  # noqa: E402
from src.table_executor.ast_executor import TableView, parse_number  # noqa: E402
from gap_tqa.nodes import YN_NEG, YN_POS, verbalize  # noqa: E402

YESNO = {"có", "không", "đúng", "sai", "phải", "không phải", "chưa"}
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
# Nhóm dạng đáp án mà một graph thao tác bảng có kiểu (select/filter/project/aggregate/compare) biểu diễn được.
GRAPH_EXPRESSIBLE = {"cell", "multi_cell", "yesno", "numeric_derived", "numeric_in_cell"}

D01 = "outputs/d01/openrouter_qwen_qwen3-8b"
D04 = "outputs/d04/openrouter_qwen_qwen3-8b/full"
SYSTEMS = {
    "few_shot": f"{D01}/few_shot_adapted.json",
    "poma_first": f"{D01}/poma_first.json",
    "poma_gsa": f"{D01}/poma_gsa_with_first_fallback.json",
    "few_shot_gsa": f"{D01}/few_shot_gsa_with_raw_fallback.json",
    "zero_shot": f"{D04}/zero_shot_adapted.json",
    "cot": f"{D04}/cot_adapted.json",
}


def as_number(text: str) -> float | None:
    try:
        return parse_number(text)
    except Exception:
        return None


def gold_kind(gold: str, cells: set[str], cell_texts: list[str], cell_numbers: set[float]) -> str:
    g = normalize_text(gold)
    if g == "null":
        return "null"
    if g in YESNO:
        return "yesno"
    if g in cells:
        return "cell"
    items = parse_list_items(gold)
    if items and all(normalize_text(i) in cells for i in items):
        return "multi_cell"
    number = as_number(gold)
    if number is not None:
        return "numeric_in_cell" if number in cell_numbers else "numeric_derived"
    if any(g in c for c in cell_texts):
        return "span_in_cell"
    if items and all(any(normalize_text(i) in c for c in cell_texts) for i in items):
        return "multi_span"
    return "free_text"


def table_index(table: dict) -> tuple[set[str], list[str], set[float]]:
    view = TableView.from_dataset(table)
    texts = [normalize_text(c) for row in view.rows for c in row if str(c).strip()]
    numbers = {as_number(m) for t in texts for m in NUM_RE.findall(t)} - {None}
    numbers |= {n for n in map(as_number, texts) if n is not None}
    return set(texts), texts, numbers


def grounded(answer: str, cells: set[str], cell_texts: list[str], cell_numbers: set[float]) -> bool:
    """Đáp án có neo được vào bảng không: là ô, đoạn trong ô, số trong bảng, Yes/No hoặc Null."""
    a = normalize_text(answer)
    if not a:
        return False
    if a in YESNO or a == "null" or a in cells or any(a in c for c in cell_texts):
        return True
    number = as_number(answer)
    return number is not None and number in cell_numbers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", default="dataset/qas_test.json")
    parser.add_argument("--tables", default="dataset/table.json")
    parser.add_argument("--train", default="dataset/qas_train.json")
    parser.add_argument("--out", default="outputs/graph_census/census.json")
    args = parser.parse_args()

    tables = {t["table_id"]: t for t in json.load(open(args.tables, encoding="utf-8"))["table"]}
    index = {tid: table_index(t) for tid, t in tables.items()}
    report: dict[str, object] = {}

    # 1 + 2: dạng đáp án gold và số đoạn, trên cả train và test.
    for split, path in (("train", args.train), ("test", args.qas)):
        qas = json.load(open(path, encoding="utf-8"))["qas"]
        kinds = Counter(gold_kind(q["answer"], *index[q["table_id"]]) for q in qas)
        n = len(qas)
        report[f"{split}_gold_kind"] = {k: [v, round(100 * v / n, 1)] for k, v in kinds.most_common()}
        report[f"{split}_graph_expressible_pct"] = round(100 * sum(kinds[k] for k in GRAPH_EXPRESSIBLE) / n, 1)
        hints = Counter(len(q["hints"]) for q in qas)
        report[f"{split}_hint_count"] = dict(sorted(hints.items()))
        report[f"{split}_ge2_segments_pct"] = round(100 * sum(v for k, v in hints.items() if k >= 2) / n, 1)

    # 3: ma trận đúng/sai của 6 hệ trên test.
    qas_list = json.load(open(args.qas, encoding="utf-8"))["qas"]
    qa_by_id = {q["qa_id"]: q for q in qas_list}
    scores: dict[str, dict[str, float]] = {}
    answers: dict[str, dict[str, str]] = {}
    for name, path in SYSTEMS.items():
        samples, _ = align_records(
            load_json_records(Path(path)), load_qas_records(Path(args.qas)), candidate_policy="single-required"
        )
        scores[name] = {s.qa_id: exact_match.score_sample(s).value for s in samples}
        preds = json.load(open(path, encoding="utf-8"))["predictions"]
        answers[name] = {p["qa_id"]: (p["prediction"][0] if p["prediction"] else "") for p in preds}
    ids = sorted(scores["few_shot_gsa"])

    # Lỗi của hệ mạnh nhất (FS+GSA) thuộc dạng gold nào -> graph có chạm tới được không.
    wrong = [i for i in ids if scores["few_shot_gsa"][i] < 1]
    wrong_kinds = Counter(gold_kind(qa_by_id[i]["answer"], *index[qa_by_id[i]["table_id"]]) for i in wrong)
    report["fs_gsa_wrong_n"] = len(wrong)
    report["fs_gsa_wrong_gold_kind"] = dict(wrong_kinds.most_common())
    report["fs_gsa_wrong_graph_expressible"] = sum(wrong_kinds[k] for k in GRAPH_EXPRESSIBLE)

    oracle = [max(scores[s][i] for s in SYSTEMS) for i in ids]
    report["oracle_of_6_em"] = round(100 * sum(oracle) / len(ids), 2)
    report["em"] = {s: round(100 * sum(scores[s].values()) / len(ids), 2) for s in SYSTEMS}

    # Selector tất định, chốt trước khi chạy: vote theo chuỗi chuẩn hoá; hoà thì ưu tiên
    # đáp án neo được vào bảng; vẫn hoà thì theo thứ tự SYSTEMS (few_shot_gsa đứng trước).
    order = ["few_shot_gsa", "poma_gsa", "few_shot", "poma_first", "zero_shot", "cot"]
    picks: dict[str, dict[str, str]] = {"vote": {}, "vote_grounded": {}}
    for i in ids:
        ctx = index[qa_by_id[i]["table_id"]]
        votes: dict[str, list[str]] = defaultdict(list)
        for s in order:
            votes[normalize_text(answers[s].get(i, ""))].append(s)
        best_vote = max(votes.values(), key=len)
        picks["vote"][i] = next(v for v in votes.values() if len(v) == len(best_vote))[0]
        ranked = sorted(
            votes.values(),
            key=lambda v: (len(v), grounded(answers[v[0]][i], *ctx), -order.index(v[0])),
            reverse=True,
        )
        picks["vote_grounded"][i] = ranked[0][0]
    base = [scores["few_shot_gsa"][i] for i in ids]
    for name, pick in picks.items():
        arm = [scores[pick[i]][i] for i in ids]
        ci = paired_bootstrap_ci(arm, base)
        report[f"selector_{name}"] = {
            "em": round(100 * sum(arm) / len(ids), 2),
            "vs_fs_gsa": ci.get("difference", ci),
            "wins": sum(a > b for a, b in zip(arm, base)),
            "losses": sum(a < b for a, b in zip(arm, base)),
        }

    # Verbalize: tái tạo gold Yes/No từ cực tính gold trên từng split (kiểm tra luật không khớp theo test).
    for split in ("train", "dev", "test"):
        split_qas = json.load(open(f"dataset/qas_{split}.json", encoding="utf-8"))["qas"]
        yn = [q for q in split_qas if normalize_text(q["answer"]) in YN_POS | YN_NEG]
        hit = sum(
            normalize_text(verbalize(q["question"], "có" if normalize_text(q["answer"]) in YN_POS else "không"))
            == normalize_text(q["answer"])
            for q in yn
        )
        report[f"verbalize_gold_reproduction_{split}"] = [len(yn), round(100 * hit / len(yn), 1)]

    # Verbalize áp lên đáp án đã lưu (tất định, không sinh lại): chấm bằng scorer của repo, ghép cặp với gốc.
    out_dir = Path(args.out).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("few_shot", "few_shot_gsa", "poma_gsa"):
        src = json.load(open(SYSTEMS[name], encoding="utf-8"))
        arm_path = out_dir / f"{name}_verbalize.json"
        arm_path.write_text(json.dumps({
            "manifest": {"derived_from": SYSTEMS[name], "transform": "scripts/census_graph_reach.py::verbalize"},
            "predictions": [
                dict(p, prediction=[verbalize(qa_by_id[p["qa_id"]]["question"], p["prediction"][0])])
                for p in src["predictions"]
            ],
        }, ensure_ascii=False), encoding="utf-8")
        samples, _ = align_records(
            load_json_records(arm_path), load_qas_records(Path(args.qas)), candidate_policy="single-required"
        )
        arm = {s.qa_id: exact_match.score_sample(s).value for s in samples}
        a, b = [arm[i] for i in ids], [scores[name][i] for i in ids]
        report[f"verbalize_{name}"] = {
            "em": round(100 * sum(a) / len(ids), 2),
            "vs_original": paired_bootstrap_ci(a, b).get("difference"),
            "wins": sum(x > y for x, y in zip(a, b)),
            "losses": sum(x < y for x, y in zip(a, b)),
        }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
