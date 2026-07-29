from types import SimpleNamespace

from baseline.llm_client import GenConfig, LLMZeroShotClient


class _FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5),
        )


def test_openai_chat_completions_converts_strict_json_schema():
    completions = _FakeCompletions()
    client = LLMZeroShotClient(openai_api_keys=[])
    client._openai_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    cfg = GenConfig(
        text_format={
            "type": "json_schema",
            "name": "hint_predictor_v1",
            "strict": True,
            "schema": {"type": "object", "properties": {}},
        }
    )

    client.generate(
        model="openai/gpt-4o-mini",
        prompt="prompt",
        config=cfg,
        max_retries=1,
        retry_delay=0,
    )

    assert completions.kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "hint_predictor_v1",
            "strict": True,
            "schema": {"type": "object", "properties": {}},
        },
    }


def test_openai_chat_completions_passes_json_object_format_unchanged():
    completions = _FakeCompletions()
    client = LLMZeroShotClient(openai_api_keys=[])
    client._openai_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    client.generate(
        model="openai/gpt-4o-mini",
        prompt="prompt",
        config=GenConfig(text_format={"type": "json_object"}),
        max_retries=1,
        retry_delay=0,
    )

    assert completions.kwargs["response_format"] == {"type": "json_object"}


def test_openai_chat_completions_omits_response_format_for_plain_text():
    completions = _FakeCompletions()
    client = LLMZeroShotClient(openai_api_keys=[])
    client._openai_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    client.generate(
        model="openai/gpt-4o-mini",
        prompt="prompt",
        config=GenConfig(),
        max_retries=1,
        retry_delay=0,
    )

    assert "response_format" not in completions.kwargs
