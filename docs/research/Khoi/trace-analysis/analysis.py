"""Q2-Q10 on the per-instance table (instances.json). Offline, no LLM calls."""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict

from common import (auroc, canon_equal, deterministic_variants_no_forcing, dump,
                    em, is_null_answer, load_json, normalize_text, qas_by_id,
                    variant_sets_agree, OUT)

qas = qas_by_id()
rows = load_json(OUT / "instances.json")
N = len(rows)
R = {}


def pct(a, b):
    return None if not b else round(100.0 * a / b, 2)


def dvars(a, question):
    """Deterministic canonical variant set (repo AN deterministic rules, no
    Why/How Null forcing). Empty/None -> ['Null'] (evaluator treats '' as unanswerable)."""
    if a is None or str(a).strip() == "" or is_null_answer(a):
        return ["Null"]
    return deterministic_variants_no_forcing(str(a), question) or ["Null"]


def same_det(a, b, question):
    return variant_sets_agree(dvars(a, question), dvars(b, question))


# =========================================================== Q2 specialists
nspec_all = Counter(r["n_specialists"] for r in rows)
nspec_tr = Counter(r["n_specialists"] for r in rows if r["traced"])
gold_n = Counter(len(r["gold_hints"]) for r in rows)
R["Q2"] = {
    "hp_all992_from_predicted_hints": dict(sorted(nspec_all.items())),
    "hp_all992_single_share_pct": pct(nspec_all[1], N),
    "hp_all992_mean": sum(k * v for k, v in nspec_all.items()) / N,
    "hp_traced592_from_router": dict(sorted(nspec_tr.items())),
    "hp_traced592_single_share_pct": pct(nspec_tr[1], sum(nspec_tr.values())),
    "gold_hint_routing_all992 (no_hp run)": dict(sorted(gold_n.items())),
    "gold_hint_routing_single_share_pct": pct(gold_n[1], N),
    "gold_hint_routing_mean": sum(k * v for k, v in gold_n.items()) / N,
    "note": "router == predicted_hints (1:1, verified on all 592 traced); so #specialists for all 992 = len(predicted_hints) in main output",
}

# =========================================================== Q3 disagreement
multi = [r for r in rows if r["traced"] and r["n_specialists"] >= 2]
lvl = Counter()
examples_surface = []
for r in multi:
    sp = r["specialists"]
    qn = r["refined_question"]
    raws = [str(s["answer"]).strip() for s in sp]
    a0 = raws[0]
    d_raw = any(x != a0 for x in raws[1:])
    d_norm = any(not (normalize_text(x) == normalize_text(a0) or (is_null_answer(x) and is_null_answer(a0))) for x in raws[1:])
    d_canon = any(not canon_equal(x, a0) for x in raws[1:])
    d_det = any(not variant_sets_agree(dvars(x, qn), dvars(a0, qn)) for x in raws[1:])
    v0 = sp[0]["an_variants"] or ["Null"]
    d_an = any(not variant_sets_agree(s["an_variants"] or ["Null"], v0) for s in sp[1:])
    r["dis_raw"], r["dis_norm"], r["dis_canon"], r["dis_det"], r["dis_an"] = d_raw, d_norm, d_canon, d_det, d_an
    nulls = [is_null_answer(x) for x in raws]
    r["hedge_raw"] = any(nulls) and not all(nulls)
    an_null = [bool(s["an_null"]) for s in sp]
    an_nonnull = [bool(s["an_nonnull"]) for s in sp]
    r["hedge_an"] = (any(an_null) and any(an_nonnull))
    for k in ("dis_raw", "dis_norm", "dis_canon", "dis_det", "dis_an", "hedge_raw", "hedge_an"):
        lvl[k] += r[k]
    if d_raw and not d_an:
        examples_surface.append({"qa_id": r["qa_id"], "raw": raws})
