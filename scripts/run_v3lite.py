"""Run the reduced POMA v3 pipeline (and its control) over a QAs file, resumable JSONL.

Arms
----
``control``  POMA on the plain Flatten V1 table (``run_poma.py`` behaviour, one record per question).
``v3lite``   POMA on the H1-reduced table. Only questions whose table string H1 actually changed are
             called; the rest are spliced from ``control``.

This script is the solver pass only. The Stage 4 formatter is free and applied when artifacts are
built; the Stage 3 answerability gate needs its own pass over the spliced answers
(``run_v3lite_gate.py``), because a ``Null`` can come from a question H1 never touched.

POMA is not bit-reproducible across runs (a probe of 8 short-table questions reproduced 7), so the
control is run fresh in the same session rather than spliced from an older artifact. Within one
session the splice still holds for questions whose table string H1 leaves unchanged: their prompt is
byte-identical to the control's, so ``build_v3lite_artifacts.py`` copies the control answer instead
of paying for the call again.

Hints come from the precomputed ``predicted_hints`` of the earlier full POMA run (``--hint-predictions``)
so both arms route to the same specialists and the HintPredictor call is not repeated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing.reduction import MIN_TABLE_TOKENS, reduce_table  # noqa: E402
from preprocessing.variants import render_table  # noqa: E402
from src.contracts.request import QARequest  # noqa: E402
from src.orchestration.pipeline import run_pipeline  # noqa: E402

DEFAULT_MODEL = "openrouter/qwen/qwen3-8b"
ARMS = ("control", "v3lite")


def load_done(path: Path) -> set[tuple[str, str]]:
    """(arm, qa_id) pairs already recorded without an error; failures are retried on resume."""
    done: set[tuple[str, str]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "error" not in row:
                    done.add((row["arm"], str(row["qa_id"])))
    return done


def process(
    qa: dict[str, Any],
    table: dict[str, Any],
    arm: str,
    *,
    hints: list[str],
    table_str: str,
    model: str,
) -> dict[str, Any]:
    """One question on one arm: run POMA over ``table_str`` and record the raw candidate answers."""
    qa_id = str(qa["qa_id"])
    record: dict[str, Any] = {
        "arm": arm,
        "qa_id": qa_id,
        "table_id": str(qa["table_id"]),
        "table_chars": len(table_str),
        "table_sha256": hashlib.sha256(table_str.encode("utf-8")).hexdigest(),
        "hints": hints,
    }
    started = time.time()
    try:
        result = run_pipeline(
            QARequest(
                question=str(qa["question"]).strip(),
                table_flattened=table_str,
                metadata={"hints": hints, "qa_id": qa_id, "hint_source": "precomputed"},
            )
        )
    except Exception as exc:  # recorded and retried on resume; never fabricated
        record.update({"elapsed_s": round(time.time() - started, 2), "error": f"{type(exc).__name__}: {exc}"[:300]})
        return record

    raw = [str(a) for a in (result.get("answer") or [])]
    record.update({
        "raw_prediction": raw,
        "prompt_tokens": result.get("prompt_tokens", 0),
        "completion_tokens": result.get("completion_tokens", 0),
        "cost_usd": result.get("cost_usd", 0.0),
    })
    record["prediction"] = raw or ["Null"]
    record["elapsed_s"] = round(time.time() - started, 2)
    return record


def build_plan(qas: list[dict], tables: dict[str, dict], k: int, count) -> dict[str, dict]:
    """qa_id -> {full/reduced table strings, whether H1 changed it}. No API calls."""
    cache: dict[str, int] = {}

    def token_count(text: str) -> int:
        if text not in cache:
            cache[text] = count(text)
        return cache[text]

    plan: dict[str, dict] = {}
    for qa in qas:
        table = tables[str(qa["table_id"])]
        full = render_table(table, "v1_raw")
        reduced = reduce_table(table, str(qa["question"]), k=k, token_count=token_count)
        plan[str(qa["qa_id"])] = {
            "full": full,
            "reduced": reduced.text,
            "changed": reduced.text != full,
            "reason": reduced.reason,
            "full_tokens": token_count(full),
            "reduced_tokens": token_count(reduced.text),
        }
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL of records")
    parser.add_argument("--plan", type=Path, required=True, help="Where to write the H1 plan (JSON)")
    parser.add_argument("--hint-predictions", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", nargs="+", default=["alibaba"])
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(argv)

    import os

    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    os.environ["POMA_LLM_MODEL"] = args.model
    os.environ["POMA_OPENROUTER_PROVIDER"] = ",".join(args.provider)
    os.environ["POMA_USE_AGENT_HINTS"] = "false"

    from transformers import AutoTokenizer  # type: ignore

    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    if args.limit:
        qas = qas[: args.limit]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}

    raw_hints = json.loads(args.hint_predictions.read_text(encoding="utf-8"))
    hint_records = raw_hints.get("predictions", raw_hints) if isinstance(raw_hints, dict) else raw_hints
    hints_by_id = {str(r["qa_id"]): list(r["predicted_hints"]) for r in hint_records if r.get("predicted_hints")}
    missing = [str(qa["qa_id"]) for qa in qas if str(qa["qa_id"]) not in hints_by_id]
    if missing:
        raise SystemExit(f"missing predicted_hints for {len(missing)} qa_ids, e.g. {missing[:5]}")

    plan = build_plan(qas, tables, args.k, lambda t: len(tokenizer.encode(t, add_special_tokens=False)))
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(
        json.dumps({"min_table_tokens": MIN_TABLE_TOKENS, "k": args.k,
                    "plan": {i: {x: v[x] for x in ("changed", "reason", "full_tokens", "reduced_tokens")}
                             for i, v in plan.items()}}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    changed = [i for i, v in plan.items() if v["changed"]]
    total_full = sum(v["full_tokens"] for v in plan.values())
    total_red = sum(v["reduced_tokens"] for v in plan.values())
    print(f"H1 k={args.k}: changed {len(changed)}/{len(plan)}; table tokens "
          f"{total_full} -> {total_red} = -{(total_full - total_red) / total_full:.1%}", flush=True)
    if args.plan_only:
        return 0

    jobs: list[tuple[dict, str, str]] = []
    if "control" in args.arms:
        jobs += [(qa, "control", plan[str(qa["qa_id"])]["full"]) for qa in qas]
    if "v3lite" in args.arms:
        # Unchanged tables give a byte-identical prompt; those answers are spliced from control.
        jobs += [(qa, "v3lite", plan[str(qa["qa_id"])]["reduced"]) for qa in qas
                 if plan[str(qa["qa_id"])]["changed"]]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    pending = [(qa, arm, text) for qa, arm, text in jobs if (arm, str(qa["qa_id"])) not in done]
    print(f"{len(done)} done, {len(pending)} to run -> {args.out}", flush=True)

    lock, written, failed = threading.Lock(), 0, 0
    with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(process, qa, tables[str(qa["table_id"])], arm,
                        hints=hints_by_id[str(qa["qa_id"])], table_str=text, model=args.model)
            for qa, arm, text in pending
        ]
        for future in as_completed(futures):
            record = future.result()
            with lock:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                written += 1
                failed += "error" in record
                if written % 25 == 0:
                    print(f"{written}/{len(pending)} (failed {failed})", flush=True)
    print(f"done: {written} written, {failed} failed (rerun to retry failures)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
