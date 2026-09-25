"""Stage 3 pass: run the answerability gate over the spliced v3lite answers (resumable JSONL).

Reads the solver records written by ``run_v3lite.py``, splices ``v3lite`` over ``control`` (a
question H1 left untouched has a byte-identical prompt, so the control answer is the v3lite answer),
applies the free Stage 4 rule formatter, and calls the gate on every question whose formatted answer
is ``Null``. Questions with a real answer cost nothing.

The gate only ever touches a ``Null``, and on a failed call the ``Null`` stands. It can still make a
correct answer wrong: ``Null`` is itself a valid gold answer for 45/992 test questions, and the gate
replaced 4 of those.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from poma_v3lite.answerability import run_gate  # noqa: E402
from poma_v3lite.formatter import format_candidates  # noqa: E402

DEFAULT_MODEL = "openrouter/qwen/qwen3-8b"


def load_records(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Latest successful record per (arm, qa_id)."""
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if "error" not in row:
                records[(row["arm"], str(row["qa_id"]))] = row
    return records


def splice(records: dict[tuple[str, str], dict[str, Any]], qa_ids: list[str]) -> dict[str, list[str]]:
    """v3lite raw candidates per qa_id: the v3lite record if H1 changed the table, else control."""
    out: dict[str, list[str]] = {}
    for qa_id in qa_ids:
        row = records.get(("v3lite", qa_id)) or records.get(("control", qa_id))
        if row is None:
            raise SystemExit(f"no solver record for qa_id={qa_id}")
        out[qa_id] = list(row.get("raw_prediction") or row.get("prediction") or [])
    return out


def _gate_caller(qa_id: str):
    """Return ``generate_json(prompt, schema_dict, step)`` bound to one question."""
    from src.contracts.structured_outputs import ResponseSchema
    from src.services.llm_client import LLMClient

    def generate_json(prompt: str, schema: dict[str, Any], step: str) -> dict[str, Any]:
        llm = LLMClient()
        set_qa_id = getattr(llm, "set_qa_id", None)
        if callable(set_qa_id):
            set_qa_id(qa_id)
        return llm.generate_json(
            prompt,
            schema=ResponseSchema(name=f"v3lite_{step}.v1", version="1", json_schema=schema),
            agent_name=step,
            prompt_name=step,
        )

    return generate_json


def process(qa: dict[str, Any], table: dict[str, Any], candidates: list[str]) -> dict[str, Any]:
    """Format the spliced candidates and, when they collapse to ``Null``, run the gate."""
    qa_id = str(qa["qa_id"])
    formatted = format_candidates(candidates)
    answer = formatted[0] if formatted else "Null"
    record: dict[str, Any] = {"qa_id": qa_id, "table_id": str(qa["table_id"]), "formatted": formatted or ["Null"]}
    outcome = run_gate(str(qa["question"]).strip(), table, answer, generate_json=_gate_caller(qa_id))
    record.update({
        "prediction": [outcome.answer] + [a for a in formatted[1:] if a != outcome.answer],
        "fired": outcome.fired,
        "changed": outcome.changed,
        "calls": outcome.calls,
        "needed_evidence": outcome.needed_evidence,
        "rows_found": outcome.rows_found,
        "error": outcome.error,
    })
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--records", type=Path, required=True, help="Solver JSONL from run_v3lite.py")
    parser.add_argument("--out", type=Path, required=True, help="Resumable JSONL of gate records")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", nargs="+", default=["alibaba"])
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args(argv)

    import os

    from dotenv import load_dotenv  # type: ignore

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    os.environ["POMA_LLM_MODEL"] = args.model
    os.environ["POMA_OPENROUTER_PROVIDER"] = ",".join(args.provider)

    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}
    records = load_records(args.records)
    spliced = splice(records, [str(qa["qa_id"]) for qa in qas])

    todo = [qa for qa in qas if not format_candidates(spliced[str(qa["qa_id"])])]
    done = set()
    if args.out.exists():
        done = {str(json.loads(l)["qa_id"]) for l in args.out.read_text(encoding="utf-8").splitlines()
                if l.strip() and json.loads(l).get("error") is None}
    pending = [qa for qa in todo if str(qa["qa_id"]) not in done]
    print(f"Null after formatting: {len(todo)}/{len(qas)}; {len(done)} gated already, {len(pending)} to run", flush=True)
    if not pending:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    lock, written, changed = threading.Lock(), 0, 0
    with args.out.open("a", encoding="utf-8") as sink, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(process, qa, tables[str(qa["table_id"])], spliced[str(qa["qa_id"])])
            for qa in pending
        ]
        for future in as_completed(futures):
            record = future.result()
            with lock:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                written += 1
                changed += bool(record["changed"])
                if written % 10 == 0:
                    print(f"{written}/{len(pending)} (recovered {changed})", flush=True)
    print(f"done: {written} gated, {changed} Null replaced by an answer", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