R["Q3"] = {
    "n_multi_traced": len(multi),
    "disagree_counts": {
        "L0_raw_string_differs": lvl["dis_raw"],
        "L1_repo_normalize_text_differs": lvl["dis_norm"],
        "L2_canon_equal_differs(normalize_text + order-free list multiset + null==null)": lvl["dis_canon"],
        "L3_repo_AN_deterministic_variant_sets_disjoint": lvl["dis_det"],
        "L4_recorded_AN_variant_sets_disjoint (incl. LLM variants & Null forcing)": lvl["dis_an"],
    },
    "hedge_counts": {"raw_mixed_null_nonnull": lvl["hedge_raw"], "AN_level_mixed": lvl["hedge_an"]},
    "disagree_rate_pct_of_multi": {k: pct(v, len(multi)) for k, v in (("L0", lvl["dis_raw"]), ("L1", lvl["dis_norm"]), ("L2", lvl["dis_canon"]), ("L3", lvl["dis_det"]), ("L4", lvl["dis_an"]))},
    "disagree_rate_pct_of_traced592": {k: pct(v, 592) for k, v in (("L0", lvl["dis_raw"]), ("L4", lvl["dis_an"]))},
    "surface_only_disagreements_examples": examples_surface[:8],
}
# agent pairs
R["Q3"]["agent_pairs"] = dict(Counter("+".join(s["agent"] for s in r["specialists"]) for r in multi).most_common())
R["Q3"]["agent_pairs_disagree_L4"] = dict(Counter("+".join(s["agent"] for s in r["specialists"]) for r in multi if r["dis_an"]).most_common())

# =========================================================== Q4 gate headroom
def spec_ok(s, mode):
    return bool(s["correct_an_bestK"]) if mode == "an" else bool(s["correct_an_first"])


cat = Counter()
cat_ids = defaultdict(list)
for r in rows:
    if r["n_specialists"] == 1:
        s = r["specialists"][0]
        if s["correct_an_first"]:
            c = "single_correct_first_variant"
        elif s["correct_an_bestK"]:
            c = "single_correct_only_nonfirst_variant"
        else:
            c = "single_wrong"
    elif r["specialists"] is None:
        c = "multi_untraced_correct_bestK" if r["poma_bestK"] else "multi_untraced_wrong_bestK"
    else:
        oks = [spec_ok(s, "an") for s in r["specialists"]]
        if not r["dis_an"]:
            c = "multi_agree_all_correct" if all(oks) else ("multi_agree_some_correct" if any(oks) else "multi_agree_wrong")
        else:
            c = "multi_disagree_ge1_correct" if any(oks) else "multi_disagree_none_correct"
    r["cat"] = c
    cat[c] += 1
    cat_ids[c].append(r["qa_id"])

err_bestK = sum(1 for r in rows if not r["poma_bestK"])
err_first = sum(1 for r in rows if not r["poma_first"])
tab = {}
for c, n in sorted(cat.items()):
    w_bk = sum(1 for q in cat_ids[c] if not next(x for x in rows if x["qa_id"] == q)["poma_bestK"])
    w_f = sum(1 for q in cat_ids[c] if not next(x for x in rows if x["qa_id"] == q)["poma_first"])
    tab[c] = {"n": n, "pct_of_992": pct(n, N),
              "bestK_wrong_in_cat": w_bk, "pct_of_bestK_errors": pct(w_bk, err_bestK),
              "first_candidate_wrong_in_cat": w_f, "pct_of_first_candidate_errors": pct(w_f, err_first)}
R["Q4"] = {"per_specialist_correctness": "specialist's own AN variant set (recorded for single-specialist; replayed from recorded AN LLM calls + deterministic rules for 2-specialist), best-of-K within that set, repo evaluator EM",
           "agreement_definition": "L4: specialists' AN variant sets intersect under canon_equal",
           "table": tab, "errors_bestK_total": err_bestK, "errors_first_candidate_total": err_first}

