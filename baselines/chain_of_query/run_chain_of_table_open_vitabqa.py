"""Chạy Chain-of-Table trên Open-ViTabQA với backbone tự host (vLLM, OpenAI-compatible).

Giữ nguyên luồng của run_chain_of_table.py (dynamic_chain_exec_one_sample rồi simple_query, T=0, 200 token, prompt
WikiTQ vì DATASET="wiki"); chỉ đổi nguồn dữ liệu và ghi kết quả theo định dạng mas_tqa để chấm chung.
Thinking của Qwen3 bị tắt: các bước của Chain-of-Table chỉ cho 150–300 token đầu ra.
Cần OPENAI_BASE_URL=<vllm>/v1 và OPENAI_API_KEY=<key vLLM> trong môi trường.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT)]

from chain.operations import simple_query  # noqa: E402
from chain.utils.chain import dynamic_chain_exec_one_sample, get_table_info, get_table_log  # noqa: E402
from chain.utils.llm import MyChatGPT  # noqa: E402
from evaluation.io import load_qas_records  # noqa: E402
from mas_tqa.code_agent import table_rows  # noqa: E402
from mas_tqa.data import tables  # noqa: E402


class CountingLLM(MyChatGPT):
    """MyChatGPT + tắt thinking + đếm lệnh gọi/token."""

    def __init__(self, model_name: str, key: str):
        super().__init__(model_name, key)
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        create = self.client.chat.completions.create

        def counted(**kw):
            r = create(**kw, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
            self.calls += 1
            if r.usage:
                self.prompt_tokens += r.usage.prompt_tokens
                self.completion_tokens += r.usage.completion_tokens
            return r

        self.client.chat.completions.create = counted


def table_text(table_id: str) -> list[list[str]]:
    """Hàng đầu là header; pad/cắt các hàng cho đủ số cột, tên cột trùng thêm hậu tố để DataFrame hợp lệ."""
    rows = table_rows(table_id)
    header, seen = [], {}
    for h in rows[0]:
        seen[h] = seen.get(h, 0) + 1
        header.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
    n = len(header)
    return [header] + [(r + [""] * n)[:n] for r in rows[1:]]


def caption(table_id: str) -> str:
    import re

    return re.sub(r"_\d+$", "", str(tables()[table_id].get("table_title") or "")).strip()


def solve(qa: dict, llm: CountingLLM) -> str:
    sample = {"statement": qa["question"], "table_caption": caption(qa["table_id"]),
              "table_text": table_text(qa["table_id"]), "cleaned_statement": qa["question"], "chain": []}
    proc, _ = dynamic_chain_exec_one_sample(sample=sample, llm=llm)
    out = simple_query(sample=proc, table_info=get_table_info(proc), llm=llm, use_demo=True,
                       llm_options=llm.get_model_options(temperature=0.0, per_example_max_decode_steps=200,
                                                         per_example_top_p=1.0))
    result = ""
    for info in get_table_log(out):
        if info["act_chain"] and "query" in info["act_chain"][-1]:
            result = info["cotable_result"]
    return str(result).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--qas", default="dataset/qas_test.json")
    ap.add_argument("--out", default="outputs/mas_tqa/qas_test/chain_of_table.runq1.jsonl")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    if not os.environ.get("OPENAI_BASE_URL"):
        raise SystemExit("Đặt OPENAI_BASE_URL=<vllm>/v1 để không gọi nhầm OpenAI thật.")
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(x)["qa_id"] for x in out.read_text(encoding="utf-8").splitlines() if x.strip()} if out.exists() else set()
    todo = [q for q in load_qas_records(ROOT / args.qas)[: args.limit] if q["qa_id"] not in done]
    print(f"chain_of_table: {len(todo)} câu cần chạy ({len(done)} đã có)", flush=True)
    key, lock = os.environ["OPENAI_API_KEY"], threading.Lock()

    def one(qa: dict) -> dict:
        llm = CountingLLM(args.model, key)
        pred = solve(qa, llm)
        return {"qa_id": qa["qa_id"], "table_id": qa["table_id"], "question": qa["question"],
                "groundtruth": qa["answer"], "method": "chain_of_table", "run": "q1", "prediction": [pred],
                "calls": llm.calls, "prompt_tokens": llm.prompt_tokens, "completion_tokens": llm.completion_tokens}

    with out.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(one, q) for q in todo]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                rec = f.result()
            except Exception as e:  # câu lỗi không ghi, lần chạy sau (resume) làm lại
                print(f"[error] {e!r}", flush=True)
                continue
            with lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
            if i % 50 == 0:
                print(f"{i}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
