"""ViNLI entailment-probability scorer used by BIF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


def resolve_entailment_id(
    label2id: Mapping[str, int] | None,
    *,
    entailment_label: str = "entailment",
    entailment_id: int | None = None,
) -> int:
    """Resolve the Entailment logit index without assuming a label ordering."""
    if entailment_id is not None:
        if entailment_id < 0:
            raise ValueError("entailment_id must be non-negative")
        return entailment_id
    normalized = {
        str(label).strip().casefold(): int(index)
        for label, index in (label2id or {}).items()
    }
    target = entailment_label.strip().casefold()
    if target in normalized:
        return normalized[target]
    raise ValueError(
        "Cannot find the Entailment label in the checkpoint config. "
        "Pass --bif-entailment-id explicitly for this checkpoint."
    )


@dataclass(frozen=True)
class ViNLIConfig:
    """Configuration needed to load and run an NLI checkpoint."""

    model_path: str
    base_model_name: str = "xlm-roberta-large"
    device: str | None = None
    batch_size: int = 32
    max_length: int = 128
    entailment_label: str = "entailment"
    entailment_id: int | None = None


def _runtime_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        import torch
        from transformers import (
            AutoConfig,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
    except ImportError as error:
        raise RuntimeError(
            "BIF requires torch and transformers. Install optional dependencies "
            "with `python -m pip install bert-score pyvi transformers torch`."
        ) from error
    return torch, AutoConfig, AutoModelForSequenceClassification, AutoTokenizer


def _unwrap_state_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping) and isinstance(payload.get("state_dict"), Mapping):
        payload = payload["state_dict"]
    if not isinstance(payload, Mapping):
        raise ValueError("legacy NLI checkpoint must contain a state dictionary")
    state_dict = {
        str(key).removeprefix("module."): value
        for key, value in payload.items()
    }
    state_dict.pop("roberta.embeddings.position_ids", None)
    return state_dict


def _infer_num_labels(state_dict: Mapping[str, Any]) -> int:
    for suffix in ("classifier.out_proj.weight", "score.weight"):
        for key, value in state_dict.items():
            if key.endswith(suffix) and hasattr(value, "shape"):
                return int(value.shape[0])
    raise ValueError(
        "Cannot infer num_labels from the legacy checkpoint; save it with "
        "save_pretrained or provide a checkpoint with classifier weights."
    )


class ViNLIScorer:
    """Load a ViNLI classifier once and batch ``P(entailment)`` inference."""

    def __init__(self, config: ViNLIConfig) -> None:
        if config.batch_size < 1:
            raise ValueError("ViNLI batch_size must be positive")
        if config.max_length < 1:
            raise ValueError("ViNLI max_length must be positive")
        self.config = config
        torch, auto_config, auto_model, auto_tokenizer = _runtime_dependencies()
        self._torch = torch
        source = Path(config.model_path)
        self.device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")

        if source.is_dir():
            self.tokenizer = auto_tokenizer.from_pretrained(str(source))
            self.model = auto_model.from_pretrained(str(source))
        elif source.is_file():
            self.tokenizer = auto_tokenizer.from_pretrained(config.base_model_name)
            state_dict = _unwrap_state_dict(torch.load(source, map_location="cpu"))
            model_config = auto_config.from_pretrained(
                config.base_model_name,
                num_labels=_infer_num_labels(state_dict),
            )
            self.model = auto_model.from_config(model_config)
            self.model.load_state_dict(state_dict, strict=True)
        else:
            raise FileNotFoundError(f"NLI model path does not exist: {source}")

        self.entailment_id = resolve_entailment_id(
            getattr(self.model.config, "label2id", None),
            entailment_label=config.entailment_label,
            entailment_id=config.entailment_id,
        )
        if self.entailment_id >= int(self.model.config.num_labels):
            raise ValueError(
                f"entailment_id {self.entailment_id} is outside the model's "
                f"{self.model.config.num_labels} labels"
            )
        self.model.to(self.device)
        self.model.eval()

    @property
    def metadata(self) -> dict[str, object]:
        labels = getattr(self.model.config, "label2id", {}) or {}
        return {
            "checkpoint": self.config.model_path,
            "base_model": self.config.base_model_name,
            "num_labels": int(self.model.config.num_labels),
            "label2id": {str(key): int(value) for key, value in labels.items()},
            "entailment_id": self.entailment_id,
            "max_length": self.config.max_length,
            "batch_size": self.config.batch_size,
            "device": self.device,
        }

    def entailment_scores(
        self, premises: Sequence[str], hypotheses: Sequence[str]
    ) -> list[float]:
        if len(premises) != len(hypotheses):
            raise ValueError("premises and hypotheses must contain the same number of items")
        scores: list[float] = []
        for start in range(0, len(premises), self.config.batch_size):
            stop = start + self.config.batch_size
            inputs = self.tokenizer(
                list(premises[start:stop]),
                list(hypotheses[start:stop]),
                truncation=True,
                padding=True,
                max_length=self.config.max_length,
                return_tensors="pt",
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            with self._torch.no_grad():
                probabilities = self._torch.softmax(
                    self.model(**inputs).logits, dim=-1
                )
            scores.extend(
                float(value)
                for value in probabilities[:, self.entailment_id].detach().cpu().tolist()
            )
        return scores
