"""Sequential, resumable local evaluation runner for Kaggle."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.kaggle_eval.jsonl_io import append_jsonl, completed_qa_ids
from src.kaggle_eval.selection import load_final_543_ids, select_pilot_qas

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover - Kaggle supplies tqdm
    tqdm = None


@dataclass(frozen=True)
class RunConfig:
    repo_root: Path
    output_root: Path
    phase: Literal["smoke", "pilot", "final"] = "pilot"
    mode: Literal["zero_shot", "poma", "both"] = "both"
    model: str = "local/sea-lion-v3-8b-it"
    prompt_profile: str = "compact"
    seed: int = 42
    pilot_n: int = 200
    limit: int | None = None
    final_ids_path: Path | None = None


def prepare_run_dirs(config: RunConfig) -> dict[str, Path]:
    root = config.output_root / "sea_lion_v3_8b_it" / config.phase
    result = {}
    for mode in ("zero_shot", "poma"):
        path = root / mode
        path.mkdir(parents=True, exist_ok=True)
        result[mode] = path
    return result


def _dataset_paths(config: RunConfig) -> tuple[Path, Path]:
    qas = config.repo_root / "dataset" / ("qas_test.json" if config.phase == "final" else "qas_dev.json")
    return qas, config.repo_root / "dataset" / "table.json"


def select_qas(config: RunConfig) -> tuple[list[dict], dict]:
    from baseline.run import load_dataset_pair
    from preprocessing.representation import create_representation
    qas_path, tables_path = _dataset_paths(config)
    qas, table_idx = load_dataset_pair(qas_path, tables_path)
    if config.phase == "final":
        wanted = set(load_final_543_ids(config.final_ids_path))
        selected = [qa for qa in qas if str(qa.get("qa_id")) in wanted]
        if len(selected) != len(wanted):
            raise ValueError("Some final QA IDs are absent from qas_test.json")
    elif config.phase == "pilot":
        counts = {key: len(create_representation(value).to_string().split()) for key, value in table_idx.items()}
        selected = select_pilot_qas(qas, table_token_counts=counts, n=config.pilot_n, seed=config.seed)
    else:
        selected = qas[:1]
    if config.limit is not None:
        selected = selected[:config.limit]
    return selected, table_idx


def _record_selection(path: Path, selected: list[dict]) -> None:
    path.write_text(json.dumps([str(qa["qa_id"]) for qa in selected], ensure_ascii=False, indent=2), encoding="utf-8")


def _pending_qas(selected: list[dict], done: set[str]) -> list[dict]:
    return [qa for qa in selected if str(qa["qa_id"]) not in done]


def _progress(qas: list[dict], *, description: str, skipped: int):
    if tqdm is None:
        print(f"{description}: {len(qas)} pending, {skipped} resumed/skipped")
        return qas
    return tqdm(
        qas,
        desc=description,
        unit="qa",
        dynamic_ncols=True,
        initial=skipped,
        total=len(qas) + skipped,
    )


def run_zero_shot(config: RunConfig, selected: list[dict], table_idx: dict) -> Path:
    from baseline.prompts import build_tableqa_prompt
    from preprocessing.representation import create_representation
    from src.contracts import CallContext, schema_for_call
    from src.services.local_transformers_client import ContextOverflowError
    from src.services.llm_client import LLMClient
    from src.services.structured_generation import StructuredGenerator
    directory = prepare_run_dirs(config)["zero_shot"]
    predictions, errors = directory / "predictions.jsonl", directory / "errors.jsonl"
    _record_selection(directory / "selected_ids.json", selected)
    done = completed_qa_ids(predictions, errors)
    pending = _pending_qas(selected, done)
    client = LLMClient()
    for qa in _progress(pending, description="Zero-shot", skipped=len(selected) - len(pending)):
        qa_id = str(qa["qa_id"])
        try:
            table = create_representation(table_idx[str(qa["table_id"])]).to_string()
            prompt, _ = build_tableqa_prompt(question=str(qa["question"]), table_str=table, prompt_style="zero_shot")
            generator = StructuredGenerator(client._generate_raw_text)
            result = generator.generate(prompt, schema_for_call("baseline_zero_shot.v1"), CallContext(qa_id=qa_id, agent_name="DirectPromptBaseline", prompt_name="zero_shot", model=config.model))
            append_jsonl(predictions, {"qa_id": qa_id, "prediction": [result.data["answer"]], "schema_valid": result.schema_valid, "repair_attempted": result.repair_attempted, "repair_succeeded": result.repair_succeeded})
        except Exception as exc:
            append_jsonl(errors, {"qa_id": qa_id, "terminal": isinstance(exc, ContextOverflowError), "error_type": "context_overflow" if isinstance(exc, ContextOverflowError) else type(exc).__name__, "error": str(exc)})
    return predictions


def run_poma(config: RunConfig, selected: list[dict], table_idx: dict) -> Path:
    os.environ.update({"POMA_LLM_MODEL": config.model, "POMA_PROMPT_PROFILE": config.prompt_profile, "POMA_USE_AGENT_HINTS": "true", "POMA_PARALLEL_WORKERS": "1", "POMA_PROJECT_ROOT": str(config.repo_root)})
    from run_poma import process_one
    from src.services.local_transformers_client import ContextOverflowError
    directory = prepare_run_dirs(config)["poma"]
    predictions, traces, errors = directory / "predictions.jsonl", directory / "traces.jsonl", directory / "errors.jsonl"
    _record_selection(directory / "selected_ids.json", selected)
    done = completed_qa_ids(predictions, errors)
    pending = _pending_qas(selected, done)
    for qa in _progress(pending, description="POMA", skipped=len(selected) - len(pending)):
        qa_id = str(qa["qa_id"])
        try:
            record = process_one(qa, table_idx)
            append_jsonl(predictions, {"qa_id": qa_id, "prediction": record.get("prediction", record.get("answers", []))})
            append_jsonl(traces, {"qa_id": qa_id, "trace": record.get("trace", {})})
        except Exception as exc:
            append_jsonl(errors, {"qa_id": qa_id, "terminal": isinstance(exc, ContextOverflowError), "error_type": "context_overflow" if isinstance(exc, ContextOverflowError) else type(exc).__name__, "error": str(exc)})
    return predictions
