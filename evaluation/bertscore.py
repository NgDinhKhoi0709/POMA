"""PhoBERT-backed BERTScore utilities for Vietnamese answer evaluation.

The supplied implementation was a runnable demonstration. This module keeps
its protocol (PyVi word segmentation, PhoBERT Large layer 17, and F1) while
making model execution opt-in and reusable by the evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def _require_equal_lengths(
    candidates: Sequence[str], references: Sequence[str]
) -> None:
    if len(candidates) != len(references):
        raise ValueError(
            "candidates and references must contain the same number of items"
        )


def segment_vietnamese(texts: Sequence[str]) -> list[str]:
    """Word-segment Vietnamese text with the segmenter used by the author code."""
    try:
        from pyvi import ViTokenizer
    except ImportError as error:
        raise RuntimeError(
            "BIF requires PyVi. Install optional dependencies with "
            "`python -m pip install bert-score pyvi transformers torch`."
        ) from error
    return [ViTokenizer.tokenize(str(text)) for text in texts]


@dataclass(frozen=True)
class PhoBERTScoreConfig:
    """Stable settings for the PhoBERT component of BIF."""

    model_type: str = "vinai/phobert-large"
    num_layers: int = 17
    device: str | None = None
    batch_size: int = 16


class PhoBERTScoreScorer:
    """Return per-pair PhoBERT BERTScore F1 values without import-time work."""

    def __init__(self, config: PhoBERTScoreConfig | None = None) -> None:
        self.config = config or PhoBERTScoreConfig()
        if self.config.batch_size < 1:
            raise ValueError("PhoBERTScore batch_size must be positive")
        try:
            from bert_score import score
        except ImportError as error:
            raise RuntimeError(
                "BIF requires bert-score. Install optional dependencies with "
                "`python -m pip install bert-score pyvi transformers torch`."
            ) from error
        self._score = score

    def score_pairs(
        self, candidates: Sequence[str], references: Sequence[str]
    ) -> list[float]:
        _require_equal_lengths(candidates, references)
        if not candidates:
            return []
        precision, recall, f1 = self._score(
            segment_vietnamese(candidates),
            segment_vietnamese(references),
            model_type=self.config.model_type,
            num_layers=self.config.num_layers,
            lang="vi",
            verbose=False,
            device=self.config.device,
            batch_size=self.config.batch_size,
        )
        scores = [float(value) for value in f1.detach().cpu().tolist()]
        del precision, recall, f1
        self._release_cuda_cache()
        return scores

    def _release_cuda_cache(self) -> None:
        """Release temporary BERTScore allocations before the ViNLI pass."""
        if self.config.device is not None and not self.config.device.startswith("cuda"):
            return
        try:
            import gc
            import torch
        except ImportError:
            return
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
