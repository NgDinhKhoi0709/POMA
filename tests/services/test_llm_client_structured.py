from types import SimpleNamespace

import pytest

from src.config.settings import LLMConfig
from src.contracts import schema_for_call
from src.services import llm_client as llm_client_module
from src.services.llm_client import LLMClient
from src.services.structured_generation import StructuredGenerationError


class _StructuredLowLevelClient:
    def __init__(self, response, usage):
        self.response = response
        self.usage = usage
        self.calls = []
        self._thread_local = SimpleNamespace(last_usage=None)

    def generate_with_usage(self, model, prompt, config, **kwargs):
        self.calls.append((model, prompt, config, kwargs))
        return self.response, dict(self.usage)


class _SequenceStructuredLowLevelClient:
    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = []
        self._thread_local = SimpleNamespace(last_usage=None)

    def generate_with_usage(self, model, prompt, config, **kwargs):
        self.calls.append((model, prompt, config, kwargs))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        raw, usage = outcome
        return raw, dict(usage)


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
    assert client.total_prompt_tokens == 2
    assert client.total_completion_tokens == 3
    assert client.total_total_tokens == 5
    assert client.total_cost_usd == 0.25


def test_generate_structured_repair_success_accounts_for_both_attempts_once():
    client = _client_with(
        _SequenceStructuredLowLevelClient(
            [
                (
                    "not json",
                    {
                        "prompt_tokens": 2,
                        "completion_tokens": 3,
                        "total_tokens": 5,
                        "cost_usd": 0.10,
                    },
                ),
                (
                    '{"predicted_hints": ["What"]}',
                    {
                        "prompt_tokens": 4,
                        "completion_tokens": 5,
                        "total_tokens": 9,
                        "cost_usd": 0.20,
                    },
                ),
            ]
        )
    )

    result = client.generate_structured(
        "prompt",
        schema=schema_for_call("hint_predictor.v1"),
    )

    assert result.repair_succeeded is True
    assert client.total_prompt_tokens == 6
    assert client.total_completion_tokens == 8
    assert client.total_total_tokens == 14
    assert client.total_cost_usd == pytest.approx(0.30)
    log = client.get_call_logs()[0]
    assert log["schema_valid"] is False
    assert log["repair_attempted"] is True
    assert log["repair_succeeded"] is True
    assert (log["prompt_tokens"], log["completion_tokens"], log["total_tokens"]) == (
        6,
        8,
        14,
    )
    assert log["cost_usd"] == pytest.approx(0.30)


def test_generate_structured_terminal_repair_failure_records_consumed_attempts():
    client = _client_with(
        _SequenceStructuredLowLevelClient(
            [
                (
                    "not json",
                    {
                        "prompt_tokens": 2,
                        "completion_tokens": 3,
                        "total_tokens": 5,
                        "cost_usd": 0.10,
                    },
                ),
                (
                    "still not json",
                    {
                        "prompt_tokens": 4,
                        "completion_tokens": 5,
                        "total_tokens": 9,
                        "cost_usd": 0.20,
                    },
                ),
            ]
        )
    )

    with pytest.raises(StructuredGenerationError, match="repair"):
        client.generate_structured(
            "prompt",
            schema=schema_for_call("hint_predictor.v1"),
        )

    assert client.total_prompt_tokens == 6
    assert client.total_completion_tokens == 8
    assert client.total_total_tokens == 14
    assert client.total_cost_usd == pytest.approx(0.30)
    log = client.get_call_logs()[0]
    assert log["schema_valid"] is False
    assert log["repair_attempted"] is True
    assert log["repair_succeeded"] is False
    assert (log["prompt_tokens"], log["completion_tokens"], log["total_tokens"]) == (
        6,
        8,
        14,
    )
    assert log["cost_usd"] == pytest.approx(0.30)


def test_generate_structured_provider_failure_during_repair_records_first_attempt():
    client = _client_with(
        _SequenceStructuredLowLevelClient(
            [
                (
                    "not json",
                    {
                        "prompt_tokens": 2,
                        "completion_tokens": 3,
                        "total_tokens": 5,
                        "cost_usd": None,
                    },
                ),
                RuntimeError("provider unavailable"),
            ]
        )
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        client.generate_structured(
            "prompt",
            schema=schema_for_call("hint_predictor.v1"),
        )

    assert client.total_prompt_tokens == 2
    assert client.total_completion_tokens == 3
    assert client.total_total_tokens == 5
    assert client.total_cost_usd is None
    log = client.get_call_logs()[0]
    assert log["schema_valid"] is False
    assert log["repair_attempted"] is True
    assert log["repair_succeeded"] is False
    assert (log["prompt_tokens"], log["completion_tokens"], log["total_tokens"]) == (
        2,
        3,
        5,
    )
    assert log["cost_usd"] is None


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


def test_local_model_routes_to_transformers_client(monkeypatch):
    calls = []

    class _FakeLocalClient:
        def generate_with_usage(self, prompt, *, max_new_tokens=None):
            calls.append((prompt, max_new_tokens))
            return (
                '{"predicted_hints": ["What"]}',
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost_usd": None,
                },
            )

    monkeypatch.setattr(
        llm_client_module,
        "_get_shared_local_client",
        lambda config: _FakeLocalClient(),
        raising=False,
    )
    client = LLMClient(LLMConfig(model="local/sea-lion-v3-8b-it", max_tokens=7))

    result = client.generate_structured(
        "prompt",
        schema=schema_for_call("hint_predictor.v1"),
    )

    assert result.data == {"predicted_hints": ["What"]}
    assert calls[0][1] == 7
    assert client.total_cost_usd is None


def test_local_model_caps_generation_at_local_token_budget(monkeypatch, tmp_path):
    calls = []

    class _FakeLocalClient:
        def generate_with_usage(self, prompt, *, max_new_tokens=None):
            calls.append(max_new_tokens)
            return (
                '{"predicted_hints": ["What"]}',
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost_usd": None,
                },
            )

    local_config = SimpleNamespace(max_new_tokens=512)
    monkeypatch.setattr(
        llm_client_module,
        "get_settings",
        lambda: SimpleNamespace(local_model=local_config, project_root=tmp_path),
    )
    monkeypatch.setattr(
        llm_client_module,
        "_get_shared_local_client",
        lambda config: _FakeLocalClient(),
    )
    client = LLMClient(
        LLMConfig(model="local/sea-lion-v3-8b-it", max_tokens=4096)
    )

    client.generate_structured(
        "prompt",
        schema=schema_for_call("hint_predictor.v1"),
    )

    assert calls == [512]
