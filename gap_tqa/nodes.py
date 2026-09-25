"""Thư viện node. Node LLM gọi Qwen3-8B qua LLMClient (có cache theo prompt); còn lại là code tất định."""

from __future__ import annotations

import hashlib
import json
import random
import re
import threading
from pathlib import Path

from evaluation.normalization import normalize_text
from gap_tqa.router import route
from gap_tqa.table import Table, contained, syllables

CACHE = Path("outputs/gap_tqa/cache.jsonl")
_lock = threading.Lock()
_cache: dict[str, dict] | None = None

FMT_NOTE = {
    "v1_raw": "mỗi dòng: tiêu_đề_hàng|tiêu_đề_cột|giá_trị; tiêu đề có hậu tố <header>",
    "pipe_nohdr": "dòng 'Cột:' là tên các cột, mỗi dòng sau là một hàng, các ô cách nhau bởi |",
    "markdown_kv_clean": "mỗi khối là một hàng, mỗi dòng 'Tên cột: giá trị'",
}


def _load_cache() -> dict[str, dict]:
    global _cache
    with _lock:
        if _cache is None:
            loaded: dict[str, dict] = {}
            if CACHE.exists():
                for line in CACHE.read_text(encoding="utf-8").splitlines():
                    rec = json.loads(line)
                    loaded.setdefault(rec["key"], rec)  # bản ghi đầu tiên thắng, như lúc chạy
            _cache = loaded
    return _cache


def llm(prompt: str, tag: str) -> tuple[str, int, bool]:
    """(câu trả lời đã bỏ <think>, prompt token, có gọi API thật không)."""
    from src.services.llm_client import LLMClient  # import muộn để test không cần khoá API

    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    cache = _load_cache()
    if key in cache:
        return cache[key]["text"], cache[key]["prompt_tokens"], False
    client = LLMClient()
    raw = client.generate_text(prompt, agent_name=f"gap_tqa.{tag}")
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    rec = {"key": key, "tag": tag, "text": text, "prompt_tokens": client.total_prompt_tokens}
    with _lock:
        if key in cache:  # luồng khác vừa ghi cùng prompt: giữ bản đầu tiên
            return cache[key]["text"], cache[key]["prompt_tokens"], True
        cache[key] = rec
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return text, rec["prompt_tokens"], True


def style_examples(train_path: str = "dataset/qas_train.json", per_class: int = 2, seed: int = 7) -> str:
    """Cặp (câu hỏi, đáp án) ngắn từ train, 2 cặp mỗi lớp: dạy phong cách đáp án, không kèm bảng."""
    qas = json.load(open(train_path, encoding="utf-8"))["qas"]
    rng = random.Random(seed)
    rng.shuffle(qas)
    picked: dict[str, list] = {}
    for q in qas:
        c = route(q["question"])
        if len(picked.setdefault(c, [])) < per_class and len(q["question"]) < 90 and len(q["answer"]) < 40:
            picked[c].append(q)
    return "\n".join(f"Hỏi: {q['question']}\nĐáp: {q['answer']}" for qs in picked.values() for q in qs)


READ_PROMPT = """Bạn trả lời câu hỏi chỉ dựa trên bảng dưới đây.
Quy tắc đáp án:
- Chỉ in ra đáp án, không giải thích, không lặp lại câu hỏi.
- Ngắn nhất có thể; ưu tiên chép nguyên văn giá trị trong bảng.
- Câu hỏi có/không: trả lời Có hoặc Không.
- Nhiều giá trị: nối bằng dấu phẩy.
- Bảng không có thông tin để trả lời: Null.

Ví dụ phong cách đáp án (lấy từ tập train):
{examples}

Bảng: {title} ({note})
{table}

Câu hỏi: {question}
Đáp:"""

LOCATE_PROMPT = """Bạn là bộ định vị ô trong bảng. Dòng 'Cột' cho tên từng cột; mỗi dòng sau là một hàng. ID của ô = ID hàng + ID cột (ví dụ r3 và c2 thành r3c2).
Bảng: {title}
{cells}

Câu hỏi: {question}

Chọn đúng MỘT ID của ô chứa thông tin trả lời câu hỏi (ô chứa đáp án, không phải ô lặp lại thông tin đã có trong câu hỏi). Chỉ in ra ID (ví dụ r3c2), không giải thích."""


def read(t: Table, question: str, fmt: str, examples: str, keep_rows: set[int] | None = None):
    prompt = READ_PROMPT.format(examples=examples, title=t.record["table_title"], note=FMT_NOTE[fmt],
                                table=t.render(fmt, keep_rows), question=question)
    text, tok, _ = llm(prompt, "read")
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return re.sub(r"^(đáp án|đáp)\s*:\s*", "", line, flags=re.IGNORECASE).strip() or "Null", tok


def grid_text(t: Table) -> str:
    ncol = max((len(r) for r in t.rows + t.headers), default=0)
    paths = [" › ".join(dict.fromkeys(h[c] for h in t.headers if c < len(h) and h[c])) for c in range(ncol)]
    seen, k = {p: paths.count(p) for p in paths}, {}
    for i, p in enumerate(paths):
        if seen[p] > 1:
            k[p] = k.get(p, 0) + 1
            paths[i] = f"{p} [{k[p]}]"
    lines = ["Cột: " + " | ".join(f"c{c} = {p}" for c, p in enumerate(paths))]
    return "\n".join(lines + [f"r{r}: " + " | ".join(row) for r, row in enumerate(t.rows)])


def locate(t: Table, question: str) -> tuple[tuple[int, int] | None, int]:
    text, tok, _ = llm(LOCATE_PROMPT.format(title=t.record["table_title"], cells=grid_text(t), question=question),
                       "locate")
    ids = re.findall(r"\br(\d+)c(\d+)\b", text, flags=re.IGNORECASE)
    if not ids:
        return None, tok
    r, c = map(int, ids[-1])
    ok = r < len(t.rows) and c < len(t.rows[r])
    return ((r, c) if ok else None), tok


EMIT_MAX_WORDS = 4  # train: ô <= 4 từ thì gold là nguyên ô ở 84-96% câu tra cứu


def clean_cell(value: str) -> str:
    return re.sub(r"\s*\[\d+\]", "", value).strip()


def is_question_cell(value: str, question: str) -> bool:
    return contained(value, " ".join(syllables(question, strip_paren=False)))


YN_POS = {"có", "đúng", "phải", "co"}
YN_NEG = {"không", "sai", "không phải", "chưa"}


def verbalize(question: str, prediction: str) -> str:
    """Đổi từ Yes/No theo đuôi câu hỏi; từ vựng đếm trên train, giữ nguyên cực tính."""
    p = normalize_text(prediction)
    if p not in YN_POS | YN_NEG:
        return prediction
    tail = normalize_text(question).rstrip("?").strip()[-25:]
    if p in YN_NEG:
        return "Sai" if "đúng hay sai" in tail else "Không"
    if "đúng không" in tail or "đúng hay sai" in tail:
        return "Đúng"
    if "phải không" in tail:
        return "Phải"
    return "Có"
