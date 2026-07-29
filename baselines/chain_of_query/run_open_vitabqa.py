from __future__ import annotations

import argparse
import importlib.util
import importlib.machinery
import json
import os
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from baselines.contracts import (
    RunPaths,
    read_jsonl,
    validate_prediction,
    write_json,
)


BASELINE_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = BASELINE_ROOT.parents[1]
if str(BASELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(BASELINE_ROOT))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from convert_open_vitabqa import convert_open_vitabqa


REQUIRED_IMPORTS = {
    "openai": "openai",
    "pandas": "pandas",
    "records": "records",
    "sqlalchemy": "sqlalchemy",
    "tiktoken": "tiktoken",
    "recognizers_suite": "recognizers-suite",
    "fuzzywuzzy": "fuzzywuzzy",
}


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (
        WORKSPACE_ROOT / ".env",
        BASELINE_ROOT / ".env",
        WORKSPACE_ROOT / "baselines" / "CoAgt" / ".env",
        WORKSPACE_ROOT / "POMA" / ".env",
        WORKSPACE_ROOT / "ViPanelTR" / ".env",
    ):
        if candidate.exists():
            load_dotenv(candidate, override=False)


def _check_dependencies() -> None:
    missing = [package for module, package in REQUIRED_IMPORTS.items() if importlib.util.find_spec(module) is None]
    if missing:
        joined = " ".join(missing)
        raise RuntimeError(f"Missing ChainofQuery dependencies. Install with: python -m pip install {joined}")


def _normalize_model_for_openai(model: str) -> str:
    if model.startswith("openai/"):
        return model.split("/", 1)[1]
    return model


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

    def estimate(self, usage: dict[str, int]) -> float:
        return (
            int(usage.get("prompt_tokens", 0)) * self.input_usd_per_1m / 1_000_000
            + int(usage.get("completion_tokens", 0)) * self.output_usd_per_1m / 1_000_000
        )


