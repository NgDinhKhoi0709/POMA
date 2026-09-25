"""Build one-answer artifacts for the v3lite arms so ``audit_d01.py`` can score them. No API calls.

Arms, each a strict superset of the previous one, so the audit reads as a component ablation:

``control``      POMA-first on the plain Flatten V1 table.
``control_fmt``  control + the Stage 4 rule formatter (free).
``h1``           H1-reduced table, spliced: the v3lite solver record where H1 changed the table,
                 the control record everywhere else.
``h1_fmt``       h1 + the rule formatter (free).
``v3lite``       h1_fmt + the Stage 3 answerability gate (uses the gate pass records).

A missing or empty answer becomes the ``[NO_VALID_ANSWER]`` sentinel, which the strict scorer counts
wrong, and is listed in the manifest rather than dropped.
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

from poma_v3lite.formatter import format_candidates  # noqa: E402

SENTINEL = "[NO_VALID_ANSWER]"
ARMS = ("control", "control_fmt", "h1", "h1_fmt", "v3lite")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def index_solver(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Latest successful solver record per (arm, qa_id)."""
    return {(r["arm"], str(r["qa_id"])): r for r in rows if "error" not in r}


def candidates_for(arm: str, qa_id: str, solver: dict, gate: dict) -> tuple[list[str], str]:
    """Ordered candidate answers for one arm, plus a short provenance tag."""
    control = solver.get(("control", qa_id))
    treated = solver.get(("v3lite", qa_id))

    if arm in ("control", "control_fmt"):
        row, source = control, "control"
    else:
        row, source = (treated, "h1") if treated is not None else (control, "spliced")

    raw = list((row or {}).get("raw_prediction") or (row or {}).get("prediction") or [])
    if arm in ("control", "h1"):
        return [a for a in (str(x).strip() for x in raw) if a], source

    def formatted() -> list[str]:
        # ``Null`` is a legitimate gold answer (45/992 on test), so a prediction that formats away
        # to nothing must stay ``Null`` and be scored, not turned into the missing-answer sentinel.
        return format_candidates(raw) or (["Null"] if raw else [])

    if arm in ("control_fmt", "h1_fmt"):
        return formatted(), source
    entry = gate.get(qa_id)
    if entry is not None:
        return [str(a) for a in entry["prediction"]], f"{source}+gate"
    return formatted(), source


def build_arm(arm: str, qa_ids: list[str], table_ids: dict[str, str], solver: dict, gate: dict) -> dict[str, Any]:
    predictions, missing, sources = [], [], {}
    for qa_id in qa_ids:
        answers, source = candidates_for(arm, qa_id, solver, gate)
        sources[source] = sources.get(source, 0) + 1
        answer = answers[0] if answers else ""
        if not answer:
            missing.append(qa_id)
            answer = SENTINEL
        predictions.append({"qa_id": qa_id, "table_id": table_ids[qa_id], "prediction": [answer]})
    return {
        "manifest": {
            "arm": arm,
            "count": len(predictions),
            "sources": sources,
            "missing_or_empty": missing,
            "sentinel": SENTINEL,
            "gate_records": len(gate),
        },
        "predictions": predictions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--gate", type=Path, help="Gate JSONL from run_v3lite_gate.py")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    args = parser.parse_args(argv)

    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    qa_ids = [str(qa["qa_id"]) for qa in qas]
    table_ids = {str(qa["qa_id"]): str(qa["table_id"]) for qa in qas}
    solver = index_solver(load_jsonl(args.records))
    gate = {}
    if args.gate and args.gate.exists():
        gate = {str(r["qa_id"]): r for r in load_jsonl(args.gate) if r.get("error") is None}

    have_control = {qa_id for (arm, qa_id) in solver if arm == "control"}
    assert have_control == set(qa_ids), (
        f"control must cover exactly the {len(qa_ids)} QAs: "
        f"missing {len(set(qa_ids) - have_control)}, extra {len(have_control - set(qa_ids))}"
    )
    extra_gate = set(gate) - set(qa_ids)
    assert not extra_gate, f"gate records outside the QAs file: {sorted(extra_gate)[:5]}"

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for arm in args.arms:
        payload = build_arm(arm, qa_ids, table_ids, solver, gate)
        (args.out_dir / f"{arm}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        manifest = payload["manifest"]
        print(f"{arm:12s} n={manifest['count']} sources={manifest['sources']} "
              f"missing={len(manifest['missing_or_empty'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
