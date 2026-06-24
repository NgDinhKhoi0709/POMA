"""Run POMA evaluation metrics for a prediction JSON or JSONL file."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.run import DEFAULT_METRICS, evaluate_files

DEFAULT_QAS_PATH = "dataset/qas_test.json"


def _parse_metrics(raw_value: str) -> list[str]:
    """Parse a comma-separated metric list and reject an empty selection."""
    metrics = [metric.strip() for metric in raw_value.split(",") if metric.strip()]
    if not metrics:
        raise argparse.ArgumentTypeError("provide at least one metric name")
    return metrics


def build_parser() -> argparse.ArgumentParser:
    """Create the standalone evaluation runner parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate POMA predictions against a QAs dataset."
    )
    parser.add_argument(
        "--qas",
        default=DEFAULT_QAS_PATH,
        help=f"Path to the QAs JSON file (default: {DEFAULT_QAS_PATH}).",
    )
    parser.add_argument(
        "--pred",
        required=True,
        help="Path to the prediction JSON or JSONL file.",
    )
    parser.add_argument(
        "--tables",
        help="Optional table.json path for table-type metrics.",
    )
    parser.add_argument("--output", help="Optional JSON report output path.")
    parser.add_argument(
        "--metrics",
        type=_parse_metrics,
        default=list(DEFAULT_METRICS),
        metavar="METRIC[,METRIC...]",
        help=f"Comma-separated metric names (default: {','.join(DEFAULT_METRICS)}).",
    )
    parser.add_argument(
        "--fail-on-metric-error",
        action="store_true",
        help="Return an error instead of skipping a metric that cannot run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run evaluation and return a process exit code."""
    args = build_parser().parse_args(argv)
    report = evaluate_files(
        args.pred,
        args.qas,
        tables_path=args.tables,
        output_path=args.output,
        metrics=args.metrics,
        fail_on_metric_error=args.fail_on_metric_error,
    )
    for name, values in report["metrics"].items():
        print(f"{name}: {values}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
