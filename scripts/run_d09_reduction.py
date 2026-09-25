"""D10 / H1: zero-shot Qwen3-8B with question-aware row selection on long tables (resumable JSONL).

Arms: ``v1_raw`` (full Flatten V1, every question) and ``h1_k<K>`` (rows selected by
``preprocessing.reduction.reduce_table``). An H1 arm is only called for questions whose table string
actually changed; every other question has a byte-identical prompt to ``v1_raw`` and takes the
``v1_raw`` answer when artifacts are built (``build_d09_artifacts.py --splice``). Model, prompt
(``v3_zs_minimal``), schema and generation settings are those of ``run_d09_representation.py``.
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


def build_plan(
    qas: list[dict], tables: dict[str, dict], ks: list[int], count
) -> tuple[dict[str, dict], dict[tuple[str, int], str]]:
    """(qa_id -> {"full_tokens", "k<K>": {reason, reduced, rows_total, rows_kept, tokens, text_sha256}}, texts). No API."""
    cache: dict[str, int] = {}

    def token_count(text: str) -> int:
        if text not in cache:
            cache[text] = count(text)
        return cache[text]

    plan: dict[str, dict] = {}
    texts: dict[tuple[str, int], str] = {}
    for qa in qas:
        table = tables[str(qa["table_id"])]
        entry: dict = {}
        for k in ks:
            result = reduce_table(table, str(qa["question"]), k=k, token_count=token_count)
            entry["full_tokens"] = token_count(render_table(table, "v1_raw"))
            texts[(str(qa["qa_id"]), k)] = result.text
            entry[f"k{k}"] = {
                "reason": result.reason, "reduced": result.reduced, "rows_total": result.rows_total,
                "rows_kept": result.rows_kept, "tokens": token_count(result.text),
                "text_sha256": hashlib.sha256(result.text.encode("utf-8")).hexdigest(),
            }
        plan[str(qa["qa_id"])] = entry
    return plan, texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL of records")
    parser.add_argument("--plan", type=Path, required=True, help="Where to write the reduction plan (JSON)")
    parser.add_argument("--k", type=int, nargs="+", default=[20, 10])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--plan-only", action="store_true", help="write the plan and print reach; no API calls")
    parser.add_argument("--long-only", type=Path, help="only questions whose full table exceeds the gate; write that QAs file here")
    parser.add_argument("--limit", type=int, default=0)
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
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    if args.limit:
        qas = qas[: args.limit]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}
    plan, texts = build_plan(qas, tables, args.k, lambda text: len(tokenizer.encode(text, add_special_tokens=False)))
    if args.long_only:
        qas = [qa for qa in qas if plan[str(qa["qa_id"])]["full_tokens"] > MIN_TABLE_TOKENS]
        plan = {str(qa["qa_id"]): plan[str(qa["qa_id"])] for qa in qas}
        args.long_only.write_text(json.dumps({"qas": qas}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"long-table questions (> {MIN_TABLE_TOKENS} tokens): {len(qas)} -> {args.long_only}", flush=True)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(json.dumps({"min_table_tokens": MIN_TABLE_TOKENS, "plan": plan}, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in args.k:
        rows = [p[f"k{k}"] for p in plan.values()]
        reduced = [(p["full_tokens"], p[f"k{k}"]["tokens"]) for p in plan.values() if p[f"k{k}"]["reduced"]]
        reasons: dict[str, int] = {}
        for row in rows:
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
        total_full = sum(p["full_tokens"] for p in plan.values())
        saved = sum(f - n for f, n in reduced)
        print(f"k={k}: reasons {reasons}; reduced {len(reduced)}/{len(plan)}; table tokens saved {saved}/{total_full} = {saved / total_full:.1%}", flush=True)
    if args.plan_only:
        return 0

    jobs = [(qa, "v1_raw", None) for qa in qas]
    for k in args.k:
        jobs += [(qa, f"h1_k{k}", texts[(str(qa["qa_id"]), k)]) for qa in qas if plan[str(qa["qa_id"])][f"k{k}"]["reduced"]]
    done = load_done(args.out) if args.out.exists() else set()
    pending = [(qa, arm, text) for qa, arm, text in jobs if (arm, str(qa["qa_id"])) not in done]
    print(f"{len(done)} done, {len(pending)} to run -> {args.out}", flush=True)

    cfg = GenConfig(temperature=args.temperature, top_p=args.top_p, max_tokens=args.max_tokens, timeout=args.timeout)
    client = LLMZeroShotClient()
    lock, written, failed = threading.Lock(), 0, 0
    try:
        with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(
                    process, qa, tables[str(qa["table_id"])], arm, client=client, cfg=cfg, model=args.model,
                    table_str=text if text is not None else render_table(tables[str(qa["table_id"])], "v1_raw"),
                )
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
    finally:
        client.shutdown()
    print(f"done: {written} written, {failed} failed (rerun to retry failures)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
