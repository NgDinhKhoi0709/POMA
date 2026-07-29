import pytest

from src.contracts.structured_outputs import (
    STRUCTURED_SCHEMAS,
    StructuredContractError,
    schema_for_call,
    validate_domain_payload,
)


def test_schema_registry_contains_every_poma_owned_call():
    assert set(STRUCTURED_SCHEMAS) == {
        "hint_predictor.v1",
        "question_refiner.v1",
        "specialist.v1",
        "answer_normalization.v1",
        "gsa.v1",
        "baseline_zero_shot.v1",
        "baseline_few_shot.v1",
        "baseline_cot.v1",
        "baseline_task_decomposition.v1",
    }


def test_all_schemas_are_closed_objects():
    for response_schema in STRUCTURED_SCHEMAS.values():
        assert response_schema.json_schema["type"] == "object"
        assert response_schema.json_schema["additionalProperties"] is False


def test_question_refiner_and_specialist_nullable_fields_use_one_of():
    refiner_target = schema_for_call("question_refiner.v1").json_schema[
        "properties"
    ]["target"]
    specialist_answer = schema_for_call("specialist.v1").json_schema[
        "properties"
    ]["answer"]

    assert refiner_target["oneOf"] == [{"type": "string"}, {"type": "null"}]
    assert specialist_answer["oneOf"] == [{"type": "string"}, {"type": "null"}]


def test_specialist_schema_preserves_native_string_evidence_items():
    evidence_items = schema_for_call("specialist.v1").json_schema[
        "properties"
    ]["evidence"]["items"]

    assert {item["type"] for item in evidence_items["oneOf"]} == {"string", "object"}


def test_gsa_schema_requires_exact_decisions_and_evidence_fields():
    schema = schema_for_call("gsa.v1").json_schema

    assert schema["required"] == [
        "final_answer",
        "supporting_evidence",
        "decision",
    ]
    assert schema["properties"]["decision"]["enum"] == [
        "selected",
        "corrected",
        "synthesized",
        "null",
    ]


def test_cot_and_task_decomposition_schemas_require_reasoning_fields():
    for name in ("baseline_cot.v1", "baseline_task_decomposition.v1"):
        assert "reasoning" in schema_for_call(name).json_schema["required"]

    assert "subproblems" in schema_for_call(
        "baseline_task_decomposition.v1"
    ).json_schema["required"]


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        (
            "hint_predictor.v1",
            {"predicted_hints": []},
            "predicted_hints",
        ),
        (
            "answer_normalization.v1",
            {"answers": []},
            "answers",
        ),
        (
            "baseline_task_decomposition.v1",
            {"reasoning": "inspect rows", "subproblems": [], "final_answer": "42"},
            "subproblems",
        ),
        (
            "gsa.v1",
            {
                "final_answer": "",
                "supporting_evidence": ["row 2"],
                "decision": "selected",
            },
            "final_answer",
        ),
        (
            "gsa.v1",
            {
                "final_answer": "Null",
                "supporting_evidence": [],
                "decision": "selected",
            },
            "evidence",
        ),
        (
            "gsa.v1",
            {
                "final_answer": "answer",
                "supporting_evidence": [],
                "decision": "null",
            },
            "final_answer=Null",
        ),
    ],
)
def test_domain_validators_reject_empty_or_inconsistent_payloads(name, data, message):
    with pytest.raises(StructuredContractError, match=message):
        validate_domain_payload(name, data)


def test_domain_validator_accepts_grounded_non_null_gsa_payload():
    validate_domain_payload(
        "gsa.v1",
        {
            "final_answer": "42",
            "supporting_evidence": ["row 2: value 42"],
            "decision": "corrected",
        },
    )
