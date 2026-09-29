"""Agent M (toán) + agent V (kiểm tra) cho câu hỏi tính toán.

M đọc bảng (Markdown-KV + memory cùng bảng), trích ô, chọn loại phép và giải thích; Python tính kết quả
tất định (không tính nhẩm). V kiểm tra hai lớp: tất định (ô trích phải có trong bảng) và LLM (đúng ô,
đủ ô, đúng phép; có thể sửa). Câu chỉ cần tra một ô thì M bỏ qua (type "lookup").
"""

from __future__ import annotations

import ast
import json
import math
import operator
import re

from evaluation.normalization import normalize_text

from .client import Usage, VLLMClient, parse_json

TYPES = ("tính", "đếm", "chọn", "xếp_hạng", "lookup")
_TYPE_ALIAS = {"tinh": "tính", "dem": "đếm", "chon": "chọn", "xep_hang": "xếp_hạng", "xếp hạng": "xếp_hạng", "tra_cứu": "lookup"}

_SCHEMA = (
    "ĐẦU RA: đúng một JSON\n"
    "{\"type\": \"tính\" | \"đếm\" | \"chọn\" | \"xếp_hạng\" | \"lookup\",\n"
    " \"cells\": [{\"label\": \"<tên hàng/đối tượng>\", \"text\": \"<chép NGUYÊN VĂN ô trong bảng>\", \"value\": <số dạng Python, vd 4512 hoặc 121.84>}],\n"
    " \"expr\": \"<chỉ cho type tính: biểu thức Python chỉ dùng các số trong cells, vd 4512 - 2999>\",\n"
    " \"select\": \"max\" | \"min\"  (type chọn: lấy nhãn có giá trị lớn nhất/nhỏ nhất; type xếp_hạng: max = xếp từ lớn đến nhỏ),\n"
    " \"k\": <thứ tự cần lấy, mặc định 1; vd 2 cho \"lớn thứ hai\">,\n"
    " \"target\": \"<type xếp_hạng: nhãn của đối tượng cần biết thứ hạng>\",\n"
    " \"explain\": \"<giải thích ngắn các bước tính>\"}\n"
)

_M_TASK = (
    "NHIỆM VỤ: câu hỏi dưới đây có thể cần tính toán trên bảng. KHÔNG tự tính nhẩm; hãy trích các ô cần dùng "
    "và mô tả phép tính, máy sẽ tính giúp.\n"
    "- type \"tính\": cộng/trừ/nhân/chia/trung bình/tỉ lệ... → cells + expr.\n"
    "- type \"đếm\": \"có bao nhiêu ...\" → cells là TẤT CẢ các hàng thỏa điều kiện (mỗi hàng một phần tử), máy đếm.\n"
    "- type \"chọn\": \"... nào nhiều/ít/cao/thấp nhất\" → cells là TẤT CẢ ứng viên kèm giá trị, select max/min, máy trả nhãn.\n"
    "- type \"xếp_hạng\": \"... đứng thứ mấy\" → cells là TẤT CẢ đối tượng kèm giá trị, target, select, máy trả thứ hạng.\n"
    "- type \"lookup\": câu hỏi chỉ cần tra đúng một ô, không cần tính → cells rỗng.\n"
)


def demo_block(qa: dict, memory: bool = True) -> str:
    """8 câu mẫu cùng bảng; memory=False (ablation): ví dụ chung của prompt few-shot gốc."""
    from .data import retrieve_same_table

    if not memory:
        from .prompts_fs import _few_shot_examples_vi

        return f"CÁC VÍ DỤ HỎI–ĐÁP CHUNG:\n{_few_shot_examples_vi().strip()}"
    demos = "\n".join(f"CÂU HỎI: {d['question']}\nĐÁP ÁN: {d['answer']}" for d in retrieve_same_table(qa, 8))
    return f"CÁC CÂU HỎI KHÁC ĐÃ ĐƯỢC TRẢ LỜI ĐÚNG TRÊN CHÍNH BẢNG NÀY:\n{demos}"


def prefix(qa: dict, memory: bool = True) -> str:
    """Tiền tố riêng cho M/V: chỉ mô tả bảng (không kèm lược đồ đầu ra của solver B) + memory cùng bảng."""
    from .methods import kv_str

    return (
        "Bạn là chuyên gia phân tích bảng. Bảng dưới đây được viết thành từng khối, mỗi khối là một hàng "
        "(\"## Hàng i\"), mỗi dòng trong khối có dạng \"Tên cột: giá trị\". CHỈ được dùng thông tin trong bảng.\n\n"
        f"BẢNG:\n{kv_str(qa['table_id'])}\n\n{demo_block(qa, memory)}\n\n"
    )


def m_suffix(qa: dict) -> str:
    return f"{_M_TASK}{_SCHEMA}\nCÂU HỎI: {qa['question']}\nĐẦU RA: "


def v_suffix(qa: dict, plan: dict, result: str) -> str:
    return (
        "NHIỆM VỤ: KIỂM TRA lời giải tính toán của một chuyên gia khác cho câu hỏi dưới đây. Đối chiếu từng ô với "
        "bảng: có đúng hàng, đúng cột, chép đúng giá trị không; với đếm/chọn/xếp hạng: có ĐỦ mọi hàng thỏa điều "
        "kiện và không thừa hàng nào không; phép tính có đúng ý câu hỏi không.\n"
        "ĐẦU RA: đúng một JSON {\"ok\": true | false, \"reason\": \"<lỗi nếu có>\", "
        "\"fix\": <nếu ok=false: lời giải đã sửa theo đúng lược đồ JSON dưới đây; nếu ok=true: null>}.\n"
        f"{_SCHEMA}\nCÂU HỎI: {qa['question']}\n"
        f"LỜI GIẢI CẦN KIỂM TRA: {json.dumps(plan, ensure_ascii=False)}\nKẾT QUẢ MÁY TÍNH: {result}\nĐẦU RA: "
    )