# gate headroom: single-string resolvers on multi-traced
g = Counter()
for r in multi:
    sp = r["specialists"]
    f_ok = [bool(s["correct_an_first"]) for s in sp]
    b_ok = [bool(s["correct_an_bestK"]) for s in sp]
    g["n"] += 1
    g["first_spec_first_variant_ok"] += f_ok[0]
    g["oracle_spec_first_variant_ok"] += any(f_ok)
    g["oracle_spec_bestK_ok"] += any(b_ok)
    g["recorded_first_candidate_ok"] += r["poma_first"]
    if r["dis_an"]:
        g["dis_n"] += 1
        g["dis_first_ok"] += f_ok[0]
        g["dis_oracle_first_variant_ok"] += any(f_ok)
        g["dis_oracle_bestK_ok"] += any(b_ok)
        g["dis_gain_first_variant"] += (any(f_ok) and not f_ok[0])
        g["dis_gain_bestK_over_first_spec_bestK"] += (any(b_ok) and not b_ok[0])
        # max-confidence choice
        confs = [s["confidence"] if s["confidence"] is not None else -1 for s in sp]
        j = max(range(len(sp)), key=lambda i: (confs[i], -i))
        g["dis_maxconf_ok"] += f_ok[j]
        g["dis_conf_tie"] += (len(set(confs)) == 1)
        # prefer non-null
        nn = [i for i, s in enumerate(sp) if not s["raw_null"]]
        j2 = nn[0] if nn else 0
        g["dis_prefer_nonnull_ok"] += f_ok[j2]
        j3 = [i for i, s in enumerate(sp) if s["raw_null"]]
        g["dis_prefer_null_ok"] += f_ok[j3[0] if j3 else 0]
R["Q4"]["multi_traced_resolvers"] = dict(g)
first_correct_992 = sum(r["poma_first"] for r in rows)
# upper bounds on 992 (single-string): replace first-candidate with oracle over specialists' first variants
ub_first = first_correct_992 + g["dis_gain_first_variant"]
R["Q4"]["upper_bounds_992"] = {
    "bestK_union (current metric; any single-answer selector over existing candidates is capped here)": sum(r["poma_bestK"] for r in rows),
    "first_candidate_single": first_correct_992,
    "perfect_specialist_resolver_single_string (traced multi only; untraced 48 multi unchanged)": ub_first,
    "perfect_resolver_gain_instances": g["dis_gain_first_variant"],
    "perfect_resolver_gain_pct_points": 100.0 * g["dis_gain_first_variant"] / N,
    "untraced_multi_48_bestK_correct": sum(r["poma_bestK"] for r in rows if r["specialists"] is None),
    "untraced_multi_48_first_correct": sum(r["poma_first"] for r in rows if r["specialists"] is None),
    "untraced_multi_48_gap_bestK_minus_first (max extra gain there)": sum(r["poma_bestK"] - r["poma_first"] for r in rows if r["specialists"] is None),
}

# =========================================================== Q5 best-of-K inflation
Ks = [r["K"] for r in rows]
R["Q5"] = {
    "EM_bestK": pct(sum(r["poma_bestK"] for r in rows), N),
    "EM_first_candidate": pct(first_correct_992, N),
    "inflation_pts": pct(sum(r["poma_bestK"] for r in rows) - first_correct_992, N),
    "K_stats": {"mean": statistics.mean(Ks), "median": statistics.median(Ks), "max": max(Ks),
                "p95": sorted(Ks)[math.ceil(0.95 * N) - 1], "K1_share_pct": pct(Ks.count(1), N),
                "dist_top": dict(Counter(Ks).most_common(12))},
}
# traced-only single-answer policies
tr = [r for r in rows if r["traced"]]
pol = Counter()
for r in tr:
    sp = r["specialists"]
    pol["n"] += 1
    pol["first_spec_raw"] += bool(sp[0]["correct_raw"])
    pol["first_spec_first_variant"] += bool(sp[0]["correct_an_first"])
    pol["first_candidate"] += r["poma_first"]
    pol["bestK"] += r["poma_bestK"]
    pol["first_spec_det_bestK"] += bool(sp[0]["correct_det"])
    pol["any_spec_det_bestK"] += any(bool(s["correct_det"]) for s in sp)
    # majority over specialists: with <=2 specialists majority == consensus, tie -> first
    pol["majority_tie_first"] += bool(sp[0]["correct_an_first"])
    confs = [s["confidence"] if s["confidence"] is not None else -1 for s in sp]
    j = max(range(len(sp)), key=lambda i: (confs[i], -i))
    pol["max_conf_first_variant"] += bool(sp[j]["correct_an_first"])
