"""D04 planner protocol: prompt, plan parsing, execution, and the frozen R2 override rule.

The prompt, few-shot plans, table serialisation, and R2 gate are ported unchanged from RankA
(``scripts/e2e_compiler_vs_direct.py`` and ``scripts/e2e_analyze.py``) so the transfer check
tests the rule RankA already fixed. The only intended difference is the decoder: RankA used a
llama.cpp GBNF grammar, which OpenRouter does not offer, so the plan is parsed and validated
after generation and any failure is logged as ``parse_error`` rather than repaired.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any

from .ast_executor import ExecutionError, RowSet, TableView, execute, repair_text

MAX_TABLE_CHARS = 24000

# Frozen from RankA e2e_analyze.py: executor overrides the reader only for these operations,
# only when execution succeeded, and never when the plan also contains a comparison.
R2_OPS = frozenset({"count", "sum", "avg", "argmax", "argmin"})
R2_EXCLUDED_OPS = frozenset({"compare"})


def serialize(table: dict[str, Any]) -> tuple[str, bool]:
    """Indexed table text shown to the planner; row 0 is the header row."""
    view = TableView.from_dataset(table)
    lines = [f"TIÊU ĐỀ: {view.title}"]
    truncated = False
    used = len(lines[0])
    if view.rows:
        header = " | ".join(f"[{i}]={repair_text(c)[:200]}" for i, c in enumerate(view.rows[0]))
        lines.append(f"CỘT: {header}")
        used += len(lines[-1])
    lines.append("DÒNG:")
    for index, row in enumerate(view.rows[1:], start=1):
        line = f"{index}: " + " | ".join(repair_text(c)[:600] for c in row)
        if used + len(line) > MAX_TABLE_CHARS:
            lines.append("[BẢNG BỊ CẮT]")
            truncated = True
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines), truncated


PLAN_SYSTEM = """Bạn là bộ lập kế hoạch: KHÔNG trả lời câu hỏi, chỉ viết chương trình AST để một bộ thực thi chạy trên bảng.
Xuất JSON: {"plan":"<1 câu ngắn>","route":"ast"|"text","ast":<node>|null}.
- route="ast" khi câu hỏi giải được bằng các phép toán dưới đây. Ngược lại route="text","ast":null (ví dụ: đáp án là một đoạn nằm TRONG một ô dài, hỏi Vì sao/Như thế nào, hoặc cần diễn đạt lại).
- Mỗi node: {"op":...,"args":{...},"input":[node,...]}. Cột đánh số từ 0 theo dòng CỘT. Dòng dữ liệu là các dòng 1,2,...
Phép toán:
 select {scope:"body"} input=[]            -> mọi dòng dữ liệu
 filter {column,equals|contains|gt|ge|lt|le} input=[rows] -> lọc dòng (equals/contains so chữ, gt/ge/lt/le so số)
 project {column} input=[rows]             -> danh sách giá trị của cột
 argmax|argmin {column} input=[rows]       -> dòng có giá trị số lớn/nhỏ nhất (rồi project để lấy giá trị)
 count input=[rows|values]                 -> đếm
 sum|avg input=[values]                    -> tổng/trung bình số
 compare {relation:eq|ne|gt|ge|lt|le} input=[a,b] -> so sánh hai giá trị (kết quả Có/Không)
 const {value} input=[]                    -> hằng số/chuỗi để so sánh
 set_union|set_intersect input=[a,b]; sort {descending} input=[values]; take {n} input=[values]
 lookup_title input=[]                     -> tiêu đề bảng
