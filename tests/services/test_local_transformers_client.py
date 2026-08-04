from types import SimpleNamespace

import pytest

from src.services.local_transformers_client import (
    ContextOverflowError,
    LocalTransformersClient,
)


class _FakeBatch(dict):
    def to(self, device):
        self.device = device
        return self


class _FakeTokenizer:
    eos_token_id = 2
    pad_token_id = None

    def __call__(self, text, return_tensors=None):
        ids = list(range(len(text.split())))
        return _FakeBatch({"input_ids": SimpleNamespace(shape=(1, len(ids)))})

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        assert messages[0]["role"] == "user"
        return messages[0]["content"] + "\nassistant:"

    def decode(self, ids, skip_special_tokens=True):
        return '{"answer": "ok"}'


class _FakeModel:
    device = "cuda"

    def generate(self, **kwargs):
        self.kwargs = kwargs
        return [[0, 1, 2]]


def test_generate_with_usage_counts_tokens_and_calls_model():
    model = _FakeModel()
    client = LocalTransformersClient(
        tokenizer=_FakeTokenizer(),
        model=model,
        model_id="local/sea-lion-v3-8b-it",
        max_input_tokens=10,
        default_max_new_tokens=4,
    )

    text, usage = client.generate_with_usage("one two")

    assert text == '{"answer": "ok"}'
    assert usage["prompt_tokens"] == 3
    assert usage["completion_tokens"] >= 1
    assert usage["cost_usd"] is None
    assert usage["model"] == "local/sea-lion-v3-8b-it"
    assert usage["quantization"] == "nf4"
    assert model.kwargs["max_new_tokens"] == 4
    assert model.kwargs["do_sample"] is False


def test_context_overflow_raises_before_generation():
    client = LocalTransformersClient(
        tokenizer=_FakeTokenizer(),
        model=_FakeModel(),
        model_id="local/sea-lion-v3-8b-it",
        max_input_tokens=2,
        default_max_new_tokens=4,
    )

    with pytest.raises(ContextOverflowError, match="max_input_tokens=2"):
        client.generate_with_usage("one two three")
