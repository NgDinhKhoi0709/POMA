"""D13: LLM header filtering vs Flatten V1, zero-shot Qwen3-8B (resumable JSONL, one record per qa x arm).

Arms
----
``v1_raw``     control: untouched Flatten V1 (the same string every other direction calls the control).
``v1_clean``   Flatten V1 over ``Grid.cleaned`` only, so the cleaning layer is separated from the filter.
``hdrfilter``  two calls: a filter call over the header-only view, then the solver over the compact
               table built from the selected headers.

Solver settings mirror ``scripts/run_d09_representation.py`` exactly (same prompt builder, schema,
repair path and ``GenConfig``); only the table string differs between arms. The filter call uses the
same client and generation config with the ``header_filter.v1`` schema.
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
from preprocessing.header_filter import apply_selection, build_filter_prompt, prepare  # noqa: E402
from preprocessing.variants import render_table  # noqa: E402
from src.contracts import CallContext, schema_for_call  # noqa: E402
from src.services import StructuredGenerator  # noqa: E402

DEFAULT_MODEL = "openrouter/qwen/qwen3-8b"
SOLVER_SCHEMA = "baseline_zero_shot.v1"
FILTER_SCHEMA = "header_filter.v1"
ARMS = ("v1_raw", "v1_clean", "hdrfilter")


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


def _generator(client, cfg: GenConfig, model: str):
    def generate_once(request_prompt: str, text_format: dict | None) -> tuple[str, dict]:
        structured = replace(
            cfg,
            text_format=None if text_format is None else dict(text_format),
            require_parameters=text_format is not None,
        )
        return client.generate_with_usage(model, request_prompt, structured, max_retries=4, retry_delay=15)

    return StructuredGenerator(generate_once)


def run_filter(qa: dict[str, Any], table: dict[str, Any], *, client, cfg, model: str) -> dict[str, Any]:
    """Header-filter call; returns the compact table string plus every decision it made."""
    grid, view = prepare(table)
    prompt = build_filter_prompt(str(qa["question"]), view)
    meta: dict[str, Any] = {
        "header_view_chars": len(view.text),
        "n_headers": view.n_headers,
        "filter_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    try:
        result = _generator(client, cfg, model).generate(
            prompt.strip(),
            schema_for_call(FILTER_SCHEMA),
            CallContext(qa_id=str(qa["qa_id"]), agent_name="HeaderFilter", prompt_name="header_filter", model=model),
        )
        selected = [str(x) for x in (result.data.get("selected_headers") or [])]
        parse_error = False
        meta.update({
            "filter_prompt_tokens": result.prompt_tokens,
            "filter_completion_tokens": result.completion_tokens,
            "filter_cost_usd": result.cost_usd,
            "filter_schema_valid": result.schema_valid,
        })
    except Exception as exc:  # a failed filter must not silently become the control
        selected, parse_error = [], True
        meta.update({"filter_error": f"{type(exc).__name__}: {exc}"[:200]})

    compact = apply_selection(grid, view, selected, parse_error=parse_error)
    meta.update({
        "selected_headers": list(compact.selected),
        "unknown_ids": list(compact.unknown_ids),
        "kept_cols": list(compact.kept_cols),
        "kept_rows_n": len(compact.kept_rows),
        "grid_cols": compact.n_cols,
        "grid_rows": compact.n_rows,
        "n_head": grid.n_head,
        "fallback": compact.fallback,
    })
    return {"table_str": compact.text, "meta": meta}


def process(qa: dict[str, Any], table: dict[str, Any], arm: str, *, client, cfg: GenConfig, model: str) -> dict[str, Any]:
    """One qa x arm: build this arm's table string, then run the zero-shot solver over it."""
    record: dict[str, Any] = {"arm": arm, "qa_id": str(qa["qa_id"]), "table_id": str(qa["table_id"])}
    started = time.time()
    if arm == "hdrfilter":
        try:
            stage = run_filter(qa, table, client=client, cfg=cfg, model=model)
        except Exception as exc:
            record.update({
                "elapsed_s": round(time.time() - started, 2),
                "error": f"filter/{type(exc).__name__}: {exc}"[:300],
            })
            return record
        table_str = stage["table_str"]
        record.update(stage["meta"])
    else:
        table_str = render_table(table, arm)

    prompt = build_tableqa_prompt(
        question=str(qa["question"]).strip(), table_str=table_str, prompt_style="zero_shot", answer_language="vi"
    )
    record.update({
        "prompt_version": "zero_shot_compact",
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "table_chars": len(table_str),
    })
    try:
        result = _generator(client, cfg, model).generate(
            prompt.strip(),
            schema_for_call(SOLVER_SCHEMA),
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
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "outputs/d13/qas_d13_200.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "outputs/d13/records.jsonl")
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
