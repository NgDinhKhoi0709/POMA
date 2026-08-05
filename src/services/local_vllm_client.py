"""vLLM-backed local inference for long-context Kaggle runs."""

from __future__ import annotations

from typing import Any

from src.config.settings import LocalModelConfig
from src.services.local_transformers_client import ContextOverflowError


class LocalVLLMClient:
    """Thin deterministic wrapper over vLLM's paged-attention engine."""

    def __init__(
        self,
        *,
        llm: Any,
        model_id: str,
        max_input_tokens: int,
        default_max_new_tokens: int,
        quantization: str,
    ) -> None:
        self._llm = llm
        self._model_id = model_id
        self._max_input_tokens = max_input_tokens
        self._default_max_new_tokens = default_max_new_tokens
        self._quantization = quantization

    @classmethod
    def from_pretrained(cls, config: LocalModelConfig) -> "LocalVLLMClient":
        try:
            from vllm import LLM
        except ImportError as exc:  # pragma: no cover - exercised on Kaggle
            raise RuntimeError(
                "POMA_LOCAL_BACKEND=vllm requires the vllm package. "
                "Install the Kaggle notebook dependencies first."
            ) from exc

        llm = LLM(
            model=config.model_id,
            dtype="float16",
            trust_remote_code=True,
            quantization="bitsandbytes",
            max_model_len=config.max_model_len,
            gpu_memory_utilization=config.vllm_gpu_memory_utilization,
            max_num_seqs=1,
            enable_prefix_caching=True,
            enforce_eager=True,
        )
        return cls(
            llm=llm,
            model_id=config.model_id,
            max_input_tokens=config.max_input_tokens,
            default_max_new_tokens=config.max_new_tokens,
            quantization=config.quantization,
        )

    def _format_prompt(self, prompt: str) -> str:
        tokenizer = self._llm.get_tokenizer()
        apply_template = getattr(tokenizer, "apply_chat_template", None)
        if not callable(apply_template):
            return prompt
        return apply_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )

    @staticmethod
    def _token_count(tokenizer: Any, text: str) -> int:
        return len(tokenizer.encode(text))

    def generate_with_usage(
        self,
        prompt: str,
        *,
        max_new_tokens: int | None = None,
    ) -> tuple[str, dict[str, object]]:
        from vllm import SamplingParams

        rendered_prompt = self._format_prompt(prompt)
        tokenizer = self._llm.get_tokenizer()
        prompt_tokens = self._token_count(tokenizer, rendered_prompt)
        if prompt_tokens > self._max_input_tokens:
            raise ContextOverflowError(
                f"Prompt has {prompt_tokens} tokens; "
                f"max_input_tokens={self._max_input_tokens}"
            )

        requested_tokens = max_new_tokens or self._default_max_new_tokens
        outputs = self._llm.generate(
            [rendered_prompt],
            SamplingParams(temperature=0.0, max_tokens=requested_tokens),
        )
        output = outputs[0]
        completion = output.outputs[0]
        text = completion.text.strip()
        completion_tokens = len(completion.token_ids)
        actual_prompt_tokens = len(getattr(output, "prompt_token_ids", [])) or prompt_tokens
        return text, {
            "prompt_tokens": actual_prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": actual_prompt_tokens + completion_tokens,
            "cost_usd": None,
            "model": self._model_id,
            "quantization": self._quantization,
        }
