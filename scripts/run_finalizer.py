"""Apply one offline answer-finalization policy to saved raw predictions."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseline.llm_client import parse_model_spec
from src.agents.answer_normalization import AnswerNormalizationAgent
from src.agents.grounded_single_answer import GroundedSingleAnswerAgent
from src.config.settings import LLMConfig, get_settings
from src.contracts.structured_outputs import StructuredOutputMode
from src.finalization.artifacts import (
    IncrementalArtifactStore,
    RunManifest,
    failure_record,
    success_record,
)
from src.finalization.finalizers import (
    CommonAnswerNormalizationFinalizer,
    FinalizationRequest,
    GroundedSingleAnswerFinalizer,
    NativeAnswerNormalizationFinalizer,
)
from src.finalization.sources import load_finalization_requests
from src.services.llm_client import LLMClient
from src.services.structured_generation import resolve_output_mode


FinalizerFactory = Callable[[LLMConfig], object]
_SOURCE_KINDS = ("poma-specialists", "direct-baseline")
_FINALIZERS = ("an-native", "an-common", "gsa")
_PROVIDERS = ("openai", "openrouter")
_PROMPT_VERSIONS = {
    "an-native": "answer_normalization.v1",
    "an-common": "answer_normalization.v1",
    "gsa": "grounded_single_answer.v1",
}
_SCHEMA_VERSIONS = {
    "an-native": "answer_normalization.v1",
    "an-common": "answer_normalization.v1",
    "gsa": "gsa.v1",
}


def _incremental_path(output_path: Path) -> Path:
    if output_path.suffix.lower() == ".jsonl":
        return output_path.with_name(f"{output_path.stem}.incremental.jsonl")
    return output_path.with_suffix(".jsonl")


class _FinalizerArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if parsed.finalizer == "gsa" and not parsed.tables:
            self.error("--tables is required when --finalizer is gsa")
        if parsed.limit is not None and parsed.limit <= 0:
            self.error("--limit must be positive")
        if parsed.max_workers <= 0:
            self.error("--max-workers must be positive")
        if parsed.retry_failed and not parsed.resume:
            self.error("--retry-failed requires --resume")

        source = _resolve_project_path(parsed.source).resolve()
        output = _resolve_project_path(parsed.output).resolve()
        if source == output:
            self.error("--output must differ from --source")
        if source == _incremental_path(output).resolve():
            self.error("incremental output must differ from --source")

        inferred_provider, _ = parse_model_spec(parsed.model)
        if parsed.provider and parsed.provider != inferred_provider:
            self.error("--provider must match the provider in --model")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = _FinalizerArgumentParser(
        description="Finalize saved POMA or direct-baseline raw answers."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-kind", choices=_SOURCE_KINDS, required=True)
    parser.add_argument("--finalizer", choices=_FINALIZERS, required=True)
    parser.add_argument("--qas", required=True)
    parser.add_argument("--tables", default=None)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", choices=_PROVIDERS, default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="On resume, explicitly retry QAs whose latest outcome is failure.",
    )
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--structured-output-mode",
        choices=tuple(mode.value for mode in StructuredOutputMode),
        default=None,
    )
    return parser


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Cannot determine git commit: {exc}") from exc
    commit = result.stdout.strip()
    if not commit:
        raise RuntimeError("Cannot determine git commit: empty revision")
    return commit


def _existing_started_at(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        header = json.loads(first_line)
        started_at = header["manifest"]["started_at"]
    except (OSError, IndexError, KeyError, TypeError, json.JSONDecodeError):
        return None
    return started_at if isinstance(started_at, str) else None


def _llm_config(model: str) -> LLMConfig:
    return replace(get_settings().llm, model=model)


def _generation_settings(
    config: LLMConfig,
    *,
    limit: int | None,
) -> dict[str, Any]:
    settings = asdict(config)
    settings["limit"] = limit
    return settings


def _make_finalizer(
    name: str,
    llm: object,
) -> object:
    if name == "gsa":
        return GroundedSingleAnswerFinalizer(GroundedSingleAnswerAgent(llm))
    normalizer = AnswerNormalizationAgent(llm)
    if name == "an-common":
        return CommonAnswerNormalizationFinalizer(normalizer)
    if name == "an-native":
        return NativeAnswerNormalizationFinalizer(normalizer)
    raise ValueError(f"Unsupported finalizer: {name!r}")


def _usage_from_llm(llm: object) -> dict[str, int | float | None]:
    fields = (
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_total_tokens",
        "total_cost_usd",
    )
    if not all(hasattr(llm, field) for field in fields):
        return {}
    return {
        "prompt_tokens": int(getattr(llm, "total_prompt_tokens")),
        "completion_tokens": int(getattr(llm, "total_completion_tokens")),
        "total_tokens": int(getattr(llm, "total_total_tokens")),
        "cost_usd": getattr(llm, "total_cost_usd"),
    }


def _structured_trace(llm: object) -> dict[str, Any]:
    getter = getattr(llm, "get_call_logs", None)
    logs = getter() if callable(getter) else []
    structured_logs = [
        log
        for log in logs
        if isinstance(log, dict) and "schema_valid" in log
    ]
    if not structured_logs:
        return {
            "structured_calls": 0,
            "schema_valid": None,
            "repair_attempted": False,
            "repair_succeeded": False,
        }
    return {
        "structured_calls": len(structured_logs),
        "schema_valid": all(
            log.get("schema_valid") is True for log in structured_logs
        ),
        "repair_attempted": any(
            log.get("repair_attempted") is True for log in structured_logs
        ),
        "repair_succeeded": any(
            log.get("repair_succeeded") is True for log in structured_logs
        ),
    }


_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    message = _SECRET_PATTERN.sub(r"\1\2[REDACTED]", message)
    for key, value in os.environ.items():
        upper_key = key.upper()
        if (
            value
            and (
                "API_KEY" in upper_key
                or upper_key.startswith("GPT_API_KEY")
            )
        ):
            message = message.replace(value, "[REDACTED]")
    return message


def _finalize_one(
    request: FinalizationRequest,
    *,
    finalizer_name: str,
    config: LLMConfig,
    llm_factory: FinalizerFactory,
) -> dict[str, Any]:
    llm = llm_factory(config)
    set_qa_id = getattr(llm, "set_qa_id", None)
    if callable(set_qa_id):
        set_qa_id(request.qa_id)
    finalizer = _make_finalizer(finalizer_name, llm)
    try:
        result = finalizer.finalize(request)
    except Exception as exc:
        record = failure_record(
            qa_id=request.qa_id,
            table_id=request.table_id,
            error_type=type(exc).__name__,
            message=_safe_error_message(exc),
            usage=_usage_from_llm(llm) or None,
        )
        record["trace"] = _structured_trace(llm)
        return record

    trace = dict(result.trace)
    trace.update(_structured_trace(llm))
    return success_record(
        qa_id=request.qa_id,
        table_id=request.table_id,
        prediction=result.prediction,
        finalizer=result.finalizer,
        trace=trace,
        usage=result.usage or _usage_from_llm(llm) or None,
    )


@contextmanager
def _use_structured_mode(
    override: StructuredOutputMode | None,
) -> Iterator[None]:
    if override is None:
        yield
        return

    import src.services.llm_client as llm_module
    import src.services.structured_generation as generation_module

    original_client_resolver = llm_module.resolve_output_mode
    original_generator_resolver = generation_module.resolve_output_mode
    llm_module.resolve_output_mode = lambda _model: override
    generation_module.resolve_output_mode = lambda _model, _override=None: override
    try:
        yield
    finally:
        llm_module.resolve_output_mode = original_client_resolver
        generation_module.resolve_output_mode = original_generator_resolver


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"


def _print_summary(
    payload: dict[str, Any],
    *,
    incremental_path: Path,
    output_path: Path,
) -> None:
    manifest = payload["manifest"]
    counts = manifest["counts"]
    records = payload["predictions"]
    structured = [
        record.get("trace", {})
        for record in records
        if isinstance(record.get("trace"), dict)
        and record["trace"].get("schema_valid") is not None
    ]
    schema_valid = sum(
        trace.get("schema_valid") is True for trace in structured
    )
    repairs = sum(
        trace.get("repair_attempted") is True for trace in structured
    )
    tokens = manifest["tokens"]
    cost = manifest["cost_usd"]

    print(
        "coverage: "
        + _rate(int(counts["successful"]), int(counts["dataset"]))
    )
    print(f"failures: {counts['failed']}")
    print(f"schema-valid rate: {_rate(schema_valid, len(structured))}")
    print(f"repair rate: {_rate(repairs, len(structured))}")
    print(
        "tokens: "
        f"prompt={tokens['prompt']} "
        f"completion={tokens['completion']} "
        f"total={tokens['total']}"
    )
    print(f"cost: {'unknown' if cost is None else f'${cost:.6f}'}")
    print(f"incremental output: {incremental_path}")
    print(f"materialized output: {output_path}")


def main(
    argv: Sequence[str] | None = None,
    *,
    llm_factory: FinalizerFactory | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source_path = _resolve_project_path(args.source)
    qas_path = _resolve_project_path(args.qas)
    tables_path = _resolve_project_path(
        args.tables or "dataset/table.json"
    )
    output_path = _resolve_project_path(args.output)
    incremental_path = _incremental_path(output_path)

    existing_paths = [
        path for path in (output_path, incremental_path) if path.exists()
    ]
    if existing_paths and not args.resume:
        parser.error(
            "existing finalizer output requires --resume: "
            + ", ".join(str(path) for path in existing_paths)
        )
    if args.resume and output_path.exists() and not incremental_path.exists():
        parser.error("--resume requires the matching incremental JSONL artifact")

    requests = load_finalization_requests(
        source_path=source_path,
        source_kind=args.source_kind,
        qas_path=qas_path,
        tables_path=tables_path,
    )
    if args.limit is not None:
        requests = requests[: args.limit]
    dataset_order = [request.qa_id for request in requests]

    config = _llm_config(args.model)
    provider, _ = parse_model_spec(args.model)
    selected_provider = args.provider or provider
    override = (
        StructuredOutputMode(args.structured_output_mode)
        if args.structured_output_mode
        else None
    )
    mode = resolve_output_mode(args.model, override)
    manifest = RunManifest.create(
        source_path=source_path,
        qas_path=qas_path,
        tables_path=tables_path,
        git_commit=_git_commit(),
        source_kind=args.source_kind,
        model=args.model,
        provider=selected_provider,
        mode=mode.value,
        prompt_version=_PROMPT_VERSIONS[args.finalizer],
        schema_version=_SCHEMA_VERSIONS[args.finalizer],
        finalizer=args.finalizer,
        generation_settings=_generation_settings(
            config,
            limit=args.limit,
        ),
        started_at=(
            _existing_started_at(incremental_path)
            if args.resume
            else None
        )
        or _utc_now(),
    )
    store = IncrementalArtifactStore(incremental_path, manifest)
    pending_ids = store.pending_qa_ids(
        dataset_order,
        retry_failed=args.retry_failed,
    )
    requests_by_id = {request.qa_id: request for request in requests}
    factory = llm_factory or LLMClient

    with _use_structured_mode(override):
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = [
                executor.submit(
                    _finalize_one,
                    requests_by_id[qa_id],
                    finalizer_name=args.finalizer,
                    config=config,
                    llm_factory=factory,
                )
                for qa_id in pending_ids
            ]
            for future in as_completed(futures):
                store.append(future.result())

    payload = store.materialize(
        output_path,
        dataset_order=dataset_order,
    )
    _print_summary(
        payload,
        incremental_path=incremental_path,
        output_path=output_path,
    )
    return 1 if payload["manifest"]["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
