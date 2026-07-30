"""Deterministic percentile bootstrap confidence intervals."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

DEFAULT_SAMPLES = 10000
DEFAULT_SEED = 20260729


def _validated_values(values: Sequence[float], name: str) -> list[float]:
    result: list[float] = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError(f"{name} must contain finite numeric values")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{name} must contain finite numeric values"
            ) from error
        if not math.isfinite(number):
            raise ValueError(f"{name} must contain finite numeric values")
        result.append(number)
    return result


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    return lower + (upper - lower) * fraction


def _interval(point_estimate: float, estimates: list[float]) -> dict[str, float]:
    ordered = sorted(estimates)
    return {
        "point_estimate": point_estimate,
        "lower": _percentile(ordered, 0.025),
        "upper": _percentile(ordered, 0.975),
    }


def paired_bootstrap_ci(
    system_a: Sequence[float],
    system_b: Sequence[float],
    *,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    system_a_ids: Sequence[str] | None = None,
    system_b_ids: Sequence[str] | None = None,
) -> dict[str, object]:
    """Bootstrap two aligned score vectors and their paired difference.

    One sampled QA-index vector is shared by both systems on every resample.
    The top-level interval is the system-A minus system-B difference.
    """
    values_a = _validated_values(system_a, "system_a")
    values_b = _validated_values(system_b, "system_b")
    if len(values_a) != len(values_b):
        raise ValueError("Paired systems must have the same length")
    if not values_a:
        raise ValueError("Paired systems must be non-empty")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if (system_a_ids is None) != (system_b_ids is None):
        raise ValueError("Both paired-system ID sequences are required together")
    if system_a_ids is not None and system_b_ids is not None:
        ids_a = [str(value) for value in system_a_ids]
        ids_b = [str(value) for value in system_b_ids]
        if len(ids_a) != len(values_a) or len(ids_b) != len(values_b):
            raise ValueError("QA ID sequences must match their system score lengths")
        if len(ids_a) != len(set(ids_a)) or len(ids_b) != len(set(ids_b)):
            raise ValueError("Paired-system QA IDs must be unique")
        if ids_a != ids_b:
            raise ValueError(
                "Paired systems must use the same QA IDs in the same order"
            )

    rng = random.Random(seed)
    count = len(values_a)
    estimates_a: list[float] = []
    estimates_b: list[float] = []
    differences: list[float] = []
    for _ in range(samples):
        indices = [rng.randrange(count) for _ in range(count)]
        mean_a = sum(values_a[index] for index in indices) / count
        mean_b = sum(values_b[index] for index in indices) / count
        estimates_a.append(mean_a)
        estimates_b.append(mean_b)
        differences.append(mean_a - mean_b)

    point_a = sum(values_a) / count
    point_b = sum(values_b) / count
    difference = _interval(point_a - point_b, differences)
    return {
        **difference,
        "samples": samples,
        "seed": seed,
        "system_a": _interval(point_a, estimates_a),
        "system_b": _interval(point_b, estimates_b),
        "difference": difference,
    }


__all__ = ["DEFAULT_SAMPLES", "DEFAULT_SEED", "paired_bootstrap_ci"]
