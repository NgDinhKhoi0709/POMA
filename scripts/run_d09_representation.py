"""D09: run zero-shot Qwen3-8B over table-representation arms (resumable JSONL, one record per qa x arm).

Mirrors ``baseline.run.process_one_qa`` for ``--prompt-style zero_shot`` (same prompt builder, same
structured-output schema and repair path, same ``GenConfig`` defaults of ``run_baseline.py``:
temperature 0, top_p 1, max_tokens 10000, timeout 60, provider pin from ``baseline.llm_client``,
provider-default thinking). Only the table string differs between arms. The ``TABLE_STR:`` marker
assertion in ``process_one_qa`` is not inherited because the current ``v3_zs_minimal`` prompt labels
the table ``BANG:``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseline.llm_client import GenConfig, LLMZeroShotClient  # noqa: E402
from baseline.prompts import build_tableqa_prompt  # noqa: E402
from preprocessing.variants import ARMS, render_table  # noqa: E402
from src.contracts import CallContext, schema_for_call  # noqa: E402
from src.services import StructuredGenerator  # noqa: E402

DEFAULT_MODEL = "openrouter/qwen/qwen3-8b"
SCHEMA = "baseline_zero_shot.v1"


def load_done(path: Path) -> set[tuple[str, str]]:
    """(arm, qa_id) pairs with a successful record; failed records are retried on resume."""
    done: set[tuple[str, str]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "error" not in row:
                    done.add((row["arm"], str(row["qa_id"])))
    return done


def process(
    qa: dict[str, Any], table: dict[str, Any], arm: str, *, client, cfg: GenConfig, model: str, table_str: str | None = None
) -> dict[str, Any]:
    """One qa x arm call. ``table_str`` overrides the arm renderer (used by question-aware reduction)."""
    if table_str is None:
        table_str = render_table(table, arm)
    prompt, prompt_version = build_tableqa_prompt(
        question=str(qa["question"]).strip(), table_str=table_str, prompt_style="zero_shot", answer_language="vi"
    )
    record: dict[str, Any] = {
        "arm": arm,
        "qa_id": str(qa["qa_id"]),
        "table_id": str(qa["table_id"]),
        "prompt_version": prompt_version,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "table_chars": len(table_str),
    }
    started = time.time()

    def generate_once(request_prompt: str, text_format: dict | None) -> tuple[str, dict]:
        structured = replace(
            cfg, text_format=None if text_format is None else dict(text_format), require_parameters=text_format is not None
        )
        return client.generate_with_usage(model, request_prompt, structured, max_retries=4, retry_delay=15)

    try:
        result = StructuredGenerator(generate_once).generate(
            prompt.strip(),
            schema_for_call(SCHEMA),
            CallContext(qa_id=record["qa_id"], agent_name="DirectPromptBaseline", prompt_name="zero_shot", model=model),
        )
    except Exception as exc:  # recorded and retried on resume; never fabricated
        record.update({"elapsed_s": round(time.time() - started, 2), "error": f"{type(exc).__name__}: {exc}"[:300]})
        return record
    record.update({
        "prediction": [result.data["final_answer"]],
        "schema_valid": result.schema_valid,
        "repair_attempted": result.repair_attempted,
        "repair_succeeded": result.repair_succeeded,
        "elapsed_s": round(time.time() - started, 2),
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "cost_usd": result.cost_usd,
    })
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "outputs/d04/qas_test_200.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL of records")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=0, help="first N questions only (smoke test)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top_p", type=float, default=1.0)
    parser.add_argument("--max_tokens", type=int, default=10000)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)

    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    if args.limit:
        qas = qas[: args.limit]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    pending = [(qa, arm) for qa in qas for arm in args.arms if (arm, str(qa["qa_id"])) not in done]
    print(f"{len(done)} done, {len(pending)} to run -> {args.out}", flush=True)

    cfg = GenConfig(temperature=args.temperature, top_p=args.top_p, max_tokens=args.max_tokens, timeout=args.timeout)
    client = LLMZeroShotClient()
    lock, written, failed = threading.Lock(), 0, 0
    try:
        with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(process, qa, tables[str(qa["table_id"])], arm, client=client, cfg=cfg, model=args.model)
                for qa, arm in pending
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
