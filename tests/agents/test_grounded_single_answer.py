from types import SimpleNamespace

import pytest

from src.agents.grounded_single_answer import GroundedSingleAnswerAgent
from src.contracts.finalization import (
    AnswerCandidate,
    GroundedAnswerRequest,
    GroundedDecision,
)
from src.errors import LLMContractError


class _FakeStructuredLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_structured(self, prompt, *, schema, agent_name, prompt_name):
        self.calls.append(
            {
                "prompt": prompt,
                "schema_name": schema.name,
                "decision_enum": schema.json_schema.get("properties", {})
                .get("decision", {})
                .get("enum"),
                "agent_name": agent_name,
                "prompt_name": prompt_name,
            }
        )
        return SimpleNamespace(data=self._responses.pop(0))


def _request(candidates=None):
    return GroundedAnswerRequest(
        question="Which city has value 42?",
        table_flattened="City | Value\nDa Nang | 42",
        candidates=candidates or [AnswerCandidate("What", "Da Nang")],
    )


@pytest.mark.parametrize(
    ("question", "table", "candidates"),
    [
        ("", "A | B", [AnswerCandidate("What", "A")]),
        ("Question?", "", [AnswerCandidate("What", "A")]),
        ("Question?", "A | B", []),
    ],
)
def test_request_rejects_empty_required_input(question, table, candidates):
    with pytest.raises(ValueError):
        GroundedAnswerRequest(question, table, candidates)


def test_request_preserves_candidate_order():
    request = _request(
        [AnswerCandidate("First", "one"), AnswerCandidate("Second", "two")]
    )

    assert [candidate.source_name for candidate in request.candidates] == [
        "First",
        "Second",
    ]


@pytest.mark.parametrize("answer", ["", " null ", "NONE", "n/a"])
def test_empty_or_null_candidate_is_canonicalized_not_dropped(answer):
    request = _request([AnswerCandidate("What", answer)])

    assert request.candidates[0].answer == "Null"


@pytest.mark.parametrize(
    ("payload", "expected_answer", "expected_decision"),
    [
        (
            {
                "final_answer": "Da Nang",
                "supporting_evidence": ["Da Nang | 42"],
                "decision": "selected",
            },
            "Da Nang",
            GroundedDecision.SELECTED,
        ),
        (
            {
                "final_answer": "42",
                "supporting_evidence": ["Da Nang | 42"],
                "decision": "corrected",
            },
            "42",
            GroundedDecision.CORRECTED,
        ),
        (
            {
                "final_answer": "Da Nang, 42",
                "supporting_evidence": ["Da Nang | 42"],
                "decision": "synthesized",
            },
            "Da Nang, 42",
            GroundedDecision.SYNTHESIZED,
        ),
        (
            {
                "final_answer": "none",
                "supporting_evidence": [],
                "decision": "null",
            },
            "Null",
            GroundedDecision.NULL,
        ),
    ],
)
def test_agent_returns_each_grounded_decision(
    payload, expected_answer, expected_decision
):
    agent = GroundedSingleAnswerAgent(_FakeStructuredLLM([payload]))

    result = agent.run(_request())

    assert result.final_answer == expected_answer
    assert result.decision is expected_decision


def test_selected_answer_matches_candidate_using_evaluation_normalization():
    agent = GroundedSingleAnswerAgent(
        _FakeStructuredLLM(
            [
                {
                    "final_answer": "  DA NANG. ",
                    "supporting_evidence": ["Da Nang | 42"],
                    "decision": "selected",
                }
            ]
        )
    )

    result = agent.run(_request())

    assert result.decision is GroundedDecision.SELECTED


def test_agent_rejects_null_decision_with_non_null_answer():
    agent = GroundedSingleAnswerAgent(
        _FakeStructuredLLM(
            [
                {
                    "final_answer": "Da Nang",
                    "supporting_evidence": [],
                    "decision": "null",
                }
            ]
        )
    )

    with pytest.raises(LLMContractError, match="final_answer=Null"):
        agent.run(_request())


def test_agent_repairs_selected_answer_not_in_candidates_once():
    invalid = {
        "final_answer": "42",
        "supporting_evidence": ["Da Nang | 42"],
        "decision": "selected",
    }
    repaired = {
        "final_answer": "42",
        "supporting_evidence": ["Da Nang | 42"],
        "decision": "synthesized",
    }
    agent = GroundedSingleAnswerAgent(_FakeStructuredLLM([invalid, repaired]))

    result = agent.run(_request())

    assert result.decision is GroundedDecision.SYNTHESIZED
    assert len(agent._llm.calls) == 2
    assert (
        "selected final_answer must match an input candidate"
        in agent._llm.calls[1]["prompt"]
    )
    assert '"final_answer": "42"' in agent._llm.calls[1]["prompt"]
    assert agent._llm.calls[1]["decision_enum"] == [
        "corrected",
        "synthesized",
        "null",
    ]


def test_agent_rejects_selected_answer_not_in_candidates_after_one_repair():
    invalid = {
        "final_answer": "Hanoi",
        "supporting_evidence": ["Da Nang | 42"],
        "decision": "selected",
    }
    agent = GroundedSingleAnswerAgent(_FakeStructuredLLM([invalid, invalid]))

    with pytest.raises(LLMContractError, match="selected"):
        agent.run(_request())

    assert len(agent._llm.calls) == 2


@pytest.mark.parametrize("decision", ["selected", "corrected", "synthesized"])
def test_agent_rejects_non_null_decision_without_table_evidence(decision):
    agent = GroundedSingleAnswerAgent(
        _FakeStructuredLLM(
            [
                {
                    "final_answer": "Da Nang",
                    "supporting_evidence": [],
                    "decision": decision,
                }
            ]
        )
    )

    with pytest.raises(LLMContractError, match="evidence"):
        agent.run(_request())


def test_agent_uses_gsa_schema_and_private_prompt_context():
    agent = GroundedSingleAnswerAgent(
        _FakeStructuredLLM(
            [
                {
                    "final_answer": "Da Nang",
                    "supporting_evidence": ["Da Nang | 42"],
                    "decision": "selected",
                }
            ]
        )
    )

    agent.run(_request([AnswerCandidate("What", "Da Nang")]))

    call = agent._llm.calls[0]
    assert call["schema_name"] == "gsa.v1"
    assert call["agent_name"] == "GroundedSingleAnswer"
    assert call["prompt_name"] == "grounded_single_answer"
    assert '"source_name": "What"' in call["prompt"]
    assert '"answer": "Da Nang"' in call["prompt"]
    assert "Nếu khác về ngữ nghĩa với mọi ứng viên" in call["prompt"]
    assert "dùng decision=`synthesized`, không bao giờ dùng `selected`" in call["prompt"]
