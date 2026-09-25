"""Refinements: provenance-based best-of-K inflation decomposition, train-learned
yes/no surface-form formatter (estimate), paired bootstrap CIs, per-type table."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from common import (AN, REPO, deterministic_variants_no_forcing, dump, em, is_null_answer,
                    load_json, normalize_text, old_list_variants, qas_by_id, OUT)
from evaluation.bootstrap import paired_bootstrap_ci
from evaluation.io import load_qas_records

qas = qas_by_id()
rows = load_json(OUT / "instances_with_cats.json")
N = len(rows)
R = {}


def pct(a, b):
    return None if not b else round(100.0 * a / b, 2)


def nset(vs):
    return {normalize_text(v) for v in vs}


# -------------------------------------------- provenance of best-of-K-only hits
prov = Counter()
prov_kind = Counter()
ex = defaultdict(list)
for r in rows:
    if not (r["poma_bestK"] and not r["poma_first"]):
        continue
    q = qas[r["qa_id"]]
    first = r["cand"][0]
    hits = [c for c in r["cand"] if em([c], q)]
    qn = r.get("refined_question") or r["question"]
    det = nset(deterministic_variants_no_forcing(first, qn) or []) | nset(deterministic_variants_no_forcing(first, r["question"]) or [])
    perm = nset(old_list_variants(AN._strip_terminal_punctuation(first)))
    kind = AN._infer_answer_kind(AN._strip_terminal_punctuation(first), qn)
    first_spec_vars = None
    if r["specialists"] is not None and len(r["specialists"]) >= 2:
        first_spec_vars = r["specialists"][0]["an_variants"] or []
    if first_spec_vars is not None and not em(first_spec_vars or [""], q):
        p = "cross-specialist (2nd specialist's answer; traced)"
    elif is_null_answer(first):
        p = "first candidate is Null, a later non-Null candidate is correct (hedged set)"
    elif any(normalize_text(h) in det for h in hits):
        p = "deterministic AN variant of the first candidate"
        prov_kind[kind or "text(context/spacing/rank)"] += 1
    elif any(normalize_text(h) in perm for h in hits):
        p = "list delimiter/adjacent-swap variant of the first candidate"
    elif r["specialists"] is None:
        p = "untraced 2-specialist: not derivable from first candidate (likely 2nd specialist)"
    else:
        p = "LLM-normalizer variant only (not deterministically derivable)"
    prov[p] += 1
    if len(ex[p]) < 5:
        ex[p].append({"qa_id": r["qa_id"], "first": first[:70], "hit": hits[0][:70], "gold": r["gold"][:70]})
R["bestK_only_provenance"] = {"total": sum(prov.values()), "counts": dict(prov),
                              "deterministic_by_answer_kind": dict(prov_kind), "examples": ex}

# -------------------------------------------- yes/no formatter learned on train (ESTIMATE)
BOOL_POS = {"có", "đúng", "phải", "yes", "true"}
BOOL_NEG = {"không", "sai", "không phải", "no", "false", "không đúng"}
CUES = ["có phải", "phải không", "phải chăng", "đúng không", "có đúng", "đúng hay", "đúng", "phải", "có"]


def cue(qtext):
    t = normalize_text(qtext)
    for c in CUES:
        if c in t:
            return c
    return "none"


train = load_qas_records(REPO / "dataset/qas_train.json")
tab = defaultdict(Counter)
for q in train:
    g = normalize_text(q["answer"])
    if g in BOOL_POS | BOOL_NEG:
        tab[(cue(q["question"]), g in BOOL_POS)][g] += 1
rule = {k: v.most_common(1)[0][0] for k, v in tab.items()}
yn = Counter()
for r in rows:
    g = normalize_text(r["gold"])
    if g not in BOOL_POS | BOOL_NEG:
        continue
    pol = g in BOOL_POS
    pred = rule.get((cue(r["question"]), pol), "có" if pol else "không")
    yn["n_test_bool_gold"] += 1
    yn["formatter_correct_given_true_polarity"] += (pred == g)
    # applied to POMA first candidate (polarity from POMA)
    f = normalize_text(r["cand"][0])
    if f in BOOL_POS | BOOL_NEG:
        yn["poma_first_is_bool"] += 1
        p2 = rule.get((cue(r["question"]), f in BOOL_POS), "có" if f in BOOL_POS else "không")
        yn["poma_first_correct_raw"] += (f == g)
        yn["poma_first_correct_after_formatter"] += (p2 == g)
        yn["poma_bestK_correct"] += r["poma_bestK"]
R["yesno_formatter_ESTIMATE"] = {"learned_on": "qas_train.json yes/no-gold items; key=(first matching cue, polarity) -> majority gold word",
                                 "rule_table": {f"{k[0]}|{'pos' if k[1] else 'neg'}": v for k, v in rule.items()},
                                 **yn}
# EM of POMA-first with train-learned yes/no formatter applied (single answer)
fixed = 0
for r in rows:
    q = qas[r["qa_id"]]
    f = normalize_text(r["cand"][0])
    if f in BOOL_POS | BOOL_NEG:
        p2 = rule.get((cue(r["question"]), f in BOOL_POS), "có" if f in BOOL_POS else "không")
        fixed += em([p2], q)
    else:
        fixed += r["poma_first"]
R["yesno_formatter_ESTIMATE"]["EM_POMA_first_with_formatter_992"] = pct(fixed, N)

# -------------------------------------------- paired bootstrap (repo implementation)
def vec(key):
    return [float(bool(r[key])) for r in rows]


pf_det = []
for r in rows:
    dv = deterministic_variants_no_forcing(r["cand"][0], r["question"]) or ["Null"]
    pf_det.append(float(em(dv, qas[r["qa_id"]])))
ids = [r["qa_id"] for r in rows]
bs = {}
for name, a, b in (
    ("POMA_bestK - FS(single)", vec("poma_bestK"), vec("FS_correct")),
    ("POMA_first - FS(single)", vec("poma_first"), vec("FS_correct")),
    ("POMA_first+det - FS+det", pf_det, vec("FS_det_correct")),
    ("POMA_bestK - FS+det", vec("poma_bestK"), vec("FS_det_correct")),
    ("POMA_bestK - POMA_first", vec("poma_bestK"), vec("poma_first")),
):
    res = paired_bootstrap_ci(a, b, samples=10000, seed=20260729, system_a_ids=ids, system_b_ids=ids)
    bs[name] = {"diff_pts": round(100 * res["point_estimate"], 2), "ci95_pts": [round(100 * res["lower"], 2), round(100 * res["upper"], 2)]}
R["paired_bootstrap"] = bs

# -------------------------------------------- per-type compact table (Q10)
types = ["Why", "MathematicalReasoning", "List", "MultiConditions", "YesNo", "What", "When", "Where", "Who", "How"]
t10 = {}
for h in types:
    rs = [r for r in rows if h in r["gold_hints"]]
    c = Counter(r["cat"] for r in rs)
    t10[h] = {
        "n": len(rs), "bestK_EM": pct(sum(r["poma_bestK"] for r in rs), len(rs)), "first_EM": pct(sum(r["poma_first"] for r in rs), len(rs)),
        "FS_EM": pct(sum(r["FS_correct"] for r in rs), len(rs)),
        "multi_spec": sum(r["n_specialists"] >= 2 for r in rs),
        "single_wrong": c["single_wrong"], "multi_agree_wrong": c["multi_agree_wrong"],
        "multi_disagree_recoverable": c["multi_disagree_ge1_correct"], "multi_disagree_none": c["multi_disagree_none_correct"],
        "multi_untraced_wrong": c["multi_untraced_wrong_bestK"],
        "surface_only(bestK ok, first wrong)": sum(r["poma_bestK"] and not r["poma_first"] for r in rs),
        "gold_null": sum(r["gold_null"] for r in rs),
        "invisible_errors(single_wrong+agree_wrong)": c["single_wrong"] + c["multi_agree_wrong"],
        "bestK_errors": sum(not r["poma_bestK"] for r in rs),
    }
R["Q10_compact"] = t10
dump("results_refine.json", R)
print(json.dumps(R, ensure_ascii=False, indent=1)[:9000])
