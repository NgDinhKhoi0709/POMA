"""CPU GGUF smoke run for Llama-SEA-LION-v3-8B-IT.

This VM has no GPU. The official Kaggle path uses 4-bit bitsandbytes on a T4.
Here we mmap the official Q4_K_M GGUF through llama.cpp and run a small
zero-shot slice (default 10 QAs) with optional lexical table pruning.

    python -m experiments.table_representation.run_sealion_gguf \\
        --limit 10 --table-mode lexical_subtable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from baseline.prompts import build_tableqa_prompt
from preprocessing.loader import DatasetLoader
from preprocessing.representation import FlattenedTable

from .pruning import prune_table

DEFAULT_MODEL_PATH = Path.home() / ".cache/poma-models/Llama-SEA-LION-v3-8B-IT-Q4_K_M.gguf"
DEFAULT_MODEL_ID = "aisingapore/Llama-SEA-LION-v3-8B-IT-GGUF"
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

TABLE_MODES = ("flatten_v1", "lexical_subtable")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", default="dataset/table.json")
    parser.add_argument("--dataset-dir", default="dataset")
    parser.add_argument("--qas", default="dataset/qas_test.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--table-mode", choices=TABLE_MODES, default="lexical_subtable")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--n-threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--output", default="outputs/sealion_gguf_cpu")
    parser.add_argument("--dry-run", action="store_true")
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


def table_text(table: Dict[str, Any], question: str, mode: str) -> str:
    if mode == "lexical_subtable":
        return prune_table(table, question, method="lexical_subtable").text
    flattened = FlattenedTable.from_table_data(table)
    body = flattened.to_string()
    title = (flattened.title or "").strip()
    if not title:
        return body
    return f"TITLE: {title}\n{body}" if body else f"TITLE: {title}"


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
    print(f"# SEA-LION GGUF CPU  n={len(selected)}  table_mode={args.table_mode}")
    for qa_id in selected_ids:
        print(f"- {qa_id}")
    if args.dry_run:
        return 0

    llm = _load_llama(Path(args.model_path), n_ctx=args.n_ctx, n_threads=args.n_threads)
    predictions_path = output_dir / "predictions.jsonl"
    traces_path = output_dir / "traces.jsonl"
    if predictions_path.exists():
        predictions_path.unlink()
    if traces_path.exists():
        traces_path.unlink()

    records: List[Dict[str, Any]] = []
    for item in selected:
        qa_id = str(item.get("qa_id"))
        table_id = str(item.get("table_id"))
        question = str(item.get("question") or "")
        started = time.time()
        table = tables[table_id]
        rendered = table_text(table, question, args.table_mode)
        prompt = build_tableqa_prompt(question=question, table_str=rendered, prompt_style="zero_shot")
        try:
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=args.max_new_tokens,
                temperature=0.0,
                top_p=1.0,
            )
            raw = str(response["choices"][0]["message"].get("content") or "")
            usage = dict(response.get("usage") or {})
            answer = parse_final_answer(raw)
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
            "table_mode": args.table_mode,
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
            f"chars={len(rendered)}\t{elapsed}s\t{error or 'ok'}"
        )

    (output_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
