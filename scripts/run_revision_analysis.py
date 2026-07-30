"""Build one deterministic Q2 revision-analysis report from saved artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match, f1, meteor, rouge1
from evaluation.bootstrap import (
    DEFAULT_SAMPLES,
    DEFAULT_SEED,
    paired_answerability_bootstrap_ci,
    paired_bootstrap_ci,
)
from evaluation.hint_metrics import evaluate_hint_metrics
from evaluation.io import align_records, load_json_records, load_qas_records
from evaluation.normalization import (
    is_unanswerable_reference,
    prediction_is_unanswerable,
)
from evaluation.parallelism import analyze_parallelism
from evaluation.run import evaluate_files

EVALUATION_METRICS = [
    "f1",
    "em",
    "rouge1",
    "meteor",
    "answerability_f1",
]
BOOTSTRAP_METRICS = ("f1", "em", "rouge1", "meteor")
MINIMUM_EM_DIFFERENCE = 0.02


class RevisionAnalysisError(ValueError):
    """Raised when an input cannot produce a complete revision report."""


def validate_evaluation_report(
    report: Mapping[str, Any],
    *,
    system_name: str,
) -> None:
    """Require every precommitted evaluator output for one system."""
    metric_errors = report.get("metric_errors")
    if metric_errors:
        raise RevisionAnalysisError(
            f"Evaluation failed for system {system_name!r}: {metric_errors}"
        )
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        metrics = {}
    analyses = report.get("analyses")
    if not isinstance(analyses, Mapping):
        analyses = {}
    required_metric_fields = {
        "f1": "f1",
        "em": "value",
        "rouge1": "f1",
        "meteor": "value",
    }
    missing = []
    for name, value_field in required_metric_fields.items():
        value = metrics.get(name)
        if (
            not isinstance(value, Mapping)
            or value.get(value_field) is None
        ):
            missing.append(name)
    answerability = analyses.get("answerability_f1")
    if (
        not isinstance(answerability, Mapping)
        or answerability.get("macro_f1") is None
    ):
        missing.append("answerability_f1")
    if missing:
        raise RevisionAnalysisError(
            f"Evaluation for system {system_name!r} is missing requested "
            f"outputs: {', '.join(missing)}"
        )


def parse_systems(values: Sequence[str]) -> dict[str, Path]:
    """Parse repeated NAME=PATH arguments while preserving their order."""
    systems: dict[str, Path] = {}
    for value in values:
        name, separator, raw_path = value.partition("=")
        name = name.strip()
        raw_path = raw_path.strip()
        if not separator or not name or not raw_path:
            raise ValueError(f"Invalid --system value: {value!r}; use NAME=PATH")
        if name in systems:
            raise ValueError(f"Duplicate system name: {name!r}")
        systems[name] = Path(raw_path)
    if not systems:
        raise ValueError("At least one --system NAME=PATH is required")
    return systems


def _unique_ids(
    records: Iterable[Mapping[str, Any]],
    *,
    source_name: str,
) -> list[str]:
    ids: list[str] = []
    for record in records:
        if not isinstance(record, Mapping) or record.get("qa_id") is None:
            raise ValueError(f"Every {source_name} record must contain qa_id")
        ids.append(str(record["qa_id"]))
    if len(ids) != len(set(ids)):
        duplicate = next(qa_id for qa_id in ids if ids.count(qa_id) > 1)
        raise ValueError(f"Duplicate qa_id in {source_name}: {duplicate!r}")
    return ids


def _validate_system_coverage(
    records: list[dict[str, Any]],
    qa_ids: list[str],
    system_name: str,
) -> None:
    record_ids = _unique_ids(records, source_name=f"system {system_name!r}")
    missing = [qa_id for qa_id in qa_ids if qa_id not in set(record_ids)]
    extras = sorted(set(record_ids).difference(qa_ids))
    if missing or extras:
        raise ValueError(
            f"System {system_name!r} QA coverage mismatch: "
            f"missing={missing}, extra={extras}"
        )


def _score_vectors(
    records: list[dict[str, Any]],
    qas: list[dict[str, Any]],
    qa_ids: list[str],
) -> tuple[dict[str, list[float]], list[bool], list[bool]]:
    samples, _ = align_records(records, qas)
    sample_by_id = {sample.qa_id: sample for sample in samples}
    ordered = [sample_by_id[qa_id] for qa_id in qa_ids]
    scorers = {
        "f1": f1.score_sample,
        "em": exact_match.score_sample,
        "rouge1": rouge1.score_sample,
        "meteor": meteor.score_sample,
    }
    vectors = {
        name: [float(scorer(sample).value) for sample in ordered]
        for name, scorer in scorers.items()
    }
    gold_unanswerable = [
        is_unanswerable_reference(sample.reference) for sample in ordered
    ]
    predicted_unanswerable = [
        prediction_is_unanswerable(sample.prediction) for sample in ordered
    ]
    return vectors, gold_unanswerable, predicted_unanswerable


def _decision_summary(records: Iterable[Mapping[str, Any]]) -> dict[str, object]:
    decisions: list[str] = []
    for record in records:
        trace = record.get("trace", record.get("finalizer_trace"))
        if isinstance(trace, Mapping):
            decision = trace.get("decision")
            if isinstance(decision, str) and decision.strip():
                decisions.append(decision.strip())
    return {
        "count": len(decisions),
        "distribution": dict(sorted(Counter(decisions).items())),
    }


def _structured_output_summary(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, float | int | None]:
    all_records = list(records)
    count = 0
    schema_valid_count = 0
    repair_attempt_count = 0
    repair_success_count = 0
    missing_count = 0
    for record in all_records:
        trace = record.get("trace")
        aggregate = trace if isinstance(trace, Mapping) else record
        if "structured_calls" in aggregate:
            fields = (
                "structured_calls",
                "schema_valid_calls",
                "repair_attempted_calls",
                "repair_succeeded_calls",
            )
            values: dict[str, int] = {}
            for field in fields:
                raw_value = aggregate.get(field)
                if (
                    isinstance(raw_value, bool)
                    or not isinstance(raw_value, int)
                    or raw_value < 0
                ):
                    raise RevisionAnalysisError(
                        f"Invalid structured telemetry field {field}: "
                        f"{raw_value!r}"
                    )
                values[field] = raw_value
            structured_calls = values["structured_calls"]
            if any(
                values[field] > structured_calls
                for field in fields[1:]
            ):
                raise RevisionAnalysisError(
                    "Structured telemetry call counts cannot exceed "
                    "structured_calls"
                )
            count += structured_calls
            schema_valid_count += values["schema_valid_calls"]
            repair_attempt_count += values["repair_attempted_calls"]
            repair_success_count += values["repair_succeeded_calls"]
        elif "schema_valid" in record:
            # Raw POMA llm_calls and legacy direct-baseline records expose
            # per-call telemetry rather than finalizer aggregate counters.
            count += 1
            schema_valid_count += record.get("schema_valid") is True
            repair_attempt_count += record.get("repair_attempted") is True
            repair_success_count += record.get("repair_succeeded") is True
        else:
            missing_count += 1
    return {
        "calls": count,
        "missing_schema_telemetry_records": missing_count,
        "initial_schema_valid_rate": (
            schema_valid_count / count if count else None
        ),
        "repair_attempt_rate": (
            repair_attempt_count / count if count else None
        ),
        "repair_success_rate": (
            repair_success_count / repair_attempt_count
            if repair_attempt_count
            else None
        ),
    }


def _failure_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    failures = [
        record for record in records if isinstance(record.get("error"), Mapping)
    ]
    count = len(records)
    types = Counter(
        str(record["error"].get("type", "unknown")) for record in failures
    )
    return {
        "count": len(failures),
        "total": count,
        "failure_rate": len(failures) / count if count else 0.0,
        "by_type": dict(sorted(types.items())),
    }


def _usage(record: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = record.get("usage")
    return nested if isinstance(nested, Mapping) else record


def _non_negative_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a non-negative finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field} must be a non-negative finite number"
        ) from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a non-negative finite number")
    return number


def _cost_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    costs: list[float] = []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    missing_cost = 0
    missing_usage = 0
    for record in records:
        usage = _usage(record)
        has_any_usage = any(
            field in usage
            for field in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
            )
        )
        if not has_any_usage:
            missing_usage += 1
        for field, accumulator in (
            ("prompt_tokens", "prompt"),
            ("completion_tokens", "completion"),
            ("total_tokens", "total"),
        ):
            value = usage.get(field)
            if value is None:
                continue
            parsed = int(_non_negative_number(value, field))
            if accumulator == "prompt":
                prompt_tokens += parsed
            elif accumulator == "completion":
                completion_tokens += parsed
            else:
                total_tokens += parsed
        raw_cost = usage.get("cost_usd")
        if raw_cost is None:
            missing_cost += 1
        else:
            costs.append(_non_negative_number(raw_cost, "cost_usd"))
    complete_cost = bool(records) and missing_cost == 0
    return {
        "records": len(records),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "known_cost_records": len(costs),
        "missing_cost_records": missing_cost,
        "missing_usage_records": missing_usage,
        "total_cost_usd": sum(costs) if complete_cost else None,
        "average_cost_usd": (
            sum(costs) / len(records) if complete_cost else None
        ),
    }


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    return sorted(values)[math.ceil(probability * len(values)) - 1]


def _latency_summary(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, float | int]:
    values: list[float] = []
    for record in records:
        raw_value = record.get("elapsed_s", record.get("latency_s"))
        if raw_value is not None:
            values.append(_non_negative_number(raw_value, "latency"))
    if not values:
        return {
            "count": 0,
            "missing_records": len(records),
            "total_s": 0.0,
            "mean_s": 0.0,
            "median_s": 0.0,
            "p95_s": 0.0,
            "maximum_s": 0.0,
        }
    return {
        "count": len(values),
        "missing_records": len(records) - len(values),
        "total_s": sum(values),
        "mean_s": sum(values) / len(values),
        "median_s": statistics.median(values),
        "p95_s": _nearest_rank(values, 0.95),
        "maximum_s": max(values),
    }


def _system_bootstrap(
    vectors: Mapping[str, Sequence[float]],
    gold_unanswerable: Sequence[bool],
    predicted_unanswerable: Sequence[bool],
    qa_ids: Sequence[str],
    *,
    samples: int,
    seed: int,
) -> dict[str, dict[str, float | int]]:
    report: dict[str, dict[str, float | int]] = {}
    for metric in BOOTSTRAP_METRICS:
        interval = paired_bootstrap_ci(
            vectors[metric],
            vectors[metric],
            samples=samples,
            seed=seed,
            system_a_ids=qa_ids,
            system_b_ids=qa_ids,
        )["system_a"]
        report[metric] = {
            **interval,
            "samples": samples,
            "seed": seed,
        }
    answerability_interval = paired_answerability_bootstrap_ci(
        gold_unanswerable,
        predicted_unanswerable,
        predicted_unanswerable,
        samples=samples,
        seed=seed,
        system_a_ids=qa_ids,
        system_b_ids=qa_ids,
    )["system_a"]
    report["answerability_f1"] = {
        **answerability_interval,
        "samples": samples,
        "seed": seed,
    }
    return report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--primary-system", required=True)
    parser.add_argument("--baseline-system", required=True)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--poma-traces", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.bootstrap_samples <= 0:
        parser.error("--bootstrap-samples must be positive")
    return args


def build_report(
    *,
    systems: Mapping[str, Path],
    primary_system: str,
    baseline_system: str,
    qas_path: Path,
    poma_traces_path: Path,
    bootstrap_samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """Compute one report without making any interpretation claims."""
    if primary_system not in systems:
        raise ValueError(f"Unknown primary system: {primary_system!r}")
    if baseline_system not in systems:
        raise ValueError(f"Unknown baseline system: {baseline_system!r}")
    if primary_system == baseline_system:
        raise ValueError("Primary and baseline systems must differ")

    qas = load_qas_records(qas_path)
    qa_ids = _unique_ids(qas, source_name="QAs")
    vectors_by_system: dict[str, dict[str, list[float]]] = {}
    answerability_by_system: dict[str, list[bool]] = {}
    gold_answerability: list[bool] | None = None
    system_reports: dict[str, dict[str, object]] = {}
    for name, path in systems.items():
        records = load_json_records(path)
        _validate_system_coverage(records, qa_ids, name)
        vectors, system_gold, system_answerability = _score_vectors(
            records,
            qas,
            qa_ids,
        )
        if gold_answerability is None:
            gold_answerability = system_gold
        elif gold_answerability != system_gold:
            raise RevisionAnalysisError(
                "Aligned systems produced inconsistent gold answerability labels"
            )
        vectors_by_system[name] = vectors
        answerability_by_system[name] = system_answerability
        evaluation = evaluate_files(
            path,
            qas_path,
            metrics=EVALUATION_METRICS,
            fail_on_metric_error=True,
        )
        validate_evaluation_report(evaluation, system_name=name)
        system_reports[name] = {
            "path": str(path),
            "evaluation": evaluation,
            "bootstrap": _system_bootstrap(
                vectors,
                system_gold,
                system_answerability,
                qa_ids,
                samples=bootstrap_samples,
                seed=seed,
            ),
            "gsa_decisions": _decision_summary(records),
            "structured_output": _structured_output_summary(records),
            "failure": _failure_summary(records),
            "cost": _cost_summary(records),
            "latency": _latency_summary(records),
        }

    primary_vectors = vectors_by_system[primary_system]
    baseline_vectors = vectors_by_system[baseline_system]
    paired = {
        metric: paired_bootstrap_ci(
            primary_vectors[metric],
            baseline_vectors[metric],
            samples=bootstrap_samples,
            seed=seed,
            system_a_ids=qa_ids,
            system_b_ids=qa_ids,
        )
        for metric in BOOTSTRAP_METRICS
    }
    if gold_answerability is None:
        raise RevisionAnalysisError("QAs must be non-empty")
    paired["answerability_f1"] = paired_answerability_bootstrap_ci(
        gold_answerability,
        answerability_by_system[primary_system],
        answerability_by_system[baseline_system],
        samples=bootstrap_samples,
        seed=seed,
        system_a_ids=qa_ids,
        system_b_ids=qa_ids,
    )

    traces = load_json_records(poma_traces_path)
    trace_ids = _unique_ids(traces, source_name="POMA traces")
    if trace_ids != qa_ids:
        missing = [qa_id for qa_id in qa_ids if qa_id not in set(trace_ids)]
        extras = sorted(set(trace_ids).difference(qa_ids))
        if missing or extras:
            raise ValueError(
                f"POMA trace QA coverage mismatch: missing={missing}, extra={extras}"
            )
    hint_predictions = [
        {
            "qa_id": trace["qa_id"],
            "predicted_hints": trace["predicted_hints"],
        }
        for trace in traces
        if "predicted_hints" in trace
    ]
    llm_calls = [
        call
        for trace in traces
        for call in trace.get("llm_calls", [])
        if isinstance(call, Mapping)
    ]
    em_interval = paired["em"]
    observed_difference = float(em_interval["point_estimate"])
    excludes_zero = (
        float(em_interval["lower"]) > 0.0
        or float(em_interval["upper"]) < 0.0
    )
    return {
        "configuration": {
            "bootstrap_samples": bootstrap_samples,
            "seed": seed,
        },
        "systems": system_reports,
        "comparison": {
            "primary_system": primary_system,
            "baseline_system": baseline_system,
            "paired_bootstrap": paired,
        },
        "hint_metrics": evaluate_hint_metrics(qas, hint_predictions),
        "parallelism": analyze_parallelism(
            traces,
            expected_qa_ids=qa_ids,
        ),
        "poma_traces": {
            "path": str(poma_traces_path),
            "structured_output": _structured_output_summary(llm_calls),
            "failure": _failure_summary(traces),
            "cost": _cost_summary(llm_calls),
            "latency": _latency_summary(traces),
        },
        "interpretation_gate": {
            "minimum_em_difference": MINIMUM_EM_DIFFERENCE,
            "observed_em_difference": observed_difference,
            "paired_ci_excludes_zero": excludes_zero,
            "passes_backbone_gate": (
                observed_difference >= MINIMUM_EM_DIFFERENCE
                and excludes_zero
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    report = build_report(
        systems=parse_systems(args.system),
        primary_system=args.primary_system,
        baseline_system=args.baseline_system,
        qas_path=args.qas,
        poma_traces_path=args.poma_traces,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
