"""Create a readable JSON view from CoAgt Open_ViTabQA smoke artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_refs(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    qas = payload.get("qas", payload if isinstance(payload, list) else [])
    return {str(qa["qa_id"]): qa for qa in qas}


def compact_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", default="outputs/open_vitabqa_smoke_5_predictions.jsonl")
    parser.add_argument("--refs", default="outputs/open_vitabqa_smoke_5_refs.json")
    parser.add_argument("--eval", default="outputs/open_vitabqa_smoke_5_eval.json")
    parser.add_argument("--summary", default="outputs/open_vitabqa_smoke_5_summary.json")
    parser.add_argument("--output", default="outputs/open_vitabqa_smoke_5_readable.json")
    parser.add_argument("--response-preview-chars", type=int, default=1200)
    args = parser.parse_args()

    predictions = load_jsonl(Path(args.pred))
    refs_by_id = load_refs(Path(args.refs))
    eval_report = json.loads(Path(args.eval).read_text(encoding="utf-8")) if Path(args.eval).exists() else {}
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8")) if Path(args.summary).exists() else {}

    samples = []
    for index, record in enumerate(predictions, start=1):
        qa_id = str(record["qa_id"])
        ref = refs_by_id.get(qa_id, {})
        samples.append(
            {
                "index": index,
                "qa_id": qa_id,
                "source_split": record.get("source_split"),
                "table_id": record.get("table_id"),
                "question": record.get("question"),
                "gold_answer": ref.get("answer", record.get("answer")),
                "prediction": record.get("prediction"),
                "hints": ref.get("hints", []),
                "num_collectors": record.get("num_collectors"),
                "api_calls": record.get("api_calls"),
                "prompt_tokens": record.get("prompt_tokens"),
                "completion_tokens": record.get("completion_tokens"),
                "total_tokens": record.get("total_tokens"),
                "cost_usd": record.get("cost_usd"),
                "response_preview": compact_text(record.get("response", ""), args.response_preview_chars),
            }
        )

    output = {
        "summary": summary,
        "metrics": eval_report.get("metrics", {}),
        "analyses": eval_report.get("analyses", {}),
        "cost": eval_report.get("cost", {}),
        "coverage": eval_report.get("coverage", {}),
        "samples": samples,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "samples": len(samples)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
