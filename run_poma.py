from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Bootstrap: ensure the standalone POMA project root is on sys.path.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env early
try:
    from dotenv import load_dotenv
    _env = _PROJECT_ROOT / ".env"
    load_dotenv(_env if _env.exists() else None)
except ImportError:
    pass

from src.contracts.request import QARequest
from src.errors import InputDataError, enrich_error
from src.orchestration.pipeline import run_pipeline
from evaluation.io import align_records
from evaluation.run import _core_metrics, DEFAULT_METRICS
from evaluation.normalization import (
    exact_text_match,
    normalize_text as normalize_eval_text,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")

STAGE_TO_STEP_KEYS: Dict[str, List[str]] = {
    "refiner": ["1_question_refiner", "2_router"],
    "specialists": ["3_specialists"],
    "normalization": ["4_answer_normalization"],
}


# ---------------------------------------------------------------------------
# Dataset helpers (reused from baseline.run)
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_dataset_pair(
    qas_path: Path, tables_path: Path
) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    qas_raw = _load_json(qas_path)
    qas = qas_raw.get("qas", qas_raw) if isinstance(qas_raw, dict) else qas_raw

    tables_raw = _load_json(tables_path)
    tables = tables_raw.get("table", tables_raw) if isinstance(tables_raw, dict) else tables_raw

    table_idx: Dict[str, Dict[str, Any]] = {}
    if isinstance(tables, list):
        for t in tables:
            if isinstance(t, dict) and t.get("table_id") is not None:
                table_idx[str(t["table_id"])] = t
    elif isinstance(tables, dict):
        for k, v in tables.items():
            if isinstance(v, dict):
                table_idx[str(k)] = v

    return qas, table_idx


def _get_table_str(table_data: Dict[str, Any]) -> str:
    from preprocessing.representation import create_representation
    return create_representation(table_data).to_string()


def _use_agent_hints_enabled() -> bool:
    from src.config.settings import get_settings

    return bool(get_settings().use_agent_hints)


def _extract_refined_hints_from_result(result: Dict[str, Any]) -> Optional[List[str]]:
    trace = result.get("trace")
    if not isinstance(trace, dict):
        return None
    steps = trace.get("steps")
    if not isinstance(steps, dict):
        return None
    refiner_step = steps.get("1_question_refiner")
    if not isinstance(refiner_step, dict):
        return None
    hints = refiner_step.get("hints")
    if not isinstance(hints, list):
        return None
    refined_hints = [hint for hint in hints if isinstance(hint, str) and hint.strip()]
    return refined_hints or None


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def process_one(
    qa: Dict[str, Any],
    table_idx: Dict[str, Dict[str, Any]],
    stages: Optional[Set[str]] = None,
    prior_traces_idx: Optional[Dict[str, Dict[str, Any]]] = None,
    hint_predictions_idx: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Run the POMA pipeline on a single QA item and return the full record."""
    qa_id = str(qa.get("qa_id", ""))
    table_id = str(qa.get("table_id", ""))
    question = str(qa.get("question", "")).strip()
    groundtruth = qa.get("answer", "")
    raw_hints = qa.get("hints", [])
    active_hints = raw_hints
    hint_source = "dataset"
    predicted_hints: Optional[List[str]] = None
    if hint_predictions_idx is not None:
        predicted_hints = hint_predictions_idx.get(qa_id)
        if predicted_hints is None:
            raise InputDataError(
                f"Missing precomputed hint prediction for qa_id={qa_id}",
                stage="input",
                qa_id=qa_id,
            )
        active_hints = predicted_hints
        hint_source = "precomputed"
    elif _use_agent_hints_enabled():
        hint_source = "agent"

    table = table_idx.get(table_id)
    if table is None:
        raise InputDataError(
            f"table_id={table_id} not found",
            stage="input",
            qa_id=qa_id,
        )

    table_str = _get_table_str(table)
    if not table_str:
        raise InputDataError(
            "empty table string",
            stage="input",
            qa_id=qa_id,
        )

    request = QARequest(
        question=question,
        table_flattened=table_str,
        metadata={"hints": active_hints, "qa_id": qa_id, "hint_source": hint_source},
    )

    prior_trace = (prior_traces_idx or {}).get(qa_id)

    t0 = time.time()
    try:
        result = run_pipeline(
            request, stages=stages, prior_trace=prior_trace,
        )
    except Exception as exc:
        error = enrich_error(exc, qa_id=qa_id)
        partial_trace = getattr(error, "trace_payload", None)
        if not isinstance(partial_trace, dict):
            partial_trace = getattr(exc, "trace_payload", None)
        if isinstance(partial_trace, dict):
            partial_trace["qa_id"] = qa_id
            partial_trace["table_id"] = table_id
            partial_trace["question"] = question
            partial_trace["groundtruth"] = groundtruth
            partial_trace["hints"] = raw_hints
            partial_trace["hint_source"] = hint_source
            if predicted_hints is not None:
                partial_trace["predicted_hints"] = predicted_hints
            partial_trace["elapsed_s"] = round(time.time() - t0, 2)
            setattr(error, "trace_payload", partial_trace)
        raise error from exc
    elapsed = time.time() - t0

    answers = result["answer"]  # List[str] of candidate surface forms
    if predicted_hints is None and hint_source == "agent":
        predicted_hints = _extract_refined_hints_from_result(result)

    rec: Dict[str, Any] = {
        "qa_id": qa_id,
        "table_id": table_id,
        "question": question,
        "groundtruth": groundtruth,
        "hints": raw_hints,
        "predicted_answer": answers,
        "hint_source": hint_source,
        "elapsed_s": round(elapsed, 2),
        "prompt_tokens": result.get("prompt_tokens", 0),
        "completion_tokens": result.get("completion_tokens", 0),
        "total_tokens": result.get("total_tokens", 0),
        "cost_usd": round(result.get("cost_usd", 0.0), 6),
    }
    if predicted_hints is not None:
        rec["predicted_hints"] = predicted_hints

    if "trace" in result:
        trace = result["trace"]
        trace["qa_id"] = qa_id
        trace["question"] = question
        trace["hints"] = raw_hints
        trace["hint_source"] = hint_source
        if predicted_hints is not None:
            trace["predicted_hints"] = predicted_hints
        trace["final_answers"] = answers
        trace["elapsed_s"] = round(elapsed, 2)
        rec["_trace"] = trace

    return rec


def _load_existing_results(path: Path) -> List[Dict[str, Any]]:
    """Load previously saved results from a JSON file."""
    if not path.exists():
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputDataError(f"Could not load existing results from {path}: {exc}") from exc

    if not text.strip():
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputDataError(f"Could not load existing results from {path}: {exc}") from exc

    if isinstance(data, dict) and isinstance(data.get("predictions"), list):
        return data["predictions"]
    if not isinstance(data, list):
        raise InputDataError(
            f"Existing results file must contain a JSON list or predictions object: {path}"
        )
    return data


def _load_hint_predictions(path: Path) -> Dict[str, List[str]]:
    """Load precomputed HintPredictor output as qa_id -> predicted_hints."""
    try:
        data = _load_json(path)
    except OSError as exc:
        raise InputDataError(f"Could not load hint predictions from {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputDataError(f"Could not load hint predictions from {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("predictions"), list):
        raise InputDataError(
            f"Hint predictions file must contain an object with a predictions list: {path}"
        )

    idx: Dict[str, List[str]] = {}
    for pos, record in enumerate(data["predictions"], 1):
        if not isinstance(record, dict):
            raise InputDataError(
                f"Hint prediction record #{pos} must be an object: {path}"
            )
        qa_id_value = record.get("qa_id")
        if qa_id_value is None or str(qa_id_value).strip() == "":
            raise InputDataError(
                f"Hint prediction record #{pos} is missing qa_id: {path}"
            )
        qa_id = str(qa_id_value)
        if qa_id in idx:
            raise InputDataError(
                f"Duplicate hint prediction for qa_id={qa_id}: {path}"
            )
        if "error" in record:
            raise InputDataError(
                f"Hint prediction for qa_id={qa_id} contains an error: {record['error']}"
            )

        predicted = record.get("predicted_hints")
        if not isinstance(predicted, list) or not predicted:
            raise InputDataError(
                f"Hint prediction for qa_id={qa_id} must have non-empty predicted_hints"
            )

        hints: List[str] = []
        for hint in predicted:
            if not isinstance(hint, str) or not hint.strip():
                raise InputDataError(
                    f"Hint prediction for qa_id={qa_id} contains a non-string or empty hint"
                )
            hints.append(hint.strip())
        idx[qa_id] = hints

    return idx


def _validate_hint_predictions_for_qas(
    qas: List[Dict[str, Any]],
    hint_predictions_idx: Dict[str, List[str]],
) -> None:
    missing = [
        str(qa.get("qa_id", ""))
        for qa in qas
        if isinstance(qa, dict) and str(qa.get("qa_id", "")) not in hint_predictions_idx
    ]
    if missing:
        preview = ", ".join(missing[:10])
        suffix = "" if len(missing) <= 10 else f", ... (+{len(missing) - 10} more)"
        raise InputDataError(
            f"Missing precomputed hint prediction for {len(missing)} QA(s): {preview}{suffix}"
        )


def _calculate_batch_stats(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_recs = [r for r in predictions if isinstance(r, dict) and "error" not in r]
    n = len(valid_recs)
    if n == 0:
        return {
            "total_elapsed_s": 0.0,
            "average_elapsed_s": 0.0,
            "total_prompt_tokens": 0,
            "average_prompt_tokens": 0.0,
            "total_completion_tokens": 0,
            "average_completion_tokens": 0.0,
            "total_tokens": 0,
            "average_total_tokens": 0.0,
            "total_cost_usd": 0.0,
            "average_cost_usd": 0.0,
            "count": 0,
        }

    total_elapsed = sum(r.get("elapsed_s", 0.0) for r in valid_recs)
    total_prompt = sum(r.get("prompt_tokens", 0) for r in valid_recs)
    total_completion = sum(r.get("completion_tokens", 0) for r in valid_recs)
    total_tok = sum(r.get("total_tokens", 0) for r in valid_recs)
    total_cost = sum(r.get("cost_usd", 0.0) for r in valid_recs)

    return {
        "total_elapsed_s": round(total_elapsed, 2),
        "average_elapsed_s": round(total_elapsed / n, 2),
        "total_prompt_tokens": total_prompt,
        "average_prompt_tokens": round(total_prompt / n, 1),
        "total_completion_tokens": total_completion,
        "average_completion_tokens": round(total_completion / n, 1),
        "total_tokens": total_tok,
        "average_total_tokens": round(total_tok / n, 1),
        "total_cost_usd": round(total_cost, 6),
        "average_cost_usd": round(total_cost / n, 6),
        "count": n,
    }


def _save_results(results: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results saved to %s  (%d records)", path, len(results))


def _save_prediction_output(
    predictions: List[Dict[str, Any]],
    path: Path,
    evaluation: Optional[Dict[str, Any]] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {"predictions": predictions}
    if evaluation:
        payload["evaluation"] = evaluation
    if "pytest" not in sys.modules:
        payload["stats"] = _calculate_batch_stats(predictions)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Prediction output saved to %s  (%d records)", path, len(predictions))


def _extract_trace(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pop the ``_trace`` key from a result record, if present."""
    return rec.pop("_trace", None)


def _extract_error_trace(error: Exception) -> Optional[Dict[str, Any]]:
    trace = getattr(error, "trace_payload", None)
    if isinstance(trace, dict):
        return trace
    return None


def _merge_records_by_qa_id(
    existing: List[Dict[str, Any]],
    new: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge records by ``qa_id``, preferring newer entries."""
    idx: Dict[str, Dict[str, Any]] = {}
    for rec in existing:
        if isinstance(rec, dict) and "qa_id" in rec:
            idx[str(rec["qa_id"])] = rec
    for rec in new:
        if isinstance(rec, dict) and "qa_id" in rec:
            idx[str(rec["qa_id"])] = rec
    return list(idx.values())


def _build_trace_index(
    traces: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Map qa_id -> trace dict for quick lookup."""
    idx: Dict[str, Dict[str, Any]] = {}
    for t in traces:
        if isinstance(t, dict) and "qa_id" in t:
            idx[str(t["qa_id"])] = t
    return idx


def _is_compatible_existing_record(
    record: Dict[str, Any],
    hint_predictions_idx: Optional[Dict[str, List[str]]],
    expected_hint_source: str = "dataset",
) -> bool:
    if hint_predictions_idx is None:
        return record.get("hint_source", "dataset") == expected_hint_source

    qa_id = str(record.get("qa_id", ""))
    return (
        record.get("hint_source") == "precomputed"
        and record.get("predicted_hints") == hint_predictions_idx.get(qa_id)
    )


def _merge_trace_lists(
    existing: List[Dict[str, Any]],
    new: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge new traces into existing, replacing entries with the same qa_id."""
    return _merge_records_by_qa_id(existing, new)


def _stages_to_persist(stages: Optional[Set[str]]) -> List[str]:
    if stages is None:
        return list(STAGE_TO_STEP_KEYS.keys())
    return [stage for stage in STAGE_TO_STEP_KEYS if stage in stages]


def _build_stage_record(
    stage_name: str,
    trace: Dict[str, Any],
    result_by_qa_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    qa_id = trace.get("qa_id")
    if qa_id is None:
        return None

    steps = trace.get("steps")
    if not isinstance(steps, dict):
        return None

    stage_steps = {
        step_key: steps[step_key]
        for step_key in STAGE_TO_STEP_KEYS[stage_name]
        if step_key in steps
    }
    if not stage_steps:
        return None

    result_rec = result_by_qa_id.get(str(qa_id), {})
    record: Dict[str, Any] = {
        "qa_id": str(qa_id),
        "steps": stage_steps,
    }

    for key in (
        "table_id",
        "question",
        "groundtruth",
        "hints",
        "predicted_hints",
        "hint_source",
        "elapsed_s",
    ):
        value = result_rec.get(key, trace.get(key))
        if value is not None:
            record[key] = value

    return record


def _build_stage_records(
    stage_name: str,
    traces: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    result_by_qa_id = {
        str(rec["qa_id"]): rec
        for rec in results
        if isinstance(rec, dict) and "qa_id" in rec
    }
    stage_records: List[Dict[str, Any]] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        record = _build_stage_record(stage_name, trace, result_by_qa_id)
        if record is not None:
            stage_records.append(record)
    return stage_records


def _save_stage_outputs(
    output_path: Optional[Path],
    stages: Optional[Set[str]],
    traces: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> None:
    if output_path is None or not traces:
        return

    for stage_name in _stages_to_persist(stages):
        stage_records = _build_stage_records(stage_name, traces, results)
        if not stage_records:
            continue
        stage_path = output_path.parent / stage_name / output_path.name
        _save_results(stage_records, stage_path)


def _should_run_auto_evaluation(stages: Optional[Set[str]]) -> bool:
    return stages is None or stages == {"normalization"}


def _run_auto_evaluation(
    predictions: List[Dict[str, Any]],
    qas: List[Dict[str, Any]],
    qas_path: Path,
    metrics: Optional[str | List[str]],
    eval_threads: int,
    fail_on_metric_error: bool,
) -> Dict[str, Any]:
    logger.info("Running automatic evaluation for %d prediction(s)...", len(predictions))
    samples, _ = align_records(predictions, qas)
    
    if metrics is None:
        requested = set(DEFAULT_METRICS)
    elif isinstance(metrics, str):
        requested = {m.strip() for m in metrics.split(",") if m.strip()}
    else:
        requested = set(metrics)

    evaluation = {}
    try:
        metrics_dict = _core_metrics(samples, requested)
        evaluation["overall"] = metrics_dict
        
        def _get_val(m_dict: Any, key: str) -> float:
            if isinstance(m_dict, dict):
                val = m_dict.get(key, {})
                if isinstance(val, dict):
                    return float(val.get("value", 0.0))
            return 0.0

        logger.info(
            "Evaluation done: F1=%.4f EM=%.4f R1=%.4f MET=%.4f",
            _get_val(metrics_dict, "f1"),
            _get_val(metrics_dict, "em"),
            _get_val(metrics_dict, "rouge1"),
            _get_val(metrics_dict, "meteor"),
        )
    except Exception as exc:
        if fail_on_metric_error:
            raise
        logger.warning(f"Evaluation error: {exc}")

    return evaluation


def run_batch(
    qas_path: Path,
    tables_path: Path,
    output_path: Optional[Path],
    limit: Optional[int],
    skip_existing: bool = True,
    traces_path: Optional[Path] = None,
    workers: int = 1,
    stages: Optional[Set[str]] = None,
    auto_evaluate: bool = True,
    eval_metrics: Optional[str | List[str]] = None,
    eval_threads: int = 1,
    fail_on_metric_error: bool = False,
    hint_predictions_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    qas, table_idx = load_dataset_pair(qas_path, tables_path)
    if limit is not None:
        qas = qas[:limit]
    current_qa_ids = {
        str(qa.get("qa_id", ""))
        for qa in qas
        if isinstance(qa, dict)
    }

    hint_predictions_idx: Optional[Dict[str, List[str]]] = None
    if hint_predictions_path is not None:
        hint_predictions_idx = _load_hint_predictions(hint_predictions_path)
        _validate_hint_predictions_for_qas(qas, hint_predictions_idx)
        logger.info(
            "Loaded precomputed hint predictions for %d QA(s) from %s",
            len(hint_predictions_idx),
            hint_predictions_path,
        )
    expected_hint_source = (
        "precomputed"
        if hint_predictions_idx is not None
        else ("agent" if _use_agent_hints_enabled() else "dataset")
    )

    existing: List[Dict[str, Any]] = []
    existing_ids: set[str] = set()
    if skip_existing and output_path and stages is None:
        existing = [
            rec for rec in _load_existing_results(output_path)
            if str(rec.get("qa_id", "")) in current_qa_ids
            and _is_compatible_existing_record(
                rec,
                hint_predictions_idx,
                expected_hint_source,
            )
        ]
        existing_ids = {
            str(r["qa_id"]) for r in existing
            if isinstance(r, dict) and "qa_id" in r
        }
        if existing_ids:
            logger.info(
                "Found %d existing result(s) in %s — will skip them.",
                len(existing_ids), output_path,
            )

    existing_traces: List[Dict[str, Any]] = []
    current_existing_traces: List[Dict[str, Any]] = []
    prior_traces_idx: Dict[str, Dict[str, Any]] = {}
    if traces_path:
        existing_traces = _load_existing_results(traces_path)
        current_existing_traces = [
            trace for trace in existing_traces
            if str(trace.get("qa_id", "")) in current_qa_ids
        ]
        if stages is not None:
            prior_traces_idx = _build_trace_index(existing_traces)
            logger.info(
                "Loaded %d prior trace(s) for stage-resume.", len(prior_traces_idx),
            )

    pending = [qa for qa in qas if str(qa.get("qa_id", "")) not in existing_ids]
    skipped = len(qas) - len(pending)
    if skipped > 0:
        logger.info("Skipped %d already-processed QA(s); %d remaining.", skipped, len(pending))

    if not pending:
        logger.info("Nothing new to process; all %d QA(s) already done.", len(qas))
        if output_path and auto_evaluate and _should_run_auto_evaluation(stages):
            evaluation = _run_auto_evaluation(
                existing,
                qas,
                qas_path,
                eval_metrics,
                eval_threads,
                fail_on_metric_error,
            )
            _save_prediction_output(existing, output_path, evaluation)
        if traces_path:
            _save_results(current_existing_traces, traces_path)
            logger.info("Traces saved to %s  (%d records)", traces_path, len(current_existing_traces))
        if output_path and current_existing_traces:
            _save_stage_outputs(output_path, stages, current_existing_traces, existing)
        return existing

    total = len(pending)
    stage_info = f" (stages: {', '.join(sorted(stages))})" if stages else ""
    logger.info("Processing %d question(s) with %d worker(s)%s...", total, workers, stage_info)
    new_results: List[Dict[str, Any]] = []
    new_traces: List[Dict[str, Any]] = []

    def _persist_error_trace(exc: Exception) -> None:
        trace = _extract_error_trace(exc)
        if trace is None:
            return
        qa_id = trace.get("qa_id")
        if qa_id is not None:
            new_traces[:] = [
                existing_trace for existing_trace in new_traces
                if str(existing_trace.get("qa_id")) != str(qa_id)
            ]
        new_traces.append(trace)

    def _incremental_save() -> None:
        if output_path:
            _save_prediction_output(existing + new_results, output_path, evaluation=None)
        if traces_path:
            _save_results(new_traces, traces_path)
        if output_path:
            _save_stage_outputs(output_path, stages, new_traces, new_results)

    if workers <= 1:
        for i, qa in enumerate(pending, 1):
            qa_id = qa.get("qa_id", "?")
            logger.info("[%d/%d] qa_id=%s  question=%s", i, total, qa_id, qa.get("question", "")[:60])
            try:
                if hint_predictions_idx is None:
                    rec = process_one(
                        qa, table_idx,
                        stages=stages,
                        prior_traces_idx=prior_traces_idx,
                    )
                else:
                    rec = process_one(
                        qa, table_idx,
                        stages=stages,
                        prior_traces_idx=prior_traces_idx,
                        hint_predictions_idx=hint_predictions_idx,
                    )
            except Exception as exc:
                _persist_error_trace(exc)
                _incremental_save()
                raise
            trace = _extract_trace(rec)
            if trace is not None:
                new_traces.append(trace)
            new_results.append(rec)
            _print_result(rec, i, total)
            _incremental_save()
    else:
        counter = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            if hint_predictions_idx is None:
                future_to_qa = {
                    pool.submit(
                        process_one,
                        qa,
                        table_idx,
                        stages,
                        prior_traces_idx,
                    ): qa
                    for qa in pending
                }
            else:
                future_to_qa = {
                    pool.submit(
                        process_one,
                        qa,
                        table_idx,
                        stages,
                        prior_traces_idx,
                        hint_predictions_idx,
                    ): qa
                    for qa in pending
                }
            try:
                for future in as_completed(future_to_qa):
                    try:
                        rec = future.result()
                    except Exception as exc:
                        _persist_error_trace(exc)
                        _incremental_save()
                        raise
                    trace = _extract_trace(rec)
                    counter += 1
                    new_results.append(rec)
                    if trace is not None:
                        new_traces.append(trace)
                    _print_result(rec, counter, total)
                    _incremental_save()
            except Exception as exc:
                for pending_future in future_to_qa:
                    if pending_future is not future:
                        pending_future.cancel()
                raise enrich_error(exc) from exc

    merged = existing + new_results
    evaluation: Optional[Dict[str, Any]] = None
    if output_path and auto_evaluate and _should_run_auto_evaluation(stages):
        evaluation = _run_auto_evaluation(
            merged,
            qas,
            qas_path,
            eval_metrics,
            eval_threads,
            fail_on_metric_error,
        )
    if output_path:
        _save_prediction_output(merged, output_path, evaluation)
    if traces_path:
        _save_results(new_traces, traces_path)
        logger.info("Traces saved to %s  (%d records)", traces_path, len(new_traces))
    if output_path:
        _save_stage_outputs(output_path, stages, new_traces, new_results)

    _print_summary(merged)
    return merged


def _print_summary(results: List[Dict[str, Any]]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    success = [r for r in results if "error" not in r and "predicted_answer" in r]
    total = len(success)
    if total == 0:
        return
    matches = 0
    for r in success:
        candidates = r.get("predicted_answer", [""])
        if _cli_has_match(r.get("groundtruth", ""), candidates, r.get("hints")):
            matches += 1

    stats = _calculate_batch_stats(results)

    print(f"\n{'='*70}")
    print(f"  ACCURACY:  {matches}/{total} exact match  ({matches/total*100:.1f}%)")
    print(f"{'-'*70}")
    print(f"  EXECUTION TIME:")
    print(f"    Total:   {stats['total_elapsed_s']}s")
    print(f"    Average: {stats['average_elapsed_s']}s/question")
    print(f"  TOKEN CONSUMPTION:")
    print(f"    Total:   {stats['total_tokens']} (Prompt: {stats['total_prompt_tokens']}, Completion: {stats['total_completion_tokens']})")
    print(f"    Average: {stats['average_total_tokens']} (Prompt: {stats['average_prompt_tokens']}, Completion: {stats['average_completion_tokens']}) per question")
    print(f"  COST:")
    print(f"    Total:   ${stats['total_cost_usd']:.6f}")
    print(f"    Average: ${stats['average_cost_usd']:.6f}/question")
    print(f"{'='*70}\n")


def _print_result(rec: Dict[str, Any], idx: int, total: int) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    candidates = rec.get("predicted_answer", [""])
    print(f"\n{'='*70}")
    print(f"  [{idx}/{total}]  qa_id: {rec.get('qa_id')}")
    print(f"  Question:    {rec.get('question')}")
    print(f"  Groundtruth: {rec.get('groundtruth')}")
    print(f"  Predicted:   {candidates}")
    match = _cli_has_match(rec.get("groundtruth", ""), candidates, rec.get("hints"))
    print(f"  Match:       {'YES' if match else 'NO'}")
    print(f"  Time:        {rec.get('elapsed_s', '?')}s")
    print(f"  Tokens:      {rec.get('total_tokens', 0)} (Prompt: {rec.get('prompt_tokens', 0)}, Completion: {rec.get('completion_tokens', 0)})")
    print(f"  Cost:        ${rec.get('cost_usd', 0.0):.6f}")
    print(f"{'='*70}")


def _normalize_cli_match_text(text: Any) -> str:
    normalized = normalize_eval_text("" if text is None else str(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"[.!?]+$", "", normalized).strip()
    return normalized


def _cli_has_match(groundtruth: Any, candidates: Any, hints: Optional[List[str]] = None) -> bool:
    gt = _normalize_cli_match_text(groundtruth)
    if not gt:
        return False

    if not isinstance(candidates, list):
        candidates = [candidates]

    return any(exact_text_match(c, groundtruth, hints=hints) for c in candidates)


def run_interactive() -> None:
    """Interactive mode: user types a question, pastes a table, gets an answer."""
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    print("\n--- POMA Interactive Mode ---")
    print("Type 'quit' to exit.\n")
    while True:
        question = input("Question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        table = input("Table (flattened, one line): ").strip()
        hints_raw = input("Hints (comma-separated, e.g. What,MathematicalReasoning): ").strip()
        hints = [h.strip() for h in hints_raw.split(",") if h.strip()]

        request = QARequest(
            question=question,
            table_flattened=table,
            metadata={"hints": hints},
        )
        result = run_pipeline(request)
        answers = result["answer"]
        print(f"\n  Answer:     {answers[0]}")
        if len(answers) > 1:
            print(f"  Candidates: {answers}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="POMA multi-agent pipeline runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--qas", default="dataset/qas_test.json",
        help="Path to QAs JSON file (default: dataset/qas_test.json)",
    )
    parser.add_argument(
        "--tables", default="dataset/table.json",
        help="Path to tables JSON file (default: dataset/table.json)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSON path (default: outputs/poma/<qas_stem>.json)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of questions to process",
    )
    parser.add_argument(
        "--model", default=None,
        help=(
            "LLM model override. Supports full ids or aliases "
            "(e.g. openai/gpt-4o-mini, qwen3-8b, llama-3.1-8b-it)."
        ),
    )
    parser.add_argument(
        "--provider",
        type=str,
        nargs="+",
        default=None,
        help=(
            "OpenRouter provider routing list for POMA (mapped to provider.only), "
            "e.g. --provider atlas-cloud/fp8 alibaba. "
            "Overrides model defaults; can also be set via POMA_OPENROUTER_PROVIDER."
        ),
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Run in interactive single-question mode",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", default=True,
        help="Skip QAs that already have results in the output file (default: on)",
    )
    parser.add_argument(
        "--no-skip", dest="skip_existing", action="store_false",
        help="Re-process all QAs even if results already exist",
    )
    parser.add_argument(
        "--save-traces", action="store_true", default=True,
        help="Save per-step pipeline traces to a separate JSON file (default: on)",
    )
    parser.add_argument(
        "--no-traces", dest="save_traces", action="store_false",
        help="Disable saving pipeline traces",
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Number of parallel workers for batch processing (default: 1)",
    )
    parser.add_argument(
        "--no-eval",
        dest="auto_evaluate",
        action="store_false",
        default=True,
        help="Disable automatic evaluation after a completed batch",
    )
    parser.add_argument(
        "--eval-metrics",
        default=None,
        help=(
            "Comma-separated evaluation metrics "
            "(default: f1,em,rouge1,meteor,f1_by_answerability,rouge1_by_hint)"
        ),
    )
    parser.add_argument(
        "--eval-threads",
        type=int,
        default=1,
        help="Number of evaluation worker threads (default: 1)",
    )
    parser.add_argument(
        "--fail-on-metric-error",
        action="store_true",
        help="Fail on metric runtime errors instead of soft fallback",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        default=None,
        choices=["refiner", "specialists", "normalization"],
        help="Run only specific pipeline stages; skipped stages load output "
             "from prior trace. E.g. --stages normalization",
    )
    hint_source_group = parser.add_mutually_exclusive_group()
    hint_source_group.add_argument(
        "--use-agent-hints",
        action="store_true",
        default=None,
        help=(
            "Use HintPredictorAgent to automatically predict hints instead of "
            "dataset hints (default for POMA batch runs)"
        ),
    )
    hint_source_group.add_argument(
        "--use-dataset-hints",
        "--no-agent-hints",
        dest="use_agent_hints",
        action="store_false",
        default=None,
        help="Use dataset hints directly and do not call HintPredictorAgent",
    )
    parser.add_argument(
        "--hint-predictions",
        default=None,
        help=(
            "Path to precomputed HintPredictor JSON output; uses predicted_hints "
            "instead of dataset hints without calling HintPredictorAgent"
        ),
    )
    args = parser.parse_args()

    if args.use_agent_hints is True and args.hint_predictions:
        parser.error("--hint-predictions cannot be used together with --use-agent-hints")

    import os
    if args.model:
        os.environ["POMA_LLM_MODEL"] = args.model
    if args.provider:
        os.environ["POMA_OPENROUTER_PROVIDER"] = ",".join(
            provider.strip() for provider in args.provider if provider.strip()
        )

    if args.use_agent_hints is None:
        os.environ.setdefault("POMA_USE_AGENT_HINTS", "true")
    else:
        os.environ["POMA_USE_AGENT_HINTS"] = "true" if args.use_agent_hints else "false"

    if args.interactive:
        run_interactive()
        return

    qas_path = Path(args.qas)
    tables_path = Path(args.tables)
    hint_predictions_path = Path(args.hint_predictions) if args.hint_predictions else None

    if not qas_path.exists():
        print(f"ERROR: QAs file not found: {qas_path}", file=sys.stderr)
        sys.exit(1)
    if not tables_path.exists():
        print(f"ERROR: Tables file not found: {tables_path}", file=sys.stderr)
        sys.exit(1)
    if hint_predictions_path is not None and not hint_predictions_path.exists():
        print(f"ERROR: Hint predictions file not found: {hint_predictions_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("outputs/poma") / f"{qas_path.stem}.json"

    stages: Optional[Set[str]] = set(args.stages) if args.stages else None

    traces_path: Optional[Path] = None
    if args.save_traces or stages is not None:
        traces_path = output_path.with_name(f"{output_path.stem}_traces.json")

    run_batch(
        qas_path, tables_path, output_path, args.limit,
        args.skip_existing, traces_path, args.workers,
        stages=stages,
        auto_evaluate=args.auto_evaluate,
        eval_metrics=args.eval_metrics,
        eval_threads=args.eval_threads,
        fail_on_metric_error=args.fail_on_metric_error,
        hint_predictions_path=hint_predictions_path,
    )


if __name__ == "__main__":
    main()
