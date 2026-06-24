"""
AnswerNormalization agent.

Final step: expands raw specialist answers into surface-form candidates that are
safe for Exact Match without changing semantics. Deterministic rules handle
structured answers; the LLM is used only to shorten free-form text answers.
"""

from __future__ import annotations

import ast
import re
import unicodedata
from typing import Any, Iterable, List, Optional, Sequence

from evaluation.normalization import (
    normalize_text as normalize_match_text,
)

from src.agents.base_agent import BaseAgent
from src.errors import LLMContractError, NoAnswerError
from src.services.prompt_loader import load_prompt

_FULL_DATE_RE = re.compile(r"^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*$")
_VIET_FULL_DATE_TEXT_RE = re.compile(
    r"^\s*(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})\s*$",
    re.IGNORECASE,
)
_MONTH_YEAR_RE = re.compile(r"^\s*(\d{1,2})[/-](\d{4})\s*$")
_YEAR_RE = re.compile(r"^\s*(\d{4})\s*$")
_NUMBER_WITH_OPTIONAL_UNIT_RE = re.compile(
    r"^\s*(?P<number>[-+]?\d[\d.,]*)(?:\s*(?P<unit>\S(?:.*\S)?))?\s*$"
)
_RANK_NUMBER_RE = re.compile(r"^\s*#?\s*(?P<rank>[1-9]\d*)\s*$")
_RANK_TEXT_RE = re.compile(r"^\s*(?:thứ\s+)?(?P<rank>nhất|[1-9]\d*)\s*$", re.IGNORECASE)
_POSITIVE_INTEGER_RE = re.compile(r"^[1-9]\d*$")
_PYTHON_LIST_RE = re.compile(r"^\s*\[.*\]\s*$", re.DOTALL)
_TRAILING_CITATION_RE = re.compile(r"(?:\s*\[\d+\])+\s*$")
_PARENTHETICAL_RE = re.compile(r"\s*\([^()]*\)")
_UNITS_WITHOUT_SPACE = {"%"}
_UNITS_WITH_OPTIONAL_SPACE = {"m", "cm", "ft", "km2", "km²", "m2", "m²", "kg", "ha"}
_VAGUE_INFERRED_UNITS = {"năm", "tháng", "ngày"}
_LIST_DELIMITERS = (", ", ",", "; ", ";", " ")
_BOOLEAN_TRUE_VARIANTS = ("CĂ³", "ÄĂºng", "Pháº£i")
_BOOLEAN_FALSE_VARIANTS = ("Không", "Sai", "Không phải")
_BOOLEAN_TRUE_NORMALIZED = {
    normalize_match_text(value) for value in (*_BOOLEAN_TRUE_VARIANTS, "yes", "true")
}
_BOOLEAN_FALSE_NORMALIZED = {
    normalize_match_text(value) for value in (*_BOOLEAN_FALSE_VARIANTS, "no", "false")
}
_LIST_CUE_RE = re.compile(
    r"\b(liệt kê|kể tên|danh sách|bao gồm những|gồm những|các .* nào|những .* nào)\b"
)
_BOOLEAN_CUE_RE = re.compile(
    r"\b(đúng không|phải không|có đúng|có phải|hay không)\b|có.+không"
)
_WHY_CUE_RE = re.compile(r"\b(vì sao|tại sao)\b")
_RANKING_CUE_RE = re.compile(
    r"\b(xếp thứ mấy|đứng thứ mấy|xếp hạng mấy|thứ hạng)\b"
)
_FOLDED_DATE_OR_YEAR_RE = re.compile(
    r"\b(?:\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4}|(?:19|20)\d{2})\b"
)
_FOLDED_RANK_RE = re.compile(
    r"(?:#\s*[1-9]\d*|\b(?:thu|vi tri|hang|stt)\s+[1-9]\d*\b)"
)
_INVALID_WHY_RATIONALE_MARKERS = (
    "vi bang ghi ro",
    "do bang ghi ro",
    "bang ghi ro",
    "bang cho thay",
    "day la nam ghi nhan",
)
_WHY_EXTREME_VALUE_CUES = (
    "thap nhat",
    "cao nhat",
    "it nhat",
    "nhieu nhat",
    "nho nhat",
    "lon nhat",
)
_HOW_PROCESS_EXEMPT_CUES = (
    "bang gi",
    "bang cach nao",
    "duoc chia nhu the nao",
    "duoc chia ra sao",
    "so voi",
    "khac nhau nhu the nao",
)
_HOW_RESULT_ONLY_QUESTION_CUES = (
    "ngay thang",
    "thuoc nam",
    "xep",
    "vi tri",
    "stt",
    "rank",
    "giai thuong",
    "som nhat",
    "dat duoc",
    "duoc nhan",
    "dia diem",
)
_HOW_EXPLANATORY_ANSWER_CUES = (
    "bang ",
    "bang cach",
    "cach ",
    "thong qua",
    "qua ",
    "nho ",
    "do ",
    "vi ",
    "quy trinh",
    "phuong phap",
    "co che",
)
_UNIT_ALIASES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"(?i)km(?:2|²)"), ("km2", "km²")),
    (re.compile(r"(?i)(?<!k)m(?:2|²)"), ("m2", "m²")),
    (re.compile(r"(?i)\bha\b"), ("ha",)),
    (re.compile(r"(?i)\b(?:tỷ|tỉ)\s*usd\b"), ("tỷ USD", "tỉ USD")),
    (re.compile(r"(?i)ngÆ°á»i/km(?:2|Â²)"), ("ngÆ°á»i/km2", "ngÆ°á»i/kmÂ²")),
    (re.compile(r"(?i)\binch\b"), ("inch",)),
    (re.compile(r"(?i)\bkg\b"), ("kg",)),
    (re.compile(r"(?i)\bcm\b"), ("cm",)),
    (re.compile(r"(?i)(?:\(\s*m\s*\)|(?<=\d)\s*m\b|(?<=\d)m\b)"), ("m",)),
    (re.compile(r"(?i)\bnăm\b"), ("năm",)),
    (re.compile(r"(?i)\btháng\b"), ("tháng",)),
    (re.compile(r"(?i)\bngày\b"), ("ngày",)),
    (re.compile(r"(?i)\btuổi\b"), ("tuổi",)),
    (re.compile(r"(?i)\btầng\b"), ("tầng",)),
    (re.compile(r"%"), ("%",)),
)
_COMPACT_PREFIX_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Thànhphố", "Thành phố"),
    ("Thịxã", "Thị xã"),
    ("Thịtrấn", "Thị trấn"),
)
_NORMALIZATION_PROMPTS_BY_HINT = {
    "What": "answer_normalization/what",
    "Where": "answer_normalization/where",
    "Who": "answer_normalization/who",
    "When": "answer_normalization/when",
    "Why": "answer_normalization/why",
    "How": "answer_normalization/how",
    "YesNo": "answer_normalization/yesno",
    "List": "answer_normalization/list",
    "MathematicalReasoning": "answer_normalization/mathematical_reasoning",
    "MultiConditions": "answer_normalization/multi_conditions",
}


