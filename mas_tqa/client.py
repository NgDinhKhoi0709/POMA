"""Client tối giản cho endpoint vLLM tương thích OpenAI (/v1/chat/completions)."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

import requests

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens


@dataclass
class VLLMClient:
    base_url: str = field(default_factory=lambda: os.environ["VLLM_BASE_URL"].rstrip("/"))
    api_key: str = field(default_factory=lambda: os.environ["VLLM_API_KEY"])
    model: str = field(default_factory=lambda: os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B"))
    timeout: int = 600

    def chat(
        self,
        prompt: str | list[dict],
        *,
        thinking: bool = True,
        n: int = 1,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int | None = None,
        min_p: float | None = None,
        max_tokens: int | None = 6000,
        retries: int = 4,
    ) -> tuple[list[str], Usage]:
        """prompt: chuỗi (một tin nhắn user) hoặc danh sách messages (có system). max_tokens=None: để server
        dùng toàn bộ ngữ cảnh còn lại (Qwen3 khuyến nghị đầu ra dài cho chế độ thinking)."""
        body = {
            "model": self.model,
            "messages": prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}],
            "n": n,
            "temperature": temperature,
            "top_p": top_p,
            **({"max_tokens": max_tokens} if max_tokens is not None else {}),
            **({"top_k": top_k} if top_k is not None else {}),
            **({"min_p": min_p} if min_p is not None else {}),
            "chat_template_kwargs": {"enable_thinking": thinking},
            # Trường bổ sung cho endpoint khác vLLM, vd. ghim provider OpenRouter:
            # VLLM_EXTRA_BODY='{"provider": {"only": ["alibaba"]}}'
            **json.loads(os.environ.get("VLLM_EXTRA_BODY") or "{}"),
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        for attempt in range(retries):
            try:
                r = requests.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                u = data.get("usage") or {}
                usage = Usage(1, int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0))
                return [c["message"].get("content") or "" for c in data["choices"]], usage
            except Exception as e:
                resp = getattr(e, "response", None)
                if attempt == retries - 1 or (resp is not None and 400 <= resp.status_code < 500 and resp.status_code != 429):
                    raise  # lỗi 4xx (vd. vượt ngữ cảnh) không tự hết khi thử lại
                time.sleep(5 * (attempt + 1))
        raise AssertionError("unreachable")


def strip_think(text: str) -> str:
    text = _THINK_RE.sub("", text)
    # Thinking bị cắt do max_tokens: không có </think> nên không có đáp án.
    return "" if "<think>" in text else text.strip()


def parse_json(text: str) -> dict | None:
    text = strip_think(text)
    m = _JSON_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


_FA_RE = re.compile(r'"final_answer"\s*:\s*"((?:[^"\\]|\\.)*)"')


def final_answer(text: str) -> str:
    obj = parse_json(text)
    if obj is not None and "final_answer" in obj:
        v = obj["final_answer"]
        return "Null" if v is None else str(v).strip()
    body = strip_think(text)
    m = _FA_RE.search(body)  # JSON hỏng nhưng vẫn có trường final_answer
    return json.loads(f'"{m.group(1)}"', strict=False).strip() if m else body
