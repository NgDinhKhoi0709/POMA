import pytest

from evaluation.bootstrap import (
    paired_answerability_bootstrap_ci,
    paired_bootstrap_ci,
)


def test_paired_bootstrap_is_reproducible_and_reports_the_observed_difference():
    first = paired_bootstrap_ci(
        system_a=[1.0, 1.0, 0.0, 0.0],
        system_b=[1.0, 0.0, 0.0, 0.0],
        samples=1000,
        seed=20260729,
    )
    second = paired_bootstrap_ci(
        system_a=[1.0, 1.0, 0.0, 0.0],
        system_b=[1.0, 0.0, 0.0, 0.0],
        samples=1000,
        seed=20260729,
    )

    assert first == second
    assert first["point_estimate"] == 0.25
    assert first["samples"] == 1000
    assert first["seed"] == 20260729
    assert first["system_a"]["point_estimate"] == 0.5
    assert first["system_b"]["point_estimate"] == 0.25
    assert first["difference"]["point_estimate"] == 0.25
    assert first["lower"] == first["difference"]["lower"]
    assert first["upper"] == first["difference"]["upper"]


def test_paired_bootstrap_uses_the_same_indices_for_both_systems():
    result = paired_bootstrap_ci(
        system_a=[0.25, 0.5, 0.75, 1.0],
        system_b=[0.0, 0.25, 0.5, 0.75],
        samples=200,
        seed=7,
    )

    assert result["difference"] == {
        "point_estimate": 0.25,
        "lower": 0.25,
        "upper": 0.25,
    }


def test_answerability_bootstrap_recomputes_macro_f1_for_each_resample():
    first = paired_answerability_bootstrap_ci(
        gold_unanswerable=[False, False, True, True],
        system_a_unanswerable=[False, True, True, False],
        system_b_unanswerable=[False, False, False, False],
        samples=500,
        seed=19,
    )
    second = paired_answerability_bootstrap_ci(
        gold_unanswerable=[False, False, True, True],
        system_a_unanswerable=[False, True, True, False],
        system_b_unanswerable=[False, False, False, False],
        samples=500,
        seed=19,
    )

    assert first == second
    assert first["system_a"]["point_estimate"] == pytest.approx(0.5)
    assert first["system_b"]["point_estimate"] == pytest.approx(1 / 3)
    assert first["point_estimate"] == pytest.approx(1 / 6)


def test_paired_bootstrap_rejects_unequal_lengths_and_different_id_orderings():
    with pytest.raises(ValueError, match="same length"):
        paired_bootstrap_ci([1.0], [1.0, 0.0])

    with pytest.raises(ValueError, match="same QA IDs in the same order"):
        paired_bootstrap_ci(
            [1.0, 0.0],
            [1.0, 0.0],
            system_a_ids=["q1", "q2"],
            system_b_ids=["q2", "q1"],
        )

    with pytest.raises(ValueError, match="unique"):
        paired_bootstrap_ci(
            [1.0, 0.0],
            [1.0, 0.0],
            system_a_ids=["q1", "q1"],
            system_b_ids=["q1", "q1"],
        )


@pytest.mark.parametrize(
    ("values", "samples", "message"),
    [
        ([], 10, "non-empty"),
        ([1.0], 0, "positive"),
    ],
)
def test_paired_bootstrap_rejects_invalid_sampling_inputs(values, samples, message):
    with pytest.raises(ValueError, match=message):
        paired_bootstrap_ci(values, values, samples=samples)
