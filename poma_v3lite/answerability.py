"""Stage 3: the answerability gate, the only component allowed to emit ``Null``.

Motivation, measured on the 992-question test split with the frozen D01 scorer and the existing
one-answer artifacts: ``few_shot_gsa`` answers ``Null`` on 73 questions but only 35 of them are
really unanswerable (precision 0.48, recall 0.78). The 38 false ``Null``s are 3.8 EM points that no
table representation or row-selection change can reach.

The gate fires only when the solver already produced ``Null``, so it costs two extra LLM calls on
roughly 7% of questions. It runs in two steps, with a deterministic table search between them:

1. ``IdentifyMissingEvidence`` (LLM) names the entities or column headers that would have to exist
   in the table for the question to be answerable.
2. ``search_rows`` (no LLM) pulls the rows that mention them.
3. ``ReAnswerOrConfirmNull`` (LLM) either answers from those cited rows or confirms ``Null``.

A step that fails or returns nothing leaves the original ``Null`` in place. That protects against
*technical* failure only. The gate has a real damage mode: it cannot tell a false ``Null`` from a
true one, and 45 of the 992 test golds really are ``Null``, so every replacement risks destroying a
correct abstention. Measured on the full test split, 16 replacements broke down as 5 correct
recoveries, 4 destroyed true ``Null``s and 7 wrong answers that stayed wrong — a replacement
precision of 5/16.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from poma_v3lite.formatter import format_answer
from poma_v3lite.table_search import render_rows, search_rows

MISSING_EVIDENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["needed_evidence"],
    "properties": {
        "needed_evidence": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {"type": "string"},
            "description": "Tên thực thể hoặc tiêu đề cột cần tìm trong bảng",
        }
    },
}

REANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answerable", "final_answer"],
    "properties": {
        "answerable": {"type": "boolean"},
        "final_answer": {"type": "string"},
        "cited_cells": {"type": "array", "items": {"type": "string"}},
    },
}

MISSING_EVIDENCE_PROMPT = """Một hệ thống hỏi đáp bảng đã trả lời "Null" (không trả lời được) cho câu hỏi dưới đây.
Nhiệm vụ của bạn KHÔNG phải trả lời câu hỏi. Hãy liệt kê những bằng chứng cần có trong bảng để trả lời được:
tên thực thể (người, nơi chốn, năm, sản phẩm...) hoặc tiêu đề cột được nhắc tới trong câu hỏi.

Chỉ liệt kê cụm từ ngắn, lấy nguyên văn từ câu hỏi nếu có. Tối đa 5 mục.

CAU HOI: {question}

Trả về JSON đúng schema."""

REANSWER_PROMPT = """Bạn nhận một câu hỏi về bảng và các hàng có liên quan được trích từ bảng.
Một lần trả lời trước đó đã nói "Null" (không trả lời được). Hãy kiểm tra lại.

- Nếu các hàng dưới đây đủ để trả lời, đặt answerable = true và điền final_answer ngắn gọn, đúng như giá trị trong bảng.
- Nếu thật sự không đủ dữ liệu, đặt answerable = false và để final_answer = "Null".
- Không suy đoán ngoài bảng.

BANG (các hàng liên quan):
{table}

CAU HOI: {question}

Trả về JSON đúng schema."""


@dataclass
class GateResult:
    """Outcome of one gate run; ``answer`` is what the pipeline should use."""

    answer: str
    fired: bool = False
    changed: bool = False
    needed_evidence: list[str] = field(default_factory=list)
    rows_found: int = 0
    error: str | None = None
    calls: int = 0


def run_gate(
    question: str,
    table_data: dict[str, Any],
    answer: str | None,
    *,
    generate_json: Callable[[str, dict, str], dict],
    max_rows: int = 12,
) -> GateResult:
    """Re-examine a ``Null`` answer. ``generate_json(prompt, schema, step_name) -> dict``."""
    current = format_answer(answer)
    if current != "Null":
        return GateResult(answer=current)

    result = GateResult(answer="Null", fired=True)
    try:
        payload = generate_json(
            MISSING_EVIDENCE_PROMPT.format(question=question.strip()),
            MISSING_EVIDENCE_SCHEMA,
            "IdentifyMissingEvidence",
        )
        result.calls += 1
        queries = [str(item).strip() for item in payload.get("needed_evidence", []) if str(item).strip()]
        result.needed_evidence = queries
        if not queries:
            return result

        indices = search_rows(table_data, queries, max_rows=max_rows)
        result.rows_found = len(indices)
        if not indices:
            return result

        payload = generate_json(
            REANSWER_PROMPT.format(table=render_rows(table_data, indices), question=question.strip()),
            REANSWER_SCHEMA,
            "ReAnswerOrConfirmNull",
        )
        result.calls += 1
        if not payload.get("answerable"):
            return result
        candidate = format_answer(payload.get("final_answer"))
        if candidate == "Null":
            return result
        result.answer = candidate
        result.changed = True
    except Exception as exc:  # a failed gate must leave the solver's Null untouched
        result.error = f"{type(exc).__name__}: {exc}"[:300]
    return result