R["Q5"]["traced592_single_answer_policies"] = dict(pol)
# decompose inflation: why is bestK right but first candidate wrong?
infl = Counter()
infl_ex = defaultdict(list)
BOOL = {"có", "không", "đúng", "sai", "phải", "không phải", "yes", "no", "true", "false"}
from evaluation.normalization import parse_list_items
for r in rows:
    if not (r["poma_bestK"] and not r["poma_first"]):
        continue
    q = qas[r["qa_id"]]
    first = r["cand"][0]
    j = next(i for i, c in enumerate(r["cand"]) if em([c], q))
    hit = r["cand"][j]
    reason = None
    if r["specialists"] is not None and len(r["specialists"]) >= 2:
        v0 = r["specialists"][0]["an_variants"] or []
        if not em(v0 or [""], q):
            reason = "second_specialist_only"
    if reason is None:
        if r["gold_null"]:
            reason = "null_in_set_after_nonnull (hedge)"
        elif normalize_text(first) in BOOL and normalize_text(hit) in BOOL:
            reason = "yes/no synonym (Có/Đúng/Phải...)"
        elif parse_list_items(first) and parse_list_items(hit) and Counter(map(normalize_text, parse_list_items(first))) == Counter(map(normalize_text, parse_list_items(hit))):
            reason = "list permutation/delimiter variant"
        elif parse_list_items(first) and not parse_list_items(hit) and normalize_text(hit).replace(" ", "") == normalize_text(first).replace(",", "").replace(";", "").replace(" ", ""):
            reason = "list space-joined variant"
        elif any(ch.isdigit() for ch in first) and any(ch.isdigit() for ch in hit) and len(first) < 40:
            reason = "number/date/unit format variant"
        else:
            reason = "text variant (LLM-shortened / context strip / spacing)"
    infl[reason] += 1
    if len(infl_ex[reason]) < 4:
        infl_ex[reason].append({"qa_id": r["qa_id"], "first": first[:80], "hit": hit[:80], "gold": r["gold"][:80], "hit_index": j})
R["Q5"]["inflation_decomposition"] = dict(infl)
R["Q5"]["inflation_examples"] = infl_ex

# =========================================================== Q6 Null analysis
def pattern(r):
    if r["specialists"] is None:
        # untraced 2-specialist: AN-level pattern is recoverable from the candidate
        # set (a single specialist never yields a mixed set; see single_mixed_in_set=0)
        if r["cand_has_null"] and r["cand_has_nonnull"]:
            return "multi_mixed(hedge)"
        return "multi_unanimous_null(untraced)" if r["cand_has_null"] else "multi_unanimous_nonnull(untraced)"
    if r["n_specialists"] == 1:
        s = r["specialists"][0]
        if r["cand_has_null"] and r["cand_has_nonnull"]:
            return "single_mixed_in_set"
        return "single_null" if r["cand_has_null"] else "single_nonnull"
    sp = r["specialists"]
    nulls = [bool(s["an_null"]) and not bool(s["an_nonnull"]) for s in sp]
    nonnull = [bool(s["an_nonnull"]) and not bool(s["an_null"]) for s in sp]
    if all(nulls):
        return "multi_unanimous_null"
    if all(nonnull):
        return "multi_unanimous_nonnull"
    return "multi_mixed(hedge)"


def pattern_raw(r):
    if r["specialists"] is None or not r["traced"]:
        return "untraced"
    raws = [is_null_answer(s["answer"]) for s in r["specialists"]]
    if len(raws) == 1:
        return "single_raw_null" if raws[0] else "single_raw_nonnull"
    if all(raws):
        return "multi_raw_unanimous_null"
    if not any(raws):
        return "multi_raw_unanimous_nonnull"
    return "multi_raw_mixed"


