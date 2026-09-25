"""Q8 evidence grounding, Q11 hint predictor & tokens, no_hp robustness,
plus refinements (inflation decomposition, fair det-variant comparison)."""
from __future__ import annotations

import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict

import numpy as np

from common import (AN, PATHS, an_variants_replay, auroc, deterministic_variants_no_forcing,
                    dump, em, is_null_answer, load_json, normalize_text, preds_by_id,
                    qas_by_id, recorded_run_an, traces_by_id, variant_sets_agree, OUT)
from evaluation.io import load_json_records
from evaluation.hint_metrics import evaluate_hint_metrics
from evaluation.normalization import parse_list_items
from preprocessing.representation import create_representation

qas = qas_by_id()
rows = load_json(OUT / "instances_with_cats.json")
byid = {r["qa_id"]: r for r in rows}
N = len(rows)
R = {}


def pct(a, b):
    return None if not b else round(100.0 * a / b, 2)


def ws(s):
    return " ".join(unicodedata.normalize("NFC", str(s)).split())


def cnorm(s):
    s = ws(s)
    s = re.sub(r"\s*<header>\s*$", "", s)
    s = s.replace("<header>", "").strip()
    s = s.strip('"').strip("“”").strip()
    return s.casefold()


# ============================================================ Q8 evidence
tables = {str(t["table_id"]): t for t in load_json_records(PATHS["tables"])}
flat_cache = {}


def flat(tid):
    if tid not in flat_cache:
        rep = create_representation(tables[tid])
        s = rep.to_string()
        lines = s.split("\n")
        cells = set()
        for ln in lines:
            for c in ln.split("|"):
                c2 = cnorm(c)
                if c2:
                    cells.add(c2)
        flat_cache[tid] = (ws(s).casefold(), cells, [cnorm(c) for c in cells])
    return flat_cache[tid]


ev_items = []
spec_feats = []
for r in rows:
    if not r["traced"]:
        continue
    tid = qas[r["qa_id"]]["table_id"]
    tstr, cells, cell_list = flat(tid)
    for s in r["specialists"]:
        evs = s["evidence"] or []
        n_items = len(evs)
        lit = 0
        parts_total = parts_exact = parts_sub = 0
        all_exact = True
        for e in evs:
            e_lit = ws(e).casefold() in tstr
            lit += e_lit
            parts = [cnorm(p) for p in str(e).split("|")]
            parts = [p for p in parts if p]
            for p in parts:
                parts_total += 1
                ex = p in cells
                sub = ex or any(p in c for c in cell_list) or (p in tstr)
                parts_exact += ex
                parts_sub += sub
                all_exact &= ex
            ev_items.append({"literal": e_lit, "n_parts": len(parts)})
        ans = s["answer"]
        a_norm = cnorm(ans) if ans is not None else ""
        ans_in_table = (not is_null_answer(ans)) and (a_norm in cells or any(a_norm in c for c in cell_list))
        spec_feats.append({
            "qa_id": r["qa_id"], "agent": s["agent"], "null": bool(s["raw_null"]),
            "correct": bool(s["correct_an_bestK"]), "correct_first": bool(s["correct_an_first"]),
            "gold_null": r["gold_null"], "n_ev": n_items,
            "ev_literal_frac": (lit / n_items) if n_items else None,
            "parts_exact_frac": (parts_exact / parts_total) if parts_total else None,
            "parts_sub_frac": (parts_sub / parts_total) if parts_total else None,
            "all_parts_exact": (all_exact and parts_total > 0),
            "ans_in_table": ans_in_table, "confidence": s["confidence"],
        })

q8 = {"n_evidence_items": len(ev_items),
      "evidence_item_literal_substring_of_flat_table_pct": pct(sum(e["literal"] for e in ev_items), len(ev_items)),
      "n_specialist_outputs": len(spec_feats),
      "outputs_with_empty_evidence": sum(f["n_ev"] == 0 for f in spec_feats),
      "empty_evidence_by_null": dict(Counter((f["null"], f["n_ev"] == 0) for f in spec_feats).items()).__repr__()}
