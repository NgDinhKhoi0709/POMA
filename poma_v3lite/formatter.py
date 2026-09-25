"""Stage 4 rule formatter: cheap, deterministic clean-up of a model answer.

Scope is deliberately narrow. ``evaluation.normalization.normalize_text`` — the frozen scorer —
already lowercases, NFC-normalizes, collapses whitespace and strips trailing periods, so rules that
only redo that work cannot change any score. What it does *not* touch is markdown emphasis,
surrounding quotes, bracketed citations and leading connector words, and those are what this module
removes.

Two rules were considered and rejected after checking the gold answers of train and dev:

* **Decimal separator.** Gold uses both ``.`` and ``,`` as the decimal mark (train: 132 vs 29), and
  ``.`` also serves as the thousands separator (``1.400.012``). No rewrite is safe.
* **Unit carry-over** (``2`` -> ``2 năm``). A formatter cannot know the unit the annotator chose;
  train has only 140/7928 answers of the ``number + unit`` shape, so guessing would lose more than
  it gains.

The rules are frozen before the arms are scored. They were written from train/dev conventions and
from the scorer's semantics, not from test predictions.
"""

from __future__ import annotations

import re
import unicodedata

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)
_CODE = re.compile(r"`+(.+?)`+", re.S)
_CITATION = re.compile(r"\s*\[(?:\d+|[a-z]|ghi chú \d+|cần dẫn nguồn)\]", re.I)
_QUOTES = "\"'“”‘’«»"
# Connector words the model prepends to an otherwise correct short answer.
_LEAD = re.compile(
    r"^(?:đáp án|câu trả lời|trả lời|kết quả)(?:\s+là)?\s*[:\-–]\s*|"
    r"^(?:đáp án|câu trả lời|trả lời|kết quả)\s+là\s+",
    re.I,
)
_TRAILING_PUNCT = ".,;:!?"


def format_answer(answer: str | None) -> str:
    """Return the answer with formatting noise removed; ``Null`` and empties become ``Null``."""
    if answer is None:
        return "Null"
    text = unicodedata.normalize("NFC", str(answer)).strip()
    if not text or text.lower() in {"null", "none", "n/a", "na"}:
        return "Null"

    text = _BOLD.sub(r"\1", text)
    text = _ITALIC.sub(r"\1", text)
    text = _CODE.sub(r"\1", text)
    text = _CITATION.sub("", text)
    text = _LEAD.sub("", text).strip()

    # Strip symmetric wrapping quotes, but never a quote that is part of the answer itself.
    while len(text) >= 2 and text[0] in _QUOTES and text[-1] in _QUOTES:
        text = text[1:-1].strip()

    text = " ".join(text.split())
    # The scorer strips trailing periods only; drop the other sentence punctuation too.
    text = text.rstrip(_TRAILING_PUNCT).rstrip()
    return text or "Null"


def format_candidates(answers: list[str] | None) -> list[str]:
    """Format every candidate, drop the ones that collapse to ``Null``, keep order, dedupe.

    Dropping ``Null`` is a *selection* policy, not clean-up: when POMA's specialists disagree and the
    first one abstains, this promotes the second candidate. On the full test split that won 4
    questions and lost 2, one of which had ``Null`` as the gold answer. Callers that need the
    solver's own ordering preserved should format each candidate with ``format_answer`` instead.
    """
    formatted: list[str] = []
    seen: set[str] = set()
    for answer in answers or []:
        value = format_answer(answer)
        if value == "Null":
            continue
        if value not in seen:
            seen.add(value)
            formatted.append(value)
    return formatted
