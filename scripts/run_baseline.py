"""Run a vendored table-QA baseline on the POMA dataset."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baselines.contracts import RunPaths, read_jsonl, validate_run_records
from baselines.dispatch import dispatch_run
from evaluation.run import evaluate_files


EVALUATION_METRICS = (
    "f1",
    "em",
    "rouge1",
    "meteor",
    "answerability_f1",
    "cost",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CoAgt or Chain-of-Query on Open-ViTabQA."
    )
    parser.add_argument("method", choices=("coagt", "coq"))
    parser.add_argument("--qas", default="dataset/qas_test.json")
    parser.add_argument("--tables", default="dataset/table.json")
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-dir", default="outputs/baselines")
    parser.add_argument("--run-id", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-eval", action="store_true")
    return parser


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _default_run_id(model: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-")
    return value or "baseline-run"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if args.max_workers <= 0:
        parser.error("--max-workers must be positive")

    _load_env()
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        print(
            "OPENAI_API_KEY is missing. Set it in the environment or POMA .env.",
            file=sys.stderr,
        )
        return 2

    qas_path = _resolve_project_path(args.qas)
    tables_path = _resolve_project_path(args.tables)
    output_dir = _resolve_project_path(args.output_dir)
    run_paths = RunPaths.create(
        output_dir,
        args.method,
        args.run_id or _default_run_id(args.model),
    )
    outcome = dispatch_run(
        args.method,
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=run_paths,
        model=args.model,
        limit=args.limit,
        max_workers=args.max_workers,
        resume=args.resume,
        overwrite=args.overwrite,
    )

    records = read_jsonl(run_paths.results_jsonl)
    validate_run_records(records, args.method)
    if records and not args.skip_eval:
        evaluate_files(
            run_paths.results_jsonl,
            run_paths.qas_subset,
            tables_path=tables_path,
            output_path=run_paths.eval_report,
            metrics=list(EVALUATION_METRICS),
            fail_on_metric_error=True,
        )

    print(f"results: {run_paths.results_jsonl}")
    print(f"errors: {run_paths.errors_jsonl}")
    print(f"metadata: {run_paths.meta_json}")
    if run_paths.eval_report.exists():
        print(f"evaluation: {run_paths.eval_report}")
    return 1 if int(outcome.get("num_errors") or 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
