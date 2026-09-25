"""Describe the v3lite run: token/cost/latency per arm, what each component changed, and where.

Reads only saved artifacts (solver JSONL, gate JSONL, the H1 plan and the built one-answer arms) plus
the frozen D01 scorer. No API call. ``audit_d01.py`` owns the significance testing; this script
supplies the per-component accounting the audit cannot see.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402


def correctness(path: Path, qas: Path) -> dict[str, bool]:
    samples, _ = align_records(
        load_json_records(path), load_qas_records(qas), candidate_policy="single-required"
    )
    return {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--arms-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    qas = {str(q["qa_id"]): q for q in json.loads(args.qas.read_text(encoding="utf-8"))["qas"]}
    plan = json.loads(args.plan.read_text(encoding="utf-8"))["plan"]
    solver = load_jsonl(args.records)
    gate = [r for r in load_jsonl(args.gate) if r.get("error") is None]
    ok = [r for r in solver if "error" not in r]

    report: dict[str, Any] = {"n_questions": len(qas)}

    # --- cost and tokens, per arm -------------------------------------------------
    by_arm: dict[str, dict[str, float]] = {}
    for row in ok:
        entry = by_arm.setdefault(row["arm"], {"n": 0, "prompt": 0, "completion": 0, "cost": 0.0, "elapsed": 0.0})
        entry["n"] += 1
        entry["prompt"] += row.get("prompt_tokens", 0)
        entry["completion"] += row.get("completion_tokens", 0)
        entry["cost"] += row.get("cost_usd", 0.0)
        entry["elapsed"] += row.get("elapsed_s", 0.0)
    for name, entry in by_arm.items():
        entry["mean_elapsed_s"] = round(entry["elapsed"] / max(entry["n"], 1), 2)
        entry["cost"] = round(entry["cost"], 4)
    report["solver_calls"] = by_arm
    report["solver_failures"] = len(solver) - len(ok)

    # H1 reach, from the plan (table-string tokens, not API tokens)
    changed = [i for i, v in plan.items() if v["changed"]]
    full = sum(v["full_tokens"] for v in plan.values())
    reduced = sum(v["reduced_tokens"] for v in plan.values())
    reasons: dict[str, int] = {}
    for value in plan.values():
        reasons[value["reason"]] = reasons.get(value["reason"], 0) + 1
    report["h1"] = {
        "changed": len(changed),
        "reasons": reasons,
        "table_tokens_full": full,
        "table_tokens_reduced": reduced,
        "table_tokens_saved_pct": round(100 * (full - reduced) / full, 2),
    }
    # Observed prompt tokens on the questions H1 actually changed (control vs treated).
    control_by_id = {str(r["qa_id"]): r for r in ok if r["arm"] == "control"}
    treated_by_id = {str(r["qa_id"]): r for r in ok if r["arm"] == "v3lite"}
    both = sorted(set(control_by_id) & set(treated_by_id))
    if both:
        c_tok = sum(control_by_id[i].get("prompt_tokens", 0) for i in both)
        t_tok = sum(treated_by_id[i].get("prompt_tokens", 0) for i in both)
        report["h1"]["api_prompt_tokens_on_changed"] = {
            "n": len(both), "control": c_tok, "v3lite": t_tok,
            "saved_pct": round(100 * (c_tok - t_tok) / c_tok, 2) if c_tok else None,
        }

    # --- gate accounting ----------------------------------------------------------
    gold_null = {i for i, q in qas.items() if str(q.get("answer", "")).strip().lower() == "null"}
    fired = [r for r in gate if r.get("fired")]
    replaced = [r for r in gate if r.get("changed")]
    report["gate"] = {
        "fired": len(fired),
        "llm_calls": sum(r.get("calls", 0) for r in gate),
        "null_replaced_by_an_answer": len(replaced),
        "replaced_where_gold_is_null": sum(1 for r in replaced if r["qa_id"] in gold_null),
        "confirmed_null": len(fired) - len(replaced),
        "confirmed_where_gold_is_null": sum(
            1 for r in fired if not r["changed"] and r["qa_id"] in gold_null
        ),
        "gold_null_total": len(gold_null),
        "errors": sum(1 for r in gate if r.get("error")),
        "no_row_found": sum(1 for r in fired if r.get("rows_found") == 0),
    }

    # --- per-arm EM and the pairwise deltas the ablation is about ------------------
    arms = {p.stem: correctness(p, args.qas) for p in sorted(args.arms_dir.glob("*.json"))}
    ids = sorted(set.intersection(*[set(v) for v in arms.values()])) if arms else []
    report["em"] = {name: round(100 * sum(v[i] for i in ids) / len(ids), 2) for name, v in arms.items()}
    pairs = [("control", "control_fmt"), ("control", "h1"), ("h1", "h1_fmt"),
             ("h1_fmt", "v3lite"), ("control", "v3lite")]
    report["pairs"] = {}
    for base, arm in pairs:
        if base not in arms or arm not in arms:
            continue
        wins = [i for i in ids if arms[arm][i] and not arms[base][i]]
        losses = [i for i in ids if arms[base][i] and not arms[arm][i]]
        report["pairs"][f"{base} -> {arm}"] = {
            "delta_em_points": round(100 * (len(wins) - len(losses)) / len(ids), 2),
            "wins": len(wins), "losses": len(losses),
            "win_ids": wins[:20], "loss_ids": losses[:20],
        }

    # EM on the slice H1 actually touched, where any H1 effect has to show up.
    if both and "control" in arms and "h1" in arms:
        report["em_on_h1_changed_slice"] = {
            "n": len(both),
            "control": round(100 * sum(arms["control"][i] for i in both) / len(both), 2),
            "h1": round(100 * sum(arms["h1"][i] for i in both) / len(both), 2),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report["em"], ensure_ascii=False, indent=1))
    print(json.dumps({k: {x: v[x] for x in ("delta_em_points", "wins", "losses")}
                      for k, v in report["pairs"].items()}, ensure_ascii=False, indent=1))
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
