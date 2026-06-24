"""Parse JSON from LLM responses (markdown blocks, surrounding text, common fixes)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON from an LLM response; return dict or fallback with _parse_failed."""
    if not response:
        return {}

    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    json_from_block = _extract_json_from_code_block(response)
    if json_from_block is not None:
        return json_from_block

    json_from_text = _extract_json_from_text(response)
    if json_from_text is not None:
        return json_from_text

    json_fixed = _try_fix_json(response)
    if json_fixed is not None:
        return json_fixed

    return {"_raw_text": response, "_parse_failed": True}


def _extract_json_from_code_block(text: str) -> Optional[Dict[str, Any]]:
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    return None


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        return None

    potential_json = text[first_brace : last_brace + 1]

    try:
        return json.loads(potential_json)
    except json.JSONDecodeError:
        return _extract_with_brace_matching(text, first_brace)


def _extract_with_brace_matching(text: str, start: int) -> Optional[Dict[str, Any]]:
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                potential_json = text[start : i + 1]
                try:
                    return json.loads(potential_json)
                except json.JSONDecodeError:
                    return None

    return None


def _try_fix_json(text: str) -> Optional[Dict[str, Any]]:
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace == -1 or last_brace == -1:
        return None

    json_str = text[first_brace : last_brace + 1]

    fixes = [
        (r",\s*}", "}"),
        (r",\s*]", "]"),
        (r"'([^']*)':", r'"\1":'),
        (r":\s*'([^']*)'", r': "\1"'),
        (r"(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":'),
        (r"\bTrue\b", "true"),
        (r"\bFalse\b", "false"),
        (r"\bNone\b", "null"),
    ]

    for pattern, replacement in fixes:
        json_str = re.sub(pattern, replacement, json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def safe_get(data: Dict[str, Any], *keys, default: Any = None) -> Any:
    """Safely get nested value from a dictionary."""
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current