# ---------- tính toán tất định ----------

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_FUN = {"sum": lambda *a: sum(_flat(a)), "min": lambda *a: min(_flat(a)), "max": lambda *a: max(_flat(a)),
        "avg": lambda *a: sum(_flat(a)) / len(_flat(a)), "mean": lambda *a: sum(_flat(a)) / len(_flat(a)),
        "abs": abs, "round": round, "len": lambda *a: len(_flat(a))}


def _flat(a) -> list[float]:
    out = []
    for x in a:
        out.extend(_flat(x) if isinstance(x, (list, tuple)) else [x])
    return out


def safe_eval(expr: str) -> float:
    """Chỉ cho số, + - * / // %, lũy thừa nhỏ, ngoặc, list và vài hàm tổng hợp."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow):
            b, e = ev(n.left), ev(n.right)
            if abs(e) > 10:
                raise ValueError("số mũ quá lớn")
            return b ** e
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(x) for x in n.elts]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUN and not n.keywords:
            return _FUN[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"biểu thức không hợp lệ: {ast.dump(n)[:60]}")
    return float(ev(ast.parse(expr.replace("×", "*").replace("÷", "/"), mode="eval")))


def _num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(" ", ""))
    except ValueError:
        return None


def fmt_number(x: float, cells: list[dict]) -> str:
    """Số nguyên → không phần thập phân; thập phân tối đa 2 chữ số (hoặc bằng số lẻ của ô).
    Dấu thập phân và dấu hàng nghìn theo cách viết của các ô được trích."""
    texts = " ".join(str(c.get("text", "")) for c in cells)
    comma_dec = re.search(r"\d,\d{1,2}(?!\d)", texts) is not None
    dot_thou = re.search(r"\d{1,3}(\.\d{3})+(?![\d,])", texts) is not None and not re.search(r"\d\.\d{1,2}(?!\d)", texts)
    if abs(x - round(x)) < 1e-9:
        s = str(int(round(x)))
        return f"{int(s):,}".replace(",", ".") if dot_thou and abs(int(s)) >= 1000 else s
    dec = max([2] + [len(m) for m in re.findall(r"\d[.,](\d{1,4})(?!\d)", texts)])
    s = f"{x:.{min(dec, 4)}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") if comma_dec else s


def execute(plan: dict) -> tuple[str | None, str]:
    """Trả (đáp án, lỗi). None khi lookup/không hợp lệ."""
    t = _TYPE_ALIAS.get(str(plan.get("type", "")).strip().lower(), str(plan.get("type", "")).strip().lower())
    cells = plan.get("cells") or []
    if t not in TYPES:
        return None, "type không hợp lệ"
    if t == "lookup":
        return None, "lookup"
    try:
        if t == "tính":
            out = fmt_number(safe_eval(str(plan.get("expr", ""))), cells)
        elif t == "đếm":
            out = str(len(cells))
        else:
            vals = [(str(c.get("label", "")).strip(), _num(c.get("value"))) for c in cells]
            vals = [(lab, v) for lab, v in vals if lab and v is not None]
            if not vals:
                return None, "không có giá trị"
            desc = plan.get("select", "max") != "min"
            ranked = sorted(vals, key=lambda p: -p[1] if desc else p[1])
            if t == "chọn":
                k = max(1, int(plan.get("k") or 1))
                out = ranked[min(k, len(ranked)) - 1][0]
            else:
                target = normalize_text(str(plan.get("target", "")))
                pos = [i for i, (lab, _) in enumerate(ranked) if normalize_text(lab) == target]
                if not pos:
                    return None, "không tìm thấy target"
                out = str(pos[0] + 1)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError, SyntaxError) as e:
        return None, f"lỗi tính: {e}"[:120]
    return out, ""  # đơn vị/kiểu viết do agent định dạng quyết định (mas_tqa/style.py)


def grounded(plan: dict, table_text: str) -> bool:
    """Mọi ô trích phải xuất hiện nguyên văn (sau chuẩn hoá) trong bảng."""
    tt = normalize_text(table_text)
    return all(normalize_text(str(c.get("text", ""))) in tt for c in plan.get("cells") or [] if str(c.get("text", "")).strip())


def solve(client: VLLMClient, qa: dict, prefix: str, table_text: str) -> dict:
    """M rồi V; trả trace đầy đủ để chọn luật ghép offline."""
    usage = Usage()
    tm, u = client.chat(prefix + m_suffix(qa)); usage.add(u)
    plan = parse_json(tm[0]) or {}
    m_ans, m_err = execute(plan)
    out = {"M_plan": plan, "M": m_ans or "", "M_err": m_err, "M_grounded": grounded(plan, table_text) if m_ans else False,
           "V_ok": None, "V_reason": "", "V_fix": None, "V": "", "usage": usage}
    if m_ans is None:
        return out
    tv, u = client.chat(prefix + v_suffix(qa, plan, m_ans)); usage.add(u)
    ver = parse_json(tv[0]) or {}
    ok = ver.get("ok")
    out["V_ok"], out["V_reason"] = (ok if isinstance(ok, bool) else None), str(ver.get("reason", ""))[:300]
    if ok is False and isinstance(ver.get("fix"), dict):
        fix_ans, _ = execute(ver["fix"])
        out["V_fix"], out["V"] = ver["fix"], fix_ans or ""
    elif ok is True:
        out["V"] = m_ans
    return out
