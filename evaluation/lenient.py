"""EM mở rộng: coi các cách viết cùng nghĩa là đúng. Không thay EM gốc; báo cáo song song.

Mức "yn": Có = Đúng = Phải; Không = Sai = Không phải (cùng cực tính).
Mức "format": thêm đồng nghĩa định dạng — tiền tố "Năm", đơn vị trong câu hỏi "bao nhiêu <đơn vị>",
dấu thập phân, dấu phân cách hàng nghìn, ký hiệu chú thích, dấu nháy, tiền tố hành chính,
"và" ≡ dấu phẩy, danh sách không xét thứ tự (trừ khi câu hỏi yêu cầu sắp xếp).
"""

from __future__ import annotations

import re
from typing import Sequence

from .normalization import exact_text_match, is_unanswerable_reference, normalize_text, prediction_is_unanswerable

YES = {"có", "đúng", "phải", "co", "đúng vậy", "chính xác", "có phải", "đúng rồi", "phải vậy"}
NO = {"không", "sai", "không phải", "chưa", "không đúng", "sai rồi"}
LEVELS = ("strict", "yn", "format")

_ADMIN = r"(thành phố|huyện|tỉnh|quận|xã|phường|thị xã|thị trấn|tp\.?)"
_UNIT_Q = re.compile(r"bao nhiêu\s+([^\s?,.]+)")
_ORDERED = re.compile(r"thứ tự|sắp xếp|giảm dần|tăng dần|lần lượt")


def _polarity(text: str) -> str | None:
    t = normalize_text(text).rstrip("!.")
    return "yes" if t in YES else "no" if t in NO else None


def _canon(text: str, question: str) -> str:
    t = normalize_text(text)
    t = re.sub(r"(\s*(\[\d+\]|\[[a-z]\]|[*†‡]+))+$", "", t)  # chú thích
    t = re.sub(r"[\"“”'‘’«»]", "", t)  # dấu nháy
    t = re.sub(r"(?<=\d)[.,\s](?=\d{3}(\D|$))", "", t)  # hàng nghìn: 10.400.000 / 10,400,000 / 10 400 000
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)  # thập phân: 34,4 → 34.4
    t = re.sub(r"^năm\s+(?=\d)", "", t)
    unit = _UNIT_Q.search(normalize_text(question))
    if unit:
        t = re.sub(rf"^(-?[\d.]+)\s+{re.escape(unit.group(1))}$", r"\1", t)
    t = re.sub(rf"^{_ADMIN}\s+", "", t)
    t = re.sub(r"\s+và\s+", ", ", t)
    return " ".join(t.split()).rstrip(".")


def _items(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,;]", text) if x.strip()]


def lenient_match(prediction: str, reference: str, question: str, *, hints: Sequence[str] | None = None,
                  level: str = "format") -> bool:
    if is_unanswerable_reference(reference):
        return prediction_is_unanswerable([prediction])
    if exact_text_match(prediction, reference, hints=hints):
        return True
    if level == "strict":
        return False
    pol = _polarity(reference)
    if pol is not None and _polarity(prediction) == pol:
        return True
    if level == "yn":
        return False
    p, r = _canon(prediction, question), _canon(reference, question)
    if p == r:
        return True
    pi, ri = [_canon(x, question) for x in _items(p)], [_canon(x, question) for x in _items(r)]
    if len(ri) > 1 and len(pi) == len(ri):
        return pi == ri if _ORDERED.search(normalize_text(question)) else sorted(pi) == sorted(ri)
    return False
