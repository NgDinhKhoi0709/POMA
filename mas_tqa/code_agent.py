"""Agent C (Program-of-Thought): LLM viết code pandas trên DataFrame của bảng, chạy trong tiến trình con.

Sandbox: tiến trình Python riêng, timeout, chỉ cho import một danh sách module, bỏ `open`/`exec`/`eval`
khỏi builtins. Đủ để chặn code sinh ra vô tình ghi file hoặc gọi mạng; không phải sandbox bảo mật mạnh.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from functools import lru_cache

from .data import tables

_CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
TIMEOUT_S = 10
ALLOWED = ("math", "re", "datetime", "statistics", "pandas", "numpy", "collections", "itertools", "unicodedata")

# Mã chạy trong tiến trình con: đọc {rows, code} từ stdin, dựng df, chạy code, in answer dạng JSON.
_RUNNER = r'''
import builtins, json, sys
import pandas as pd
inp = json.loads(sys.stdin.buffer.read().decode("utf-8"))  # -I bỏ qua PYTHONIOENCODING
rows = inp["rows"]
head, seen = [], {}
for i, c in enumerate(rows[0] if rows else []):
    c = str(c).strip() or f"cot_{i}"
    seen[c] = seen.get(c, 0) + 1
    head.append(c if seen[c] == 1 else f"{c} ({seen[c]})")
body = [list(r) + [""] * (len(head) - len(r)) for r in rows[1:]]
df = pd.DataFrame([r[: len(head)] for r in body], columns=head)
_imp = builtins.__import__
ALLOWED = set(inp["allowed"])
def _guard(name, *a, **k):
    if name.split(".")[0] not in ALLOWED:
        raise ImportError(f"module {name} không được phép")
    return _imp(name, *a, **k)
safe = {k: getattr(builtins, k) for k in dir(builtins) if k not in {"open", "exec", "eval", "compile", "input", "breakpoint", "exit", "quit"}}
safe["__import__"] = _guard
import collections, datetime, itertools, math, re, statistics
import numpy as np
g = {"__builtins__": safe, "df": df, "pd": pd, "np": np, "re": re, "math": math, "datetime": datetime,
     "statistics": statistics, "collections": collections, "itertools": itertools}
exec(inp["code"], g)
ans = g.get("answer")
if isinstance(ans, (list, tuple, set)):
    ans = ", ".join(str(x) for x in ans)
elif isinstance(ans, float) and ans.is_integer():
    ans = str(int(ans))
sys.stdout.buffer.write(json.dumps({"answer": None if ans is None else str(ans)}).encode("utf-8"))
'''


@lru_cache(maxsize=None)
def table_rows(table_id: str) -> list[list[str]]:
    t = tables()[table_id]
    d = t.table_dict if hasattr(t, "table_dict") else t["table_dict"]
    rows = d["table_rows"] if isinstance(d, dict) else d
    return [[str(c) for c in r] for r in rows]


def df_view(table_id: str) -> str:
    rows = table_rows(table_id)
    if not rows:
        return "(bảng rỗng)"
    lines = [f"cột: {json.dumps(rows[0], ensure_ascii=False)}"]
    lines += [f"{i}: {json.dumps(r, ensure_ascii=False)}" for i, r in enumerate(rows[1:])]
    return "\n".join(lines)


def extract_code(text: str) -> str:
    blocks = _CODE_RE.findall(text)
    return blocks[-1].strip() if blocks else ""


def run_code(rows: list[list[str]], code: str, timeout: int = TIMEOUT_S) -> tuple[str | None, str]:
    """Trả (answer, lỗi). answer None khi code lỗi, quá thời gian hoặc không gán biến `answer`."""
    if not code:
        return None, "không có code"
    try:
        p = subprocess.run(
            [sys.executable, "-I", "-c", _RUNNER],
            input=json.dumps({"rows": rows, "code": code, "allowed": ALLOWED}, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if p.returncode != 0:
        return None, (p.stderr.strip().splitlines() or ["lỗi"])[-1][:300]
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])["answer"], ""
    except (json.JSONDecodeError, IndexError, KeyError):
        return None, "không đọc được đầu ra"


if __name__ == "__main__":
    rows = [["Tên", "Số"], ["a", "1,5"], ["b", "2"]]
    assert run_code(rows, "answer = df['Tên'].tolist()") == ("a, b", "")
    assert run_code(rows, "answer = sum(float(x.replace(',', '.')) for x in df['Số'])")[0] == "3.5"
    assert run_code(rows, "import os\nanswer = 1")[0] is None
    assert run_code(rows, "open('x.txt', 'w')")[0] is None
    assert run_code([["Tên"], ["Hà Nội"]], "answer = re.sub('Hà ', '', df.iloc[0, 0])") == ("Nội", "")
    assert run_code(rows, "while True: pass", timeout=2) == (None, "timeout")
    print("ok")
