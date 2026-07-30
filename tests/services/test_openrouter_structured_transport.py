from unittest.mock import Mock

import pytest

from baseline.llm_client import GenConfig, LLMZeroShotClient


class _FakeResponse:
    status_code = 200
    text = ""

    @staticmethod
    def json():
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "answer"}],
                }
            ],
            "usage": {"input_tokens": 2, "output_tokens": 3},
        }


@pytest.fixture
def fake_post(monkeypatch):
    post = Mock(return_value=_FakeResponse())
    monkeypatch.setattr("requests.post", post)
    return post


@pytest.fixture
def client(fake_post):
    return LLMZeroShotClient(openai_api_keys=[], openrouter_api_keys=["test-key"])


def test_openrouter_responses_sends_strict_json_schema(client, fake_post):
    cfg = GenConfig(
        text_format={
            "type": "json_schema",
            "name": "gsa_v1",
            "strict": True,
            "schema": {"type": "object", "properties": {}},
        },
        require_parameters=True,
    )

    client.generate(
        model="openrouter/google/gemma-3-4b-it",
        prompt="prompt",
        config=cfg,
        max_retries=1,
        retry_delay=0,
    )

    body = fake_post.call_args.kwargs["json"]
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "gsa_v1",
        "strict": True,
        "schema": {"type": "object", "properties": {}},
    }
    assert body["provider"]["require_parameters"] is True


def test_openrouter_responses_sends_json_object_format(client, fake_post):
    client.generate(
        model="openrouter/google/gemma-3-4b-it",
        prompt="prompt",
        config=GenConfig(text_format={"type": "json_object"}),
        max_retries=1,
        retry_delay=0,
    )

    body = fake_post.call_args.kwargs["json"]
    assert body["text"] == {"format": {"type": "json_object"}}
    assert "provider" not in body


def test_openrouter_responses_merges_provider_only_with_require_parameters(client, fake_post):
    provider = {"only": ["provider-a"]}
    client.generate(
        model="openrouter/google/gemma-3-4b-it",
        prompt="prompt",
        config=GenConfig(openrouter_provider=provider, require_parameters=True),
        max_retries=1,
        retry_delay=0,
    )

    body = fake_post.call_args.kwargs["json"]
    assert body["provider"] == {"only": ["provider-a"], "require_parameters": True}
    assert provider == {"only": ["provider-a"]}


def test_openrouter_responses_omits_structured_fields_for_plain_text(client, fake_post):
    client.generate(
        model="openrouter/google/gemma-3-4b-it",
        prompt="prompt",
        config=GenConfig(),
        max_retries=1,
        retry_delay=0,
    )

    body = fake_post.call_args.kwargs["json"]
    assert "text" not in body
    assert "provider" not in body


def test_generate_with_usage_returns_unknown_cost_and_a_usage_copy(
    client,
    fake_post,
):
    _, usage = client.generate_with_usage(
        "openrouter/google/gemma-3-4b-it",
        "prompt",
        GenConfig(),
        max_retries=1,
        retry_delay=0,
    )

    usage["prompt_tokens"] = 999
    assert client._thread_local.last_usage["prompt_tokens"] == 2
    assert usage["cost_usd"] is None


def test_generate_with_usage_preserves_provider_reported_cost(client, fake_post):
    fake_post.return_value.json = Mock(
        return_value={
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "answer"}],
                }
            ],
            "usage": {
                "input_tokens": 2,
                "output_tokens": 3,
                "cost": "0.00042",
            },
        }
    )

    _, usage = client.generate_with_usage(
        "openrouter/google/gemma-3-4b-it",
        "prompt",
        GenConfig(),
        max_retries=1,
        retry_delay=0,
    )

    assert usage["cost_usd"] == 0.00042
