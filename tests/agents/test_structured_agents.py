from types import SimpleNamespace

import pytest

from src.agents.answer_normalization import AnswerNormalizationAgent
from src.agents.hint_predictor import HintPredictorAgent
from src.agents.question_refiner import QuestionRefinerAgent
from src.agents.specialists._base_specialist import BaseSpecialistAgent
from src.contracts.responses import RefinedQuery
from src.errors import LLMContractError


class _FakeStructuredLLM:
    def __init__(self, responses=()):
        self._responses = list(responses)
        self.calls = []

    def generate_structured(self, prompt, *, schema, agent_name, prompt_name):
        self.calls.append(
            {
                "prompt": prompt,
                "schema_name": schema.name,
                "agent_name": agent_name,
                "prompt_name": prompt_name,
            }
        )
        if not self._responses:
            raise AssertionError("unexpected structured LLM call")
        return SimpleNamespace(data=self._responses.pop(0))


class _Specialist(BaseSpecialistAgent):
    name = "TestSpecialist"
    prompt_name = "test_specialist"

    def _load_prompt(self, **kwargs):
        return "specialist prompt"


def test_hint_predictor_uses_its_schema_and_parses_valid_payload():
    llm = _FakeStructuredLLM([{"predicted_hints": ["What"]}])

    result = HintPredictorAgent(llm).run("Câu hỏi gì?", "table")

    assert result == ["What"]
    assert llm.calls[0]["schema_name"] == "hint_predictor.v1"


def test_hint_predictor_rejects_invalid_payload():
    agent = HintPredictorAgent(_FakeStructuredLLM([{"predicted_hints": "What"}]))

    with pytest.raises(LLMContractError, match="must be a list"):
        agent.run("Câu hỏi gì?", "table")


def test_question_refiner_uses_its_schema_and_parses_valid_payload():
    llm = _FakeStructuredLLM(
        [{"normalized_question": "Câu hỏi", "target": "Giá trị", "constraints": ["Năm 2020"]}]
    )

    result = QuestionRefinerAgent(llm).run("Câu hỏi", ["What"])

    assert result == RefinedQuery(
        normalized_question="Câu hỏi",
        hints=["What"],
        target="Giá trị",
        constraints=["Năm 2020"],
    )
    assert llm.calls[0]["schema_name"] == "question_refiner.v1"


def test_question_refiner_rejects_invalid_payload_after_structured_generation():
    agent = QuestionRefinerAgent(
        _FakeStructuredLLM(
            [{"normalized_question": "", "target": None, "constraints": []}]
        )
    )

    with pytest.raises(LLMContractError, match="normalized_question.*non-empty"):
        agent.run("Câu hỏi", ["What"])


def test_specialist_uses_its_schema_and_preserves_native_parsing():
    llm = _FakeStructuredLLM(
        [
            {
                "answer": "42",
                "evidence": [
                    "row 1: 42",
                    {"text": "row 2: 42", "row_index": 2, "col": "value"},
                ],
                "confidence": "0.75",
                "reason": "matched the table",
            }
        ]
    )
    agent = _Specialist(llm)

    result = agent.run(
        RefinedQuery("Câu hỏi", ["What"], None, []),
        "table",
    )

    assert result.answer == "42"
    assert [(item.text, item.row_index, item.col) for item in result.evidence] == [
        ("row 1: 42", None, None),
        ("row 2: 42", 2, "value"),
    ]
    assert result.confidence == 0.75
    assert result.reason == "matched the table"
    assert llm.calls[0]["schema_name"] == "specialist.v1"


def test_specialist_rejects_invalid_payload():
    agent = _Specialist(
        _FakeStructuredLLM(
            [{"answer": "42", "evidence": [], "confidence": "bad", "reason": "why"}]
        )
    )

    with pytest.raises(LLMContractError, match="confidence.*numeric"):
        agent.run(RefinedQuery("Câu hỏi", ["What"], None, []), "table")


def test_answer_normalization_uses_schema_and_preserves_ordered_variants():
    llm = _FakeStructuredLLM([{"answers": ["Alpha", "Beta"]}])
    agent = AnswerNormalizationAgent(llm)

    assert agent.run("Alpha", "Câu hỏi", target="Giá trị", answer_hint="Who") == [
        "Alpha",
        "Beta",
    ]
    assert llm.calls[0]["schema_name"] == "answer_normalization.v1"
    assert llm.calls[0]["prompt_name"] == "answer_normalization/who"
    assert agent.run_many(["2020", "2021"], "Năm nào?") == [
        "2020",
        "Năm 2020",
        "2021",
        "Năm 2021",
    ]


def test_answer_normalization_rejects_invalid_payload():
    agent = AnswerNormalizationAgent(_FakeStructuredLLM([{"answers": "Alpha"}]))

    with pytest.raises(LLMContractError, match="non-empty list"):
        agent.run("Alpha", "Câu hỏi")
