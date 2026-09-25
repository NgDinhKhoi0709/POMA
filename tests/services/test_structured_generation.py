import pytest

from src.contracts import (
    CallContext,
    ResponseSchema,
    StructuredOutputMode,
    STRUCTURED_SCHEMAS,
)
from src.services.structured_generation import (
    StructuredGenerationError,
    StructuredGenerator,
    UnsupportedStructuredOutputModel,
    resolve_output_mode,
)


SIMPLE_SCHEMA = ResponseSchema(
    name="answer.v1",
    version="v1",
    json_schema={
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    },
)


def _context(model="openrouter/qwen/qwen3-8b"):
    return CallContext(
        qa_id="qa-1",
        agent_name="test-agent",
        prompt_name="test-prompt",
        model=model,
    )


class _SequenceTransport:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, prompt, text_format):
        self.calls.append((prompt, text_format))
        if not self._responses:
            raise AssertionError("Structured generator made an unexpected extra call")
        return self._responses.pop(0)


def _generator(responses, *, mode_override=None):
    transport = _SequenceTransport(responses)
    return StructuredGenerator(transport, mode_override=mode_override), transport


def test_qwen_uses_prompt_only_mode():
    assert (
        resolve_output_mode("openrouter/qwen/qwen3-8b")
        is StructuredOutputMode.PROMPT_ONLY
    )


def test_gemma_uses_strict_schema_mode():
    assert (
        resolve_output_mode("openrouter/google/gemma-3-4b-it")
        is StructuredOutputMode.STRICT_JSON_SCHEMA
    )


def test_existing_openai_model_uses_strict_schema_mode():
    assert (
        resolve_output_mode("openai/gpt-4o-mini")
        is StructuredOutputMode.STRICT_JSON_SCHEMA
    )


def test_unknown_openrouter_model_requires_explicit_override():
    with pytest.raises(UnsupportedStructuredOutputModel):
        resolve_output_mode("openrouter/acme/unknown")

    assert (
        resolve_output_mode(
            "openrouter/acme/unknown",
            StructuredOutputMode.JSON_OBJECT,
        )
        is StructuredOutputMode.JSON_OBJECT
    )


def test_local_sea_lion_uses_json_text_extract_mode():
    assert (
        resolve_output_mode("local/sea-lion-v3-8b-it")
        is StructuredOutputMode.JSON_TEXT_EXTRACT
    )
    assert (
        resolve_output_mode("local/aisingapore/Llama-SEA-LION-v3-8B-IT")
        is StructuredOutputMode.JSON_TEXT_EXTRACT
    )


