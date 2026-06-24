from __future__ import annotations

import os
import sys
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


MODEL_ALIASES: Dict[str, Tuple[str, str]] = {
    "qwen3-8b": ("openrouter", "qwen/qwen3-8b"),
    "llama-3.1-8b-it": ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
}

DEFAULT_OPENROUTER_PROVIDERS: Dict[str, Dict[str, List[str]]] = {
    "qwen/qwen3-8b": {"only": ["atlas-cloud/fp8"]},
    "meta-llama/llama-3.1-8b-instruct": {"only": ["deepinfra/bf16"]},
}

MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # model_name_substring: (input_cost_per_token, output_cost_per_token)
    "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
    "gpt-3.5-turbo": (0.50 / 1_000_000, 1.50 / 1_000_000),
}


def _split_keys(s: str) -> List[str]:
    raw: List[str] = []
    for part in s.replace(";", ",").replace("\n", ",").split(","):
        p = part.strip()
        if p:
            raw.append(p)
    return raw


def _dedupe_keep_order(keys: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def get_openai_api_keys() -> List[str]:
    """
    Accepted env vars (priority):
      - GPT_API_KEYS
      - GPT_API_KEY_1..N
      - GPT_API_KEY (single key or CSV)
      - OPENAI_API_KEY
    """
    keys: List[str] = []

    multi = os.environ.get("GPT_API_KEYS")
    if multi:
        keys.extend(_split_keys(multi))

    for i in range(1, 51):
        k = os.environ.get(f"GPT_API_KEY_{i}")
        if k and k.strip():
            keys.append(k.strip())

    single = os.environ.get("GPT_API_KEY")
    if single and single.strip():
        if "," in single or ";" in single or "\n" in single:
            keys.extend(_split_keys(single))
        else:
            keys.append(single.strip())

    fallback = os.environ.get("OPENAI_API_KEY")
    if fallback and fallback.strip():
        keys.append(fallback.strip())

    out = _dedupe_keep_order(keys)
    if not out:
        raise RuntimeError(
            "Missing OpenAI key. Set GPT_API_KEY/GPT_API_KEYS or OPENAI_API_KEY."
        )
    return out


def get_openrouter_api_keys() -> List[str]:
    """
    Accepted env vars (priority):
      - OPENROUTER_API_KEYS
      - OPENROUTER_API_KEY_1..N
      - OPENROUTER_API_KEY (single key or CSV)
    """
    keys: List[str] = []

    multi = os.environ.get("OPENROUTER_API_KEYS")
    if multi:
        keys.extend(_split_keys(multi))

    for i in range(1, 51):
        k = os.environ.get(f"OPENROUTER_API_KEY_{i}")
        if k and k.strip():
            keys.append(k.strip())

    single = os.environ.get("OPENROUTER_API_KEY")
    if single and single.strip():
        if "," in single or ";" in single or "\n" in single:
            keys.extend(_split_keys(single))
        else:
            keys.append(single.strip())

    out = _dedupe_keep_order(keys)
    if not out:
        raise RuntimeError(
            "Missing OpenRouter key. Set OPENROUTER_API_KEY or OPENROUTER_API_KEYS."
        )
    return out


def parse_model_spec(model: str) -> Tuple[str, str]:
    """
    Parse model id:
      - openai/gpt-4o-mini            -> ("openai", "gpt-4o-mini")
      - openrouter/qwen/qwen3-8b      -> ("openrouter", "qwen/qwen3-8b")
      - qwen3-8b                      -> ("openrouter", "qwen/qwen3-8b")
      - llama-3.1-8b-it               -> ("openrouter", "meta-llama/llama-3.1-8b-instruct")
      - gpt-4o-mini                   -> ("openai", "gpt-4o-mini")
    """
    s = str(model or "").strip()
    if not s:
        raise ValueError("Model id is empty.")

    low = s.lower()
    if low.startswith("local:") or low.startswith("local/"):
        raise ValueError("Local provider has been removed. Use openai/<model> or openrouter/<model>.")

    if low in MODEL_ALIASES:
        return MODEL_ALIASES[low]

    if "/" in s:
        provider, rest = s.split("/", 1)
        p = provider.strip().lower()
        if p in {"openai", "openrouter"}:
            if not rest.strip():
                raise ValueError(f"Invalid model id: {model!r}")
            return p, rest.strip()
    return "openai", s


def _usage_get(usage: Any, *names: str) -> Any:
    for name in names:
        if isinstance(usage, dict):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        if value is not None:
            return value
    return None


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_usage(usage: Any) -> Dict[str, Any]:
    prompt_tokens = _to_int(_usage_get(usage, "prompt_tokens", "input_tokens"))
    completion_tokens = _to_int(_usage_get(usage, "completion_tokens", "output_tokens"))
    total_tokens = _to_int(
        _usage_get(usage, "total_tokens"),
        default=prompt_tokens + completion_tokens,
    )

    normalized: Dict[str, Any] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    cost_usd = _to_float_or_none(_usage_get(usage, "cost_usd", "cost"))
    if cost_usd is not None:
        normalized["cost_usd"] = cost_usd
    return normalized


def calculate_call_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    model_lower = model.lower()
    if "/" in model_lower:
        _, model_name = model_lower.split("/", 1)
    else:
        model_name = model_lower

    input_price, output_price = MODEL_PRICING["gpt-4o-mini"]
    for name, prices in MODEL_PRICING.items():
        if name in model_name:
            input_price, output_price = prices
            break

    return (prompt_tokens * input_price) + (completion_tokens * output_price)


def usage_cost_usd(model: str, usage: Dict[str, Any]) -> float:
    provided_cost = usage.get("cost_usd", usage.get("cost"))
    if provided_cost is not None:
        try:
            return float(provided_cost)
        except (TypeError, ValueError):
            pass
    return calculate_call_cost(
        model,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
    )


def _openrouter_provider_for_model(
    model_name: str,
    explicit_provider: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if explicit_provider is not None:
        return explicit_provider

    provider = DEFAULT_OPENROUTER_PROVIDERS.get(str(model_name).strip().lower())
    if provider is None:
        return None
    return {"only": list(provider["only"])}


@dataclass
class GenConfig:
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 2048
    timeout: int = 60
    openrouter_provider: Optional[Dict[str, Any]] = None


class LLMZeroShotClient:
    """
    Zero-shot LLM wrapper for OpenAI + OpenRouter.
    """

    def __init__(
        self,
        openai_api_keys: Optional[List[str]] = None,
        openrouter_api_keys: Optional[List[str]] = None,
        openrouter_api_base: str = "https://openrouter.ai/api/v1",
    ):
        self._openai_keys = openai_api_keys
        self._openrouter_keys = openrouter_api_keys
        self._openai_idx = 0
        self._openrouter_idx = 0
        self._openrouter_api_base = openrouter_api_base.rstrip("/")
        self._thread_local = threading.local()

        self._OpenAI = None
        self._openai_client = None
        self._maybe_init_openai_client()

    def _maybe_init_openai_client(self) -> None:
        keys = self._openai_keys
        if keys is None:
            try:
                keys = get_openai_api_keys()
            except RuntimeError:
                return
            self._openai_keys = keys

        if not keys:
            return

        try:
            from openai import OpenAI
        except Exception as e:
            raise RuntimeError("Missing dependency `openai`. Install it: pip install openai") from e

        self._OpenAI = OpenAI
        self._openai_client = OpenAI(api_key=keys[self._openai_idx])

    def _rotate_openai_key(self) -> bool:
        keys = self._openai_keys or []
        if self._OpenAI is None or self._openai_client is None or self._openai_idx + 1 >= len(keys):
            return False
        self._openai_idx += 1
        print(
            f"[key-rotate] OpenAI key {self._openai_idx + 1}/{len(keys)}",
            file=sys.stderr,
            flush=True,
        )
        self._openai_client = self._OpenAI(api_key=keys[self._openai_idx])
        return True

    def _rotate_openrouter_key(self) -> bool:
        keys = self._openrouter_keys
        if keys is None:
            try:
                keys = get_openrouter_api_keys()
            except RuntimeError:
                return False
            self._openrouter_keys = keys

        if self._openrouter_idx + 1 >= len(keys):
            return False
        self._openrouter_idx += 1
        print(
            f"[key-rotate] OpenRouter key {self._openrouter_idx + 1}/{len(keys)}",
            file=sys.stderr,
            flush=True,
        )
        return True

    @staticmethod
    def _is_quota_exhausted(err: BaseException) -> bool:
        blob = (repr(err) + " " + str(err)).upper()
        return ("429" in blob) or ("RATE_LIMIT" in blob) or ("QUOTA" in blob)

    @staticmethod
    def _openrouter_input_from_prompt(prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ]

    @staticmethod
    def _extract_openrouter_output_text(payload: Dict[str, Any]) -> str:
        parts: List[str] = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content_item in item.get("content", []) or []:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") == "output_text":
                    text = content_item.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
        return "".join(parts).strip()

    def _generate_openai(self, model_name: str, prompt: str, cfg: GenConfig) -> str:
        if self._openai_client is None:
            self._maybe_init_openai_client()
        if self._openai_client is None:
            raise RuntimeError(
                "OpenAI client is unavailable. Set GPT_API_KEY/GPT_API_KEYS or OPENAI_API_KEY."
            )

        response = self._openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens,
        )
        usage = getattr(response, "usage", None)
        if usage:
            self._thread_local.last_usage = _normalize_usage(usage)
        else:
            self._thread_local.last_usage = None

        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            return content.strip() if content else ""
        return ""

    def _generate_openrouter(self, model_name: str, prompt: str, cfg: GenConfig) -> str:
        try:
            import requests  # type: ignore
        except Exception as e:
            raise RuntimeError("Missing dependency `requests`. Install it: pip install requests") from e

        if self._openrouter_keys is None:
            self._openrouter_keys = get_openrouter_api_keys()
        if not self._openrouter_keys:
            raise RuntimeError("OpenRouter client is unavailable: missing OPENROUTER_API_KEY.")

        api_key = self._openrouter_keys[self._openrouter_idx]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": model_name,
            "input": self._openrouter_input_from_prompt(prompt),
            "max_output_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
        }
        if cfg.top_p is not None:
            body["top_p"] = cfg.top_p
        openrouter_provider = _openrouter_provider_for_model(model_name, cfg.openrouter_provider)
        if openrouter_provider is not None:
            body["provider"] = openrouter_provider

        url = f"{self._openrouter_api_base}/responses"
        resp = requests.post(url, headers=headers, json=body, timeout=cfg.timeout)
        if resp.status_code != 200:
            excerpt = (resp.text or "").strip()
            if len(excerpt) > 2000:
                excerpt = excerpt[:2000] + "...(truncated)"
            raise RuntimeError(f"OpenRouter request failed (status={resp.status_code}): {excerpt}")

        data = resp.json()
        usage = data.get("usage")
        if usage:
            self._thread_local.last_usage = _normalize_usage(usage)
        else:
            self._thread_local.last_usage = None

        text = self._extract_openrouter_output_text(data)
        if text:
            return text
        raise RuntimeError("OpenRouter response did not contain any output_text content.")

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        config: Optional[GenConfig] = None,
        max_retries: int = 4,
        retry_delay: float = 15,
    ) -> str:
        self._thread_local.last_usage = None
        cfg = config or GenConfig()
        provider, model_name = parse_model_spec(model)
        last_err: Optional[BaseException] = None

        for attempt in range(max_retries):
            try:
                if provider == "openai":
                    res = self._generate_openai(model_name, prompt, cfg)
                elif provider == "openrouter":
                    res = self._generate_openrouter(model_name, prompt, cfg)
                else:
                    raise ValueError(
                        "Unsupported provider: "
                        f"{provider}. Use openai/<model> or openrouter/<model>."
                    )

                if not getattr(self._thread_local, "last_usage", None):
                    prompt_est = max(1, int(len(prompt.split()) * 1.4))
                    comp_est = max(1, int(len(res.split()) * 1.4))
                    self._thread_local.last_usage = {
                        "prompt_tokens": prompt_est,
                        "completion_tokens": comp_est,
                        "total_tokens": prompt_est + comp_est,
                    }
                return res
            except Exception as e:
                last_err = e
                if self._is_quota_exhausted(e):
                    if provider == "openai" and self._rotate_openai_key():
                        continue
                    if provider == "openrouter" and self._rotate_openrouter_key():
                        continue
                remaining = max_retries - attempt - 1
                print(
                    f"[retry] Attempt {attempt + 1}/{max_retries} failed: {e!r}. "
                    f"Retrying in {retry_delay}s ({remaining} left)...",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(retry_delay)

        raise RuntimeError(f"Generation failed for model={model}. Last error: {last_err!r}") from last_err

    def shutdown(self) -> None:
        return None