q6 = {"gold_null": sum(r["gold_null"] for r in rows), "gold_answerable": sum(not r["gold_null"] for r in rows)}
FA_set = [r for r in rows if not r["gold_null"] and r["cand_has_null"]]
H_set = [r for r in rows if r["gold_null"] and not r["cand_has_null"]]
FA_first = [r for r in rows if not r["gold_null"] and is_null_answer(r["cand"][0])]
H_first = [r for r in rows if r["gold_null"] and not is_null_answer(r["cand"][0])]
# literal-'Null' only variant of the rule (not counting '', 'none', ...)
lit = lambda c: normalize_text(c) == "null"
FA_lit = [r for r in rows if not r["gold_null"] and any(lit(c) for c in r["cand"])]
H_lit = [r for r in rows if r["gold_null"] and not any(lit(c) for c in r["cand"])]
q6["rule_set_contains_null (paper)"] = {"false_abstentions": len(FA_set), "hallucinations": len(H_set)}
q6["rule_literal_Null_string_only"] = {"false_abstentions": len(FA_lit), "hallucinations": len(H_lit)}
q6["rule_single_first_candidate"] = {"false_abstentions": len(FA_first), "hallucinations": len(H_first)}
q6["FA_set_but_EM_correct_via_nonnull_candidate"] = sum(r["poma_bestK"] for r in FA_set)
q6["candidate_sets_with_both_null_and_nonnull_992"] = sum(r["cand_has_null"] and r["cand_has_nonnull"] for r in rows)
q6["candidate_sets_with_both_by_gold"] = {"gold_null": sum(r["cand_has_null"] and r["cand_has_nonnull"] for r in rows if r["gold_null"]),
                                          "gold_answerable": sum(r["cand_has_null"] and r["cand_has_nonnull"] for r in rows if not r["gold_null"])}
q6["FA_set_by_AN_pattern"] = dict(Counter(pattern(r) for r in FA_set))
q6["H_set_by_AN_pattern"] = dict(Counter(pattern(r) for r in H_set))
q6["FA_first_by_AN_pattern"] = dict(Counter(pattern(r) for r in FA_first))
q6["H_first_by_AN_pattern"] = dict(Counter(pattern(r) for r in H_first))
q6["FA_set_by_raw_pattern(traced)"] = dict(Counter(pattern_raw(r) for r in FA_set))
q6["H_set_by_raw_pattern(traced)"] = dict(Counter(pattern_raw(r) for r in H_set))
q6["gold_null_by_AN_pattern"] = dict(Counter(pattern(r) for r in rows if r["gold_null"]))
tot_err_set = len(FA_set) + len(H_set)
tot_err_first = len(FA_first) + len(H_first)
hedge_visible_set = sum(1 for r in FA_set + H_set if pattern(r) in ("multi_mixed(hedge)", "single_mixed_in_set"))
hedge_visible_first = sum(1 for r in FA_first + H_first if pattern(r) in ("multi_mixed(hedge)", "single_mixed_in_set"))
hedge_visible_set_multi_only = sum(1 for r in FA_set + H_set if pattern(r) == "multi_mixed(hedge)")
q6["hedge_trigger_visibility"] = {
    "answerability_errors_set_rule": tot_err_set,
    "visible_to_hedge_trigger_set_rule (specialist-level mixed OR single-set mixed)": hedge_visible_set,
    "visible_specialist_level_mixed_only": hedge_visible_set_multi_only,
    "pct_visible_set_rule": pct(hedge_visible_set, tot_err_set),
    "pct_visible_specialist_level_only": pct(hedge_visible_set_multi_only, tot_err_set),
    "answerability_errors_first_rule": tot_err_first,
    "visible_first_rule": hedge_visible_first,
    "pct_visible_first_rule": pct(hedge_visible_first, tot_err_first),
    "untraced_multi_among_errors_set_rule": sum(1 for r in FA_set + H_set if r["specialists"] is None),
    "all_gold_null_routed_to_single_specialist": all(r["n_specialists"] == 1 for r in rows if r["gold_null"]),
}
# hedge rule: when the candidate set is mixed, answer the first non-Null candidate (single answer)
mixed = [r for r in rows if r["cand_has_null"] and r["cand_has_nonnull"]]
q6["mixed_sets"] = {"n": len(mixed), "traced": sum(r["traced"] for r in mixed),
                    "first_candidate_is_null": sum(is_null_answer(r["cand"][0]) for r in mixed),
                    "first_candidate_correct": sum(r["poma_first"] for r in mixed),
                    "first_nonnull_candidate_correct": sum(em([next(c for c in r["cand"] if not is_null_answer(c))], qas[r["qa_id"]]) for r in mixed),
                    "bestK_correct": sum(r["poma_bestK"] for r in mixed)}
