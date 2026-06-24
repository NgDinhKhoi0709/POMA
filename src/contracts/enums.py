"""
Canonical hint vocabulary and alias mapping.

Every hint that enters the Router MUST be one of the ``HintType`` values.
Upstream aliases (e.g. ``"Mathematical Reasoning"``) are normalised by
``QuestionRefiner`` via ``HINT_ALIASES_TO_CANONICAL``.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class HintType(str, Enum):
    WHAT = "What"
    WHERE = "Where"
    WHO = "Who"
    WHEN = "When"
    WHY = "Why"
    HOW = "How"
    YES_NO = "YesNo"
    LIST = "List"
    MATHEMATICAL_REASONING = "MathematicalReasoning"
    MULTI_CONDITIONS = "MultiConditions"


HINT_ALIASES_TO_CANONICAL: Dict[str, str] = {
    # English canonical + common short aliases
    "What": HintType.WHAT.value,
    "what": HintType.WHAT.value,
    "Where": HintType.WHERE.value,
    "where": HintType.WHERE.value,
    "Who": HintType.WHO.value,
    "who": HintType.WHO.value,
    "When": HintType.WHEN.value,
    "when": HintType.WHEN.value,
    "Why": HintType.WHY.value,
    "why": HintType.WHY.value,
    "How": HintType.HOW.value,
    "how": HintType.HOW.value,
    "Yes/No": HintType.YES_NO.value,
    "yes/no": HintType.YES_NO.value,
    "YesNo": HintType.YES_NO.value,
    "List": HintType.LIST.value,
    "list": HintType.LIST.value,
    "Mathematical Reasoning": HintType.MATHEMATICAL_REASONING.value,
    "mathematical reasoning": HintType.MATHEMATICAL_REASONING.value,
    "MathematicalReasoning": HintType.MATHEMATICAL_REASONING.value,
    "Multi-conditions": HintType.MULTI_CONDITIONS.value,
    "Multi-Conditions": HintType.MULTI_CONDITIONS.value,
    "multi-conditions": HintType.MULTI_CONDITIONS.value,
    "MultiConditions": HintType.MULTI_CONDITIONS.value,
    # Vietnamese dataset hint descriptions (Open-ViTabQA)
    "Cái gì, cái nào, công ty nào,... hoặc những từ đồng nghĩa (What)": HintType.WHAT.value,
    "Ở đâu, trong thành phố nào, ở nước nào,... hoặc những từ đồng nghĩa (Where)": HintType.WHERE.value,
    "Ai, người nào,... hoặc những từ đồng nghĩa (Who)": HintType.WHO.value,
    "Khi nào, thời gian nào, ... hoặc những từ đồng nghĩa (When)": HintType.WHEN.value,
    "Vì sao, tại sao,... hoặc những từ đồng nghĩa (Why)": HintType.WHY.value,
    "Làm thế nào, như thế nào, bằng cách nào,... hoặc những từ đồng nghĩa (How)": HintType.HOW.value,
    "Câu hỏi Yes/No": HintType.YES_NO.value,
    "Sử dụng yêu cầu liệt kê, sắp xếp": HintType.LIST.value,
    "Sử dụng tính toán": HintType.MATHEMATICAL_REASONING.value,
    "Sử dụng hỏi kết hợp giữa các ô, các hàng, các cột": HintType.MULTI_CONDITIONS.value,
}

HINT_TO_AGENT: Dict[str, str] = {h.value: h.value for h in HintType}
