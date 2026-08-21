from __future__ import annotations

import concurrent.futures
from dataclasses import replace
import json
import math
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Bootstrap: ensure the standalone POMA project root is on sys.path.
_BASELINE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BASELINE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from .llm_client import GenConfig, LLMZeroShotClient
from .prompts import PROMPT_STYLES, build_tableqa_prompt
from src.contracts import CallContext, schema_for_call
from src.services import StructuredGenerator

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None  # type: ignore

_FILE_LOCK = threading.Lock()

SCHEMA_BY_PROMPT_STYLE = {
    "zero_shot": "baseline_zero_shot.v1",
    "few_shot": "baseline_few_shot.v1",
    "cot": "baseline_cot.v1",
    "task_decomposition": "baseline_task_decomposition.v1",
}

_AUTHORIZATION_PATTERN = re.compile(
    r"(?i)(\bauthorization[ \t]*[:=][ \t]*)"
    r"(?:(?:bearer|basic)[ \t]+)?"
    r"[^ \t\r\n,;]+"
)
_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _sanitize_run_id(run_id: str) -> str:
    s = run_id.strip()
    if not s:
        raise ValueError("Run id (output folder name) must be non-empty.")
    if ".." in s or "/" in s or "\\" in s:
        raise ValueError(
            f"Invalid run id {run_id!r}: must not contain path separators or '..'"
        )
    return s