# gate firing: lower bound on untraced multi (mixed sets imply disagreement)
R.setdefault("gate_firing", {})["traced_multi_disagree_L4"] = sum(1 for r in rows if r.get("dis_an"))
R["gate_firing"]["untraced_multi_mixed_set_lower_bound"] = sum(1 for r in rows if r["specialists"] is None and r["cand_has_null"] and r["cand_has_nonnull"])
# how does a Null get in? AN-forced vs specialist-emitted (traced FA)
src = Counter()
for r in FA_set:
    if not r["traced"]:
        src["untraced"] += 1
        continue
    for s in r["specialists"]:
        if s["an_null"]:
            src["specialist_emitted_Null" if s["raw_null"] else "AN_forced_Null (Why/How rule or LLM)"] += 1
q6["FA_null_source_traced"] = dict(src)
q6["H_set_ids"] = [r["qa_id"] for r in H_set]
R["Q6"] = q6

# =========================================================== Q7 confidence
specs = [(r, s) for r in rows if r["traced"] for s in r["specialists"]]
confs = [s["confidence"] for _, s in specs]
R["Q7"] = {
    "n_specialist_outputs": len(specs),
    "confidence_distribution": dict(sorted(Counter(confs).items(), key=lambda x: -x[1])),
    "share_eq_1.0_pct": pct(sum(1 for c in confs if c == 1.0), len(confs)),
    "share_ge_0.9_pct": pct(sum(1 for c in confs if c is not None and c >= 0.9), len(confs)),
    "AUROC_conf_vs_correct_an_bestK": auroc(confs, [bool(s["correct_an_bestK"]) for _, s in specs]),
    "AUROC_conf_vs_correct_an_first": auroc(confs, [bool(s["correct_an_first"]) for _, s in specs]),
    "AUROC_conf_vs_correct_raw": auroc(confs, [bool(s["correct_raw"]) for _, s in specs]),
    "AUROC_nonnull_only_bestK": auroc([s["confidence"] for _, s in specs if not s["raw_null"]], [bool(s["correct_an_bestK"]) for _, s in specs if not s["raw_null"]]),
    "accuracy_by_conf_bucket": {},
    "confidence_of_Null_answers": dict(Counter(s["confidence"] for _, s in specs if s["raw_null"]).most_common(6)),
}
buckets = defaultdict(lambda: [0, 0])
for _, s in specs:
    c = s["confidence"]
    b = "1.0" if c == 1.0 else "[0.9,1.0)" if c >= 0.9 else "[0.7,0.9)" if c >= 0.7 else "<0.7"
    buckets[b][0] += 1
    buckets[b][1] += bool(s["correct_an_bestK"])
R["Q7"]["accuracy_by_conf_bucket"] = {k: {"n": v[0], "acc_pct": pct(v[1], v[0])} for k, v in buckets.items()}
R["Q7"]["disagreement_cases"] = {k: g[k] for k in ("dis_n", "dis_first_ok", "dis_maxconf_ok", "dis_conf_tie", "dis_prefer_nonnull_ok", "dis_prefer_null_ok", "dis_oracle_first_variant_ok")}

