"""D04: run the AST planner + deterministic executor over a QAs file (resumable JSONL).

The planner never sees the gold answer or hint labels and is independent of every reader, so one
log serves the override on top of any reader artifact. Qwen3-8B is called through OpenRouter with the
same provider pin as the baselines; thinking is disabled to match RankA's planner protocol.
"""

from __future__ import annotations

import argparse
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

from baseline.llm_client import (  # noqa: E402
    _openrouter_provider_for_model,
    get_openrouter_api_keys,
)
from src.table_executor.ast_executor import TableView  # noqa: E402
from src.table_executor.planner import (  # noqa: E402
    ops_used,
    plan_messages,
    run_plan,
    serialize,
)

DEFAULT_MODEL = "qwen/qwen3-8b"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
PLANNER_MAX_TOKENS = 450


def _chat(
    messages: list[dict[str, str]], *, model: str, api_key: str, timeout: int, retries: int = 4
) -> dict[str, Any]:
    import requests  # type: ignore

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "top_p": 1,
        "max_tokens": PLANNER_MAX_TOKENS,
        "reasoning": {"enabled": False},
    }
    provider = _openrouter_provider_for_model(model)
    if provider:
        body["provider"] = provider
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error = ""
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=body, timeout=timeout)
            if response.status_code == 200:
                payload = response.json()
                choices = payload.get("choices") or []
                if choices:
                    return payload
                last_error = f"no choices: {json.dumps(payload)[:200]}"
            else:
                last_error = f"status {response.status_code}: {response.text[:200]}"
        except Exception as exc:  # network failure: retry, never fabricate a result
            last_error = f"{type(exc).__name__}: {exc}"[:300]
        time.sleep(min(30, 3 * 2 ** attempt))
    raise RuntimeError(last_error)


def _process(item: dict[str, Any], table: dict[str, Any], *, model: str, api_key: str, timeout: int) -> dict[str, Any]:
    table_text, truncated = serialize(table)
    view = TableView.from_dataset(table)
    record: dict[str, Any] = {
        "qa_id": item["qa_id"],
        "table_id": item["table_id"],
        "question": item["question"],
        "table_truncated": truncated,
        "n_rows": len(view.rows),
    }
    started = time.time()
    try:
        payload = _chat(plan_messages(table_text, item["question"]), model=model, api_key=api_key, timeout=timeout)
    except Exception as exc:
        record["infra_error"] = str(exc)[:300]
        return record
    raw = payload["choices"][0]["message"].get("content") or ""
    usage = payload.get("usage") or {}
    record.update({
        "plan_raw": raw,
        "plan_s": round(time.time() - started, 2),
        "provider": payload.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),
        "finish_reason": payload["choices"][0].get("finish_reason"),
    })
    outcome = run_plan(raw, view, item["question"])
    record.update({f"exec_{key}": value for key, value in outcome.items()})
    record["ops"] = ops_used(outcome.get("ast"))
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--tables", type=Path, default=Path("dataset/table.json"))
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL log")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model id (no provider prefix)")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many new items (smoke test)")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    api_key = get_openrouter_api_keys()[0]

    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done: set[str] = set()
    if args.out.exists():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "infra_error" not in row:  # retry infra failures on resume
                    done.add(str(row["qa_id"]))
    pending = [q for q in qas if str(q["qa_id"]) not in done]
    if args.limit:
        pending = pending[: args.limit]
    print(f"{len(done)} done, {len(pending)} to run -> {args.out}", flush=True)

    lock = threading.Lock()
    written = 0
    with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(_process, q, tables[str(q["table_id"])], model=args.model, api_key=api_key, timeout=args.timeout)
            for q in pending
        ]
        for future in as_completed(futures):
            record = future.result()
            with lock:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                written += 1
                if written % 20 == 0:
                    print(f"{written}/{len(pending)}", flush=True)
    print(f"done: {written} written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
