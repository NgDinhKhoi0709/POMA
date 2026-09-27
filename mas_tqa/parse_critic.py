"""Parse-Critic agent: LLM tự nhận xét cách bảng HTML được parse thành Flatten V1, viết ghi chú cấu trúc.

Chạy một lần mỗi bảng, cache ở outputs/mas_tqa/parse_notes.jsonl. Không viết lại nội dung ô.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from bs4 import BeautifulSoup

from .client import VLLMClient, parse_json
from .data import ROOT, table_str, tables

CACHE = ROOT / "outputs/mas_tqa/parse_notes.jsonl"
_LOCK = threading.Lock()


def clean_html(html: str) -> str:
    """Giữ khung bảng (tr/th/td + rowspan/colspan) và chữ trong ô; bỏ link, ảnh, chú thích [n], thuộc tính khác."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["img", "sup", "style", "script"]):
        tag.decompose()
    rows = []
    for tr in soup.find_all("tr"):
        cells = []
        for c in tr.find_all(["th", "td"], recursive=False):
            attrs = "".join(f' {a}="{c[a]}"' for a in ("rowspan", "colspan") if c.has_attr(a) and str(c[a]).strip() not in ("", "1"))
            text = re.sub(r"\s+", " ", c.get_text(" ", strip=True))
            cells.append(f"<{c.name}{attrs}>{text}</{c.name}>")
        if cells:
            rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def critic_prompt(table_id: str) -> str:
    t = tables()[table_id]
    return (
        "Bạn là agent kiểm tra việc chuyển bảng HTML sang văn bản cho một hệ hỏi–đáp.\n"
        "Dưới đây là (1) bảng HTML gốc đã làm gọn, còn giữ rowspan/colspan, và (2) bản Flatten V1 mà hệ thống đang dùng: "
        "mỗi dòng dạng tiêu_đề_hàng|tiêu_đề_cột|giá_trị, tiêu đề có hậu tố <header>.\n"
        "Hãy tự nhận xét bản Flatten V1 có trung thành với bảng gốc không: ô gộp (rowspan/colspan) đã được lan đúng "
        "hàng/cột chưa, header nhiều tầng có bị mất hoặc ghép sai không, có ô nào bị lệch cột, mất hay lặp không, "
        "tiêu đề hàng/cột có được xác định đúng không.\n"
        "Sau đó viết GHI CHÚ CẤU TRÚC ngắn gọn (tối đa 5 dòng) giúp người đọc bản Flatten V1 hiểu đúng bảng: "
        "chỉ mô tả cấu trúc và cách đọc (vd. cột nào thuộc nhóm header nào, ô nào áp dụng cho nhiều hàng); "
        "KHÔNG trả lời câu hỏi nào, KHÔNG bịa nội dung ô.\n"
        "ĐẦU RA: đúng một JSON {\"ok\": true/false, \"issues\": [\"<vấn đề>\"], \"notes\": \"<ghi chú cấu trúc; chuỗi rỗng nếu ok>\"}.\n\n"
        f"TIÊU ĐỀ BẢNG: {t.get('table_title', '')}\n\n(1) HTML GỐC:\n{clean_html(t['table_html'])}\n\n"
        f"(2) FLATTEN V1:\n{table_str(table_id)}\n"
    )


def load_cache() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    return {r["table_id"]: r for r in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines()) if r}


def critique(client: VLLMClient, table_id: str) -> dict:
    t, u = client.chat(critic_prompt(table_id))
    obj = parse_json(t[0]) or {}
    rec = {
        "table_id": table_id,
        "ok": bool(obj.get("ok", True)),
        "issues": [str(x) for x in obj.get("issues") or []],
        "notes": str(obj.get("notes") or "").strip(),
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
    }
    with _LOCK:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


_NOTES: dict[str, dict] | None = None


def notes_for(table_id: str) -> str:
    global _NOTES
    if _NOTES is None:
        _NOTES = load_cache()
    r = _NOTES.get(table_id)
    return r["notes"] if r and not r["ok"] and r["notes"] else ""