def _install_unused_dataset_stub() -> None:
    """Avoid installing HuggingFace datasets for the local Open_ViTabQA runner."""
    if importlib.util.find_spec("datasets") is not None or "datasets" in sys.modules:
        return
    module = types.ModuleType("datasets")
    module.__spec__ = importlib.machinery.ModuleSpec("datasets", loader=None)

    class Dataset(list):
        @classmethod
        def from_list(cls, values: list[dict[str, Any]]) -> "Dataset":
            return cls(values)

    def load_dataset(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("HuggingFace datasets is not available in the Open_ViTabQA runner.")

    module.Dataset = Dataset
    module.load_dataset = load_dataset
    sys.modules["datasets"] = module


def _as_answer_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _missing_full_pipeline_modules() -> list[str]:
    required = [
        "utils.agents.column_selector",
        "utils.agents.withas",
        "utils.agents.row_selector",
        "utils.agents.aggfunc1",
        "utils.agents.aggfunc2",
        "utils.agents.order1",
        "utils.agents.order2",
    ]
    return [name for name in required if importlib.util.find_spec(name) is None]


def require_fallback_mode(record: dict[str, Any]) -> None:
    if record.get("pipeline_mode") != "coq_base_sql_fallback":
        raise RuntimeError(
            "CoQ integration requires pipeline_mode=coq_base_sql_fallback "
            "for the available source snapshot"
        )
    if not str(record.get("fallback_reason") or "").strip():
        raise RuntimeError("CoQ fallback_reason must be non-empty")


def get_record_id(record: dict[str, Any]) -> str | None:
    value = record.get("qa_id") or record.get("key") or record.get("ids")
    return str(value) if value is not None else None


def extract_done_id_from_line(line: str) -> str | None:
    try:
        payload = json.loads(line)
        return get_record_id(payload) if isinstance(payload, dict) else None
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


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_done_ids(*paths: Path) -> set[str]:
    done: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = []
            records = payload if isinstance(payload, list) else payload.get("results", []) if isinstance(payload, dict) else []
            for record in records if isinstance(records, list) else []:
                if isinstance(record, dict):
                    qa_id = get_record_id(record)
                    if qa_id is not None:
                        done.add(qa_id)
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


def load_result_records(path: Path, order: dict[str, int]) -> list[dict[str, Any]]:
    records = [record for record in iter_jsonl(path) or [] if isinstance(record, dict)]
    records.sort(key=lambda item: order.get(str(item.get("qa_id")), 10**9))
    return records


def seed_jsonl_from_json(json_path: Path, jsonl_path: Path) -> None:
    if jsonl_path.exists() or not json_path.exists():
        return
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    records = payload if isinstance(payload, list) else payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(records, list):
        return
    for record in records:
        if isinstance(record, dict):
            write_jsonl(jsonl_path, record)


def _run_one(
    record: dict[str, Any],
    *,
    model: str,
    api_key: str,
    pricing: Pricing,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    _install_unused_dataset_stub()

    from utils.database import MYSQLDB
    from utils.general_prompt import create_table_prompt, select_x_rows_prompt
    from utils.helper import PipelineContext
    from utils.myllm import MyChatGPT
    from utils.reasoner import ANSWER_agent, chainofthought_answer_agent

    missing_pipeline_modules = _missing_full_pipeline_modules()
    if missing_pipeline_modules:
        from utils.agents.base_sql_generator import base_sql_agent

        agent_pipeline = None
        pipeline_mode = "coq_base_sql_fallback"
        fallback_reason = "Missing full pipeline modules: " + ", ".join(missing_pipeline_modules)
    else:
        pipeline_mode = "full_chainofquery"
        fallback_reason = None
        try:
            from utils.pipeline import agent_pipeline
        except (ModuleNotFoundError, ImportError) as exc:
            sys.modules.pop("utils.pipeline", None)
            from utils.agents.base_sql_generator import base_sql_agent

            agent_pipeline = None
            pipeline_mode = "coq_base_sql_fallback"
            fallback_reason = str(exc)

    if pipeline_mode == "coq_base_sql_fallback" and "base_sql_agent" not in locals():
        from utils.agents.base_sql_generator import base_sql_agent

    start = time.perf_counter()
    sqldb = None
    log: dict[str, Any] = {
        "sqls": [],
        "s_answer": "",
        "p_answer": "",
        "valid": None,
        "correct": None,
    }
    prediction = ""
    error = None
    valid_flag = False
    answer_flag = False
    sql_query = ""
    response = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "api_calls": 0}

    try:
        table_info = record["table"]
        question = str(record["question"])
        standard_answer = _as_answer_text(record.get("answer", ""))
        sqldb = MYSQLDB(tables=[table_info])

        table_df = sqldb.get_table_df()
        table_title = sqldb.get_table_title()
        table_dict = sqldb.get_table()
        prompt_table = create_table_prompt(df=table_df, title=table_title)
        total_rows, prompt_rows = select_x_rows_prompt(
            full_table=False,
            df=table_df,
            title=table_title,
            num_rows=3,
        )
        prompt_schema = prompt_table + prompt_rows

        llm = MyChatGPT(model_name=model, key=api_key)
        ctx = PipelineContext(
            llm=llm,
            sqldb=sqldb,
            question=question,
            prompt_schema=prompt_schema,
            title=table_title,
            previous_sql_query=None,
            total_rows=total_rows,
            log=log,
            flag=None,
            num_rows=3,
            llm_options={"temperature": temperature},
            debug=False,
            strategy="top",
            extras={"timeout": timeout},
        )

        if agent_pipeline is not None:
            valid_flag, answer_flag, sql_query, generated_answer, log = agent_pipeline(ctx, standard_answer)
            if valid_flag:
                prediction = generated_answer
                response = generated_answer
            elif not answer_flag:
                analysis, prediction = chainofthought_answer_agent(
                    llm=llm,
                    question=question,
                    table_dict=table_dict,
                    debug=False,
                )
                response = analysis
            else:
                prediction = generated_answer
                response = generated_answer
        else:
            sql_query = base_sql_agent(
                llm=llm,
                question=question,
                prompt_schema=prompt_schema,
                title=table_title,
                debug=False,
            )
            log["sqls"].append(sql_query)
            sql_result = sqldb.execute_query(sql_query)
            valid_flag = not bool(sql_result.get("sqlite_error"))
            if valid_flag:
                answer_flag, prediction, log = ANSWER_agent(
                    llm=llm,
                    sqldb=sqldb,
                    question=question,
                    prompt_schema=prompt_schema,
                    title=table_title,
                    standard_answer=standard_answer,
                    sql_query=sql_query,
                    log=log,
                )
                response = prediction
            if not prediction:
                analysis, prediction = chainofthought_answer_agent(
                    llm=llm,
                    question=question,
                    table_dict=table_dict,
                    debug=False,
                )
                response = analysis
        log["p_answer"] = prediction
        log["s_answer"] = standard_answer
        log["valid"] = bool(valid_flag)
        log["correct"] = bool(answer_flag)
        usage = llm.usage.to_dict()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if sqldb is not None:
            sqldb.close()

    cost_usd = pricing.estimate(usage)
    return {
        "qa_id": record.get("qa_id"),
        "key": record.get("qa_id"),
        "table_id": record.get("table_id"),
        "source_split": record.get("source_split", "test"),
        "question": record.get("question"),
        "response": response,
        "prediction": prediction,
        "answer": record.get("answer", ""),
        "hints": record.get("hints", []),
        "model": model,
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "api_calls": usage["api_calls"],
        "cost_usd": round(cost_usd, 8),
        "stage": "chainofquery_open_vitabqa",
        "temperatures": {"default": temperature},
        "method": "coq",
        "pipeline_mode": pipeline_mode,
        "fallback_reason": fallback_reason,
        "valid_sql": valid_flag,
        "answer_flag": answer_flag,
        "final_sql": sql_query,
        "latency_s": round(time.perf_counter() - start, 3),
        "error": error,
        "log": log,
    }


def _run_open_vitabqa_args(args: argparse.Namespace) -> dict[str, Any]:
    _load_env_files()
    _check_dependencies()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or "adapter-test-key"

    source_records = convert_open_vitabqa(args.qas, args.tables, limit=args.limit)
    backend_model = _normalize_model_for_openai(args.model)
    pricing = Pricing.from_env(backend_model)
    run_dir = args.output_dir / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results_path = run_dir / "results.json"
    results_jsonl_path = run_dir / "results.jsonl"
    errors_jsonl_path = Path(args.errors_output) if args.errors_output else run_dir / "errors.jsonl"
    meta_path = run_dir / "meta.json"
    if args.overwrite:
        for path in (results_path, results_jsonl_path, errors_jsonl_path, meta_path):
            if path.exists():
                path.unlink()
    if args.resume:
        seed_jsonl_from_json(results_path, results_jsonl_path)

    data_path = run_dir / "input_open_vitabqa.json"
    data_path.write_text(json.dumps(source_records, ensure_ascii=False, indent=2), encoding="utf-8")
    qas_subset_path = run_dir / "qas_subset.json"
    qas_subset = {
        "qas": [
            {
                "qa_id": record.get("qa_id"),
                "table_id": record.get("table_id"),
                "question": record.get("question"),
                "answer": record.get("answer", ""),
                "hints": record.get("hints", []),
            }
            for record in source_records
        ]
    }
    qas_subset_path.write_text(json.dumps(qas_subset, ensure_ascii=False, indent=2), encoding="utf-8")

    selected_records = len(source_records)
    done_ids = load_done_ids(results_jsonl_path, errors_jsonl_path, results_path) if args.resume else set()
    pending_records, skipped_existing, skipped_duplicate_input = filter_records_for_resume(source_records, done_ids)
    order = {record["qa_id"]: idx for idx, record in enumerate(source_records)}
    max_workers = max(1, int(args.max_workers or 1))

    if max_workers <= 1:
        for idx, record in enumerate(pending_records, start=1):
            print(f"[{idx}/{len(pending_records)}] {record['qa_id']}", flush=True)
            result = _run_one(
                record,
                model=backend_model,
                api_key=api_key,
                pricing=pricing,
                temperature=args.temperature,
                timeout=args.timeout,
            )
            if result.get("error"):
                write_jsonl(errors_jsonl_path, result)
            else:
                write_jsonl(results_jsonl_path, result)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_by_id = {
                executor.submit(
                    _run_one,
                    record,
                    model=backend_model,
                    api_key=api_key,
                    pricing=pricing,
                    temperature=args.temperature,
                    timeout=args.timeout,
                ): record.get("qa_id")
                for record in pending_records
            }
            for future in as_completed(future_by_id):
                print(f"completed {future_by_id[future]}", flush=True)
                try:
                    result = future.result()
                    if result.get("error"):
                        write_jsonl(errors_jsonl_path, result)
                    else:
                        write_jsonl(results_jsonl_path, result)
                except Exception as exc:
                    write_jsonl(errors_jsonl_path, {"qa_id": future_by_id[future], "error": f"{type(exc).__name__}: {exc}"})

    results = load_result_records(results_jsonl_path, order)
    errors = [record for record in iter_jsonl(errors_jsonl_path) or [] if isinstance(record, dict)]
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "method": "coq",
        "upstream_commit": _read_git_commit(),
        "model": args.model,
        "backend_model": backend_model,
        "limit": args.limit,
        "selected_records": selected_records,
        "pending_records": len(pending_records),
        "max_workers": max_workers,
        "resume": args.resume,
        "overwrite": args.overwrite,
        "existing_done_ids": len(done_ids),
        "skipped_existing": skipped_existing,
        "skipped_duplicate_input": skipped_duplicate_input,
        "num_records": len(results),
        "num_errors": len(errors),
        "num_valid_sql": sum(1 for item in results if item.get("valid_sql")),
        "prompt_tokens": sum(int(item.get("prompt_tokens") or 0) for item in results),
        "completion_tokens": sum(int(item.get("completion_tokens") or 0) for item in results),
        "total_tokens": sum(int(item.get("total_tokens") or 0) for item in results),
        "api_calls": sum(int(item.get("api_calls") or 0) for item in results),
        "cost_usd": round(sum(float(item.get("cost_usd") or 0.0) for item in results), 8),
        "pricing": {
            "input_usd_per_1m": pricing.input_usd_per_1m,
            "output_usd_per_1m": pricing.output_usd_per_1m,
        },
        "avg_latency_s": round(sum(float(item.get("latency_s") or 0) for item in results) / len(results), 3)
        if results
        else 0,
        "input_path": str(data_path),
        "qas_subset_path": str(qas_subset_path),
        "results_path": str(results_path),
        "results_jsonl_path": str(results_jsonl_path),
        "errors_jsonl_path": str(errors_jsonl_path),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"results_path": results_path, "meta_path": meta_path, "meta": meta}


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
    args = argparse.Namespace(
        qas=qas_path,
        tables=tables_path,
        model=model,
        output_dir=run_paths.root.parent,
        run_id=run_paths.root.name,
        limit=limit,
        max_workers=max(1, max_workers),
        temperature=0.0,
        timeout=60,
        errors_output=run_paths.errors_jsonl,
        resume=resume,
        overwrite=overwrite,
    )
    outcome = _run_open_vitabqa_args(args)
    results = read_jsonl(run_paths.results_jsonl)
    for record in results:
        require_fallback_mode(record)
        validate_prediction(record, "coq")

    missing = _missing_full_pipeline_modules()
    fallback_reason = (
        str(results[0]["fallback_reason"])
        if results
        else "Missing full pipeline modules: " + ", ".join(missing)
    )
    meta = dict(outcome["meta"])
    meta["method"] = "coq"
    meta["pipeline_mode"] = "coq_base_sql_fallback"
    meta["fallback_reason"] = fallback_reason
    require_fallback_mode(meta)
    write_json(run_paths.meta_json, meta)
    return meta


def _read_git_commit() -> str:
    head = BASELINE_ROOT / ".git" / "HEAD"
    if not head.exists():
        return ""
    value = head.read_text(encoding="utf-8").strip()
    if value.startswith("ref:"):
        ref = BASELINE_ROOT / ".git" / value.split(" ", 1)[1]
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip()
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ChainofQuery on Open_ViTabQA.")
    parser.add_argument("--qas", required=True, type=Path)
    parser.add_argument("--tables", required=True, type=Path)
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--output-dir", type=Path, default=Path("run_test/ChainofQuery"))
    parser.add_argument("--run-id", default="smoke-gpt4o-mini")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--errors-output", type=Path, default=None)
    parser.add_argument("--resume", action="store_true", help="Skip qa_ids already present in results/errors JSONL.")
    parser.add_argument("--overwrite", action="store_true", help="Delete existing result, error, and meta files before running.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outcome = _run_open_vitabqa_args(args)
    print(f"Wrote results to {outcome['results_path']}")
    print(f"Wrote meta to {outcome['meta_path']}")


if __name__ == "__main__":
    main()