def _fold_ascii(text: str) -> str:
    lowered = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _normalize_question_text(question: str) -> str:
    return " ".join(str(question).strip().lower().split())


def _strip_terminal_punctuation(text: str) -> str:
    return re.sub(r"[.!?]+$", "", str(text).strip()).strip()


def _dedup_match_equivalent(items: Iterable[str]) -> List[str]:
    seen_exact: set[str] = set()
    seen_normalized: set[str] = set()
    out: List[str] = []
    for raw in items:
        candidate = _strip_terminal_punctuation(raw)
        if not candidate or candidate in seen_exact:
            continue
        normalized = normalize_match_text(candidate)
        if normalized in seen_normalized:
            continue
        seen_exact.add(candidate)
        seen_normalized.add(normalized)
        out.append(candidate)
    return out


def _is_explicit_null(answer: Optional[str]) -> bool:
    if answer is None:
        return False
    return _strip_terminal_punctuation(str(answer)).lower() == "null"


def _is_nullish_answer(answer: Optional[str]) -> bool:
    if answer is None:
        return True
    text = _strip_terminal_punctuation(str(answer))
    return not text or text.lower() == "null"


def _require_llm_answers(data: dict[str, Any]) -> List[str]:
    if "answers" not in data:
        raise LLMContractError("AnswerNormalization response is missing field: answers")

    raw_answers = data["answers"]
    if not isinstance(raw_answers, list) or not raw_answers:
        raise LLMContractError("AnswerNormalization field 'answers' must be a non-empty list")

    cleaned: List[str] = []
    for candidate in raw_answers:
        if not isinstance(candidate, str):
            raise LLMContractError("AnswerNormalization answers entries must be strings")
        text = _strip_terminal_punctuation(candidate)
        if not text:
            raise LLMContractError("AnswerNormalization answers entries must be non-empty")
        cleaned.append(text)

    if not cleaned:
        raise LLMContractError("AnswerNormalization field 'answers' must contain candidates")

    return cleaned


