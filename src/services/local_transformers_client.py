"""Local Hugging Face Transformers client for SEA-LION inference."""

from __future__ import annotations

from typing import Any, Mapping

from src.config.settings import LocalModelConfig


class ContextOverflowError(RuntimeError):
    """Raised when a rendered request cannot fit the local context budget."""


class LocalTransformersClient:
    """Small deterministic inference wrapper around a causal language model."""

    def __init__(
        self,
        *,
        tokenizer: Any,
        model: Any,
        model_id: str,
        max_input_tokens: int,
        default_max_new_tokens: int = 512,
        quantization: str = "nf4",
    ) -> None:
        self._tokenizer = tokenizer
        self._model = model
        self._model_id = model_id
        self._max_input_tokens = max_input_tokens
        self._default_max_new_tokens = default_max_new_tokens
        self._quantization = quantization

    @classmethod
    def from_pretrained(cls, config: LocalModelConfig) -> "LocalTransformersClient":
        """Load the model only when local inference is actually selected."""
        if config.quantization.lower() != "nf4":
            raise ValueError("Only NF4 4-bit quantization is supported for local inference")

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as exc:  # pragma: no cover - exercised on Kaggle
            raise RuntimeError(
                "Local inference requires transformers, bitsandbytes, and torch. "
                "Install the Kaggle notebook dependencies first."
            ) from exc

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            config.model_id,
            trust_remote_code=True,
        )
        if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
            tokenizer.pad_token_id = tokenizer.eos_token_id
        model = AutoModelForCausalLM.from_pretrained(
            config.model_id,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
            attn_implementation="sdpa",
        )
        return cls(
            tokenizer=tokenizer,
            model=model,
            model_id=config.model_id,
            max_input_tokens=config.max_input_tokens,
            default_max_new_tokens=config.max_new_tokens,
            quantization=config.quantization,
        )

    def _format_prompt(self, prompt: str) -> str:
        apply_template = getattr(self._tokenizer, "apply_chat_template", None)
        if not callable(apply_template):
            return prompt
        return apply_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )

    def _move_to_model_device(self, batch: Mapping[str, Any]) -> Mapping[str, Any]:
        device = getattr(self._model, "device", None)
        if device is None:
            return batch
        move_batch = getattr(batch, "to", None)
        if callable(move_batch):
            return move_batch(device)
        return {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in batch.items()
        }

    @staticmethod
    def _sequence_length(sequence: Any) -> int:
        shape = getattr(sequence, "shape", None)
        if shape:
            return int(shape[-1])
        return len(sequence)

    def generate_with_usage(
        self,
        prompt: str,
        *,
        max_new_tokens: int | None = None,
    ) -> tuple[str, dict[str, object]]:
        rendered_prompt = self._format_prompt(prompt)
        encoded = self._move_to_model_device(
            self._tokenizer(rendered_prompt, return_tensors="pt")
        )
        input_ids = encoded["input_ids"]
        prompt_tokens = self._sequence_length(input_ids)
        if prompt_tokens > self._max_input_tokens:
            raise ContextOverflowError(
                f"Prompt has {prompt_tokens} tokens; "
                f"max_input_tokens={self._max_input_tokens}"
            )

        requested_tokens = max_new_tokens or self._default_max_new_tokens
        generated = self._model.generate(
            **encoded,
            max_new_tokens=requested_tokens,
            do_sample=False,
            pad_token_id=getattr(self._tokenizer, "pad_token_id", None)
            or getattr(self._tokenizer, "eos_token_id", None),
            eos_token_id=getattr(self._tokenizer, "eos_token_id", None),
        )
        full_sequence = generated[0]
        completion_ids = full_sequence[prompt_tokens:]
        if self._sequence_length(completion_ids) == 0:
            completion_ids = full_sequence
        completion_tokens = self._sequence_length(completion_ids)
        text = self._tokenizer.decode(completion_ids, skip_special_tokens=True).strip()
        return text, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": None,
            "model": self._model_id,
            "quantization": self._quantization,
        }

