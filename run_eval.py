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
from evaluation.bif_score import BIFConfig
from evaluation.exceptions import EvaluationDataError

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
    parser.add_argument(
        "--candidate-policy",
        choices=("all", "first", "single-required"),
        default="all",
        help=(
            "Candidate policy used for scoring (default: all). "
            "With multiple candidates, all is an oracle diagnostic; "
            "use single-required and --strict for final answers."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Reject duplicate or missing IDs, extra predictions, invalid "
            "candidate counts, empty answers, and metric errors."
        ),
    )
    parser.add_argument(
        "--bif-nli-model",
        help=(
            "Hugging Face ViNLI checkpoint directory or legacy .pt state dict. "
            "Required when --metrics includes bif."
        ),
    )
    parser.add_argument(
        "--bif-nli-base-model",
        default="xlm-roberta-large",
        help="Base architecture used only to load a legacy .pt checkpoint.",
    )
    parser.add_argument(
        "--bif-phobert-model",
        default="vinai/phobert-large",
        help="PhoBERT model used for the semantic BERTScore component.",
    )
    parser.add_argument(
        "--bif-alpha",
        type=float,
        default=0.5,
        help="PhoBERT F1 weight in BIF Eq. 15 (default: 0.5).",
    )
    parser.add_argument(
        "--bif-device",
        choices=("cpu", "cuda"),
        help="Device for both BIF models; defaults to CUDA when available.",
    )
    parser.add_argument(
        "--bif-batch-size",
        type=int,
        default=16,
        help="Batch size for BIF inference (default: 16).",
    )
    parser.add_argument(
        "--bif-max-length",
        type=int,
        default=128,
        help="Maximum NLI pair length (default: 128).",
    )
    parser.add_argument(
        "--bif-entailment-label",
        default="entailment",
        help="Entailment label in a Hugging Face checkpoint config.",
    )
    parser.add_argument(
        "--bif-entailment-id",
        type=int,
        help=(
            "Explicit Entailment logit index. Required for legacy checkpoints "
            "without label metadata; the author-provided 3-label script uses 0."
        ),
    )
    parser.add_argument(
        "--bif-details",
        help="Optional JSON path for selected per-QA BIF component scores.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run evaluation and return a process exit code."""
    args = build_parser().parse_args(argv)
    bif_config = None
    if "bif" in args.metrics:
        if not args.bif_nli_model:
            build_parser().error("--bif-nli-model is required when --metrics includes bif")
        bif_config = BIFConfig(
            nli_model_path=args.bif_nli_model,
            nli_base_model=args.bif_nli_base_model,
            phobert_model=args.bif_phobert_model,
            alpha=args.bif_alpha,
            device=args.bif_device,
            batch_size=args.bif_batch_size,
            max_length=args.bif_max_length,
            entailment_label=args.bif_entailment_label,
            entailment_id=args.bif_entailment_id,
        )
    try:
        report = evaluate_files(
            args.pred,
            args.qas,
            tables_path=args.tables,
            output_path=args.output,
            metrics=args.metrics,
            fail_on_metric_error=args.fail_on_metric_error,
            candidate_policy=args.candidate_policy,
            strict=args.strict,
            bif_config=bif_config,
            bif_details_path=args.bif_details,
        )
    except EvaluationDataError as error:
        print(f"Evaluation input error: {error}", file=sys.stderr)
        return 2
    for name, values in report["metrics"].items():
        print(f"{name}: {values}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