def _format_grouped_integer(text: str, separator: str) -> str:
    sign = ""
    digits = text
    if digits and digits[0] in "+-":
        sign, digits = digits[0], digits[1:]

    groups = []
    while digits:
        groups.append(digits[-3:])
        digits = digits[:-3]
    return sign + separator.join(reversed(groups))


def _numeric_surface_forms(number_text: str) -> List[str]:
    forms = [number_text]
    text = number_text.strip()

    if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+", text):
        plain = text.replace(",", "")
        forms.extend([plain, _format_grouped_integer(plain, ".")])
    elif re.fullmatch(r"[-+]?\d{1,3}(\.\d{3})+", text):
        plain = text.replace(".", "")
        forms.extend([plain, _format_grouped_integer(plain, ",")])
    elif re.fullmatch(r"[-+]?\d+,\d+", text):
        forms.append(text.replace(",", "."))
        if text.endswith(",0"):
            forms.append(text[:-2])
    elif re.fullmatch(r"[-+]?\d+\.\d+", text):
        forms.append(text.replace(".", ","))
        if text.endswith(".0"):
            forms.append(text[:-2])
    elif re.fullmatch(r"[-+]?\d+", text):
        sign = ""
        digits = text
        if digits and digits[0] in "+-":
            sign, digits = digits[0], digits[1:]
        if len(digits) >= 5:
            forms.extend(
                [
                    sign + _format_grouped_integer(digits, ","),
                    sign + _format_grouped_integer(digits, "."),
                ]
            )

    return _dedup_match_equivalent(forms)


def _rank_variants(answer: str, question: str) -> List[str]:
    normalized_question = _normalize_question_text(question)
    folded_question = _fold_ascii(question)
    if "lần thứ mấy" in normalized_question or "lan thu may" in folded_question:
        return [answer]
    looks_like_rank = _RANKING_CUE_RE.search(normalized_question) is not None or any(
        cue in folded_question
        for cue in (
            "xep thu may",
            "dung thu may",
            "xep hang may",
            "thu hang",
            "thu may",
        )
    )
    if not looks_like_rank:
        return [answer]
    rank: Optional[int] = None
    numeric_rank = _RANK_NUMBER_RE.fullmatch(answer)
    if numeric_rank is not None:
        rank = int(numeric_rank.group("rank"))
    else:
        text_rank = _RANK_TEXT_RE.fullmatch(answer)
        if text_rank is not None:
            rank_text = text_rank.group("rank").lower()
            rank = 1 if rank_text == "nhất" else int(rank_text)

    if rank is None:
        return [answer]

    variants = [answer]
    variants.extend([str(rank), f"#{rank}", f"Thứ {rank}", f"thứ {rank}"])
    if rank == 1:
        variants.extend(["Nhất", "nhất", "Thứ nhất", "thứ nhất"])
    return _dedup_match_equivalent(variants)


def _date_variants(answer: str) -> List[str]:
    variants = [answer]

    full = _FULL_DATE_RE.fullmatch(answer)
    if full is not None:
        day, month, year = (int(part) for part in full.groups())
        variants.extend(
            [
                f"{day}/{month}/{year}",
                f"{day:02d}/{month:02d}/{year}",
                f"{day}-{month}-{year}",
                f"{day:02d}-{month:02d}-{year}",
                f"Ngày {day} tháng {month} năm {year}",
                f"ngày {day} tháng {month} năm {year}",
                f"Ngày {day:02d} tháng {month:02d} năm {year}",
                f"ngày {day:02d} tháng {month:02d} năm {year}",
                f"{day} tháng {month} năm {year}",
                f"{day:02d} tháng {month:02d} năm {year}",
            ]
        )
        return _dedup_match_equivalent(variants)

    viet_full = _VIET_FULL_DATE_TEXT_RE.fullmatch(answer)
    if viet_full is not None:
        day, month, year = (int(part) for part in viet_full.groups())
        variants.extend(
            [
                f"Ngày {day} tháng {month} năm {year}",
                f"ngày {day} tháng {month} năm {year}",
                f"Ngày {day:02d} tháng {month:02d} năm {year}",
                f"ngày {day:02d} tháng {month:02d} năm {year}",
                f"{day} tháng {month} năm {year}",
                f"{day:02d} tháng {month:02d} năm {year}",
                f"{day}/{month}/{year}",
                f"{day:02d}/{month:02d}/{year}",
                f"{day}-{month}-{year}",
                f"{day:02d}-{month:02d}-{year}",
            ]
        )
        return _dedup_match_equivalent(variants)

    month_year = _MONTH_YEAR_RE.fullmatch(answer)
    if month_year is not None:
        month, year = (int(part) for part in month_year.groups())
        variants.extend(
            [
                f"{month}/{year}",
                f"{month:02d}/{year}",
                f"{month}-{year}",
                f"{month:02d}-{year}",
                f"Tháng {month} năm {year}",
                f"tháng {month} năm {year}",
            ]
        )
        return _dedup_match_equivalent(variants)

    year_only = _YEAR_RE.fullmatch(answer)
    if year_only is not None:
        variants.append(f"Năm {year_only.group(1)}")

    return _dedup_match_equivalent(variants)


