"""Q1 extras: per-instance raw-first vs first-candidate on traced; ESTIMATE of w/o-AN on 992."""
import json
from common import load_json, dump, em, qas_by_id, OUT
qas = qas_by_id()
rows = load_json(OUT / "instances_with_cats.json")
tr = [r for r in rows if r["traced"]]
un = [r for r in rows if not r["traced"]]
same = sum(bool(r["specialists"][0]["correct_raw"]) == bool(r["poma_first"]) for r in tr)
raw_bestK_tr = sum(em([str(s["answer"]) for s in r["specialists"]], qas[r["qa_id"]]) for r in tr)
raw_first_tr = sum(bool(r["specialists"][0]["correct_raw"]) for r in tr)
first_un = sum(r["poma_first"] for r in un)
bestK_un = sum(r["poma_bestK"] for r in un)
# estimate raw best-of-K on untraced: first-candidate EM there, scaled by traced raw_bestK/raw_first ratio
est_raw_un = first_un * raw_bestK_tr / raw_first_tr
out = {
  "traced_raw_first_vs_first_candidate_same_correctness": f"{same}/{len(tr)}",
  "traced": {"raw_bestK": raw_bestK_tr, "raw_first": raw_first_tr, "with_AN_bestK": sum(r["poma_bestK"] for r in tr), "n": len(tr)},
  "untraced": {"first_candidate": first_un, "with_AN_bestK": bestK_un, "n": len(un)},
  "ESTIMATE_raw_bestK_untraced": round(est_raw_un, 1),
  "ESTIMATE_wo_AN_EM_992_pct": round(100 * (raw_bestK_tr + est_raw_un) / 992, 2),
  "ESTIMATE_AN_flips_992": round(796 - (raw_bestK_tr + est_raw_un), 1),
  "ESTIMATE_AN_flips_992_by_traced_rate": round(67 / 592 * 992, 1),
  "what_would_be_needed_for_62.40_(619/992)": {"untraced_raw_correct_needed": 619 - raw_bestK_tr, "as_pct_of_400": round(100 * (619 - raw_bestK_tr) / 400, 2),
                                               "untraced_first_candidate_pct_observed": round(100 * first_un / 400, 2)},
}
dump("q1_extra.json", out)
print(json.dumps(out, indent=1))
