"""Agent định dạng (tất định): chỉnh cách viết đáp án theo phong cách gold của các câu train CÙNG BẢNG.

Người gán nhãn nhất quán theo bảng ở vài đặc trưng (đo leave-one-out trên train): tiền tố "Năm" cho
đáp án năm (đa số toàn cục 85,6% → đa số cùng bảng 93,0%) và việc kèm đơn vị khi câu hỏi
"bao nhiêu <đơn vị>" (94,0% → 97,0%). Dấu thập phân theo cách viết của chính ô bảng. Chỉ đổi khi có bằng chứng.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from .data import train_by_table

_YEAR = re.compile(r"(?i)(năm\s+)?(\d{3,4})\.?")
_TIME_Q = re.compile(r"(?i)(khi nào|năm nào|thời gian nào|lúc nào|bao giờ|năm bao nhiêu|vào năm|thời điểm nào)")
_DEC = re.compile(r"(-?\d+)[.,](\d{1,2})(\s+\S.*)?")
_UNIT_Q = re.compile(r"(?i)bao nhiêu\s+([^\s?,.]+)")
_NUM_ANS = re.compile(r"(-?\d(?:[\d.,]|\s(?=\d{3}\b))*)(?:\s+(\D.*))?")


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def _vote(flags: list[bool]) -> bool | None:
    """Đa số nghiêm ngặt; hoà hoặc không có bằng chứng → None (giữ nguyên)."""
    if not flags or 2 * sum(flags) == len(flags):
        return None
    return 2 * sum(flags) > len(flags)


@lru_cache(maxsize=None)
def _cells(table_id: str) -> str:
    from .code_agent import table_rows

    return "\n".join(" | ".join(r) for r in table_rows(table_id))


def _train(qa: dict) -> list[dict]:
    return [r for r in train_by_table().get(qa["table_id"], []) if r["qa_id"] != qa["qa_id"]]


def year_style(ans: str, qa: dict) -> str:
    m = _YEAR.fullmatch(_nfc(ans))
    if not m or not _TIME_Q.search(_nfc(qa["question"])):
        return ans
    flags = [_nfc(r["answer"]).lower().startswith("năm") for r in _train(qa)
             if _YEAR.fullmatch(_nfc(r["answer"])) and _TIME_Q.search(_nfc(r["question"]))]
    want = _vote(flags)
    if want is None:
        return ans
    return f"Năm {m.group(2)}" if want else m.group(2)


def decimal_style(ans: str, qa: dict) -> str:
    """Số thập phân viết theo đúng dạng xuất hiện trong ô bảng (gold thường chép từ bảng)."""
    m = _DEC.fullmatch(_nfc(ans))
    if not m:
        return ans
    comma, dot = f"{m.group(1)},{m.group(2)}", f"{m.group(1)}.{m.group(2)}"
    cells = _cells(qa["table_id"])
    has_c = re.search(rf"(?<![\d.,]){re.escape(comma)}(?![\d])", cells) is not None
    has_d = re.search(rf"(?<![\d.,]){re.escape(dot)}(?![\d])", cells) is not None
    if has_c == has_d:
        return ans
    return f"{comma if has_c else dot}{m.group(3) or ''}"


def unit_style(ans: str, qa: dict) -> str:
    """Thêm đơn vị chỉ khi câu train cùng bảng hỏi đúng đơn vị đó và đa số gold kèm đơn vị;
    bỏ hậu tố chỉ khi hậu tố chính là đơn vị trong câu hỏi và đa số gold không kèm."""
    qm = _UNIT_Q.search(_nfc(qa["question"]))
    am = _NUM_ANS.fullmatch(_nfc(ans).rstrip("."))
    if not qm or not am or qm.group(1)[:1].isupper():  # từ viết hoa là tên riêng, không phải đơn vị
        return ans
    unit = qm.group(1).lower()
    suffix = (am.group(2) or "").lower()
    if suffix and suffix != unit:
        return ans
    same = []
    for r in _train(qa):
        rq, ra = _UNIT_Q.search(_nfc(r["question"])), _NUM_ANS.fullmatch(_nfc(r["answer"]).rstrip("."))
        if rq and ra and rq.group(1).lower() == unit:
            same.append(bool(ra.group(2)))
    want = _vote(same)
    if want is None:
        return ans
    return f"{am.group(1)} {qm.group(1)}" if want else am.group(1)


_FOOTNOTE = re.compile(r"(\s*(\[\d+\]|\[[a-z]\]|[*†‡]+))+$")


def strip_footnote(ans: str, qa: dict) -> str:
    """Gold không bao giờ giữ ký hiệu chú thích (*, †, [1]) dù 90 ô bảng trong train có."""
    out = _FOOTNOTE.sub("", _nfc(ans))
    return out if out and out != _nfc(ans) else ans


def thousands_style(ans: str, qa: dict) -> str:
    """Số nguyên ≥ 10.000 viết liền → dấu chấm hàng nghìn, nếu bảng viết số kiểu 1.234.567."""
    a = _nfc(ans)
    if not re.fullmatch(r"\d{5,}", a) or not re.search(r"(?<![\d.,])\d{1,3}(\.\d{3})+(?![\d,])", _cells(qa["table_id"])):
        return ans
    return f"{int(a):,}".replace(",", ".")


_PREFIX = re.compile(r"(?i)^(huyện|quận|thành phố|tỉnh|xã|phường|thị xã|thị trấn|trận)\s+")


def cell_prefix(ans: str, qa: dict) -> str:
    """Đáp án và một ô bảng chỉ khác nhau ở tiền tố hành chính → viết đúng như ô (gold chép từ ô)."""
    a = _nfc(ans)
    cells = {_nfc(c).lower(): _nfc(c) for c in _cells(qa["table_id"]).replace("\n", " | ").split(" | ") if c.strip()}
    if a.lower() in cells or "," in a:
        return ans
    bare = _PREFIX.sub("", a)
    options = [c for low, c in cells.items() if _PREFIX.sub("", low) == bare.lower() and low != a.lower()]
    return options[0] if len(options) == 1 else ans


def dedupe_list(ans: str, qa: dict) -> str:
    items = [x.strip() for x in _nfc(ans).split(",")]
    return items[0] if len(items) > 1 and all(items) and len({x.lower() for x in items}) == 1 else ans


RULES = {"year": year_style, "decimal": decimal_style, "unit": unit_style, "footnote": strip_footnote,
         "thousands": thousands_style, "cell_prefix": cell_prefix, "dedupe": dedupe_list}


DEFAULT = ("year", "unit", "footnote", "thousands", "dedupe")  # chốt trên dev v8 (sửa 9, hỏng 0)


def harmonize(ans: str, qa: dict, rules: tuple[str, ...] = DEFAULT) -> str:
    for name in rules:
        ans = RULES[name](ans, qa)
    return ans


if __name__ == "__main__":
    fake = {"t": [{"qa_id": f"r{i}", "question": "Xây vào năm nào?", "answer": "Năm 2001"} for i in range(3)]
            + [{"qa_id": "u1", "question": "Ông bao nhiêu tuổi?", "answer": "45 tuổi"},
               {"qa_id": "d1", "question": "Bao nhiêu?", "answer": "3,5"},
               {"qa_id": "f1", "question": "Nhà có bao nhiêu tầng?", "answer": "30"}]}
    globals()["train_by_table"] = lambda: fake
    globals()["_cells"] = lambda t: "Tỉ lệ | 0,6 | 12.5 | Quận Ninh Kiều | Hòa Vang | 4.512"
    qa = {"qa_id": "q", "table_id": "t", "question": "Bà ấy bao nhiêu tuổi?"}
    assert harmonize("Burundi*", qa) == "Burundi" and harmonize("Việt Nam [3]", qa) == "Việt Nam"
    assert harmonize("10400000", {**qa, "question": "Chênh lệch?"}) == "10.400.000"
    assert cell_prefix("Ninh Kiều", {**qa, "question": "Quận nào?"}) == "Quận Ninh Kiều"  # không nằm trong DEFAULT
    assert cell_prefix("Huyện Hòa Vang", {**qa, "question": "Huyện nào?"}) == "Hòa Vang"
    assert harmonize("24.3, 24.3", {**qa, "question": "Nhiệt độ?"}) == "24.3"
    assert harmonize("2012", {**qa, "question": "Khánh thành khi nào?"}) == "Năm 2012"
    assert harmonize("335", {**qa, "question": "Tháp có bao nhiêu tầng?"}) == "335"
    assert harmonize("10", qa) == "10 tuổi"
    assert decimal_style("0.6", {**qa, "question": "Tỉ lệ?"}) == "0,6"  # không nằm trong DEFAULT
    assert decimal_style("12,5", {**qa, "question": "Tỉ lệ?"}) == "12.5"
    assert harmonize("4", {**qa, "question": "Có bao nhiêu chiến thắng?"}) == "4"
    assert harmonize("149 000 000", {**qa, "question": "Bao nhiêu tuổi?"}) == "149 000 000 tuổi"
    assert harmonize("Hà Nội", qa) == "Hà Nội"
    print("ok")
