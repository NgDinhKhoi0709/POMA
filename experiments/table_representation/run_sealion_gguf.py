"""CPU GGUF smoke run for Llama-SEA-LION-v3-8B-IT.

This VM has no GPU. The official Kaggle path uses 4-bit bitsandbytes on a T4.
Here we mmap the official Q4_K_M GGUF through llama.cpp.

    python -m experiments.table_representation.run_sealion_gguf \\
        --limit 50 --table-mode auto --prompt-style few_shot
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from preprocessing.loader import DatasetLoader
from preprocessing.representation import FlattenedTable

from .encodings import encode_table
from .pruning import prune_table

DEFAULT_MODEL_PATH = Path.home() / ".cache/poma-models/Llama-SEA-LION-v3-8B-IT-Q4_K_M.gguf"
DEFAULT_MODEL_ID = "aisingapore/Llama-SEA-LION-v3-8B-IT-GGUF"
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_FULL_CHAR_BUDGET = 2800

TABLE_MODES = ("flatten_v1", "lexical_subtable", "markdown", "auto")
PROMPT_STYLES = ("zero_shot", "few_shot")

ZERO_SHOT_PROMPT = """Chỉ dùng TABLE_STR để trả lời QUESTION.

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

FEW_SHOT_PROMPT = """Bạn là hệ thống TableQA tiếng Việt. Chỉ dùng TABLE_STR. Không dùng kiến thức ngoài bảng.

Quy tắc:
- Tra cứu: copy đúng ô (không thêm giải thích).
- Yes/No: dùng đúng cặp từ của câu hỏi (Có phải → Phải/Không; có ... không? → Có/Không; đúng không? → Đúng/Không).
- Đếm "bao nhiêu": đếm số hàng thỏa điều kiện; nếu không có hàng nào thì 0.
- Không đủ thông tin: null.

Ví dụ:
TABLE_STR:
| Người | Quê quán |
| --- | --- |
| An | Hà Nội |
QUESTION: Quê quán của An ở đâu?
OUTPUT: {{"final_answer": "Hà Nội"}}

TABLE_STR:
| Người | Quê quán |
| --- | --- |
| An | Hà Nội |
QUESTION: Tuổi của An là bao nhiêu?
OUTPUT: {{"final_answer": null}}

TABLE_STR:
| Tòa nhà | Cao (m) |
| --- | --- |
| A | 120 |
| B | 160 |
| C | 155 |
QUESTION: Có phải có 2 tòa nhà cao từ 150m trở lên?
OUTPUT: {{"final_answer": "Phải"}}

TABLE_STR:
| Xã | Năm |
| --- | --- |
| An | 2018 |
| Bình | 2019 |
| Chi | 2018 |
QUESTION: Có bao nhiêu xã được công nhận vào năm 2018?
OUTPUT: {{"final_answer": "2"}}

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

_PROMPT_BY_STYLE = {
    "zero_shot": ZERO_SHOT_PROMPT,
    "few_shot": FEW_SHOT_PROMPT,
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", default="dataset/table.json")
    parser.add_argument("--dataset-dir", default="dataset")
    parser.add_argument("--qas", default="dataset/qas_test.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--table-mode", choices=TABLE_MODES, default="auto")
    parser.add_argument("--prompt-style", choices=PROMPT_STYLES, default="few_shot")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--n-threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--max-rows", type=int, default=24)
    parser.add_argument("--max-cols", type=int, default=8)
    parser.add_argument("--output", default="outputs/sealion_gguf_cpu")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def load_qas(path: str) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("qas", payload)
        if isinstance(items, dict):
            items = list(items.values())
        return list(items)
    return list(payload)


def select_items(items: Sequence[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return list(items[:limit])


def parse_final_answer(text: str) -> Optional[str]:
    """Pull `final_answer` from a JSON object, mapping JSON null to dataset Null."""
    match = _JSON_RE.search(text or "")
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "final_answer" not in payload:
        return None
    value = payload.get("final_answer")
    if value is None:
        return "Null"
    return str(value).strip()


def yesno_pair(question: str) -> Optional[Tuple[str, str]]:
    lowered = (question or "").lower()
    if "có phải" in lowered or "phải không" in lowered:
        return ("Phải", "Không")
    if "đúng không" in lowered or lowered.rstrip().endswith("đúng không?"):
        return ("Đúng", "Không")
    if lowered.strip().endswith("không?") or " không?" in lowered:
        return ("Có", "Không")
    return None


def canonicalize_answer(question: str, answer: Optional[str]) -> Optional[str]:
    if answer is None:
        return None
    pair = yesno_pair(question)
    if pair is None:
        return answer
    positive, negative = pair
    key = answer.strip().lower()
    if key in {"yes", "true", "phải", "có", "đúng", "right"}:
        return positive
    if key in {"no", "false", "không", "sai", "wrong"}:
        return negative
    return answer


def build_prompt(*, question: str, table_str: str, prompt_style: str) -> str:
    template = _PROMPT_BY_STYLE.get(prompt_style)
    if template is None:
        raise ValueError(f"Unknown prompt_style={prompt_style!r}")
    return template.format(question=question, table_str=str(table_str or "").strip())


def _flatten_with_title(table: Dict[str, Any]) -> str:
    flattened = FlattenedTable.from_table_data(table)
    body = flattened.to_string()
    title = (flattened.title or "").strip()
    if not title:
        return body
    return f"TITLE: {title}\n{body}" if body else f"TITLE: {title}"


def table_text(
    table: Dict[str, Any],
    question: str,
    mode: str,
    *,
    max_rows: int,
    max_cols: int,
) -> Tuple[str, str]:
    if mode == "flatten_v1":
        return _flatten_with_title(table), "flatten_v1"
    if mode == "markdown":
        return encode_table(table, "markdown").text, "markdown"
    if mode == "lexical_subtable":
        pruned = prune_table(table, question, method="lexical_subtable", max_rows=max_rows, max_cols=max_cols)
        return pruned.text, "lexical_subtable"
    markdown = encode_table(table, "markdown").text
    if len(markdown) <= _FULL_CHAR_BUDGET:
        return markdown, "markdown_full"
    pruned = prune_table(
        table,
        question,
        method="lexical_subtable",
        max_rows=max_rows,
        max_cols=max_cols,
    )
    return pruned.text, "lexical_subtable"


def _load_tables(args: argparse.Namespace) -> Dict[str, Dict[str, Any]]:
    loader = DatasetLoader(dataset_dir=args.dataset_dir)
    tables_path = Path(args.tables)
    if tables_path.exists():
        return loader.load_tables_path(str(tables_path.resolve()))
    return loader.load_tables_path(args.tables)


def _load_llama(model_path: Path, *, n_ctx: int, n_threads: int) -> Any:
    from llama_cpp import Llama

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Missing GGUF at {model_path}. Download "
            f"{DEFAULT_MODEL_ID} Q4_K_M first."
        )
    return Llama(
        model_path=str(model_path),
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=0,
        use_mmap=True,
        use_mlock=False,
        logits_all=False,
        embedding=False,
        verbose=False,
        chat_format="llama-3",
    )


def _completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        qa_id = str(record.get("qa_id") or "").strip()
        if qa_id:
            done.add(qa_id)
    return done


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    tables = _load_tables(args)
    selected = select_items(load_qas(args.qas), limit=args.limit)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_ids = [str(item.get("qa_id")) for item in selected]
    (output_dir / "selected_ids.json").write_text(
        json.dumps(selected_ids, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"# SEA-LION GGUF CPU  n={len(selected)}  "
        f"table_mode={args.table_mode}  prompt={args.prompt_style}"
    )
    for qa_id in selected_ids:
        print(f"- {qa_id}")
    if args.dry_run:
        return 0

    predictions_path = output_dir / "predictions.jsonl"
    traces_path = output_dir / "traces.jsonl"
    done = _completed_ids(predictions_path) if args.resume else set()
    if not args.resume:
        if predictions_path.exists():
            predictions_path.unlink()
        if traces_path.exists():
            traces_path.unlink()

    llm = _load_llama(Path(args.model_path), n_ctx=args.n_ctx, n_threads=args.n_threads)
    records: List[Dict[str, Any]] = []
    if args.resume and predictions_path.exists():
        records = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    pending = [item for item in selected if str(item.get("qa_id")) not in done]
    for item in pending:
        qa_id = str(item.get("qa_id"))
        table_id = str(item.get("table_id"))
        question = str(item.get("question") or "")
        started = time.time()
        table = tables[table_id]
        rendered, used_mode = table_text(
            table,
            question,
            args.table_mode,
            max_rows=args.max_rows,
            max_cols=args.max_cols,
        )
        prompt = build_prompt(question=question, table_str=rendered, prompt_style=args.prompt_style)
        try:
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=args.max_new_tokens,
                temperature=0.0,
                top_p=1.0,
            )
            raw = str(response["choices"][0]["message"].get("content") or "")
            usage = dict(response.get("usage") or {})
            answer = canonicalize_answer(question, parse_final_answer(raw))
            error = None if answer is not None else "json_parse"
        except Exception as exc:  # llama.cpp may raise on context overflow
            raw = ""
            usage = {}
            answer = None
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.time() - started, 2)
        prediction = [] if answer is None else [answer]
        record = {
            "qa_id": qa_id,
            "table_id": table_id,
            "prediction": prediction,
            "table_mode": used_mode,
            "prompt_style": args.prompt_style,
            "n_table_chars": len(rendered),
            "elapsed_sec": elapsed,
            "error": error,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
        records.append(record)
        traces_path.open("a", encoding="utf-8").write(
            json.dumps({"qa_id": qa_id, "raw": raw, "error": error}, ensure_ascii=False) + "\n"
        )
        predictions_path.open("a", encoding="utf-8").write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )
        print(
            f"{qa_id}\tpred={answer!r}\tgold={item.get('answer')!r}\t"
            f"mode={used_mode}\tchars={len(rendered)}\t{elapsed}s\t{error or 'ok'}"
        )

    (output_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