def _load_json(path: str | Path) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_dataset_pair(
    qas_path: str | Path,
    tables_path: str | Path,
) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Load (qas, table_idx) from explicit JSON paths.

    Supported formats:
      - QAs: {"qas": [...]} or [...]
      - Tables: {"table": [...]} or [...] or {table_id: table_obj}
    """
    qas_raw = _load_json(qas_path)
    qas = qas_raw.get("qas", qas_raw) if isinstance(qas_raw, dict) else qas_raw
    if not isinstance(qas, list):
        raise ValueError(f"Invalid QAs JSON format at {qas_path!r}: expected list or {{'qas': list}}")

    tables_raw = _load_json(tables_path)
    tables = tables_raw.get("table", tables_raw) if isinstance(tables_raw, dict) else tables_raw

    table_idx: Dict[str, Dict[str, Any]] = {}
    if isinstance(tables, list):
        for t in tables:
            if isinstance(t, dict) and t.get("table_id") is not None:
                table_idx[str(t["table_id"])] = t
    elif isinstance(tables, dict):
        if all(isinstance(v, dict) for v in tables.values()):
            for k, v in tables.items():
                if isinstance(v, dict):
                    table_idx[str(k)] = v
        else:
            raise ValueError(f"Invalid tables JSON format at {tables_path!r}: expected list/dict of tables")
    else:
        raise ValueError(f"Invalid tables JSON format at {tables_path!r}: expected list or dict")

    return qas, table_idx


def _append_jsonl_record(path: Path, record: Dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    with _FILE_LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    message = _AUTHORIZATION_PATTERN.sub(r"\1[REDACTED]", message)
    message = _SECRET_PATTERN.sub(r"\1\2[REDACTED]", message)
    for key, value in os.environ.items():
        upper_key = key.upper()
        if value and (
            "API_KEY" in upper_key
            or upper_key.startswith("GPT_API_KEY")
        ):
            message = message.replace(value, "[REDACTED]")
    return message


def _load_jsonl_records(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    records.append({"_line": line_no, "_raw": s, "_error": "not_a_json_object"})
            except Exception as e:
                records.append({"_line": line_no, "_raw": s, "_error": f"json_decode_error: {e}"})
    return records


def _load_existing_qa_ids(path: Path) -> set[str]:
    qa_ids: set[str] = set()
    for rec in _load_jsonl_records(path):
        if not isinstance(rec, dict):
            continue
        qa_id = rec.get("qa_id")
        if qa_id is not None:
            qa_ids.add(str(qa_id))
    return qa_ids


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

    total_elapsed = sum(float(r.get("elapsed_s") or 0.0) for r in valid_recs)
    total_prompt = sum(int(r.get("prompt_tokens") or 0) for r in valid_recs)
    total_completion = sum(int(r.get("completion_tokens") or 0) for r in valid_recs)
    total_tok = sum(int(r.get("total_tokens") or 0) for r in valid_recs)
    costs = [r.get("cost_usd") for r in valid_recs]
    has_unknown_cost = any(
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(float(cost))
        or float(cost) < 0
        for cost in costs
    )
    total_cost = None if has_unknown_cost else sum(float(cost) for cost in costs)

    return {
        "total_elapsed_s": round(total_elapsed, 2),
        "average_elapsed_s": round(total_elapsed / n, 2),
        "total_prompt_tokens": total_prompt,
        "average_prompt_tokens": round(total_prompt / n, 1),
        "total_completion_tokens": total_completion,
        "average_completion_tokens": round(total_completion / n, 1),
        "total_tokens": total_tok,
        "average_total_tokens": round(total_tok / n, 1),
        "total_cost_usd": None if total_cost is None else round(total_cost, 6),
        "average_cost_usd": (
            None if total_cost is None else round(total_cost / n, 6)
        ),
        "count": n,
    }


def _write_pretty_json_from_jsonl(jsonl_path: Path) -> Path:
    json_path = jsonl_path.with_suffix(".json")
    records = _load_jsonl_records(jsonl_path)
    _ensure_dir(json_path.parent)
    payload = {
        "predictions": records,
        "evaluation": None,
        "stats": _calculate_batch_stats(records),
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return json_path


def process_one_qa(
    qa: Dict[str, Any],
    table_idx: Dict[str, Any],
    models: Sequence[str],
    outputs: Dict[str, Path],
    client: LLMZeroShotClient,
    cfg: GenConfig,
    sleep_s: float,
    prompt_style: str = "zero_shot",
) -> str:
    qa_id = str(qa.get("qa_id") or "")
    table_id = str(qa.get("table_id") or "")
    question = str(qa.get("question") or "").strip()
    groundtruth = qa.get("answer")

    if not question:
        raise ValueError(f"qa_id={qa_id}: question is empty")

    if not table_id:
        raise ValueError(f"qa_id={qa_id}: table_id is empty")

    table = table_idx.get(table_id)
    if not isinstance(table, dict):
        raise ValueError(f"qa_id={qa_id}: table_id={table_id!r} not found in table index")

    table_str = ""
    try:
        from preprocessing.representation import create_representation

        table_repr = create_representation(table)
        table_str = str(table_repr.to_string() or "").strip()
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Table processing requires the bundled preprocessing package. "
            "Install the project (pip install -e .) and ensure `beautifulsoup4` is available."
        ) from e
    except ImportError as e:
        raise RuntimeError(
            "Table processing failed to import. Ensure `beautifulsoup4` is installed."
        ) from e

    if not table_str:
        raise ValueError(f"qa_id={qa_id}: table string is empty for table_id={table_id!r}")

    ps = (prompt_style or "zero_shot").strip().lower()
    prompt = build_tableqa_prompt(
        question=question,
        table_str=table_str,
        prompt_style=ps,
        answer_language="vi",
    )
    prompt_text = str(prompt or "").strip()

    if not prompt_text:
        raise ValueError(f"qa_id={qa_id}: prompt is empty")
    if "TABLE_STR:" not in prompt_text or "QUESTION:" not in prompt_text:
        raise ValueError(f"qa_id={qa_id}: prompt must contain TABLE_STR and QUESTION markers")
    if table_str not in prompt_text:
        raise ValueError(f"qa_id={qa_id}: prompt does not include rendered table string")

    for model in models:
        started_at = time.time()
        schema_name = SCHEMA_BY_PROMPT_STYLE[ps]
        schema = schema_for_call(schema_name)

        def generate_once(
            request_prompt: str,
            text_format: Optional[Dict[str, Any]],
        ) -> tuple[str, Dict[str, Any]]:
            structured_cfg = replace(
                cfg,
                text_format=(
                    None if text_format is None else dict(text_format)
                ),
                require_parameters=text_format is not None,
            )
            return client.generate_with_usage(
                model,
                request_prompt,
                structured_cfg,
                max_retries=4,
                retry_delay=15,
            )

        try:
            result = StructuredGenerator(generate_once).generate(
                prompt_text,
                schema,
                CallContext(
                    qa_id=qa_id,
                    agent_name="DirectPromptBaseline",
                    prompt_name=ps,
                    model=model,
                ),
            )
        except Exception as exc:
            elapsed_s = round(time.time() - started_at, 2)
            _append_jsonl_record(
                outputs[model],
                {
                    "qa_id": qa_id,
                    "table_id": table_id,
                    "question": question,
                    "groundtruth": (
                        "" if groundtruth is None else groundtruth
                    ),
                    "schema_name": schema_name,
                    "prompt_style": ps,
                    "elapsed_s": elapsed_s,
                    "error": {
                        "type": type(exc).__name__,
                        "message": _safe_error_message(exc),
                    },
                },
            )
            if sleep_s > 0:
                time.sleep(float(sleep_s))
            continue
        elapsed_s = round(time.time() - started_at, 2)
        rec = {
            "qa_id": qa_id,
            "table_id": table_id,
            "question": question,
            "groundtruth": ("" if groundtruth is None else groundtruth),
            "prediction": [result.data["final_answer"]],
            "schema_name": result.schema_name,
            "structured_output": result.data,
            "schema_valid": result.schema_valid,
            "repair_attempted": result.repair_attempted,
            "repair_succeeded": result.repair_succeeded,
            "prompt_style": ps,
            "elapsed_s": elapsed_s,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "cost_usd": result.cost_usd,
        }
        _append_jsonl_record(outputs[model], rec)

        if sleep_s > 0:
            time.sleep(float(sleep_s))

    return qa_id


def run_batch_zeroshot(
    *,
    qas_path: str | Path,
    tables_path: str | Path,
    models: Sequence[str],
    output_dir: str | Path,
    limit: Optional[int] = None,
    sleep_s: float = 0.0,
    gen_config: Optional[GenConfig] = None,
    max_workers: int = 8,
    output_id: Optional[str] = None,
    openrouter_provider: Optional[Sequence[str]] = None,
    skip_existing_qas: bool = True,
    prompt_style: str = "zero_shot",
) -> Dict[str, Path]:
    ps = (prompt_style or "zero_shot").strip().lower()
    if ps not in PROMPT_STYLES:
        raise ValueError(f"Unknown prompt_style={prompt_style!r}. Choose from {PROMPT_STYLES}.")

    qas, table_idx = load_dataset_pair(qas_path, tables_path)

    if limit is not None:
        qas = qas[: int(limit)]

    out_dir = Path(output_dir)
    _ensure_dir(out_dir)

    for model in models:
        model_s = str(model).strip().lower()
        if model_s.startswith("local/") or model_s.startswith("local:"):
            raise ValueError(
                "Local provider has been removed. Use openai/<model> or openrouter/<model>."
            )

    client = LLMZeroShotClient()
    cfg = gen_config or GenConfig()
    if openrouter_provider:
        cfg.openrouter_provider = {"only": [str(p).strip() for p in openrouter_provider if str(p).strip()]}

    outputs: Dict[str, Path] = {}
    run_id_raw = str(output_id).strip() if output_id is not None else Path(qas_path).stem
    if not run_id_raw:
        run_id_raw = Path(qas_path).stem
    run_id = _sanitize_run_id(run_id_raw)
    pred_root = out_dir / run_id
    for model in models:
        safe_model = model.replace("/", "_").replace(":", "_")
        out_path = pred_root / f"{safe_model}.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not skip_existing_qas:
            out_path.write_text("", encoding="utf-8")
        elif not out_path.exists():
            out_path.write_text("", encoding="utf-8")
        outputs[model] = out_path

    if skip_existing_qas and qas:
        existing_sets = [_load_existing_qa_ids(outputs[m]) for m in models]
        existing_all = set.intersection(*existing_sets) if existing_sets else set()
        if existing_all:
            original_count = len(qas)
            qas = [qa for qa in qas if str(qa.get("qa_id") or "") not in existing_all]
            skipped_count = original_count - len(qas)
            if skipped_count > 0:
                print(f"[skip-existing-qas] skipped {skipped_count} QA(s); pending {len(qas)} QA(s).")

    pbar = None
    try:
        if tqdm is not None:
            pbar = tqdm(total=len(qas), desc="LLM-ZeroShot", unit="qa")

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        )
        in_flight: set[concurrent.futures.Future[str]] = set()
        qa_iter = iter(qas)

        def fill_available_slots() -> None:
            while len(in_flight) < max_workers:
                try:
                    qa = next(qa_iter)
                except StopIteration:
                    return
                in_flight.add(
                    executor.submit(
                        process_one_qa,
                        qa,
                        table_idx,
                        models,
                        outputs,
                        client,
                        cfg,
                        sleep_s,
                        ps,
                    )
                )

        try:
            fill_available_slots()
            processed_count = 0
            while in_flight:
                completed, _ = concurrent.futures.wait(
                    in_flight,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                in_flight.difference_update(completed)
                for future in completed:
                    processed_count += 1
                    try:
                        qa_id = future.result()
                        if pbar is not None:
                            pbar.set_postfix_str(f"qa_id={qa_id}")
                            pbar.update(1)
                        elif (
                            processed_count % 5 == 0
                            or processed_count == len(qas)
                        ):
                            print(
                                f"[{processed_count}/{len(qas)}] "
                                f"processed qa_id={qa_id}"
                            )
                    except Exception as e:
                        if pbar is not None:
                            tqdm.write(f"QA Failed: {e!r}")
                            pbar.update(1)
                        else:
                            print(f"QA Failed: {e!r}")
                fill_available_slots()
        except BaseException:
            for future in in_flight:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)

        for _, jsonl_path in outputs.items():
            try:
                _write_pretty_json_from_jsonl(jsonl_path)
            except Exception as e:
                print(f"[warn] failed to write pretty JSON for {jsonl_path}: {e!r}", file=sys.stderr)
    finally:
        if pbar is not None:
            pbar.close()
        client.shutdown()

    return outputs
