"""Public evaluation API for POMA."""

from .contracts import AlignedSample, AlignmentCoverage, MetricScore
from .run import evaluate_files

__all__ = ["AlignedSample", "AlignmentCoverage", "MetricScore", "evaluate_files"]