def test_local_mode_uses_concise_contract_instead_of_full_json_schema():
    generator, transport = _generator(
        [
            (
                '{"answer":"yes"}',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ],
        mode_override=StructuredOutputMode.JSON_TEXT_EXTRACT,
    )

    generator.generate("Answer.", SIMPLE_SCHEMA, _context("local/sea-lion-v3-8b-it"))

    prompt, text_format = transport.calls[0]
    assert text_format is None
    assert 'JSON: {"answer":"string"}' in prompt
    assert "additionalProperties" not in prompt


def test_qwen_prompt_only_mode_omits_format_and_appends_compact_schema_instruction():
    generator, transport = _generator(
        [
            (
                '{"answer": "yes"}',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ]
    )

    generator.generate("Answer the question.", SIMPLE_SCHEMA, _context())

    prompt, text_format = transport.calls[0]
    assert text_format is None
    assert "Answer the question." in prompt
    assert '"additionalProperties":false' in prompt


def test_strict_mode_sends_strict_schema_format():
    generator, transport = _generator(
        [
            (
                '{"answer": "yes"}',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ]
    )

    generator.generate(
        "Answer the question.",
        SIMPLE_SCHEMA,
        _context("openai/gpt-4o-mini"),
    )

    assert transport.calls[0][1] == {
        "type": "json_schema",
        "name": "answer_v1_v1",
        "strict": True,
        "schema": SIMPLE_SCHEMA.json_schema,
    }


def test_valid_first_response_makes_one_call_and_normalizes_known_cost():
    generator, transport = _generator(
        [
            (
                '{"answer": "yes"}',
                {
                    "prompt_tokens": "2",
                    "completion_tokens": 3,
                    "total_tokens": "5",
                    "cost_usd": 0.25,
                },
            )
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 1
    assert result.data == {"answer": "yes"}
    assert result.schema_valid is True
    assert result.repair_attempted is False
    assert result.repair_succeeded is False
    assert (
        result.prompt_tokens,
        result.completion_tokens,
        result.total_tokens,
    ) == (2, 3, 5)
    assert result.cost_usd == 0.25


def test_fenced_json_is_decoded_without_repair():
    generator, transport = _generator(
        [
            (
                '```json\n{"answer": "yes"}\n```',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 1
    assert result.data == {"answer": "yes"}
    assert result.schema_valid is True
    assert result.repair_attempted is False


def test_text_wrapped_single_json_object_is_decoded_without_repair():
    generator, transport = _generator(
        [
            (
                'Here is the answer:\n{"answer": "yes"}\nDone.',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ],
        mode_override=StructuredOutputMode.JSON_TEXT_EXTRACT,
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context("local/sea-lion-v3-8b-it"))

    assert len(transport.calls) == 1
    assert result.data == {"answer": "yes"}
    assert result.repair_attempted is False


def test_ambiguous_multiple_json_objects_repair_once():
    generator, transport = _generator(
        [
            (
                '{"answer": "first"}\n{"answer": "second"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                '{"answer": "repaired"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ],
        mode_override=StructuredOutputMode.JSON_TEXT_EXTRACT,
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context("local/sea-lion-v3-8b-it"))

    assert len(transport.calls) == 2
    assert result.data == {"answer": "repaired"}
    assert "multiple JSON objects" in transport.calls[1][0]


def test_malformed_json_is_repaired_once_with_aggregated_known_usage():
    generator, transport = _generator(
        [
            (
                "not json",
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost": 0.10,
                },
            ),
            (
                '{"answer": "repaired"}',
                {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    "cost_usd": 0.20,
                },
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.data == {"answer": "repaired"}
    assert result.schema_valid is False
    assert result.repair_attempted is True
    assert result.repair_succeeded is True
    assert (
        result.prompt_tokens,
        result.completion_tokens,
        result.total_tokens,
    ) == (6, 8, 14)
    assert result.cost_usd == pytest.approx(0.30)
    assert "Return one JSON object only." in transport.calls[1][0]
    assert "Validation errors:" in transport.calls[1][0]
    assert "Previous response:" in transport.calls[1][0]
    assert "not json" in transport.calls[1][0]
    assert transport.calls[1][1] == transport.calls[0][1]


def test_qwen_repair_retains_original_context_and_schema_instruction():
    generator, transport = _generator(
        [
            (
                "not json",
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                '{"answer": "repaired"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ]
    )

    generator.generate("Answer the original question.", SIMPLE_SCHEMA, _context())

    repair_prompt, repair_format = transport.calls[1]
    assert "Answer the original question." in repair_prompt
    assert '"additionalProperties":false' in repair_prompt
    assert "Return one JSON object only." in repair_prompt
    assert "The previous response failed validation." in repair_prompt
    assert "Validation errors:" in repair_prompt
    assert "Previous response:" in repair_prompt
    assert repair_format is transport.calls[0][1] is None


def test_schema_invalid_json_is_repaired_once():
    generator, transport = _generator(
        [
            ("{}", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}),
            (
                '{"answer": "repaired"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.data == {"answer": "repaired"}
    assert "$.answer" in transport.calls[1][0]


def test_domain_invalid_json_is_repaired_once():
    schema = STRUCTURED_SCHEMAS["gsa.v1"]
    generator, transport = _generator(
        [
            (
                (
                    '{"final_answer": "answer", "supporting_evidence": [], '
                    '"decision": "selected"}'
                ),
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                (
                    '{"final_answer": "answer", "supporting_evidence": ['
                    '"row 1"], "decision": "selected"}'
                ),
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ]
    )

    result = generator.generate("Answer.", schema, _context())

    assert len(transport.calls) == 2
    assert result.repair_succeeded is True
    assert "non-null GSA decisions require evidence" in transport.calls[1][0]


@pytest.mark.parametrize(
    ("schema_name", "invalid_response", "valid_response", "expected_path"),
    [
        (
            "gsa.v1",
            (
                '{"final_answer": "answer", "supporting_evidence": [], '
                '"decision": "selected"}'
            ),
            (
                '{"final_answer": "answer", "supporting_evidence": ['
                '"row 1"], "decision": "selected"}'
            ),
            "$.supporting_evidence",
        ),
        (
            "hint_predictor.v1",
            '{"predicted_hints": []}',
            '{"predicted_hints": ["What"]}',
            "$.predicted_hints",
        ),
        (
            "answer_normalization.v1",
            '{"answers": []}',
            '{"answers": ["answer"]}',
            "$.answers",
        ),
    ],
)
def test_domain_validation_errors_identify_the_invalid_field(
    schema_name,
    invalid_response,
    valid_response,
    expected_path,
):
    generator, transport = _generator(
        [
            (
                invalid_response,
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                valid_response,
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ]
    )

    result = generator.generate(
        "Answer.",
        STRUCTURED_SCHEMAS[schema_name],
        _context(),
    )

    assert result.repair_succeeded is True
    assert expected_path in transport.calls[1][0]


def test_invalid_repair_raises_after_exactly_two_calls():
    generator, transport = _generator(
        [
            (
                "not json",
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                "still not json",
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ]
    )

    with pytest.raises(StructuredGenerationError, match="repair"):
        generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2


def test_unknown_cost_propagates_through_repair_sequence():
    generator, transport = _generator(
        [
            (
                "not json",
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost": 0.10,
                },
            ),
            (
                '{"answer": "repaired"}',
                {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    "cost_usd": "not-a-number",
                },
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.cost_usd is None


@pytest.mark.parametrize(
    "invalid_cost",
    [True, -0.01, float("nan"), float("inf"), -float("inf")],
    ids=["boolean", "negative", "nan", "positive-infinity", "negative-infinity"],
)
def test_invalid_provider_cost_propagates_unknown_through_repair(invalid_cost):
    generator, transport = _generator(
        [
            (
                "not json",
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost": 0.10,
                },
            ),
            (
                '{"answer": "repaired"}',
                {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    "cost_usd": invalid_cost,
                },
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.cost_usd is None


@pytest.mark.parametrize(
    "string_cost_usage",
    [{"cost_usd": "0.20"}, {"cost": "0.20"}],
    ids=["preferred-alias", "fallback-alias"],
)
def test_numeric_string_cost_propagates_unknown_through_repair(string_cost_usage):
    generator, transport = _generator(
        [
            (
                "not json",
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost": 0.10,
                },
            ),
            (
                '{"answer": "repaired"}',
                {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    **string_cost_usage,
                },
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.cost_usd is None


@pytest.mark.parametrize(
    "invalid_preferred_cost",
    [None, "0.50", True, -0.01],
    ids=["null", "numeric-string", "boolean", "negative"],
)
def test_valid_cost_alias_follows_invalid_preferred_alias(invalid_preferred_cost):
    generator, transport = _generator(
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
                '{"answer": "repaired"}',
                {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    "cost_usd": invalid_preferred_cost,
                    "cost": 0.20,
                },
            ),
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert len(transport.calls) == 2
    assert result.cost_usd == pytest.approx(0.30)


def test_preferred_valid_cost_usd_wins_over_conflicting_cost_alias():
    generator, _ = _generator(
        [
            (
                '{"answer": "yes"}',
                {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "cost_usd": 0.20,
                    "cost": 0.90,
                },
            )
        ]
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context())

    assert result.cost_usd == 0.20
