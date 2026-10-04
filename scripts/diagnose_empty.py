"""Chẩn đoán đáp án rỗng/JSON hỏng của agent B: chạy lại đúng prompt, ghi finish_reason và đuôi output,
so sánh greedy (T=0, như v7/v8) với cấu hình Qwen3 khuyến nghị cho thinking (T=0.6, top_p=0.95, top_k=20).

python scripts/diagnose_empty.py --split dev --file memxam_sckv.runv8dev
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from evaluation.normalization import normalize_text  # noqa: E402
from mas_tqa.client import strip_think  # noqa: E402
from mas_tqa.methods import _parse_evid, kv_prefix  # noqa: E402
from scripts.analyze_memxam import correct  # noqa: E402

CONFIGS = {"greedy": {"temperature": 0.0}, "qwen_rec": {"temperature": 0.6, "top_p": 0.95, "top_k": 20}}


def call(prompt: str, cfg: dict) -> dict:
    body = {"model": os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B"), "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 6000, "chat_template_kwargs": {"enable_thinking": True}, **cfg,
            **json.loads(os.environ.get("VLLM_EXTRA_BODY") or "{}")}
    r = requests.post(f"{os.environ['VLLM_BASE_URL'].rstrip('/')}/chat/completions", json=body, timeout=600,
                      headers={"Authorization": f"Bearer {os.environ['VLLM_API_KEY']}"})
    r.raise_for_status()
    d = r.json()
    ch = d["choices"][0]
    content = ch["message"].get("content") or ""
    return {"finish": ch.get("finish_reason"), "completion_tokens": (d.get("usage") or {}).get("completion_tokens"),
            "content_tail": strip_think(content)[-300:], "answer": _parse_evid(content)[0]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--file", default="memxam_sckv.runv8dev")
    ap.add_argument("--out", default="outputs/mas_tqa/eval/diagnose_empty_B.jsonl")
    args = ap.parse_args()
    qas = {q["qa_id"]: q for q in load_qas_records(ROOT / f"dataset/qas_{args.split}.json")}
    recs = [json.loads(x) for x in (ROOT / f"outputs/mas_tqa/qas_{args.split}/{args.file}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    todo = [r for r in recs if not normalize_text(r["trace"]["B"])]
    print(f"{len(todo)} câu B rỗng", flush=True)

    def one(r: dict) -> dict:
        qa = qas[r["qa_id"]]
        prompt = kv_prefix(qa) + f"BÂY GIỜ TRẢ LỜI CÂU HỎI SAU.\nCÂU HỎI: {qa['question']}\nĐẦU RA: "
        out = {"qa_id": r["qa_id"]}
        for name, cfg in CONFIGS.items():
            try:
                res = call(prompt, cfg)
            except Exception as e:  # ghi lỗi để không mất cả lượt
                res = {"finish": f"error {e!r}"[:120], "answer": ""}
            res["correct"] = correct(res["answer"], qa) if res.get("answer") else 0
            out[name] = res
        return out

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, todo))
    (ROOT / args.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    for name in CONFIGS:
        fin = [x[name].get("finish") for x in rows]
        empty = sum(not normalize_text(x[name].get("answer", "")) for x in rows)
        print(f"{name:<9} finish={ {f: fin.count(f) for f in set(fin)} }  rỗng {empty}/{len(rows)}  đúng {sum(x[name]['correct'] for x in rows)}")


if __name__ == "__main__":
    main()
