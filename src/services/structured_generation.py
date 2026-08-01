"""Validated structured generation with one bounded repair attempt."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any

from jsonschema import Draft202012Validator

from src.contracts import (
    CallContext,
    ResponseSchema,
    StructuredContractError,
    StructuredOutputMode,
    StructuredResult,
    validate_domain_payload,
)


class UnsupportedStructuredOutputModel(ValueError):
    """Raised when a model has no known structured-output capability."""


class StructuredGenerationError(RuntimeError):
    """Raised when a response remains invalid after one repair attempt."""


GenerateOnce = Callable[
    [str, dict[str, Any] | None],
    tuple[str, dict[str, Any]],
]


def resolve_output_mode(
    model: str,
    override: StructuredOutputMode | None = None,
) -> StructuredOutputMode:
    """Resolve the safe structured-output mode for a configured model."""
    if override is not None:
        return override

    normalized = model.removeprefix("openrouter/")
    if normalized == "google/gemma-3-4b-it":
        return StructuredOutputMode.STRICT_JSON_SCHEMA
    if normalized in {"qwen/qwen3-8b", "qwen/qwen3-8b-04-28"}:
        return StructuredOutputMode.PROMPT_ONLY
    if model.startswith("openai/"):
        return StructuredOutputMode.STRICT_JSON_SCHEMA
    raise UnsupportedStructuredOutputModel(model)


def _strict_text_format(schema: ResponseSchema) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": f"{schema.name.replace('.', '_')}_{schema.version}",
        "strict": True,
        "schema": schema.json_schema,
    }


def _qwen_prompt(prompt: str, schema: ResponseSchema) -> str:
    compact_schema = json.dumps(
        schema.json_schema,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"{prompt}\n\n"
        "Return one JSON object matching this JSON Schema: "
        f"{compact_schema}"
    )


_JSON_FENCE_PATTERN = re.compile(
    r"\A\s*```(?:json)?\s*(.*?)\s*```\s*\Z",
    flags=re.IGNORECASE | re.DOTALL,
)


def _strip_optional_json_fence(raw_response: str) -> str:
    match = _JSON_FENCE_PATTERN.fullmatch(raw_response)
    return match.group(1).strip() if match else raw_response


def _json_path(error: Any) -> str:
    path = "$"
    for part in error.absolute_path:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"

    if path == "$" and error.validator == "required":
        match = re.search(r"'([^']+)' is a required property", error.message)
        if match:
            return f"$.{match.group(1)}"
    return path


def _validation_errors(raw_response: str, schema: ResponseSchema) -> list[str]:
    try:
        payload = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as exc:
        detail = getattr(exc, "msg", str(exc))
        return [f"$: invalid JSON ({detail})"]

    if not isinstance(payload, dict):
        return ["$: response must be a JSON object"]

    validator = Draft202012Validator(schema.json_schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        return [f"{_json_path(error)}: {error.message}" for error in errors]

    try:
        validate_domain_payload(schema.name, payload)
    except StructuredContractError as exc:
        return [f"{_domain_error_path(schema.name, str(exc))}: {exc}"]
    return []


def _decode_and_validate(
    raw_response: str,
    schema: ResponseSchema,
) -> tuple[dict[str, Any] | None, list[str]]:
    json_text = _strip_optional_json_fence(raw_response)
    errors = _validation_errors(json_text, schema)
    if errors:
        return None, errors
    return json.loads(json_text), []


def _domain_error_path(schema_name: str, message: str) -> str:
    if schema_name == "gsa.v1":
        if "final_answer" in message or "null decision" in message:
            return "$.final_answer"
        return "$.supporting_evidence"

    paths = {
        "hint_predictor.v1": "$.predicted_hints",
        "answer_normalization.v1": "$.answers",
        "baseline_task_decomposition.v1": "$.subproblems",
    }
    return paths.get(schema_name, "$")


def _repair_prompt(
    original_prompt: str,
    validation_errors: list[str],
    raw_response: str,
) -> str:
    errors_text = "\n".join(validation_errors)
    return (
        "Original request:\n"
        f"{original_prompt}\n\n"
        "Return one JSON object only.\n"
        "The previous response failed validation.\n"
        "Validation errors:\n"
        f"{errors_text}\n"
        "Previous response:\n"
        f"{raw_response}"
    )


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cost_from_usage(usage: dict[str, Any]) -> float | None:
    for field in ("cost_usd", "cost"):
        raw_value = usage.get(field)
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            continue
        value = float(raw_value)
        if math.isfinite(value) and value >= 0:
            return value
    return None


def _normalize_usage(usage: dict[str, Any]) -> dict[str, int | float | None]:
    prompt_tokens = _to_int(usage.get("prompt_tokens"))
    completion_tokens = _to_int(usage.get("completion_tokens"))
    total_tokens = _to_int(
        usage.get("total_tokens"),
        default=prompt_tokens + completion_tokens,
    )
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": _cost_from_usage(usage),
    }


def _aggregate_usage(
    usages: list[dict[str, int | float | None]],
) -> tuple[int, int, int, float | None]:
    prompt_tokens = sum(int(usage["prompt_tokens"]) for usage in usages)
    completion_tokens = sum(int(usage["completion_tokens"]) for usage in usages)
    total_tokens = sum(int(usage["total_tokens"]) for usage in usages)
    costs = [usage["cost_usd"] for usage in usages]
    if any(cost is None for cost in costs):
        return prompt_tokens, completion_tokens, total_tokens, None
    cost_usd = sum(float(cost) for cost in costs)
    return prompt_tokens, completion_tokens, total_tokens, cost_usd


class StructuredGenerator:
    """Generate a schema- and domain-validated response with one repair."""

    def __init__(
        self,
        generate_once: GenerateOnce,
        *,
        mode_override: StructuredOutputMode | None = None,
    ) -> None:
        self._generate_once = generate_once
        self._mode_override = mode_override

    def generate(
        self,
        prompt: str,
        schema: ResponseSchema,
        context: CallContext,
    ) -> StructuredResult:
        """Generate once, then repair exactly once when validation fails."""
        mode = resolve_output_mode(context.model, self._mode_override)
        if mode is StructuredOutputMode.STRICT_JSON_SCHEMA:
            text_format = _strict_text_format(schema)
        elif mode is StructuredOutputMode.JSON_OBJECT:
            text_format = {"type": "json_object"}
        else:
            text_format = None
        request_prompt = (
            _qwen_prompt(prompt, schema)
            if mode
            in {
                StructuredOutputMode.JSON_OBJECT,
                StructuredOutputMode.PROMPT_ONLY,
            }
            else prompt
        )

        raw_response, raw_usage = self._generate_once(request_prompt, text_format)
        usages = [_normalize_usage(raw_usage)]
        data, validation_errors = _decode_and_validate(raw_response, schema)
        if data is not None:
            return self._result(
                data=data,
                raw_response=raw_response,
                schema=schema,
                schema_valid=True,
                repair_attempted=False,
                repair_succeeded=False,
                usages=usages,
            )

        repair_prompt = _repair_prompt(prompt, validation_errors, raw_response)
        if mode in {
            StructuredOutputMode.JSON_OBJECT,
            StructuredOutputMode.PROMPT_ONLY,
        }:
            repair_prompt = _qwen_prompt(repair_prompt, schema)
        repair_response, repair_usage = self._generate_once(
            repair_prompt,
            text_format,
        )
        usages.append(_normalize_usage(repair_usage))
        repaired_data, repair_errors = _decode_and_validate(repair_response, schema)
        if repaired_data is None:
            detail = "; ".join(repair_errors)
            raise StructuredGenerationError(
                f"Structured-output repair failed validation: {detail}"
            )

        return self._result(
            data=repaired_data,
            raw_response=repair_response,
            schema=schema,
            schema_valid=False,
            repair_attempted=True,
            repair_succeeded=True,
            usages=usages,
        )

    @staticmethod
    def _result(
        *,
        data: dict[str, Any],
        raw_response: str,
        schema: ResponseSchema,
        schema_valid: bool,
        repair_attempted: bool,
        repair_succeeded: bool,
        usages: list[dict[str, int | float | None]],
    ) -> StructuredResult:
        prompt_tokens, completion_tokens, total_tokens, cost_usd = _aggregate_usage(
            usages
        )
        return StructuredResult(
            data=data,
            raw_response=raw_response,
            schema_name=schema.name,
            schema_valid=schema_valid,
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
        )


__all__ = [
    "StructuredGenerationError",
    "StructuredGenerator",
    "UnsupportedStructuredOutputModel",
    "resolve_output_mode",
]
