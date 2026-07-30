import pytest

from evaluation.parallelism import analyze_parallelism


def _trace(qa_id, specialist_names):
    return {
        "qa_id": qa_id,
        "steps": {"2_router": {"specialist_names": specialist_names}},
    }


def test_parallelism_reports_actual_routed_specialist_counts():
    traces = [
        _trace("q1", ["What"]),
        _trace("q2", ["Where"]),
        _trace("q3", ["What", "Who"]),
        _trace("q4", ["What", "Where", "When"]),
    ]

    result = analyze_parallelism(
        traces,
        expected_qa_ids=["q1", "q2", "q3", "q4"],
    )

    assert result == {
        "count": 4,
        "distribution": {"1": 2, "2": 1, "3": 1},
        "mean": 1.75,
        "median": 1.5,
        "maximum": 3,
        "multi_specialist_rate": 0.5,
    }


def test_parallelism_rejects_missing_trace_ids_instead_of_shrinking_denominator():
    with pytest.raises(ValueError, match=r"Missing trace IDs: \['q2'\]"):
        analyze_parallelism(
            [_trace("q1", ["What"])],
            expected_qa_ids=["q1", "q2"],
        )


def test_parallelism_requires_the_exact_router_path():
    with pytest.raises(ValueError, match="steps.2_router.specialist_names"):
        analyze_parallelism(
            [{"qa_id": "q1", "specialist_names": ["What"]}],
            expected_qa_ids=["q1"],
        )
