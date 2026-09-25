"""Chọn lớp câu hỏi -> graph. Luật viết từ câu hỏi train; hint gold chỉ dùng làm oracle chẩn đoán."""

from __future__ import annotations

import re

from evaluation.normalization import normalize_text

CLASSES = ("yesno", "compute", "list", "explain", "lookup")

_YESNO = re.compile(r"(không|chưa|đúng hay sai|hay sai)\s*\?*\s*$|^có phải")
_EXPLAIN = re.compile(r"tại sao|vì sao|vì lý do gì|lý do|như thế nào|bằng cách nào|làm sao|làm thế nào")
_LIST = re.compile(r"liệt kê|kể tên|sắp xếp|(những|các) [^?]{0,40}\bnào\b")
_COMPUTE = re.compile(
    r"bao nhiêu|\bmấy\b|tổng|trung bình|chênh lệch|gấp|nhiều hơn|ít hơn|cao hơn|thấp hơn|lớn hơn|nhỏ hơn"
    r"|tỉ lệ|tỷ lệ|phần trăm|thứ hai|thứ ba|bai nhiêu"
    r"|(nhiều|ít|cao|thấp|lớn|nhỏ|dài|ngắn|sớm|muộn|mới|cũ|đông|trẻ|già|nặng|nhẹ|xa|gần|rộng|hẹp)(\s+\w+){0,2}\s+nhất"
    r"|(trên|dưới|hơn|trước năm|sau năm)\s+\d"
)


def route(question: str) -> str:
    q = normalize_text(question)
    if _YESNO.search(q):
        return "yesno"
    if _EXPLAIN.search(q):
        return "explain"
    if _LIST.search(q):
        return "list"
    if _COMPUTE.search(q):
        return "compute"
    return "lookup"


def gold_class(hints: list[str]) -> str:
    h = " ".join(hints).lower()
    if "yes/no" in h:
        return "yesno"
    if "tính toán" in h:
        return "compute"
    if "liệt kê" in h:
        return "list"
    if "(why)" in h or "(how)" in h:
        return "explain"
    return "lookup"