nn = [f for f in spec_feats if not f["null"] and f["n_ev"] > 0]
q8["nonnull_with_evidence"] = len(nn)
q8["cell_part_exact_match_rate_pct (all parts, pooled over nonnull outputs)"] = pct(sum(f["parts_exact_frac"] for f in nn), len(nn))
q8["cell_part_substring_match_rate_pct"] = pct(sum(f["parts_sub_frac"] for f in nn), len(nn))
q8["outputs_all_parts_exact_pct"] = pct(sum(f["all_parts_exact"] for f in nn), len(nn))
q8["outputs_any_literal_item_pct"] = pct(sum((f["ev_literal_frac"] or 0) > 0 for f in nn), len(nn))


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold)); fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum((not p) and g for p, g in zip(pred, gold))
    return {"precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "n_flagged": tp + fp, "base_rate": sum(gold) / len(gold) if gold else None}


y = [f["correct"] for f in nn]
q8["base_accuracy_nonnull_with_evidence_pct"] = pct(sum(y), len(y))
q8["predict_correct"] = {
    "AUROC_parts_exact_frac": auroc([f["parts_exact_frac"] for f in nn], y),
    "AUROC_parts_sub_frac": auroc([f["parts_sub_frac"] for f in nn], y),
    "AUROC_literal_frac": auroc([f["ev_literal_frac"] for f in nn], y),
    "grounded(all_parts_exact)->correct": prf([f["all_parts_exact"] for f in nn], y),
    "grounded(parts_sub_frac==1)->correct": prf([f["parts_sub_frac"] == 1 for f in nn], y),
    "UNgrounded(parts_sub_frac<1) -> wrong": prf([f["parts_sub_frac"] < 1 for f in nn], [not v for v in y]),
    "acc_if_all_parts_exact_pct": pct(sum(f["correct"] for f in nn if f["all_parts_exact"]), sum(f["all_parts_exact"] for f in nn)),
    "acc_if_not_all_parts_exact_pct": pct(sum(f["correct"] for f in nn if not f["all_parts_exact"]), sum(not f["all_parts_exact"] for f in nn)),
    "AUROC_answer_in_table": auroc([f["ans_in_table"] for f in nn], y),
    "answer_in_table_rate_pct": pct(sum(f["ans_in_table"] for f in nn), len(nn)),
}
# per-agent grounding
pa = defaultdict(lambda: [0, 0, 0])
for f in nn:
    pa[f["agent"]][0] += 1; pa[f["agent"]][1] += f["all_parts_exact"]; pa[f["agent"]][2] += f["correct"]
q8["per_agent(n, pct_all_parts_exact, acc_pct)"] = {k: (v[0], pct(v[1], v[0]), pct(v[2], v[0])) for k, v in pa.items()}
# as Null-checker: hallucinations on gold-null (traced) vs correct non-null on answerable
hal = [f for f in spec_feats if f["gold_null"] and not f["null"]]
ans_ok = [f for f in spec_feats if (not f["gold_null"]) and (not f["null"]) and f["correct"]]
ans_bad = [f for f in spec_feats if (not f["gold_null"]) and (not f["null"]) and not f["correct"]]
q8["null_checker"] = {
    "hallucinated_outputs_traced": len(hal),
    "hallucinated_all_parts_exact": sum(f["all_parts_exact"] for f in hal),
    "hallucinated_parts_sub_frac_mean": statistics.mean([f["parts_sub_frac"] for f in hal if f["parts_sub_frac"] is not None]) if hal else None,
    "correct_nonnull_all_parts_exact_pct": pct(sum(f["all_parts_exact"] for f in ans_ok), len(ans_ok)),
    "wrong_nonnull_answerable_all_parts_exact_pct": pct(sum(f["all_parts_exact"] for f in ans_bad), len(ans_bad)),
    "rule 'flag Null if evidence not fully grounded' on nonnull outputs": {
        "flags": sum((not f["all_parts_exact"]) for f in spec_feats if not f["null"]),
        "flags_on_gold_null": sum((not f["all_parts_exact"]) for f in hal),
        "flags_on_answerable_correct (would become false abstentions)": sum((not f["all_parts_exact"]) for f in ans_ok),
    },
}
# false abstentions: Null outputs on answerable questions -- do they cite evidence?
fa = [f for f in spec_feats if (not f["gold_null"]) and f["null"]]
tn = [f for f in spec_feats if f["gold_null"] and f["null"]]
q8["null_outputs"] = {
    "false_abstention_outputs": len(fa), "FA_with_nonempty_evidence": sum(f["n_ev"] > 0 for f in fa),
    "FA_with_all_parts_exact": sum(f["all_parts_exact"] for f in fa),
    "correct_null_outputs": len(tn), "correctNull_with_nonempty_evidence": sum(f["n_ev"] > 0 for f in tn),
    "correctNull_all_parts_exact": sum(f["all_parts_exact"] for f in tn),
    "AUROC_nonempty_evidence_for_FA_vs_correctNull": auroc([f["n_ev"] > 0 for f in fa + tn], [True] * len(fa) + [False] * len(tn)),
}
R["Q8"] = q8

# ============================================================ Q11 hints / tokens
main = preds_by_id("hp")
nohp = preds_by_id("no_hp")
qlist = list(qas.values())
hm_main = evaluate_hint_metrics(qlist, [{"qa_id": q, "predicted_hints": main[q]["predicted_hints"]} for q in qas])
hp_file = {p["qa_id"]: p for p in load_json(PATHS["hint_pred"])["predictions"]}
hm_file = evaluate_hint_metrics(qlist, [{"qa_id": q, "predicted_hints": hp_file[q]["predicted_hints"]} for q in qas])
same = sum(set(hp_file[q]["predicted_hints"]) == set(main[q]["predicted_hints"]) for q in qas)
q11 = {
    "hint_metrics_main_hp_run": {k: v for k, v in hm_main.items() if k != "coverage"},
    "hint_metrics_hint_predictor_file": {k: hm_file[k] for k in ("exact_set_accuracy", "jaccard", "micro", "macro")},
    "hint_predictor_file_equals_main_run_hints": same,
}
# confusion: predicted vs gold singletons
conf = Counter()
for r in rows:
    g = tuple(sorted(r["gold_hints"])); p = tuple(sorted(r["predicted_hints"]))
    if g != p:
        conf[f"{'+'.join(g)} -> {'+'.join(p)}"] += 1
q11["top_hint_confusions"] = dict(conf.most_common(15))
# specialists & tokens
tok = {k: sum(p["total_tokens"] for p in d.values()) for k, d in (("hp", main), ("no_hp", nohp))}
ptok = {k: sum(p["prompt_tokens"] for p in d.values()) for k, d in (("hp", main), ("no_hp", nohp))}
ctok = {k: sum(p["completion_tokens"] for p in d.values()) for k, d in (("hp", main), ("no_hp", nohp))}
q11["tokens"] = {"total": tok, "total_increase_pct": pct(tok["hp"] - tok["no_hp"], tok["no_hp"]),
                 "prompt": ptok, "prompt_increase_pct": pct(ptok["hp"] - ptok["no_hp"], ptok["no_hp"]),
                 "completion": ctok, "completion_increase_pct": pct(ctok["hp"] - ctok["no_hp"], ctok["no_hp"]),
                 "mean_specialists_hp": statistics.mean(r["n_specialists"] for r in rows),
                 "mean_specialists_gold_routing": statistics.mean(len(r["gold_hints"]) for r in rows)}
# estimate: per-instance prompt tokens vs table-reading calls; proxy table size = ZS baseline prompt tokens
zs = preds_by_id("ZS")
X_hp, y_hp, X_no, y_no = [], [], [], []
for q in qas:
    Tz = zs[q]["prompt_tokens"]
    r = byid[q]
    X_hp.append([1.0, Tz, r["n_specialists"] * Tz]); y_hp.append(main[q]["prompt_tokens"])
    ns = len(r["gold_hints"])
    X_no.append([1.0, ns * Tz]); y_no.append(nohp[q]["prompt_tokens"])
b_hp, *_ = np.linalg.lstsq(np.array(X_hp), np.array(y_hp, float), rcond=None)
b_no, *_ = np.linalg.lstsq(np.array(X_no), np.array(y_no, float), rcond=None)
meanTz = statistics.mean(zs[q]["prompt_tokens"] for q in qas)
q11["token_regression_ESTIMATE"] = {
    "proxy": "table size proxy Tz = ZS-baseline prompt tokens of the same question",
    "hp_prompt ~ c0 + c1*Tz + c2*nspec*Tz": list(map(float, b_hp)),
    "no_hp_prompt ~ d0 + d2*nspec*Tz": list(map(float, b_no)),
    "mean_Tz": meanTz,
    "est_extra_prompt_tokens_per_q_from_Tz_term_hp (c1*meanTz)": float(b_hp[1] * meanTz),
    "observed_mean_prompt_diff_per_q": (ptok["hp"] - ptok["no_hp"]) / N,
    "est_prompt_diff_due_to_more_specialists": float(b_no[1] * meanTz * (statistics.mean(r["n_specialists"] for r in rows) - statistics.mean(len(r["gold_hints"]) for r in rows))),
}
# paired per-instance deltas by (hp nspec, gold nspec)
d = defaultdict(list)
for q in qas:
    r = byid[q]
    d[f"hp{r['n_specialists']}_gold{len(r['gold_hints'])}"].append(main[q]["total_tokens"] - nohp[q]["total_tokens"])
q11["paired_total_token_delta_by_routing"] = {k: {"n": len(v), "mean_delta": round(statistics.mean(v))} for k, v in sorted(d.items())}
# accuracy with predicted vs gold hints
q11["EM_hp_vs_no_hp"] = {"hp_bestK": pct(sum(r["poma_bestK"] for r in rows), N), "no_hp_bestK": pct(sum(r["no_hp_bestK"] for r in rows), N),
                         "hp_first": pct(sum(r["poma_first"] for r in rows), N), "no_hp_first": pct(sum(r["no_hp_first"] for r in rows), N)}
R["Q11"] = q11

# ============================================================ no_hp robustness for Q3/Q4
trn = traces_by_id("no_hp_traces")
rb = Counter()
for q, t in trn.items():
    st = t["steps"]; sps = st["3_specialists"]
    if len(sps) < 2:
        continue
    rq = st["1_question_refiner"]
    calls = [c for c in t["llm_calls"] if c["agent_name"] == "AnswerNormalization"]
    with recorded_run_an():
        per, merged, ok, _ = an_variants_replay(sps, rq["normalized_question"], rq.get("target"), calls)
    rb["multi"] += 1
    rb["recon_exact"] += merged == st["4_answer_normalization"]["normalized_answers"]
    raws = [str(s["answer"]).strip() for s in sps]
    rb["dis_raw"] += any(x != raws[0] for x in raws[1:])
    dis = any(not variant_sets_agree(v or ["Null"], per[0] or ["Null"]) for v in per[1:])
    rb["dis_an"] += dis
    fo = [em((v or [""])[:1], qas[q]) for v in per]
    bo = [em(v or [""], qas[q]) for v in per]
    if dis:
        rb["dis_ge1_correct"] += any(bo)
        rb["dis_gain_first_variant"] += any(fo) and not fo[0]
    else:
        rb["agree_wrong"] += not any(bo)
    nul = [is_null_answer(x) for x in raws]
    rb["hedge_raw"] += any(nul) and not all(nul)
R["no_hp_robustness_multi_traced"] = dict(rb)
R["no_hp_traced_n"] = len(trn)

# ============================================================ refinements
# (a) fair comparison: POMA-first + same deterministic variants as baselines
pf_det = 0
for r in rows:
    dv = deterministic_variants_no_forcing(r["cand"][0], r["question"]) or ["Null"]
    pf_det += em(dv, qas[r["qa_id"]])
R["fair_det_variant_comparison"] = {
    "POMA_first_plus_det_variants_EM": pct(pf_det, N),
    "FS_plus_det_variants_EM": pct(sum(r["FS_det_correct"] for r in rows), N),
    "ZS_plus_det_variants_EM": pct(sum(r["ZS_det_correct"] for r in rows), N),
    "CoT_plus_det_variants_EM": pct(sum(r["CoT_det_correct"] for r in rows), N),
    "TD_plus_det_variants_EM": pct(sum(r["TD_det_correct"] for r in rows), N),
    "POMA_bestK_EM": pct(sum(r["poma_bestK"] for r in rows), N),
}
# (b) inflation decomposition refined
BOOL = {"có", "không", "đúng", "sai", "phải", "không phải", "yes", "no", "true", "false"}
infl = Counter(); ex = defaultdict(list)
for r in rows:
    if not (r["poma_bestK"] and not r["poma_first"]):
        continue
    q = qas[r["qa_id"]]; first = r["cand"][0]
    j = next(i for i, c in enumerate(r["cand"]) if em([c], q)); hit = r["cand"][j]
    nf, nh = normalize_text(first), normalize_text(hit)
    reason = None
    if r["specialists"] is not None and len(r["specialists"]) >= 2 and not em(r["specialists"][0]["an_variants"] or [""], q):
        reason = "cross-specialist: only 2nd specialist correct"
    elif nf in BOOL and nh in BOOL:
        reason = "yes/no synonym"
    elif parse_list_items(first) and parse_list_items(hit):
        reason = "list delimiter/permutation"
    elif parse_list_items(first) and nh.replace(" ", "") == re.sub(r"[,;\s]", "", nf):
        reason = "list space-joined"
    elif re.search(r"\d", first) and re.search(r"\d", hit) and (nh in nf or nf in nh):
        reason = "number/date/unit/rank surface form (substring)"
    elif nh in nf:
        reason = "text shortened (hit is substring of first)"
    elif r["specialists"] is None:
        reason = "untraced multi: hit not derivable from first (likely 2nd specialist)"
    else:
        reason = "other surface form (hit NOT substring of first)"
    infl[reason] += 1
    if len(ex[reason]) < 6:
        ex[reason].append({"qa_id": r["qa_id"], "first": first[:70], "hit": hit[:70], "gold": r["gold"][:70], "K": r["K"], "n_spec": r["n_specialists"]})
R["inflation_decomposition_refined"] = dict(infl)
R["inflation_examples_refined"] = ex
# (c) yes/no surface-form: how often gold polarity word is predictable from the question
yn = Counter()
for r in rows:
    g = normalize_text(r["gold"])
    if g not in BOOL:
        continue
    qn = normalize_text(r["question"])
    pos = g in {"có", "đúng", "phải", "yes", "true"}
    if "có phải" in qn or "phải không" in qn or qn.startswith("phải"):
        pred = "phải" if pos else "không phải"
    elif "đúng" in qn:
        pred = "đúng" if pos else "sai"
    else:
        pred = "có" if pos else "không"
    yn["n"] += 1; yn[f"gold={g}"] += 1
    yn["echo_rule_matches_gold_form"] += (pred == g)
R["yesno_surface_form"] = dict(yn)
# (d) stored-evaluation answerability counts (reviewer's 12?)
st = load_json(PATHS["hp"])["evaluation"]["samples"]
R["stored_eval_answerability"] = {f"gold={a}|pred={b}": n for (a, b), n in Counter((s["gold_answerability"], s["pred_answerability"]) for s in st).items()}

dump("results_q8_q11.json", R)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:20000])
