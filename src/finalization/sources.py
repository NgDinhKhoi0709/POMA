"""Strict adapters from experiment artifacts to finalization requests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from preprocessing.representation import create_representation
from src.contracts.finalization import AnswerCandidate
from src.finalization.finalizers import (
    FinalizationRequest,
    FinalizationSourceFailure,
)


class FinalizationInputError(ValueError):
    """An input artifact cannot be adapted without changing its meaning."""


def _load_json(path: Path, label: str) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            if path.suffix.lower() == ".jsonl":
                records: list[dict[str, Any]] = []
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise FinalizationInputError(
                            f"Cannot load {label} JSONL from {path}: "
                            f"line {line_number} is invalid JSON"
                        ) from exc
                    if not isinstance(value, dict):
                        raise FinalizationInputError(
                            f"Cannot load {label} JSONL from {path}: "
                            f"line {line_number} is not an object"
                        )
                    records.append(value)
                return records
            return json.load(handle)
    except FinalizationInputError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalizationInputError(
            f"Cannot load {label} JSON from {path}: {exc}"
        ) from exc


def _as_records(value: Any, wrapper: str, label: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get(wrapper)
    if not isinstance(value, list) or not all(
        isinstance(item, dict) for item in value
    ):
        raise FinalizationInputError(
            f"{label} must be a list or an object containing {wrapper!r}"
        )
    return value


def _required_id(record: dict[str, Any], field: str, label: str) -> str:
    value = record.get(field)
    if value is None or not str(value).strip():
        raise FinalizationInputError(f"{label} is missing non-empty {field}")
    return str(value)


def _index_unique(
    records: list[dict[str, Any]],
    *,
    field: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = _required_id(record, field, label)
        if record_id in indexed:
            raise FinalizationInputError(
                f"Duplicate {field} {record_id!r} in {label}"
            )
        indexed[record_id] = record
    return indexed


def _load_qas(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records = _as_records(_load_json(path, "QAs"), "qas", "QAs")
    return records, _index_unique(records, field="qa_id", label="QAs")


def _load_tables(path: Path) -> dict[str, dict[str, Any]]:
    value = _load_json(path, "tables")
    if isinstance(value, dict) and "table" in value:
        value = value["table"]

    if isinstance(value, list):
        records = value
    elif isinstance(value, dict) and all(
        isinstance(table, dict) for table in value.values()
    ):
        records = []
        for table_id, table in value.items():
            copied = dict(table)
            copied.setdefault("table_id", table_id)
            records.append(copied)
    else:
        raise FinalizationInputError(
            "Tables must be a list, a {'table': list} object, "
            "or a table-id mapping"
        )

    if not all(isinstance(record, dict) for record in records):
        raise FinalizationInputError("Every table record must be an object")
    return _index_unique(records, field="table_id", label="tables")


def _poma_candidates(record: dict[str, Any], qa_id: str) -> list[AnswerCandidate]:
    steps = record.get("steps")
    specialists = steps.get("3_specialists") if isinstance(steps, dict) else None
    if not isinstance(specialists, list) or not specialists:
        raise FinalizationInputError(
            f"qa_id={qa_id!r} has no non-empty steps.3_specialists"
        )

    candidates: list[AnswerCandidate] = []
    for index, specialist in enumerate(specialists):
        if not isinstance(specialist, dict):
            raise FinalizationInputError(
                f"qa_id={qa_id!r} specialist {index} must be an object"
            )
        source_name = specialist.get("agent_name")
        answer = specialist.get("answer")
        if not isinstance(source_name, str) or not source_name.strip():
            raise FinalizationInputError(
                f"qa_id={qa_id!r} specialist {index} has no agent_name"
            )
        if not isinstance(answer, str) or not answer.strip():
            raise FinalizationInputError(
                f"qa_id={qa_id!r} specialist {index} has no raw answer"
            )
        candidates.append(AnswerCandidate(source_name=source_name, answer=answer))
    return candidates


def _poma_native_context(
    record: dict[str, Any],
    qa_id: str,
) -> tuple[str, str | None]:
    steps = record.get("steps")
    refiner = (
        steps.get("1_question_refiner")
        if isinstance(steps, dict)
        else None
    )
    if not isinstance(refiner, dict):
        raise FinalizationInputError(
            f"qa_id={qa_id!r} has no steps.1_question_refiner object"
        )

    normalized_question = refiner.get("normalized_question")
    if (
        not isinstance(normalized_question, str)
        or not normalized_question.strip()
    ):
        raise FinalizationInputError(
            f"qa_id={qa_id!r} has no non-empty "
            "steps.1_question_refiner.normalized_question"
        )
    if "target" not in refiner:
        raise FinalizationInputError(
            f"qa_id={qa_id!r} is missing "
            "steps.1_question_refiner.target"
        )
    target = refiner["target"]
    if target is not None and (
        not isinstance(target, str) or not target.strip()
    ):
        raise FinalizationInputError(
            f"qa_id={qa_id!r} steps.1_question_refiner.target "
            "must be null or a non-empty string"
        )
    return (
        normalized_question.strip(),
        target.strip() if isinstance(target, str) else None,
    )


def _baseline_source_failure(
    record: dict[str, Any],
    qa_id: str,
) -> FinalizationSourceFailure | None:
    if "error" not in record:
        return None
    if "prediction" in record:
        raise FinalizationInputError(
            f"qa_id={qa_id!r} direct baseline must contain exactly one "
            "of prediction or error"
        )
    error = record["error"]
    if not isinstance(error, dict):
        raise FinalizationInputError(
            f"qa_id={qa_id!r} direct baseline error must be an object"
        )
    error_type = error.get("type")
    message = error.get("message")
    if not isinstance(error_type, str) or not error_type.strip():
        raise FinalizationInputError(
            f"qa_id={qa_id!r} direct baseline error.type must be non-empty"
        )
    if not isinstance(message, str) or not message.strip():
        raise FinalizationInputError(
            f"qa_id={qa_id!r} direct baseline error.message must be non-empty"
        )
    return FinalizationSourceFailure(
        error_type=error_type.strip(),
        message=message.strip(),
    )


def _baseline_candidates(
    record: dict[str, Any],
    qa_id: str,
) -> list[AnswerCandidate]:
    prediction = record.get("prediction")
    if isinstance(prediction, str):
        answers = [prediction]
    elif isinstance(prediction, list):
        answers = prediction
    else:
        answers = []

    if (
        len(answers) != 1
        or not isinstance(answers[0], str)
        or not answers[0].strip()
    ):
        raise FinalizationInputError(
            f"qa_id={qa_id!r} direct baseline must contain exactly one "
            "non-empty raw prediction"
        )
    return [AnswerCandidate(source_name="direct-baseline", answer=answers[0])]


def load_finalization_requests(
    *,
    source_path: Path,
    source_kind: Literal["poma-specialists", "direct-baseline"],
    qas_path: Path,
    tables_path: Path,
) -> list[FinalizationRequest]:
    """Load one strict finalization request per QA in dataset order."""
    if source_kind not in ("poma-specialists", "direct-baseline"):
        raise FinalizationInputError(f"Unsupported source kind: {source_kind!r}")

    qas, qa_index = _load_qas(Path(qas_path))
    tables = _load_tables(Path(tables_path))
    source_value = _load_json(Path(source_path), "source")
    source_records = _as_records(
        source_value,
        "predictions",
        f"{source_kind} source",
    )
    source_index = _index_unique(
        source_records,
        field="qa_id",
        label=f"{source_kind} source",
    )

    unknown_source_ids = set(source_index).difference(qa_index)
    if unknown_source_ids:
        unknown = sorted(unknown_source_ids)[0]
        raise FinalizationInputError(
            f"Source qa_id={unknown!r} does not exist in the QAs dataset"
        )

    missing_source_ids = set(qa_index).difference(source_index)
    if missing_source_ids:
        missing = next(
            str(qa["qa_id"])
            for qa in qas
            if str(qa["qa_id"]) in missing_source_ids
        )
        raise FinalizationInputError(
            f"QAs qa_id={missing!r} has no source raw answer"
        )

    requests: list[FinalizationRequest] = []
    for qa in qas:
        qa_id = str(qa["qa_id"])
        table_id = _required_id(qa, "table_id", f"QA qa_id={qa_id!r}")
        question = qa.get("question")
        if not isinstance(question, str) or not question.strip():
            raise FinalizationInputError(
                f"QA qa_id={qa_id!r} is missing a non-empty question"
            )

        table = tables.get(table_id)
        if table is None:
            raise FinalizationInputError(
                f"QA qa_id={qa_id!r} references missing table {table_id!r}"
            )
        flattened = create_representation(table).to_string()
        if not isinstance(flattened, str) or not flattened.strip():
            raise FinalizationInputError(
                f"QA qa_id={qa_id!r} table {table_id!r} has no Flatten V1 data"
            )

        source = source_index[qa_id]
        source_table_id = source.get("table_id")
        if source_table_id is not None and str(source_table_id) != table_id:
            raise FinalizationInputError(
                f"qa_id={qa_id!r} source table_id does not match the dataset"
            )
        native_question: str | None = None
        native_target: str | None = None
        source_failure: FinalizationSourceFailure | None = None
        if source_kind == "poma-specialists":
            candidates = _poma_candidates(source, qa_id)
            native_question, native_target = _poma_native_context(
                source,
                qa_id,
            )
        else:
            source_failure = _baseline_source_failure(source, qa_id)
            candidates = (
                []
                if source_failure is not None
                else _baseline_candidates(source, qa_id)
            )

        requests.append(
            FinalizationRequest(
                qa_id=qa_id,
                table_id=table_id,
                question=question,
                table_flattened=flattened,
                candidates=candidates,
                native_question=native_question,
                native_target=native_target,
                source_failure=source_failure,
            )
        )
    return requests


__all__ = ["FinalizationInputError", "load_finalization_requests"]
