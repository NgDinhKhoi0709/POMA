from types import SimpleNamespace

import pytest

from src.config.settings import LLMConfig
from src.contracts import schema_for_call
from src.services.llm_client import LLMClient


class _StructuredLowLevelClient:
    def __init__(self, response, usage):
        self.response = response
        self.usage = usage
        self.calls = []
        self._thread_local = SimpleNamespace(last_usage=None)

    def generate_with_usage(self, model, prompt, config, **kwargs):
        self.calls.append((model, prompt, config, kwargs))
        return self.response, dict(self.usage)


def _client_with(low_level_client):
    client = LLMClient(LLMConfig(model="openai/gpt-4o-mini", max_retries=1))
    client._client = low_level_client
    return client


def test_generate_structured_delegates_and_records_schema_telemetry():
    low_level_client = _StructuredLowLevelClient(
        '{"predicted_hints": ["What"]}',
        {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
            "cost_usd": 0.25,
        },
    )
    client = _client_with(low_level_client)

    result = client.generate_structured(
        "prompt",
        schema=schema_for_call("hint_predictor.v1"),
        agent_name="HintPredictor",
        prompt_name="hint_predictor",
    )

    assert result.data == {"predicted_hints": ["What"]}
    assert low_level_client.calls[0][2].text_format["type"] == "json_schema"
    assert low_level_client.calls[0][2].require_parameters is True
    call_log = client.get_call_logs()[0]
    assert call_log["schema_name"] == "hint_predictor.v1"
    assert call_log["schema_valid"] is True
    assert call_log["repair_attempted"] is False
    assert call_log["repair_succeeded"] is False
    assert call_log["mode"] == "strict_json_schema"
    assert call_log["prompt_tokens"] == 2
    assert call_log["completion_tokens"] == 3
    assert call_log["total_tokens"] == 5
    assert call_log["cost_usd"] == 0.25


def test_generate_json_requires_schema_and_delegates_to_structured_generation():
    low_level_client = _StructuredLowLevelClient(
        '{"predicted_hints": ["What"]}',
        {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    )
    client = _client_with(low_level_client)

    with pytest.raises(TypeError):
        client.generate_json("prompt")

    data = client.generate_json(
        "prompt",
        schema=schema_for_call("hint_predictor.v1"),
    )

    assert data == {"predicted_hints": ["What"]}