# =========================================================== Q9 heterogeneous voters
SYS = ["FS", "ZS", "CoT", "TD"]
def kappa_phi(a, b):
    n = len(a)
    n11 = sum(x and y for x, y in zip(a, b)); n00 = sum((not x) and (not y) for x, y in zip(a, b))
    n10 = sum(x and not y for x, y in zip(a, b)); n01 = sum((not x) and y for x, y in zip(a, b))
    po = (n11 + n00) / n
    pa, pb = (n11 + n10) / n, (n11 + n01) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe != 1 else None
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    phi = (n11 * n00 - n10 * n01) / den if den else None
    exp_both_wrong = n * (1 - pa) * (1 - pb)
    return {"both_right": n11, "only_A": n10, "only_B": n01, "both_wrong": n00,
            "expected_both_wrong_if_independent": round(exp_both_wrong, 1),
            "both_wrong_ratio_obs_over_exp": round(n00 / exp_both_wrong, 2) if exp_both_wrong else None,
            "cohen_kappa": kappa, "phi": phi}

vec = {"POMA_bestK": [r["poma_bestK"] for r in rows], "POMA_first": [r["poma_first"] for r in rows]}
for k in SYS:
    vec[k] = [r[f"{k}_correct"] for r in rows]
    vec[k + "_detK"] = [r[f"{k}_det_correct"] for r in rows]
q9 = {"EM_single_string_current_evaluator": {k: pct(sum(v), N) for k, v in vec.items()}}
q9["2x2"] = {
    "POMA_bestK_vs_FS": kappa_phi(vec["POMA_bestK"], vec["FS"]),
    "POMA_first_vs_FS": kappa_phi(vec["POMA_first"], vec["FS"]),
    "POMA_first_vs_FS_detK": kappa_phi(vec["POMA_first"], vec["FS_detK"]),
    "POMA_bestK_vs_FS_detK": kappa_phi(vec["POMA_bestK"], vec["FS_detK"]),
}
pair = {}
names = ["POMA_first", "FS", "ZS", "CoT", "TD"]
for i, a in enumerate(names):
    for b in names[i + 1:]:
        kp = kappa_phi(vec[a], vec[b])
        pair[f"{a}~{b}"] = {"kappa": round(kp["cohen_kappa"], 3), "both_wrong": kp["both_wrong"], "exp_indep": kp["expected_both_wrong_if_independent"]}
q9["pairwise_kappa_on_correctness"] = pair
q9["oracle_any_correct"] = {
    "POMA_bestK+FS+ZS+CoT+TD": pct(sum(any(t) for t in zip(vec["POMA_bestK"], vec["FS"], vec["ZS"], vec["CoT"], vec["TD"])), N),
    "POMA_first+FS+ZS+CoT+TD": pct(sum(any(t) for t in zip(vec["POMA_first"], vec["FS"], vec["ZS"], vec["CoT"], vec["TD"])), N),
    "POMA_first+FS": pct(sum(any(t) for t in zip(vec["POMA_first"], vec["FS"])), N),
    "FS+ZS+CoT+TD (baselines only)": pct(sum(any(t) for t in zip(vec["FS"], vec["ZS"], vec["CoT"], vec["TD"])), N),
    "POMA_first+FS_detK+ZS_detK+CoT_detK+TD_detK": pct(sum(any(t) for t in zip(vec["POMA_first"], vec["FS_detK"], vec["ZS_detK"], vec["CoT_detK"], vec["TD_detK"])), N),
}
# errors of POMA (first) that at least one baseline fixes
q9["POMA_first_wrong_but_some_baseline_right"] = sum((not p) and any(t) for p, *t in zip(vec["POMA_first"], vec["FS"], vec["ZS"], vec["CoT"], vec["TD"]))
q9["POMA_bestK_wrong_but_some_baseline_right"] = sum((not p) and any(t) for p, *t in zip(vec["POMA_bestK"], vec["FS"], vec["ZS"], vec["CoT"], vec["TD"]))


