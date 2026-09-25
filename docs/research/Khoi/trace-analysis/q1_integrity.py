"""Q1: data integrity, EM reproduction, provenance of Table 6 'w/o AN'."""
from __future__ import annotations

from collections import Counter

from common import (PATHS, REPO, dump, em, load_json, preds_by_id, qas_by_id,
                    traces_by_id, an_variants_replay, AN_PATCH_NOTE)
from evaluation.run import evaluate_files
from evaluation import exact_match, f1, rouge1, meteor
from evaluation.contracts import AlignedSample
from evaluation.io import align_records, load_json_records

R = {"an_patch_note": AN_PATCH_NOTE}
qas = qas_by_id()

# ---- instance counts per file
counts = {}
for k, p in PATHS.items():
    if k in ("tables",):
        continue
    d = load_json(p)
    if isinstance(d, list):
        counts[str(p.relative_to(REPO))] = {"type": "list", "n": len(d)}
    else:
        n = len(d.get("predictions", d.get("qas", [])))
        counts[str(p.relative_to(REPO))] = {"type": "dict", "keys": list(d.keys()), "n_predictions": n}
for sub in ("specialists", "refiner", "normalization"):
    for tag in ("hp", "no_hp"):
        p = REPO / f"outputs/poma/qwen/{sub}/poma_qas_test_qwen3_8b_{tag}.json"
        counts[str(p.relative_to(REPO))] = {"type": "list", "n": len(load_json(p))}
R["instance_counts"] = counts

# ---- which 592? position in main-output order
main_hp = load_json(PATHS["hp"])["predictions"]
tr_hp = traces_by_id("hp_traces")
order = [p["qa_id"] for p in main_hp]
pos = [i for i, q in enumerate(order) if q in tr_hp]
R["hp_traced_subset"] = {
    "n": len(tr_hp), "positions_in_main_order": [min(pos), max(pos)],
    "contiguous_tail": pos == list(range(len(order) - len(tr_hp), len(order))),
    "specialists_file_same_ids": set(x["qa_id"] for x in load_json(REPO / "outputs/poma/qwen/specialists/poma_qas_test_qwen3_8b_hp.json")) == set(tr_hp),
    "normalized_answers_equal_main_predicted_answer": sum(
        1 for q, t in tr_hp.items() if t["steps"]["4_answer_normalization"]["normalized_answers"] == next(p for p in main_hp if p["qa_id"] == q)["predicted_answer"]),
}
main_nohp = load_json(PATHS["no_hp"])["predictions"]
tr_nohp = traces_by_id("no_hp_traces")
order2 = [p["qa_id"] for p in main_nohp]
pos2 = [i for i, q in enumerate(order2) if q in tr_nohp]
R["no_hp_traced_subset"] = {"n": len(tr_nohp), "positions_in_main_order": [min(pos2), max(pos2)],
                            "contiguous_tail": pos2 == list(range(len(order2) - len(tr_nohp), len(order2)))}
# is the traced subset representative? gold hint mix + null share
def mix(ids):
    c = Counter()
    for q in ids:
        for h in qas[q]["hints"]:
            c[h] += 1
    return c
from common import gold_canon_hints, gold_is_null
def profile(ids):
    ids = list(ids)
    c = Counter(h for q in ids for h in gold_canon_hints(qas[q]))
    return {"n": len(ids), "gold_null": sum(gold_is_null(qas[q]) for q in ids),
            "hint_share": {k: round(v / len(ids), 3) for k, v in sorted(c.items())}}
R["hp_traced_vs_untraced_profile"] = {
    "traced": profile(tr_hp), "untraced": profile(set(qas) - set(tr_hp))}

# ---- reproduce stored metrics with repo evaluator
def full_eval(path, policy="all"):
    rep = evaluate_files(path, PATHS["qas"], metrics=["f1", "em", "rouge1", "meteor", "answerability_f1"], candidate_policy=policy)
    m = rep["metrics"]
    return {"n": len(rep["coverage"]["evaluated_ids"]),
            "missing_predictions": len(rep["coverage"]["missing_predictions"]),
            "EM": m["em"]["value"], "F1": m["f1"]["f1"],
            "R1": m["rouge1"]["f1"], "MET": m["meteor"]["value"],
            "answerability_confusion": rep["analyses"]["answerability_f1"]["confusion"],
            "answerability_f1": {k: v["f1"] for k, v in rep["analyses"]["answerability_f1"]["per_class"].items()},
            "candidate_stats": rep["source_candidate_statistics"]}
R["repro"] = {}
for k in ("hp", "no_hp", "FS", "ZS", "CoT", "TD", "abl_hp", "abl_no_hp"):
    R["repro"][k] = full_eval(PATHS[k])
    R["repro"][k]["stored_overall_EM"] = load_json(PATHS[k])["evaluation"]["overall"]["exact_match"]
    R["repro"][k]["stored_overall_F1"] = load_json(PATHS[k])["evaluation"]["overall"]["f1_score"]
