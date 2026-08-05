from types import ModuleType, SimpleNamespace
import sys

from src.config.settings import LocalModelConfig


def test_vllm_client_preserves_chat_template_and_reports_token_usage(monkeypatch):
    from src.services.local_vllm_client import LocalVLLMClient

    calls = {}

    class FakeTokenizer:
        def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
            calls["messages"] = messages
            assert tokenize is False
            assert add_generation_prompt is True
            return "<chat>" + messages[0]["content"]

        def encode(self, text):
            return list(range(len(text.split())))

    class FakeLLM:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        def get_tokenizer(self):
            return FakeTokenizer()

        def generate(self, prompts, sampling_params):
            calls["prompts"] = prompts
            calls["sampling"] = sampling_params
            return [
                SimpleNamespace(
                    prompt_token_ids=[0, 1],
                    outputs=[SimpleNamespace(text='{"answer":"ok"}', token_ids=[2, 3])],
                )
            ]

    class FakeSamplingParams:
        def __init__(self, **kwargs):
            calls["sampling_kwargs"] = kwargs

    fake_vllm = ModuleType("vllm")
    fake_vllm.LLM = FakeLLM
    fake_vllm.SamplingParams = FakeSamplingParams
    monkeypatch.setitem(sys.modules, "vllm", fake_vllm)

    client = LocalVLLMClient.from_pretrained(
        LocalModelConfig(backend="vllm", max_model_len=4096)
    )
    text, usage = client.generate_with_usage("hello world", max_new_tokens=7)

    assert calls["init"]["quantization"] == "bitsandbytes"
    assert calls["init"]["max_model_len"] == 4096
    assert calls["prompts"] == ["<chat>hello world"]
    assert calls["sampling_kwargs"] == {"temperature": 0.0, "max_tokens": 7}
    assert text == '{"answer":"ok"}'
    assert usage == {
        "prompt_tokens": 2,
        "completion_tokens": 2,
        "total_tokens": 4,
        "cost_usd": None,
        "model": "aisingapore/Llama-SEA-LION-v3-8B-IT",
        "quantization": "nf4",
    }
