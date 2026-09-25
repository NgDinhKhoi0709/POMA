"""Stage run: pipe representations and pipe + H1 on the first N test questions (resumable JSONL).

Arms (zero-shot Qwen3-8B, prompt ``v3_zs_minimal``; everything but the table string is that of
``run_d09_representation.py``):

``v1_raw``      Flatten V1, control. Rerun here because the parser fix changed 95/329 table strings, so the
                D09 control (old parser, 200 questions) is not comparable.
``pipe_clean``  cleaned grid, pipe rows, no ``<header>`` tag.
``pipe_nohdr``  cleaned grid, one labelled ``Cột: A|B|C`` schema line, pipe rows.
``nohdr_h1``    ``pipe_nohdr`` plus the same H1 rule, so the schema line is kept. Same 38 questions as ``pipe_h1``.
``pipe_h1``     ``pipe_clean`` plus H1 row selection for tables longer than 2000 tokens *as sent* (pipe
                tokens), k=20, the frozen D10 rule. Called only where H1 changed the string; every other
                question has a byte-identical prompt to ``pipe_clean`` and takes that answer when the
                artifacts are built (``build_d09_artifacts.py --splice pipe_h1 --base-arm pipe_clean``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseline.llm_client import GenConfig, LLMZeroShotClient  # noqa: E402
from preprocessing.reduction import MIN_TABLE_TOKENS, reduce_table  # noqa: E402
from preprocessing.variants import render_table  # noqa: E402
from scripts.run_d09_representation import DEFAULT_MODEL, load_done, process  # noqa: E402

PLAIN_ARMS = ("v1_raw", "pipe_clean", "pipe_nohdr")
ALL_ARMS = PLAIN_ARMS + ("pipe_h1", "nohdr_h1")
H1_BASE_ARM = "pipe_clean"
# H1 arm -> the plain arm it reduces. ``pipe_h1`` keeps its original keys in the plan; ``nohdr_h1`` is additive.
H1_ARMS = {"pipe_h1": "pipe_clean", "nohdr_h1": "pipe_nohdr"}


def build_plan(qas: list[dict], tables: dict[str, dict], k: int, count) -> dict[str, dict]:
    """qa_id -> the table string every arm sends, plus H1 bookkeeping. No API calls."""
    cache: dict[str, int] = {}

    def token_count(text: str) -> int:
        if text not in cache:
            cache[text] = count(text)
        return cache[text]

    plan: dict[str, dict] = {}
    for qa in qas:
        table = tables[str(qa["table_id"])]
        texts = {arm: render_table(table, arm) for arm in PLAIN_ARMS}
        reduction = reduce_table(
            table, str(qa["question"]), k=k, token_count=token_count, arm=H1_BASE_ARM
        )
        nohdr = reduce_table(table, str(qa["question"]), k=k, token_count=token_count, arm=H1_ARMS["nohdr_h1"])
        plan[str(qa["qa_id"])] = {
            "texts": texts,
            "h1_text": reduction.text,
            "h1_changed": reduction.text != texts[H1_BASE_ARM],
            "h1_reason": reduction.reason,
            "rows_total": reduction.rows_total,
            "rows_kept": reduction.rows_kept,
            "nohdr_h1_text": nohdr.text,
            "nohdr_h1_changed": nohdr.text != texts[H1_ARMS["nohdr_h1"]],
            "tokens": {arm: token_count(text) for arm, text in texts.items()}
            | {"pipe_h1": token_count(reduction.text), "nohdr_h1": token_count(nohdr.text)},
        }
    return plan


def summarize(plan: dict[str, dict]) -> dict:
    n = len(plan)
    reasons: dict[str, int] = {}
    for entry in plan.values():
        reasons[entry["h1_reason"]] = reasons.get(entry["h1_reason"], 0) + 1
    mean = {arm: sum(e["tokens"][arm] for e in plan.values()) / n for arm in ALL_ARMS}
    return {
        "n_questions": n,
        "mean_table_tokens": {arm: round(value, 1) for arm, value in mean.items()},
        "table_tokens_vs_v1_raw_pct": {arm: round(100 * (mean[arm] / mean["v1_raw"] - 1), 2) for arm in ALL_ARMS},
        "h1_changed": sum(1 for e in plan.values() if e["h1_changed"]),
        "nohdr_h1_changed": sum(1 for e in plan.values() if e["nohdr_h1_changed"]),
        "h1_reasons": reasons,
        "gate_tokens": MIN_TABLE_TOKENS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL of records")
    parser.add_argument("--plan", type=Path, required=True, help="Where to write the plan summary (JSON)")
    parser.add_argument("--limit", type=int, default=500, help="first N questions of the QAs file")
    parser.add_argument("--arms", nargs="+", default=list(ALL_ARMS), choices=list(ALL_ARMS))
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--plan-only", action="store_true", help="write the plan and print reach; no API calls")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top_p", type=float, default=1.0)
    parser.add_argument("--max_tokens", type=int, default=10000)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)

    from dotenv import load_dotenv  # type: ignore
    from transformers import AutoTokenizer  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"][: args.limit]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}

    plan = build_plan(qas, tables, args.k, lambda text: len(tokenizer.encode(text, add_special_tokens=False)))
    summary = summarize(plan)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(
        json.dumps(
            {"summary": summary, "k": args.k, "qa_ids": [str(q["qa_id"]) for q in qas],
             "h1": {i: {x: e[x] for x in ("h1_changed", "h1_reason", "rows_total", "rows_kept", "nohdr_h1_changed")}
                    | {"tokens": e["tokens"]}
                    for i, e in plan.items()},
             "text_sha256": {i: {arm: hashlib.sha256(t.encode("utf-8")).hexdigest() for arm, t in e["texts"].items()}
                             for i, e in plan.items()}},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)
    if args.plan_only:
        return 0

    jobs: list[tuple[dict, str, str]] = []
    for qa in qas:
        entry = plan[str(qa["qa_id"])]
        for arm in args.arms:
            if arm in PLAIN_ARMS:
                jobs.append((qa, arm, entry["texts"][arm]))
            elif arm == "pipe_h1" and entry["h1_changed"]:
                jobs.append((qa, arm, entry["h1_text"]))
            elif arm == "nohdr_h1" and entry["nohdr_h1_changed"]:
                jobs.append((qa, arm, entry["nohdr_h1_text"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    pending = [(qa, arm, text) for qa, arm, text in jobs if (arm, str(qa["qa_id"])) not in done]
    print(f"{len(done)} done, {len(pending)} to run -> {args.out}", flush=True)

    cfg = GenConfig(temperature=args.temperature, top_p=args.top_p, max_tokens=args.max_tokens, timeout=args.timeout)
    client = LLMZeroShotClient()
    lock, written, failed = threading.Lock(), 0, 0
    try:
        with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(process, qa, tables[str(qa["table_id"])], arm,
                            client=client, cfg=cfg, model=args.model, table_str=text)
                for qa, arm, text in pending
            ]
            for future in as_completed(futures):
                record = future.result()
                with lock:
                    sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                    sink.flush()
                    written += 1
                    failed += "error" in record
                    if written % 50 == 0:
                        print(f"{written}/{len(pending)} (failed {failed})", flush=True)
    finally:
        client.shutdown()
    print(f"done: {written} written, {failed} failed (rerun to retry failures)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
