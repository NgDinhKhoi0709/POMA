"""Parse model JSON output with reasoning + final_answer."""

from __future__ import annotations

from typing import Tuple

from .utils.json_parser import parse_json_response


def parse_reasoning_final_answer(raw: str) -> Tuple[bool, str, str]:
    """
    Parse LLM output for keys reasoning and final_answer.

    Returns (parse_ok, reasoning, final_answer).
    On failure: parse_ok False, reasoning "", final_answer from last non-empty line heuristic.
    """
    text = raw or ""
    data = parse_json_response(text)
    if data.get("_parse_failed"):
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        fallback = lines[-1] if lines else ""
        return False, "", fallback

    reasoning = data.get("reasoning")
    final_answer = data.get("final_answer")
    rs = str(reasoning).strip() if reasoning is not None else ""
    fa = str(final_answer).strip() if final_answer is not None else ""
    return True, rs, fa
