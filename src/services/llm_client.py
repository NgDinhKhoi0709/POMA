"""
Thin wrapper around the existing ``baseline.llm_client`` so the
multi-agent pipeline reuses the same key-rotation / retry logic.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from baseline.llm_client import GenConfig, LLMZeroShotClient

from src.config.settings import LLMConfig, get_settings
from src.errors import LLMContractError

_shared_client: Optional[LLMZeroShotClient] = None
logger = logging.getLogger(__name__)
_RAW_RESPONSE_PREVIEW_CHARS = 500
_PROMPT_PREVIEW_CHARS = 500
_RAW_DUMP_LOCK = threading.Lock()
_JSON_CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _get_shared_client() -> LLMZeroShotClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = LLMZeroShotClient()
    return _shared_client


def _sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return sanitized or "unknown"


def _preview_raw_response(raw: str) -> str:
    compact = " ".join(raw.split())
    if len(compact) <= _RAW_RESPONSE_PREVIEW_CHARS:
        return compact
    return compact[: _RAW_RESPONSE_PREVIEW_CHARS - 3] + "..."


def _preview_prompt(prompt: str) -> str:
    compact = " ".join(prompt.split())
    if len(compact) <= _PROMPT_PREVIEW_CHARS:
        return compact
    return compact[: _PROMPT_PREVIEW_CHARS - 3] + "..."


def _extract_json_candidate(raw: str) -> Optional[str]:
    stripped = raw.strip()
    fence_match = _JSON_CODE_FENCE_RE.match(stripped)
    if fence_match:
        return fence_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1].strip()
    return None


def _extract_labeled_json_fallback(raw: str) -> Optional[Dict[str, Any]]:
    fields: Dict[str, str] = {}
    label = r"(?:\*\*)?(answer|evidence|confidence|reason|note)(?:\*\*)?\s*:"
    matches = list(re.finditer(label, raw, flags=re.IGNORECASE))
    if not matches:
        return None

    for index, match in enumerate(matches):
        name = match.group(1).lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[start:end].strip()
        if name != "note" and value:
            fields[name] = value

    required = {"answer", "evidence", "confidence", "reason"}
    if not required.issubset(fields):
        return None

    evidence_text = fields["evidence"]
    quoted_evidence = [
        item.strip()
        for item in re.findall(r'"([^"]+)"', evidence_text)
        if item.strip()
    ]
    if quoted_evidence:
        evidence: List[str] = quoted_evidence
    elif evidence_text in {"[]", ""}:
        evidence = []
    else:
        evidence = [evidence_text.strip()]

    confidence_match = re.search(r"-?\d+(?:\.\d+)?", fields["confidence"])
    if not confidence_match:
        return None

    return {
        "answer": fields["answer"].strip().strip('"'),
        "evidence": evidence,
        "confidence": float(confidence_match.group(0)),
        "reason": fields["reason"].strip().strip('"'),
    }


def _strip_jsonish_string(raw: str) -> str:
    text = raw.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1]
    return text.replace('\\"', '"').strip()


def _parse_jsonish_evidence_list(raw: str) -> Optional[List[str]]:
    text = raw.strip()
    if not text:
        return []
    try:
        parsed = json.loads(f"[{text}]")
    except json.JSONDecodeError:
        pass
    else:
        if isinstance(parsed, list) and all(isinstance(item, str) and item.strip() for item in parsed):
            return [item.strip() for item in parsed]
        return None

    # Tolerate the common model error where one evidence string contains raw
    # double quotes copied from a table cell, e.g. ..."It's You"... .
    if text.startswith('"') and text.endswith('"'):
        item = _strip_jsonish_string(text)
        return [item] if item else None
    return None


def _extract_specialist_jsonish_fallback(raw: str) -> Optional[Dict[str, Any]]:
    candidate = _extract_json_candidate(raw) or raw.strip()
    answer_match = re.search(
        r'"answer"\s*:\s*(null|"(?:\\.|[^"\\])*"|[^,\n}]+)',
        candidate,
        flags=re.DOTALL | re.IGNORECASE,
    )
    evidence_match = re.search(
        r'"evidence"\s*:\s*\[(.*?)\]\s*,\s*"confidence"',
        candidate,
        flags=re.DOTALL | re.IGNORECASE,
    )
    confidence_match = re.search(
        r'"confidence"\s*:\s*(-?\d+(?:\.\d+)?)',
        candidate,
        flags=re.IGNORECASE,
    )
    reason_match = re.search(
        r'"reason"\s*:\s*("(?:\\.|[^"\\])*"|[^}\n]+)',
        candidate,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not (answer_match and evidence_match and confidence_match and reason_match):
        return None

    answer_raw = answer_match.group(1).strip()
    answer: Any
    if answer_raw.lower() == "null":
        answer = None
    else:
        answer = _strip_jsonish_string(answer_raw)

    evidence = _parse_jsonish_evidence_list(evidence_match.group(1))
    if evidence is None:
        return None

    return {
        "answer": answer,
        "evidence": evidence,
        "confidence": float(confidence_match.group(1)),
        "reason": _strip_jsonish_string(reason_match.group(1)),
    }


def _parse_json_object_from_raw(raw: str) -> Dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError("LLM response must be a JSON object")
    return parsed


def _parse_json_object_with_candidate(raw: str) -> Dict[str, Any]:
    try:
        return _parse_json_object_from_raw(raw)
    except json.JSONDecodeError:
        candidate = _extract_json_candidate(raw)
        if candidate and candidate != raw.strip():
            return _parse_json_object_from_raw(candidate)
        raise


def _build_json_repair_prompt(original_prompt: str, raw_response: str) -> str:
    return (
        "Bạn là bộ sửa định dạng JSON cho một pipeline tự động.\n"
        "Nhiệm vụ: chuyển RAW_RESPONSE thành đúng một JSON object hợp lệ theo schema "
        "và yêu cầu trong ORIGINAL_PROMPT.\n"
        "Không thêm markdown, không giải thích, không thêm text ngoài JSON.\n"
        "Không thay đổi ý nghĩa dữ liệu nếu RAW_RESPONSE đã chứa dữ liệu có ích.\n"
        "Nếu RAW_RESPONSE không chứa dữ liệu có ích, hãy dựa vào ORIGINAL_PROMPT để tạo "
        "má»™t JSON object há»£p lá»‡ tá»‘i thiá»ƒu theo schema, khĂ´ng tráº£ lá»i cĂ¢u há»i.\n\n"
        "ORIGINAL_PROMPT:\n"
        "<<<ORIGINAL_PROMPT\n"
        f"{original_prompt}\n"
        "ORIGINAL_PROMPT>>>\n\n"
        "RAW_RESPONSE:\n"
        "<<<RAW_RESPONSE\n"
        f"{raw_response}\n"
        "RAW_RESPONSE>>>\n\n"
        "Chá»‰ tráº£ vá» JSON object há»£p lá»‡:"
    )


def _dump_raw_response(
    raw: str,
    *,
    model: str,
    reason: str,
    qa_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    prompt_name: Optional[str] = None,
    response_format: Optional[str] = None,
) -> Path | None:
    dump_dir = (
        get_settings().project_root
        / "outputs"
        / "debug"
        / "llm_contract_errors"
    )
    resolved_qa_id = (qa_id or "").strip() or "no_qid"
    filename = f"{_sanitize_filename(resolved_qa_id)}_{_sanitize_filename(model)}.txt"
    dump_path = dump_dir / filename
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    entry = (
        "\n" + "=" * 80 + "\n"
        f"timestamp={timestamp}\n"
        f"qa_id={resolved_qa_id}\n"
        f"reason={reason}\n"
        f"model={model}\n"
        f"agent_name={(agent_name or 'unknown')}\n"
        f"prompt_name={(prompt_name or '')}\n"
        f"response_format={(response_format or 'unknown')}\n"
        "raw_response:\n"
        f"{raw}\n"
    )

    try:
        with _RAW_DUMP_LOCK:
            dump_dir.mkdir(parents=True, exist_ok=True)
            with dump_path.open("a", encoding="utf-8") as handle:
                handle.write(entry)
    except OSError:
        logger.exception(
            "Failed to dump raw LLM response "
            "(reason=%s, model=%s, qa_id=%s)",
            reason,
            model,
            resolved_qa_id,
        )
        return None

    return dump_path


def _log_contract_error(
    raw: str,
    *,
    model: str,
    reason: str,
    qa_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    prompt_name: Optional[str] = None,
    response_format: Optional[str] = None,
    dump_path: Path | None = None,
) -> Path | None:
    resolved_dump_path = dump_path or _dump_raw_response(
        raw,
        model=model,
        reason=reason,
        qa_id=qa_id,
        agent_name=agent_name,
        prompt_name=prompt_name,
        response_format=response_format,
    )
    preview = _preview_raw_response(raw)

    if resolved_dump_path is None:
        logger.error(
            "LLM contract error (%s) from model %s. "
            "Raw response dump failed. Preview: %s",
            reason,
            model,
            preview,
        )
        return None

    logger.error(
        "LLM contract error (%s) from model %s. "
        "Raw response dumped to %s. Preview: %s",
        reason,
        model,
        resolved_dump_path,
        preview,
    )
    return resolved_dump_path


MODEL_PRICING = {
    # model_name_substring: (input_cost_per_token, output_cost_per_token)
    "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
    "gpt-3.5-turbo": (0.50 / 1_000_000, 1.50 / 1_000_000),
}


def calculate_call_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    model_lower = model.lower()
    if "/" in model_lower:
        _, model_name = model_lower.split("/", 1)
    else:
        model_name = model_lower

    input_price, output_price = MODEL_PRICING["gpt-4o-mini"]  # default fallback
    for name, prices in MODEL_PRICING.items():
        if name in model_name:
            input_price, output_price = prices
            break

    return (prompt_tokens * input_price) + (completion_tokens * output_price)


def _usage_cost_usd(model: str, usage: Dict[str, Any]) -> float:
    provided_cost = usage.get("cost_usd", usage.get("cost"))
    if provided_cost is not None:
        try:
            return float(provided_cost)
        except (TypeError, ValueError):
            pass
    return calculate_call_cost(model, usage["prompt_tokens"], usage["completion_tokens"])


class LLMClient:
    """Agent-facing LLM interface.

    Wraps ``LLMZeroShotClient`` and adds structured JSON output parsing.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self._cfg = config or get_settings().llm
        self._client = _get_shared_client()
        self._call_logs: List[Dict[str, Any]] = []
        self._call_logs_lock = threading.Lock()
        self._call_index = 0
        self._qa_id: Optional[str] = None
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_total_tokens = 0
        self.total_cost_usd = 0.0

    def set_qa_id(self, qa_id: Optional[str]) -> None:
        if qa_id is None:
            self._qa_id = None
            return
        text = str(qa_id).strip()
        self._qa_id = text or None

    def _last_usage_or_estimate(self, prompt: str, raw: str) -> Dict[str, Any]:
        usage = getattr(self._client, "_thread_local", None)
        last_usage = getattr(usage, "last_usage", None) if usage else None
        if last_usage:
            return last_usage

        prompt_est = max(1, int(len(prompt.split()) * 1.4))
        comp_est = max(1, int(len(raw.split()) * 1.4))
        return {
            "prompt_tokens": prompt_est,
            "completion_tokens": comp_est,
            "total_tokens": prompt_est + comp_est,
        }

    def _record_usage_totals(self, usage: Dict[str, Any]) -> None:
        cost_usd = _usage_cost_usd(self._cfg.model, usage)

        self.total_prompt_tokens += usage["prompt_tokens"]
        self.total_completion_tokens += usage["completion_tokens"]
        self.total_total_tokens += usage["total_tokens"]
        self.total_cost_usd += cost_usd

    def _record_call(self, payload: Dict[str, Any]) -> None:
        with self._call_logs_lock:
            self._call_index += 1
            self._call_logs.append({"call_index": self._call_index, **payload})

    def get_call_logs(self) -> List[Dict[str, Any]]:
        with self._call_logs_lock:
            return [dict(item) for item in self._call_logs]

    def _generate_raw_text(self, prompt: str) -> str:
        gen_cfg = GenConfig(
            temperature=self._cfg.temperature,
            top_p=self._cfg.top_p,
            max_tokens=self._cfg.max_tokens,
            timeout=self._cfg.timeout,
            openrouter_provider=self._cfg.openrouter_provider,
        )
        return self._client.generate(
            model=self._cfg.model,
            prompt=prompt,
            config=gen_cfg,
            max_retries=self._cfg.max_retries,
            retry_delay=self._cfg.retry_delay,
        )

    def generate_text(
        self,
        prompt: str,
        *,
        agent_name: Optional[str] = None,
        prompt_name: Optional[str] = None,
    ) -> str:
        raw = self._generate_raw_text(prompt)
        
        usage = getattr(self._client, "_thread_local", None)
        last_usage = getattr(usage, "last_usage", None) if usage else None
        if not last_usage:
            prompt_est = max(1, int(len(prompt.split()) * 1.4))
            comp_est = max(1, int(len(raw.split()) * 1.4))
            last_usage = {
                "prompt_tokens": prompt_est,
                "completion_tokens": comp_est,
                "total_tokens": prompt_est + comp_est,
            }
            
        cost_usd = _usage_cost_usd(self._cfg.model, last_usage)
        
        self.total_prompt_tokens += last_usage["prompt_tokens"]
        self.total_completion_tokens += last_usage["completion_tokens"]
        self.total_total_tokens += last_usage["total_tokens"]
        self.total_cost_usd += cost_usd

        _dump_raw_response(
            raw,
            model=self._cfg.model,
            reason="pre_parse_text",
            qa_id=self._qa_id,
            agent_name=agent_name,
            prompt_name=prompt_name,
            response_format="text",
        )
        self._record_call(
            {
                "agent_name": agent_name or "unknown",
                "prompt_name": prompt_name or "",
                "response_format": "text",
                "model": self._cfg.model,
                "prompt_preview": _preview_prompt(prompt),
                "raw_response": raw,
            }
        )
        return raw

    def generate_json(
        self,
        prompt: str,
        *,
        agent_name: Optional[str] = None,
        prompt_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw = self._generate_raw_text(prompt)
        self._record_usage_totals(self._last_usage_or_estimate(prompt, raw))

        pre_parse_dump_path = _dump_raw_response(
            raw,
            model=self._cfg.model,
            reason="pre_parse_json",
            qa_id=self._qa_id,
            agent_name=agent_name,
            prompt_name=prompt_name,
            response_format="json",
        )
        call_payload: Dict[str, Any] = {
            "agent_name": agent_name or "unknown",
            "prompt_name": prompt_name or "",
            "response_format": "json",
            "model": self._cfg.model,
            "prompt_preview": _preview_prompt(prompt),
            "raw_response": raw,
        }
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            candidate = _extract_json_candidate(raw)
            if candidate and candidate != raw.strip():
                try:
                    parsed = _parse_json_object_from_raw(candidate)
                    call_payload["json_recovered_from"] = "wrapped_response"
                except (json.JSONDecodeError, TypeError):
                    pass
                else:
                    call_payload["parsed_response"] = parsed
                    self._record_call(call_payload)
                    return parsed

            parsed = _extract_labeled_json_fallback(raw)
            if parsed is not None:
                call_payload["json_recovered_from"] = "labeled_response"
                call_payload["parsed_response"] = parsed
                self._record_call(call_payload)
                return parsed

            parsed = _extract_specialist_jsonish_fallback(raw)
            if parsed is not None:
                call_payload["json_recovered_from"] = "jsonish_specialist_response"
                call_payload["parsed_response"] = parsed
                self._record_call(call_payload)
                return parsed

            repair_prompt = _build_json_repair_prompt(prompt, raw)
            repair_raw = self._generate_raw_text(repair_prompt)
            self._record_usage_totals(self._last_usage_or_estimate(repair_prompt, repair_raw))
            call_payload["repair_response"] = repair_raw
            _dump_raw_response(
                repair_raw,
                model=self._cfg.model,
                reason="pre_parse_json_repair",
                qa_id=self._qa_id,
                agent_name=agent_name,
                prompt_name=prompt_name,
                response_format="json",
            )
            try:
                parsed = _parse_json_object_with_candidate(repair_raw)
            except (json.JSONDecodeError, TypeError):
                parsed = _extract_specialist_jsonish_fallback(repair_raw)
                if parsed is not None:
                    call_payload["json_recovered_from"] = "repair_jsonish_specialist_response"
                    call_payload["parsed_response"] = parsed
                    self._record_call(call_payload)
                    return parsed
            else:
                call_payload["json_recovered_from"] = "repair_retry"
                call_payload["parsed_response"] = parsed
                self._record_call(call_payload)
                return parsed

            call_payload["error"] = "invalid_json"
            self._record_call(call_payload)
            dump_path = _log_contract_error(
                raw,
                model=self._cfg.model,
                reason="invalid_json",
                qa_id=self._qa_id,
                agent_name=agent_name,
                prompt_name=prompt_name,
                response_format="json",
                dump_path=pre_parse_dump_path,
            )
            detail = "LLM response was not valid JSON"
            if dump_path is not None:
                detail = f"{detail}; raw response dumped to {dump_path}"
            raise LLMContractError(detail) from exc

        if not isinstance(parsed, dict):
            call_payload["error"] = "non_object_json"
            call_payload["parsed_response"] = parsed
            self._record_call(call_payload)
            dump_path = _log_contract_error(
                raw,
                model=self._cfg.model,
                reason="non_object_json",
                qa_id=self._qa_id,
                agent_name=agent_name,
                prompt_name=prompt_name,
                response_format="json",
                dump_path=pre_parse_dump_path,
            )
            detail = "LLM response must be a JSON object"
            if dump_path is not None:
                detail = f"{detail}; raw response dumped to {dump_path}"
            raise LLMContractError(detail)

        call_payload["parsed_response"] = parsed
        self._record_call(call_payload)
        return parsed
