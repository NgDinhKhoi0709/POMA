"""Build one per-instance table (992 rows) used by all later analyses."""
from __future__ import annotations

import json
from collections import Counter

from common import (AN, PATHS, an_variants_replay, recorded_run_an, deterministic_variants,
                    deterministic_variants_no_forcing, dump, em,
                    gold_canon_hints, gold_is_null, is_null_answer, load_json,
                    preds_by_id, qas_by_id, traces_by_id)

qas = qas_by_id()
main = preds_by_id("hp")
trs = traces_by_id("hp_traces")
base = {k: preds_by_id(k) for k in ("FS", "ZS", "CoT", "TD")}
nohp_main = preds_by_id("no_hp")
nohp_trs = traces_by_id("no_hp_traces")

rows = []
recon = Counter()
recon_fail = []
for qid, q in qas.items():
    p = main[qid]
    cand = [str(c) for c in p["predicted_answer"]]
    r = {
        "qa_id": qid, "gold": q["answer"], "gold_null": gold_is_null(q),
        "gold_hints": gold_canon_hints(q), "question": q["question"],
        "predicted_hints": p.get("predicted_hints") or [],
        "n_specialists": len(p.get("predicted_hints") or []),
        "cand": cand, "K": len(cand),
        "poma_bestK": em(cand, q), "poma_first": em(cand[:1], q),
        "cand_has_null": any(is_null_answer(c) for c in cand),
        "cand_has_nonnull": any(not is_null_answer(c) for c in cand),
        "traced": qid in trs, "tokens_hp": p["total_tokens"],
        "tokens_no_hp": nohp_main[qid]["total_tokens"],
        "no_hp_n_specialists": (len(nohp_trs[qid]["steps"]["2_router"]["specialist_names"]) if qid in nohp_trs else None),
        "no_hp_bestK": em(nohp_main[qid]["predicted_answer"], q),
        "no_hp_first": em(nohp_main[qid]["predicted_answer"][:1], q),
    }
    for k, d in base.items():
        a = d[qid]["predicted_answer"]
        a = [str(x) for x in a] if isinstance(a, list) else [str(a)]
        r[f"{k}_answer"] = a[0] if a else ""
        r[f"{k}_correct"] = em(a[:1], q)
        dv = deterministic_variants_no_forcing(a[0] if a else "", q["question"])
        r[f"{k}_det_variants"] = dv
        r[f"{k}_det_correct"] = em(dv or [""], q)
    if qid in trs:
        t = trs[qid]
        st = t["steps"]
        sps = st["3_specialists"]
        rq = st["1_question_refiner"]
        an_calls = [c for c in t["llm_calls"] if c["agent_name"] == "AnswerNormalization"]
        try:
            with recorded_run_an():
                per, merged, ok, used = an_variants_replay(sps, rq["normalized_question"], rq.get("target"), an_calls)
            recorded = st["4_answer_normalization"]["normalized_answers"]
            match = merged == recorded
            recon["union_correctness_equal"] += (em(merged or [""], q) == em(recorded, q))
            if len(sps) == 1:
                # single specialist: its variant set IS the recorded set
                per = [list(recorded)]
            recon["exact_match" if match else "mismatch"] += 1
            if not ok:
                recon["unused_llm_calls"] += 1
            if not match:
                recon_fail.append({"qa_id": qid, "recorded": st["4_answer_normalization"]["normalized_answers"], "replayed": merged, "raw": [s["answer"] for s in sps]})
        except Exception as e:  # noqa: BLE001
            per = [None] * len(sps)
            recon["error:" + type(e).__name__] += 1
            recon_fail.append({"qa_id": qid, "error": str(e)})
            match = False
        specs = []
        for i, s in enumerate(sps):
            v = per[i]
            raw = s.get("answer")
            dv = deterministic_variants_no_forcing(raw, rq["normalized_question"], rq.get("target"), s.get("agent_name"))
            specs.append({
                "agent": s.get("agent_name"), "answer": raw,
                "confidence": s.get("confidence"),
                "evidence": [e.get("text") if isinstance(e, dict) else str(e) for e in (s.get("evidence") or [])],
                "reason": s.get("reason"),
                "an_variants": v, "an_variants_reconstructed_exact": bool(match) or len(sps) == 1,
                "det_variants": dv,
                "raw_null": is_null_answer(raw),
                "an_null": (v is not None and any(is_null_answer(x) for x in v)),
                "an_nonnull": (v is not None and any(not is_null_answer(x) for x in v)),
                "correct_raw": em([str(raw)], q),
                "correct_det": em(dv or [""], q),
                "correct_an_bestK": (em(v or [""], q) if v is not None else None),
                "correct_an_first": (em((v or [""])[:1], q) if v is not None else None),
            })
        r["specialists"] = specs
        r["refined_question"] = rq["normalized_question"]
        r["target"] = rq.get("target")
    elif r["n_specialists"] == 1:
        # untraced single-specialist: its AN variant set == the final candidate set
        r["specialists"] = [{
            "agent": r["predicted_hints"][0], "answer": None, "confidence": None,
            "evidence": None, "reason": None, "an_variants": cand,
            "an_variants_reconstructed_exact": True, "det_variants": None,
            "raw_null": None, "an_null": r["cand_has_null"], "an_nonnull": r["cand_has_nonnull"],
            "correct_raw": None, "correct_det": None,
            "correct_an_bestK": r["poma_bestK"], "correct_an_first": r["poma_first"],
            "from_candidate_set": True,
        }]
    else:
        r["specialists"] = None  # untraced multi-specialist: split unknown
    rows.append(r)

meta = {"reconstruction": dict(recon), "reconstruction_failures": recon_fail[:40]}
dump("instances.json", rows)
dump("instances_meta.json", meta)
print(json.dumps(meta, ensure_ascii=False, indent=1)[:6000])
print("rows", len(rows), Counter((r["traced"], r["n_specialists"]) for r in rows))