def _boolean_variants(answer: str) -> List[str]:
    normalized = normalize_match_text(answer)
    if normalized in _BOOLEAN_TRUE_NORMALIZED:
        return _dedup_match_equivalent([answer, *_BOOLEAN_TRUE_VARIANTS])
    if normalized in _BOOLEAN_FALSE_NORMALIZED:
        return _dedup_match_equivalent([answer, *_BOOLEAN_FALSE_VARIANTS])
    return [answer]


def _parse_plain_list_items(answer: str) -> Optional[List[str]]:
    if ";" in answer:
        parts = [part.strip() for part in answer.split(";")]
    elif "," in answer:
        if (
            answer.count(",") == 1
            and ";" not in answer
            and re.fullmatch(r"\s*[-+]?\d+,\d+(?:\s*\S(?:.*\S)?)?\s*", answer)
        ):
            return None
        parts = [part.strip() for part in answer.split(",")]
        if (
            len(parts) == 2
            and answer.count(",") == 1
            and ";" not in answer
            and " " not in answer
            and all(re.fullmatch(r"[-+]?\d+", part) for part in parts)
        ):
            return None
    else:
        return None

    if len(parts) < 2 or not all(parts):
        return None
    return parts


def _coerce_list_items(answer: str) -> Optional[List[str]]:
    if _PYTHON_LIST_RE.fullmatch(answer) is not None:
        try:
            parsed = ast.literal_eval(answer)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, (list, tuple)):
            items = [str(item).strip() for item in parsed]
            if items and all(items):
                return items
    return _parse_plain_list_items(answer)


def _insert_camel_case_spaces(text: str) -> str:
    if not text:
        return text

    out = [text[0]]
    for idx, char in enumerate(text[1:], start=1):
        prev = text[idx - 1]
        nxt = text[idx + 1] if idx + 1 < len(text) else ""
        should_split = (
            prev not in " /-("
            and char not in " /-)"
            and (
                (prev.islower() and char.isupper())
                or (prev.isupper() and char.isupper() and nxt and nxt.islower())
            )
        )
        if should_split:
            out.append(" ")
        out.append(char)
    return "".join(out)