Câu hỏi Có/Không về một giá trị: dùng compare với const. Kiểm tra tồn tại: compare gt của count(...) với const 0."""

_SEL = {"op": "select", "args": {"scope": "body"}, "input": []}


def _n(op: str, args: dict[str, Any], *inputs: dict[str, Any]) -> dict[str, Any]:
    return {"op": op, "args": args, "input": list(inputs)}


def _plan(plan: str, ast: dict[str, Any] | None) -> str:
    return json.dumps({"plan": plan, "route": "ast" if ast else "text", "ast": ast}, ensure_ascii=False, separators=(",", ":"))


_CAST = (
    "TIÊU ĐỀ: Thời đại độc lập (phim)_0\nCỘT: [0]=Diễn viên | [1]=Vai\nDÒNG:\n1: Trần Tương kỳ | Kỳ Kỳ\n"
    "2: Nghê Thục Quân | Molly\n3: Vương Duy Minh | Tiểu Minh\n4: Đặng An Ninh | Larry\n5: Vương Vách Sâm | A Khâm"
)
_BUILD = (
    "TIÊU ĐỀ: Danh sách tòa nhà cao nhất Bắc Ninh_0\nCỘT: [0]=Khu vực | [1]=≥50m | [2]=≥100m\nDÒNG:\n"
    "1: Bắc Ninh | 36 | 7\n2: Quế Võ | 6 | -\n3: Từ Sơn | 3 | -\n4: Thuận Thành | 2 | -"
)
_POP = (
    "TIÊU ĐỀ: Đắk Lắk_0\nCỘT: [0]=Quận | [1]=Dân số\nDÒNG:\n1: Ban Mê Thuột | 95.664\n2: Buôn Hồ | 31.527\n"
    "3: Lạc Thiện | 19.456\n4: Phước An | 10.887\n5: Tổng số | 157.534"
)
_ALBUM = (
    "TIÊU ĐỀ: Các tác phẩm của San Holo_0\nCỘT: [0]=Tựa đề | [1]=Chi tiết | [2]=US Dance\nDÒNG:\n"
    "1: album1 | Phát hành: 21 tháng 9 năm 2018 Hãng phát hành: bitbird | 7\n"
    "2: bb u ok? | Phát hành: 4 tháng 6 năm 2021 Hãng phát hành: bitbird, Counter Records | 3"
)

PLAN_SHOTS = [
    (_CAST, "Ai là người diễn vai A Khâm?",
     _plan("Lọc dòng có Vai=A Khâm rồi lấy cột Diễn viên.", _n("project", {"column": 0}, _n("filter", {"column": 1, "equals": "A Khâm"}, _SEL)))),
    (_CAST, "Vai Tiểu Minh là của diễn viên Vương Duy Minh đúng không?",
     _plan("So sánh diễn viên của vai Tiểu Minh với Vương Duy Minh.",
           _n("compare", {"relation": "eq"}, _n("project", {"column": 0}, _n("filter", {"column": 1, "equals": "Tiểu Minh"}, _SEL)),
              _n("const", {"value": "Vương Duy Minh"})))),
    (_BUILD, "Tổng số tòa nhà cao từ 50m của Từ Sơn và Thuận Thành là bao nhiêu?",
     _plan("Cộng cột ≥50m của hai khu vực.",
           _n("sum", {}, _n("set_union", {},
                            _n("project", {"column": 1}, _n("filter", {"column": 0, "equals": "Từ Sơn"}, _SEL)),
                            _n("project", {"column": 1}, _n("filter", {"column": 0, "equals": "Thuận Thành"}, _SEL)))))),
    (_BUILD, "Khu vực nào có nhiều tòa nhà cao từ 50m nhất?",
     _plan("Lấy dòng có cột ≥50m lớn nhất rồi lấy tên khu vực.", _n("project", {"column": 0}, _n("argmax", {"column": 1}, _SEL)))),
    (_POP, "Có bao nhiêu Quận có dân số ít hơn 30.000?",
     _plan("Đếm dòng có dân số nhỏ hơn 30000.", _n("count", {}, _n("filter", {"column": 1, "lt": 30000}, _SEL)))),
    (_ALBUM, "Album bb u ok? được phát hành vào khi nào?",
     _plan("Ngày phát hành nằm trong một đoạn văn dài của ô, không có phép toán để cắt.", None)),
]


def plan_messages(table_text: str, question: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": PLAN_SYSTEM}]
    for shot_table, shot_question, shot_plan in PLAN_SHOTS:
        messages.append({"role": "user", "content": f"{shot_table}\n\nCÂU HỎI: {shot_question}"})
        messages.append({"role": "assistant", "content": shot_plan})
    messages.append({"role": "user", "content": f"{table_text}\n\nCÂU HỎI: {question}"})
    return messages


# ----------------------------------------------------------------------------- rendering

_YES_FORMS = re.compile(r"\b(đúng không|có đúng|đúng hay sai|đúng chứ)\b")
_PHAI_FORMS = re.compile(r"\b(phải không|có phải|phải chăng)\b")


def _normalize_question(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text)).casefold()
    value = re.sub(r"[^\w\s%]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def yes_no_surface(question: str, value: bool) -> str:
    q = _normalize_question(question)
    if _YES_FORMS.search(q):
        return "Đúng" if value else "Sai"
    if _PHAI_FORMS.search(q):
        return "Phải" if value else "Không"
    return "Có" if value else "Không"


def render_value(value: object, question: str) -> str | None:
    """Turn an executor value into one answer string, or None if not renderable."""
    if isinstance(value, bool):
        return yes_no_surface(question, value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isfinite(value) and value == int(value):
            return str(int(value))
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(items) if items else None
    return None


# ----------------------------------------------------------------------------- execution


def extract_json_object(raw: str) -> dict[str, Any] | None:
    """Parse the planner reply, tolerating a code fence or surrounding prose."""
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def run_plan(raw: str, view: TableView, question: str) -> dict[str, Any]:
    """Parse, execute and render one planner output. Never raises."""
    parsed = extract_json_object(raw)
    if parsed is None:
        return {"status": "parse_error", "rendered": None, "value": None, "ast": None}
    route, ast = parsed.get("route"), parsed.get("ast")
    if route != "ast" or not isinstance(ast, dict):
        return {"status": "text", "rendered": None, "value": None, "ast": None, "plan": parsed.get("plan")}
    try:
        value = execute(ast, view)
    except ExecutionError as exc:
        return {"status": "error", "error": str(exc)[:160], "rendered": None, "value": None, "ast": ast}
    except (RecursionError, ValueError, TypeError, KeyError) as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:160], "rendered": None, "value": None, "ast": ast}
    if isinstance(value, RowSet):
        return {"status": "error", "error": "plan returned a row set, not a value", "rendered": None, "value": None, "ast": ast}
    rendered = render_value(value, question)
    empty = rendered is None or (isinstance(value, (list, tuple)) and not value)
    return {
        "status": "empty" if empty else "ok",
        "rendered": rendered,
        "value": value if isinstance(value, (str, int, float, bool, list)) else str(value),
        "ast": ast,
        "plan": parsed.get("plan"),
    }


def ops_used(ast: dict[str, Any] | None) -> list[str]:
    if not isinstance(ast, dict):
        return []
    found = [ast.get("op")]
    for child in ast.get("input", []) or []:
        found.extend(ops_used(child))
    return [op for op in found if op]


def r2_override(record: dict[str, Any]) -> str | None:
    """The frozen RankA R2 rule: return the executor answer, or None to keep the reader's."""
    ops = set(record.get("ops") or [])
    if record.get("exec_status") == "ok" and ops & R2_OPS and not ops & R2_EXCLUDED_OPS:
        rendered = record.get("exec_rendered")
        return rendered if isinstance(rendered, str) and rendered.strip() else None
    return None
