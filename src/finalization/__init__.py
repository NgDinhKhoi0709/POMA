"""Finalizer adapters for normalized and table-grounded predictions."""

from .finalizers import (
    CommonAnswerNormalizationFinalizer,
    FinalizationRequest,
    FinalizationResult,
    GroundedSingleAnswerFinalizer,
    NativeAnswerNormalizationFinalizer,
)

__all__ = [
    "CommonAnswerNormalizationFinalizer",
    "FinalizationRequest",
    "FinalizationResult",
    "GroundedSingleAnswerFinalizer",
    "NativeAnswerNormalizationFinalizer",
]
