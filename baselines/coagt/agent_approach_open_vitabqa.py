"""Run CoAgt on Open_ViTabQA records converted to WikiTQ-style JSONL.

This script intentionally reuses the original CoAgt prompt functions from
utils.agents_prompt_wtq without editing them. Only dataset format, model,
temperatures, and chunk size are adapted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from baselines.contracts import (
    RunPaths,
    append_jsonl,
    read_jsonl,
    validate_prediction,
    write_json,
)
from .convert_open_vitabqa import convert_open_vitabqa, load_records
from .utils.agents_prompt_wtq import (
    prompt_agent_follow,
    prompt_agent_synthesis,
    prompt_answer_refiner,
)
from .utils.spliter_chunk import chunk_table


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0

    def add(self, usage: Any) -> None:
        if usage is None:
            return
        self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)
        self.calls += 1


@dataclass(frozen=True)
class Pricing:
    input_usd_per_1m: float
    output_usd_per_1m: float

    @classmethod
    def from_env(cls, model: str) -> "Pricing":
        default_input = 0.15 if model == "gpt-4o-mini" else 0.0
        default_output = 0.60 if model == "gpt-4o-mini" else 0.0
        return cls(
            input_usd_per_1m=float(os.getenv("OPENAI_INPUT_USD_PER_1M", default_input)),
            output_usd_per_1m=float(os.getenv("OPENAI_OUTPUT_USD_PER_1M", default_output)),
        )

    def estimate(self, usage: Usage) -> float:
        return (
            usage.prompt_tokens * self.input_usd_per_1m / 1_000_000
            + usage.completion_tokens * self.output_usd_per_1m / 1_000_000
        )


def load_env() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)


def normalize_openai_model(model: str) -> str:
    value = str(model).strip()
    return value.split("/", 1)[1] if value.startswith("openai/") else value


def call_model(client: OpenAI, *, model: str, prompt: str, temperature: float, max_retries: int, usage: Usage) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            usage.add(response.usage)
            return response.choices[0].message.content or ""
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt >= max_retries:
                break
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(str(last_error)) from last_error


def run_sample(
    record: dict[str, Any],
    *,
    client: OpenAI,
    model: str,
    pricing: Pricing,
    max_chunk_tokens: int,
    collector_temperature: float,
    synthesizer_temperature: float,
    refiner_temperature: float,
    max_retries: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    ids = record["ids"]
    title = record["title"]
    headers = record["table_text"][0]
    table = record["table_text"][1:]
    total_rows = len(table)
    question = record["statement"]
    answer = ", ".join(str(value) for value in record.get("answer", []))
    chunks = chunk_table(table, max_tokens=max_chunk_tokens)
    agents_outputs = [""]
    usage = Usage()

    row_pointer = 1
    for agent_index, subtable in enumerate(chunks, start=1):
        row_rank = list(range(row_pointer, row_pointer + len(subtable)))
        prompt = prompt_agent_follow(title, question, headers, total_rows, agents_outputs[agent_index - 1], subtable, agent_index, row_rank)
        collector_output = call_model(
            client,
            model=model,
            prompt=prompt,
            temperature=collector_temperature,
            max_retries=max_retries,
            usage=usage,
        )
        agents_outputs.append(f"AGENT_COL_{agent_index}: {collector_output}")
        row_pointer += len(subtable)

    synthesis_prompt = prompt_agent_synthesis(title, question, headers, total_rows, agents_outputs)
    response = call_model(
        client,
        model=model,
        prompt=synthesis_prompt,
        temperature=synthesizer_temperature,
        max_retries=max_retries,
        usage=usage,
    )
    answer_prompt = prompt_answer_refiner(question, response)
    prediction = call_model(
        client,
        model=model,
        prompt=answer_prompt,
        temperature=refiner_temperature,
        max_retries=max_retries,
        usage=usage,
    ).strip()
    cost_usd = pricing.estimate(usage)

    return {
        "qa_id": ids,
        "key": ids,
        "table_id": record.get("table_id"),
        "source_split": record.get("source_split"),
        "question": question,
        "response": response,
        "prediction": prediction,
        "answer": answer,
        "model": model,
        "method": "coagt",
        "num_collectors": len(chunks),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "api_calls": usage.calls,
        "cost_usd": round(cost_usd, 8),
        "latency_s": round(time.perf_counter() - started, 3),
        "error": None,
        "stage": "coagt_open_vitabqa",
        "temperatures": {
            "collector": collector_temperature,
            "synthesizer": synthesizer_temperature,
            "refiner": refiner_temperature,
        },
        "max_chunk_tokens": max_chunk_tokens,
    }


def run_sample_worker(
    record: dict[str, Any],
    *,
    model: str,
    pricing: Pricing,
    max_chunk_tokens: int,
    collector_temperature: float,
    synthesizer_temperature: float,
    refiner_temperature: float,
    max_retries: int,
) -> dict[str, Any]:
    return run_sample(
        record,
        client=OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip() or "missing"),
        model=model,
        pricing=pricing,
        max_chunk_tokens=max_chunk_tokens,
        collector_temperature=collector_temperature,
        synthesizer_temperature=synthesizer_temperature,
        refiner_temperature=refiner_temperature,
        max_retries=max_retries,
    )


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_record_id(record: dict[str, Any]) -> str | None:
    value = record.get("ids") or record.get("qa_id") or record.get("key")
    return str(value) if value is not None else None


def extract_done_id_from_line(line: str) -> str | None:
    try:
        record = json.loads(line)
        return get_record_id(record) if isinstance(record, dict) else None
    except json.JSONDecodeError:
        for marker in ('"qa_id"', '"key"', '"ids"'):
            marker_index = line.find(marker)
            if marker_index == -1:
                continue
            colon_index = line.find(":", marker_index + len(marker))
            if colon_index == -1:
                continue
            remainder = line[colon_index + 1 :].lstrip()
            if not remainder.startswith('"'):
                continue
            end_index = remainder.find('"', 1)
            if end_index > 1:
                return remainder[1:end_index]
    return None


def load_done_ids(*paths: Path) -> set[str]:
    done: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                qa_id = extract_done_id_from_line(line)
                if qa_id is not None:
                    done.add(qa_id)
    return done


def filter_records_for_resume(records: list[dict[str, Any]], done_ids: set[str]) -> tuple[list[dict[str, Any]], int, int]:
    pending: list[dict[str, Any]] = []
    scheduled_ids: set[str] = set()
    skipped_existing = 0
    skipped_duplicate_input = 0
    for record in records:
        qa_id = get_record_id(record)
        if qa_id is None:
            pending.append(record)
            continue
        if qa_id in done_ids:
            skipped_existing += 1
            continue
        if qa_id in scheduled_ids:
            skipped_duplicate_input += 1
            continue
        scheduled_ids.add(qa_id)
        pending.append(record)
    return pending, skipped_existing, skipped_duplicate_input


def _prepare_run_paths(
    run_paths: RunPaths,
    *,
    resume: bool,
    overwrite: bool,
) -> None:
    existing = [path for path in run_paths.generated_files() if path.exists()]
    if existing and not resume and not overwrite:
        raise FileExistsError(
            f"run already contains generated files: {run_paths.root}"
        )
    if overwrite:
        for path in run_paths.generated_files():
            if path.exists():
                path.unlink()
    run_paths.root.mkdir(parents=True, exist_ok=True)


def run_open_vitabqa(
    *,
    qas_path: Path,
    tables_path: Path,
    run_paths: RunPaths,
    model: str,
    limit: int | None,
    max_workers: int,
    resume: bool,
    overwrite: bool,
) -> dict[str, Any]:
    _prepare_run_paths(run_paths, resume=resume, overwrite=overwrite)
    load_env()
    backend_model = normalize_openai_model(model)
    pricing = Pricing.from_env(backend_model)
    records = convert_open_vitabqa(qas_path, tables_path, limit=limit)
    selected_qas = load_records(qas_path, "qas")
    if limit is not None:
        selected_qas = selected_qas[:limit]
    write_json(run_paths.qas_subset, {"qas": selected_qas})

    done_ids = (
        load_done_ids(run_paths.results_jsonl, run_paths.errors_jsonl)
        if resume
        else set()
    )
    pending, skipped_existing, skipped_duplicate_input = filter_records_for_resume(
        records, done_ids
    )
    failures = 0
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or "adapter-test-key"
    client = OpenAI(api_key=api_key)

    def handle_success(prediction: dict[str, Any]) -> None:
        validate_prediction(prediction, "coagt")
        append_jsonl(run_paths.results_jsonl, prediction)

    if max_workers <= 1:
        for record in pending:
            try:
                handle_success(
                    run_sample(
                        record,
                        client=client,
                        model=backend_model,
                        pricing=pricing,
                        max_chunk_tokens=1000,
                        collector_temperature=0.2,
                        synthesizer_temperature=0.5,
                        refiner_temperature=0.0,
                        max_retries=5,
                    )
                )
            except Exception as error:  # noqa: BLE001
                failures += 1
                append_jsonl(
                    run_paths.errors_jsonl,
                    {
                        "qa_id": record.get("ids"),
                        "table_id": record.get("table_id"),
                        "error": f"{type(error).__name__}: {error}",
                    },
                )
    else:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, max_workers)
        ) as executor:
            futures = {
                executor.submit(
                    run_sample_worker,
                    record,
                    model=backend_model,
                    pricing=pricing,
                    max_chunk_tokens=1000,
                    collector_temperature=0.2,
                    synthesizer_temperature=0.5,
                    refiner_temperature=0.0,
                    max_retries=5,
                ): record
                for record in pending
            }
            for future in concurrent.futures.as_completed(futures):
                record = futures[future]
                try:
                    handle_success(future.result())
                except Exception as error:  # noqa: BLE001
                    failures += 1
                    append_jsonl(
                        run_paths.errors_jsonl,
                        {
                            "qa_id": record.get("ids"),
                            "table_id": record.get("table_id"),
                            "error": f"{type(error).__name__}: {error}",
                        },
                    )

    results = read_jsonl(run_paths.results_jsonl)
    errors = read_jsonl(run_paths.errors_jsonl)
    order = {str(record["ids"]): index for index, record in enumerate(records)}
    results.sort(key=lambda item: order.get(str(item.get("qa_id")), 10**9))
    write_json(run_paths.results_json, results)
    total_prompt = sum(int(item.get("prompt_tokens") or 0) for item in results)
    total_completion = sum(
        int(item.get("completion_tokens") or 0) for item in results
    )
    total_tokens = sum(int(item.get("total_tokens") or 0) for item in results)
    total_calls = sum(int(item.get("api_calls") or 0) for item in results)
    total_cost = sum(float(item.get("cost_usd") or 0.0) for item in results)
    meta = {
        "method": "coagt",
        "model": model,
        "backend_model": backend_model,
        "selected_records": len(records),
        "pending_records": len(pending),
        "num_records": len(results),
        "num_errors": len(errors),
        "failures": failures,
        "max_workers": max(1, max_workers),
        "resume": resume,
        "overwrite": overwrite,
        "existing_done_ids": len(done_ids),
        "skipped_existing": skipped_existing,
        "skipped_duplicate_input": skipped_duplicate_input,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "api_calls": total_calls,
        "cost_usd": round(total_cost, 8),
        "temperatures": {
            "collector": 0.2,
            "synthesizer": 0.5,
            "refiner": 0.0,
        },
        "max_chunk_tokens": 1000,
    }
    write_json(run_paths.meta_json, meta)
    return meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dataset_wtq/open_vitabqa_smoke_5.jsonl")
    parser.add_argument("--output", default="outputs/open_vitabqa_smoke_5_predictions.jsonl")
    parser.add_argument("--errors-output", help="Error JSONL path. Defaults to <output-stem>_errors.jsonl")
    parser.add_argument("--summary-output", help="Summary JSON path. Defaults to <output-stem>_summary.json")
    parser.add_argument("--limit", type=int, help="Only run the first N records from the input JSONL")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-chunk-tokens", type=int, default=1000)
    parser.add_argument("--collector-temperature", type=float, default=0.2)
    parser.add_argument("--synthesizer-temperature", type=float, default=0.5)
    parser.add_argument("--refiner-temperature", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--max-workers", type=int, default=1, help="Number of QA samples to process concurrently")
    parser.add_argument("--resume", action="store_true", help="Skip qa_ids already present in output/error JSONL files")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    load_env()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is missing. Put it in baselines/CoAgt/.env or set it in the environment.")

    output_path = Path(args.output)
    errors_path = Path(args.errors_output) if args.errors_output else output_path.with_name(f"{output_path.stem}_errors.jsonl")
    summary_path = Path(args.summary_output) if args.summary_output else output_path.with_name(f"{output_path.stem}_summary.json")
    if args.overwrite:
        for path in (output_path, errors_path, summary_path):
            if path.exists():
                path.unlink()

    client = OpenAI()
    pricing = Pricing.from_env(args.model)
    total_usage = Usage()
    total_cost = 0.0
    failures = 0
    records = list(iter_jsonl(Path(args.input)))
    if args.limit is not None:
        if args.limit < 0:
            raise SystemExit("--limit must be non-negative")
        records = records[: args.limit]
    selected_records = len(records)
    done_ids = load_done_ids(output_path, errors_path) if args.resume else set()
    records, skipped_existing, skipped_duplicate_input = filter_records_for_resume(records, done_ids)
    max_workers = max(1, args.max_workers)

    if max_workers == 1:
        for record in tqdm(records, desc="CoAgt Open_ViTabQA"):
            try:
                prediction = run_sample(
                    record,
                    client=client,
                    model=args.model,
                    pricing=pricing,
                    max_chunk_tokens=args.max_chunk_tokens,
                    collector_temperature=args.collector_temperature,
                    synthesizer_temperature=args.synthesizer_temperature,
                    refiner_temperature=args.refiner_temperature,
                    max_retries=args.max_retries,
                )
                write_jsonl(output_path, prediction)
                total_usage.prompt_tokens += prediction["prompt_tokens"]
                total_usage.completion_tokens += prediction["completion_tokens"]
                total_usage.total_tokens += prediction["total_tokens"]
                total_usage.calls += prediction["api_calls"]
                total_cost += prediction["cost_usd"]
            except Exception as error:  # noqa: BLE001
                failures += 1
                write_jsonl(errors_path, {"qa_id": record.get("ids"), "table_id": record.get("table_id"), "error": str(error)})
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_record: dict[concurrent.futures.Future[dict[str, Any]], dict[str, Any]] = {}
            for record in records:
                future = executor.submit(
                    run_sample_worker,
                    record,
                    model=args.model,
                    pricing=pricing,
                    max_chunk_tokens=args.max_chunk_tokens,
                    collector_temperature=args.collector_temperature,
                    synthesizer_temperature=args.synthesizer_temperature,
                    refiner_temperature=args.refiner_temperature,
                    max_retries=args.max_retries,
                )
                future_to_record[future] = record

            for future in tqdm(
                concurrent.futures.as_completed(future_to_record),
                total=len(future_to_record),
                desc=f"CoAgt Open_ViTabQA ({max_workers} workers)",
            ):
                record = future_to_record[future]
                try:
                    prediction = future.result()
                    write_jsonl(output_path, prediction)
                    total_usage.prompt_tokens += prediction["prompt_tokens"]
                    total_usage.completion_tokens += prediction["completion_tokens"]
                    total_usage.total_tokens += prediction["total_tokens"]
                    total_usage.calls += prediction["api_calls"]
                    total_cost += prediction["cost_usd"]
                except Exception as error:  # noqa: BLE001
                    failures += 1
                    write_jsonl(errors_path, {"qa_id": record.get("ids"), "table_id": record.get("table_id"), "error": str(error)})

    summary = {
        "input": args.input,
        "output": str(output_path),
        "errors_output": str(errors_path),
        "selected_records": selected_records,
        "pending_records": len(records),
        "limit": args.limit,
        "failures": failures,
        "model": args.model,
        "max_chunk_tokens": args.max_chunk_tokens,
        "max_workers": max_workers,
        "resume": args.resume,
        "existing_done_ids": len(done_ids),
        "skipped_existing": skipped_existing,
        "skipped_duplicate_input": skipped_duplicate_input,
        "temperatures": {
            "collector": args.collector_temperature,
            "synthesizer": args.synthesizer_temperature,
            "refiner": args.refiner_temperature,
        },
        "usage": {
            "prompt_tokens": total_usage.prompt_tokens,
            "completion_tokens": total_usage.completion_tokens,
            "total_tokens": total_usage.total_tokens,
            "api_calls": total_usage.calls,
        },
        "cost": {
            "total_cost_usd": round(total_cost, 8),
            "input_usd_per_1m": pricing.input_usd_per_1m,
            "output_usd_per_1m": pricing.output_usd_per_1m,
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
