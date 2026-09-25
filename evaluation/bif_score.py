"""BIF: blend PhoBERT semantic F1 with ViNLI entailment probability."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean
from typing import Sequence

from .bertscore import PhoBERTScoreConfig, PhoBERTScoreScorer
from .contracts import AlignedSample
from .vinliscore import ViNLIConfig, ViNLIScorer


@dataclass(frozen=True)
class BIFConfig:
    """Full, reportable configuration of a BIF run."""

    nli_model_path: str
    nli_base_model: str = "xlm-roberta-large"
    phobert_model: str = "vinai/phobert-large"
    alpha: float = 0.5
    device: str | None = None
    batch_size: int = 16
    max_length: int = 128
    entailment_label: str = "entailment"
    entailment_id: int | None = None


def combine_bif_scores(
    phobert_scores: Sequence[float], nli_scores: Sequence[float], alpha: float
) -> list[float]:
    """Apply Eq. 15: alpha * PhoBERT F1 + (1 - alpha) * P(entailment)."""
    if len(phobert_scores) != len(nli_scores):
        raise ValueError("PhoBERT and NLI score vectors must have equal length")
    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be a finite value in [0, 1]")
    return [
        alpha * float(phobert) + (1.0 - alpha) * float(nli)
        for phobert, nli in zip(phobert_scores, nli_scores)
    ]


class BIFScorer:
    """Compute BIF using reference as NLI premise and prediction as hypothesis."""

    def __init__(self, config: BIFConfig) -> None:
        if config.batch_size < 1:
            raise ValueError("BIF batch_size must be positive")
        if not math.isfinite(config.alpha) or not 0.0 <= config.alpha <= 1.0:
            raise ValueError("alpha must be a finite value in [0, 1]")
        self.config = config
        self.phobert = PhoBERTScoreScorer(
            PhoBERTScoreConfig(
                model_type=config.phobert_model,
                num_layers=17 if "large" in config.phobert_model else 9,
                device=config.device,
                batch_size=config.batch_size,
            )
        )
        self.nli = ViNLIScorer(
            ViNLIConfig(
                model_path=config.nli_model_path,
                base_model_name=config.nli_base_model,
                device=config.device,
                batch_size=config.batch_size,
                max_length=config.max_length,
                entailment_label=config.entailment_label,
                entailment_id=config.entailment_id,
            )
        )

    @classmethod
    def from_scorers(
        cls, phobert: object, nli: object, *, alpha: float = 0.5
    ) -> "BIFScorer":
        """Construct a scorer with test doubles, without loading model runtimes."""
        instance = cls.__new__(cls)
        instance.config = BIFConfig(nli_model_path="injected", alpha=alpha)
        instance.phobert = phobert
        instance.nli = nli
        return instance

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "formula": "alpha * phobert_f1 + (1 - alpha) * nli_entailment",
            "alpha": self.config.alpha,
            "phobert_model": self.config.phobert_model,
            "phobert_num_layers": 17 if "large" in self.config.phobert_model else 9,
            "segmenter": "pyvi.ViTokenizer",
            "nli": getattr(self.nli, "metadata", {}),
            "nli_pair_direction": "reference_premise_to_prediction_hypothesis",
        }

    def compute_bif(
        self, references: Sequence[str], candidates: Sequence[str]
    ) -> tuple[float, list[dict[str, float | str]]]:
        if len(references) != len(candidates):
            raise ValueError("references and candidates must contain the same number of items")
        phobert_scores = self.phobert.score_pairs(candidates, references)
        nli_scores = self.nli.entailment_scores(references, candidates)
        bif_scores = combine_bif_scores(phobert_scores, nli_scores, self.config.alpha)
        details = [
            {
                "reference": str(reference),
                "candidate": str(candidate),
                "phobert_f1": float(phobert),
                "nli_entailment": float(nli),
                "bif_score": float(bif),
            }
            for reference, candidate, phobert, nli, bif in zip(
                references, candidates, phobert_scores, nli_scores, bif_scores
            )
        ]
        return (fmean(bif_scores) if bif_scores else 0.0), details

    def evaluate_samples(
        self, samples: Sequence[AlignedSample]
    ) -> tuple[dict[str, float | int], list[dict[str, float | int | str]]]:
        """Score samples, selecting the highest-BIF candidate per QA if needed."""
        references: list[str] = []
        candidates: list[str] = []
        locations: list[tuple[str, int]] = []
        skipped_empty = 0
        for sample in samples:
            valid_candidates = [
                (index, candidate)
                for index, candidate in enumerate(sample.prediction)
                if candidate.strip()
            ]
            if not valid_candidates:
                skipped_empty += 1
                continue
            for index, candidate in valid_candidates:
                references.append(sample.reference)
                candidates.append(candidate)
                locations.append((sample.qa_id, index))

        _, pair_details = self.compute_bif(references, candidates)
        grouped: dict[str, list[dict[str, float | int | str]]] = {}
        for (qa_id, candidate_index), detail in zip(locations, pair_details):
            record: dict[str, float | int | str] = {
                "qa_id": qa_id,
                "candidate_index": candidate_index,
                **detail,
            }
            grouped.setdefault(qa_id, []).append(record)

        selected = [
            max(records, key=lambda record: float(record["bif_score"]))
            for records in grouped.values()
        ]
        if not selected:
            return {
                "count": 0,
                "value": 0.0,
                "phobert_f1": 0.0,
                "nli_entailment": 0.0,
                "skipped_empty_predictions": skipped_empty,
            }, []
        return {
            "count": len(selected),
            "value": fmean(float(record["bif_score"]) for record in selected),
            "phobert_f1": fmean(float(record["phobert_f1"]) for record in selected),
            "nli_entailment": fmean(
                float(record["nli_entailment"]) for record in selected
            ),
            "skipped_empty_predictions": skipped_empty,
        }, selected