def vote(r, voters):
    """Majority vote; clusters by deterministic-variant equivalence. Tie ->
    cluster containing earliest voter in `voters` order. Returns (string,
    cluster_det_variant_union, size)."""
    qn = r["question"]
    answers = [(v, a) for v, a in voters]
    clusters = []  # list of [members]
    for v, a in answers:
        for cl in clusters:
            if same_det(a, cl[0][1], qn):
                cl.append((v, a))
                break
        else:
            clusters.append([(v, a)])
    best = max(clusters, key=lambda cl: (len(cl), -answers.index(cl[0])))
    rep = best[0][1]
    union = []
    for _, a in best:
        union += dvars(a, qn)
    return rep, union, len(best), len(clusters)


vres = Counter()
for r in rows:
    q = qas[r["qa_id"]]
    voters = [("POMA", r["cand"][0])] + [(k, r[f"{k}_answer"]) for k in SYS]
    rep, union, size, ncl = vote(r, voters)
    ok = em([rep], q)
    okK = em(union or [""], q)
    vres["vote5_single"] += ok
    vres["vote5_detK"] += okK
    vres["vote5_unanimous"] += (ncl == 1)
    # gate (i): POMA-first vs FS disagree -> vote; else POMA first
    agree_fs = same_det(r["cand"][0], r["FS_answer"], r["question"])
    vres["gate_POMAvsFS_fires"] += (not agree_fs)
    vres["gate_POMAvsFS_single"] += (r["poma_first"] if agree_fs else ok)
    vres["gate_POMAvsFS_detK"] += (r["poma_bestK"] if agree_fs else okK)
    # POMA best-of-K kept when agree; when gate fires, winner cluster: if POMA in cluster use POMA full set
    if not agree_fs:
        in_cl = same_det(rep, r["cand"][0], r["question"])
        vres["gate_POMAvsFS_bestK_keepPOMAset"] += (r["poma_bestK"] if in_cl else okK)
    else:
        vres["gate_POMAvsFS_bestK_keepPOMAset"] += r["poma_bestK"]
    # gate (ii): POMA specialists disagree (L4) -> vote over spec first variants + baselines
    if r.get("dis_an"):
        sv = [("POMA_s%d" % i, (s["an_variants"] or ["Null"])[0]) for i, s in enumerate(r["specialists"])]
        rep2, _, _, _ = vote(r, sv + [(k, r[f"{k}_answer"]) for k in SYS])
        vres["gate_specdis_fires"] += 1
        vres["gate_specdis_single"] += em([rep2], q)
    else:
        vres["gate_specdis_single"] += r["poma_first"]
    # POMA + FS only: 2 voters, prefer POMA on tie == POMA; so use FS as tie-break only when POMA Null
    pf = r["cand"][0]
    choose = r["FS_answer"] if (is_null_answer(pf) and not is_null_answer(r["FS_answer"])) else pf
    vres["POMA_first_null->FS"] += em([choose], q)
q9["vote_EM_pct"] = {k: pct(v, N) for k, v in vres.items() if not k.endswith("fires") and k != "vote5_unanimous"}
q9["vote_counts"] = dict(vres)
q9["notes"] = ("baselines are single-string (no AN). *_detK = baseline scored best-of-K over the repo's deterministic AN variants "
               "(boolean synonyms, number/date/unit forms, rank forms, spacing/context) -- same canonicalization for all systems. "
               "Voting clusters answers whose deterministic variant sets intersect under canon_equal.")
R["Q9"] = q9

# =========================================================== Q10 per type
bytype = defaultdict(Counter)
for r in rows:
    for h in r["gold_hints"]:
        bytype[h]["n"] += 1
        bytype[h][r["cat"]] += 1
        bytype[h]["bestK_ok"] += r["poma_bestK"]
        bytype[h]["first_ok"] += r["poma_first"]
        bytype[h]["FS_ok"] += r["FS_correct"]
        bytype[h]["multi"] += r["n_specialists"] >= 2
R["Q10"] = {h: dict(c) for h, c in sorted(bytype.items())}

dump("results_q2_q10.json", R)
dump("instances_with_cats.json", rows)
print(json.dumps({k: R[k] for k in ("Q2", "Q3", "Q4")}, ensure_ascii=False, indent=1, default=str))