R["repro"]["hp_first_candidate"] = full_eval(PATHS["hp"], policy="first")
R["repro"]["no_hp_first_candidate"] = full_eval(PATHS["no_hp"], policy="first")

# ---- ablation files: provenance
for k in ("abl_hp", "abl_no_hp"):
    d = load_json(PATHS[k])
    preds = d["predictions"]
    # price check: implied $/M from per-record cost = a*prompt + b*completion
    import numpy as np
    A = np.array([[p["prompt_tokens"], p["completion_tokens"]] for p in preds], float)
    y = np.array([p["cost_usd"] for p in preds], float)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    ev = sum(em(p["predicted_answer"], qas[p["qa_id"]]) for p in preds)
    R.setdefault("ablation", {})[k] = {
        "ablation_block": {kk: vv for kk, vv in d["ablation"].items() if kk != "skipped_missing_stage3_qa_ids"},
        "n_predictions": len(preds),
        "EM_on_available": ev / len(preds), "correct": ev,
        "EM_over_992_missing_as_wrong": ev / 992,
        "implied_price_usd_per_M_tokens": {"prompt": coef[0] * 1e6, "completion": coef[1] * 1e6},
        "candidate_len_dist": dict(Counter(len(p["predicted_answer"]) for p in preds)),
    }
for k in ("hp", "no_hp"):
    preds = load_json(PATHS[k])["predictions"]
    import numpy as np
    A = np.array([[p["prompt_tokens"], p["completion_tokens"]] for p in preds], float)
    y = np.array([p["cost_usd"] for p in preds], float)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    R.setdefault("price_check", {})[k] = {"prompt": coef[0] * 1e6, "completion": coef[1] * 1e6}

# ---- Qwen3-8B w/o AN from raw specialist answers (592 traced hp; 621 no_hp)
def eval_candidate_lists(cands_by_id):
    preds = [{"qa_id": q, "predicted_answer": c} for q, c in cands_by_id.items()]
    samples, _ = align_records(preds, list(qas.values()))
    out = {}
    out["n"] = len(samples)
    out["EM"] = exact_match.aggregate(exact_match.score_sample(s) for s in samples)["value"]
    out["EM_correct"] = sum(exact_match.score_sample(s).value for s in samples)
    out["F1"] = f1.aggregate(f1.score_sample(s) for s in samples)["f1"]
    out["R1"] = rouge1.aggregate(rouge1.score_sample(s) for s in samples)["f1"]
    out["MET"] = meteor.aggregate(meteor.score_sample(s) for s in samples)["value"]
    return out

R["wo_AN_qwen"] = {}
for tag, trs, main in (("hp", tr_hp, main_hp), ("no_hp", tr_nohp, main_nohp)):
    mp = {p["qa_id"]: p for p in main}
    raw_all = {q: [str(s["answer"]) for s in t["steps"]["3_specialists"]] for q, t in trs.items()}
    raw_first = {q: v[:1] for q, v in raw_all.items()}
    raw_dedup = {q: t["steps"]["4_answer_normalization"]["raw_answers"] for q, t in trs.items()}
    with_an = {q: mp[q]["predicted_answer"] for q in trs}
    with_an_first = {q: mp[q]["predicted_answer"][:1] for q in trs}
    R["wo_AN_qwen"][tag] = {
        "subset_n": len(trs),
        "raw_best_of_K_all_specialists": eval_candidate_lists(raw_all),
        "raw_best_of_K_trace_raw_answers_field": eval_candidate_lists(raw_dedup),
        "raw_first_specialist_single": eval_candidate_lists(raw_first),
        "with_AN_best_of_K_same_subset": eval_candidate_lists(with_an),
        "with_AN_first_candidate_same_subset": eval_candidate_lists(with_an_first),
    }
    # flips on this subset
    w2r = r2w = 0
    for q in trs:
        a = em(raw_all[q], qas[q]); b = em(with_an[q], qas[q])
        w2r += (not a) and b; r2w += a and (not b)
    R["wo_AN_qwen"][tag]["AN_flips_wrong_to_right"] = w2r
    R["wo_AN_qwen"][tag]["AN_flips_right_to_wrong"] = r2w

# ---- the '177 / 17.84%' number: candidates
poma_c = {q: em(p["predicted_answer"], qas[q]) for q, p in ((p["qa_id"], p) for p in main_hp)}
zs = preds_by_id("ZS")
zs_c = {q: em(zs[q]["predicted_answer"], qas[q]) for q in qas}
R["n177_check"] = {
    "POMA_correct_992": sum(poma_c.values()), "ZS_correct_992": sum(zs_c.values()),
    "difference": sum(poma_c.values()) - sum(zs_c.values()),
    "POMA_right_ZS_wrong": sum(poma_c[q] and not zs_c[q] for q in qas),
    "ZS_right_POMA_wrong": sum(zs_c[q] and not poma_c[q] for q in qas),
    "68.41_as_fraction": {"405/592": 405 / 592, "678/992": 678 / 992, "679/992": 679 / 992},
}
dump("q1_integrity.json", R)
import json
print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:12000])