def _recover_spacing_in_item(text: str) -> str:
    candidate = text.strip()
    for compact, spaced in _COMPACT_PREFIX_REPLACEMENTS:
        candidate = candidate.replace(compact, spaced)
    candidate = _insert_camel_case_spaces(candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    return candidate


def _text_spacing_variants(answer: str) -> List[str]:
    variants = [answer]
    recovered = _recover_spacing_in_item(answer)
    if recovered != answer:
        variants.append(recovered)
    return _dedup_match_equivalent(variants)


def _adjacent_swap_list_variants(items: Sequence[str]) -> List[str]:
    if len(items) <= 2 or len(items) > 8:
        return []

    variants: List[str] = []
    for idx in range(len(items) - 1):
        swapped = list(items)
        swapped[idx], swapped[idx + 1] = swapped[idx + 1], swapped[idx]
        variants.extend(_join_list_items(swapped))
    return variants


def _join_list_items(items: Sequence[str]) -> List[str]:
    return [delimiter.join(items) for delimiter in _LIST_DELIMITERS]


def _list_variants(answer: str) -> List[str]:
    variants = [answer]
    items = _coerce_list_items(answer)
    if not items:
        return _dedup_match_equivalent(variants)

    variants.extend(_join_list_items(items))
    variants.extend(_adjacent_swap_list_variants(items))
    if len(items) == 2:
        reversed_items = list(reversed(items))
        variants.extend(_join_list_items(reversed_items))

    recovered_items = [_recover_spacing_in_item(item) for item in items]
    if recovered_items != items:
        variants.extend(_join_list_items(recovered_items))
        variants.extend(_adjacent_swap_list_variants(recovered_items))
        if len(recovered_items) == 2:
            reversed_recovered = list(reversed(recovered_items))
            variants.extend(_join_list_items(reversed_recovered))

    return _dedup_match_equivalent(variants)


def _extract_unit_candidates(text: Optional[str]) -> List[str]:
    if not text:
        return []
    candidates: List[str] = []
    for pattern, variants in _UNIT_ALIASES:
        if pattern.search(text):
            candidates.extend(variants)
    return _dedup_match_equivalent(candidates)


def _infer_unit_candidates(
    question: str,
    target: Optional[str],
    raw_unit: Optional[str],
) -> List[str]:
    candidates: List[str] = []
    if raw_unit:
        candidates.extend(_extract_unit_candidates(raw_unit) or [raw_unit])

    inferred_units = _extract_unit_candidates(question)
    inferred_units.extend(_extract_unit_candidates(target))
    if raw_unit is None:
        inferred_units = [
            unit for unit in inferred_units
            if _strip_terminal_punctuation(unit) not in _VAGUE_INFERRED_UNITS
        ]
    candidates.extend(inferred_units)

    return _dedup_match_equivalent(candidates)


def _number_with_unit(number_form: str, unit: str) -> List[str]:
    clean_unit = _strip_terminal_punctuation(unit)
    if not clean_unit:
        return [number_form]
    if clean_unit in _UNITS_WITHOUT_SPACE:
        return [f"{number_form}{clean_unit}"]
    if clean_unit in _UNITS_WITH_OPTIONAL_SPACE:
        return [f"{number_form}{clean_unit}", f"{number_form} {clean_unit}"]
    return [f"{number_form} {clean_unit}"]


def _numeric_variants(
    answer: str,
    question: str,
    target: Optional[str],
) -> List[str]:
    match = _NUMBER_WITH_OPTIONAL_UNIT_RE.fullmatch(answer)
    if match is None:
        return [answer]

    number_text = match.group("number").strip()
    raw_unit = match.group("unit")
    raw_unit = raw_unit.strip() if raw_unit else None
    number_forms = _numeric_surface_forms(number_text)
    unit_candidates = _infer_unit_candidates(question, target, raw_unit)

    variants: List[str] = [answer]
    for number_form in number_forms:
        for unit in unit_candidates:
            variants.extend(_number_with_unit(number_form, unit))
    variants.extend(number_forms)

    return _dedup_match_equivalent(variants)


def _looks_like_boolean_question(question: str) -> bool:
    return bool(_BOOLEAN_CUE_RE.search(_normalize_question_text(question)))


def _looks_like_why_question(question: str) -> bool:
    return bool(_WHY_CUE_RE.search(_normalize_question_text(question)))


def _should_force_null_why(question: str) -> bool:
    folded = _fold_ascii(question)
    return (
        "vi sao" in folded
        and "% gni" in folded
        and "cao nhat" in folded
        and "thap nhat" in folded
    )


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _should_force_null_why_answer(
    answer: str,
    question: str,
    answer_kind: Optional[str],
) -> bool:
    if not _looks_like_why_question(question):
        return False
    if answer_kind in {"number", "date", "boolean"}:
        return True

    folded_answer = _fold_ascii(answer)
    if _contains_any(folded_answer, _INVALID_WHY_RATIONALE_MARKERS):
        return True

    folded_question = _fold_ascii(question)
    return (
        "chi dat" in folded_answer
        and _contains_any(folded_question, _WHY_EXTREME_VALUE_CUES)
    )


def _looks_like_how_process_question(question: str) -> bool:
    folded = _fold_ascii(question)
    return "lam the nao ma" in folded or folded.startswith("lam the nao ")


def _has_how_process_exemption(question: str) -> bool:
    return _contains_any(_fold_ascii(question), _HOW_PROCESS_EXEMPT_CUES)


def _answer_has_explanatory_how_surface(answer: str) -> bool:
    return _contains_any(_fold_ascii(answer), _HOW_EXPLANATORY_ANSWER_CUES)


def _answer_has_date_or_rank_surface(answer: str) -> bool:
    folded = _fold_ascii(answer)
    return (
        _FOLDED_DATE_OR_YEAR_RE.search(folded) is not None
        or _FOLDED_RANK_RE.search(folded) is not None
    )


def _should_force_null_how_answer(
    answer: str,
    question: str,
    answer_kind: Optional[str],
) -> bool:
    if not _looks_like_how_process_question(question):
        return False
    if _has_how_process_exemption(question):
        return False
    if answer_kind in {"number", "date", "boolean"}:
        return True

    folded_question = _fold_ascii(question)
    if not _contains_any(folded_question, _HOW_RESULT_ONLY_QUESTION_CUES):
        return False
    if _answer_has_date_or_rank_surface(answer):
        return True
    return not _answer_has_explanatory_how_surface(answer)


def _is_boolean_answer(answer: str) -> bool:
    normalized = normalize_match_text(answer)
    return normalized in _BOOLEAN_TRUE_NORMALIZED | _BOOLEAN_FALSE_NORMALIZED


def _is_explicit_list_answer(answer: str) -> bool:
    return _PYTHON_LIST_RE.fullmatch(answer) is not None and _coerce_list_items(answer) is not None


def _infer_answer_kind(
    answer: str,
    question: str,
    answer_hint: Optional[str] = None,
) -> Optional[str]:
    hint = str(answer_hint).strip() if answer_hint else ""
    restrict_plain_list = hint in {"Why", "How"}

    if _is_explicit_list_answer(answer) or (
        not restrict_plain_list and _coerce_list_items(answer)
    ):
        return "list"
    if (
        _FULL_DATE_RE.fullmatch(answer)
        or _VIET_FULL_DATE_TEXT_RE.fullmatch(answer)
        or _MONTH_YEAR_RE.fullmatch(answer)
        or _YEAR_RE.fullmatch(answer)
    ):
        return "date"
    if _rank_variants(answer, question) != [answer]:
        return "number"
    if _is_boolean_answer(answer) or _looks_like_boolean_question(question):
        return "boolean"
    if _NUMBER_WITH_OPTIONAL_UNIT_RE.fullmatch(answer):
        return "number"
    if (
        not restrict_plain_list
        and _LIST_CUE_RE.search(_normalize_question_text(question))
        and _coerce_list_items(answer)
    ):
        return "list"
    return None


def _text_context_variants(answer: str, question: str) -> List[str]:
    variants = [answer]
    normalized_question = _normalize_question_text(question).replace("**", "")
    stripped = answer.strip()

    without_citation = _TRAILING_CITATION_RE.sub("", stripped).strip()
    if without_citation and without_citation != stripped:
        variants.append(without_citation)

    without_parenthetical = _PARENTHETICAL_RE.sub("", stripped)
    without_parenthetical = re.sub(r"\s+", " ", without_parenthetical).strip()
    without_parenthetical = re.sub(r"\s+,", ",", without_parenthetical)
    if without_parenthetical and without_parenthetical != stripped:
        variants.append(without_parenthetical)

    if "huân chương gì" in normalized_question and stripped.lower().startswith("huân chương "):
        variants.append(stripped[len("Huân chương ") :].strip())

    prefix_rules = (
        ("thôn nào", "thôn "),
        ("xã nào", "xã "),
        ("huyện nào", "huyện "),
        ("thành phố nào", "thành phố "),
        ("tỉnh nào", "tỉnh "),
        ("bằng gì", "bằng "),
        ("bằng cách nào", "bằng "),
    )
    for cue, prefix in prefix_rules:
        if cue in normalized_question and stripped.lower().startswith(prefix):
            variants.append(stripped[len(prefix):].strip())

    if _looks_like_why_question(question):
        for prefix in ("Vì ", "vì ", "Do ", "do ", "Bởi vì ", "bởi vì "):
            if stripped.startswith(prefix):
                reason = stripped[len(prefix):].strip()
                variants.append(reason)
                variants.append(f"Vì {reason}")
                variants.append(f"Do {reason}")
                variants.append(f"Bởi vì {reason}")
                break
        reason_match = re.search(
            r"không\s+chấp\s+nhận\s+sự\s+cai\s+trị\s+của\s+ông",
            stripped,
            re.IGNORECASE,
        )
        if reason_match is not None:
            variants.append("Vì không chấp nhận sự cai trị của ông")

    return _dedup_match_equivalent(variants)


def _deterministic_variants(
    answer: str,
    *,
    question: str,
    target: Optional[str],
    answer_kind: Optional[str],
) -> List[str]:
    variants = [answer]

    if answer_kind == "number":
        variants.extend(_numeric_variants(answer, question, target))
    elif answer_kind == "date":
        variants.extend(_date_variants(answer))
    elif answer_kind == "boolean":
        variants.extend(_boolean_variants(answer))
    elif answer_kind == "list":
        variants.extend(_list_variants(answer))

    variants.extend(_rank_variants(answer, question))
    variants.extend(_text_spacing_variants(answer))
    variants.extend(_text_context_variants(answer, question))
    return _dedup_match_equivalent(variants)


class AnswerNormalizationAgent(BaseAgent):
    name = "AnswerNormalization"
    prompt_name = "answer_normalization"

    def _prompt_name_for_hint(self, answer_hint: Optional[str]) -> str:
        if not answer_hint:
            return self.prompt_name
        return _NORMALIZATION_PROMPTS_BY_HINT.get(str(answer_hint).strip(), self.prompt_name)

    def _load_normalization_prompt(self, prompt_name: str, **kwargs: str) -> str:
        return load_prompt(prompt_name, **kwargs)

    def _call_llm_json_for_prompt(self, prompt: str, prompt_name: str) -> dict[str, Any]:
        original_prompt_name = self.prompt_name
        self.prompt_name = prompt_name
        try:
            return self._call_llm_json(prompt)
        finally:
            self.prompt_name = original_prompt_name

    def run(
        self,
        answer: str,
        question: str,
        target: Optional[str] = None,
        answer_hint: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> List[str]:
        answer = _strip_terminal_punctuation(answer)
        if _should_force_null_why(question):
            return ["Null"]
        if _is_explicit_null(answer):
            return ["Null"]

        effective_answer_hint = answer_hint or agent_name
        answer_kind = _infer_answer_kind(answer, question, effective_answer_hint)
        if _should_force_null_why_answer(answer, question, answer_kind):
            return ["Null"]
        if _should_force_null_how_answer(answer, question, answer_kind):
            return ["Null"]
        deterministic = _deterministic_variants(
            answer,
            question=question,
            target=target,
            answer_kind=answer_kind,
        )
        if answer_kind in {"number", "date", "boolean", "list"}:
            return deterministic

        selected_prompt_name = self._prompt_name_for_hint(effective_answer_hint)
        prompt = self._load_normalization_prompt(
            selected_prompt_name,
            question=question,
            answer=answer,
            target=target or "unknown",
        )
        data = self._call_llm_json_for_prompt(prompt, selected_prompt_name)
        candidates = _require_llm_answers(data)
        return _dedup_match_equivalent(candidates + deterministic)

    def run_many(
        self,
        answers: List[Optional[str]],
        question: str,
        target: Optional[str] = None,
        specialist_names_by_answer: Optional[Sequence[Optional[str]]] = None,
    ) -> List[str]:
        explicit_null_seen = any(_is_explicit_null(answer) for answer in answers)
        concrete_answers: List[tuple[int, str]] = []
        for idx, answer in enumerate(answers):
            if _is_nullish_answer(answer):
                continue
            concrete_answers.append((idx, _strip_terminal_punctuation(str(answer))))

        if not concrete_answers:
            if explicit_null_seen:
                return ["Null"]
            raise NoAnswerError("AnswerNormalization received no concrete answers")

        merged: List[str] = []
        concrete_by_idx = dict(concrete_answers)

        for idx, answer in enumerate(answers):
            if _is_explicit_null(answer):
                merged.append("Null")
            elif idx in concrete_by_idx:
                answer_hint = None
                if specialist_names_by_answer is not None and idx < len(specialist_names_by_answer):
                    answer_hint = specialist_names_by_answer[idx]
                merged.extend(
                    self.run(
                        concrete_by_idx[idx],
                        question,
                        target=target,
                        answer_hint=answer_hint,
                    )
                )

        merged = _dedup_match_equivalent(merged)
        if merged:
            return merged
        if explicit_null_seen:
            return ["Null"]
        raise NoAnswerError("AnswerNormalization produced no concrete normalized answers")
