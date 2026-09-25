"""Evaluator wiring tests for the optional BIF metric."""

from __future__ import annotations

import json

from evaluation.bif_score import BIFConfig
from evaluation.run import evaluate_files


class _FakeBIFScorer:
    def __init__(self, config):
        self.config = config

    @property
    def metadata(self):
        return {"formula": "verified"}

    def evaluate_samples(self, samples):
        assert [sample.qa_id for sample in samples] == ["a"]
        return (
            {"count": 1, "value": 0.75, "phobert_f1": 0.8, "nli_entailment": 0.7},
            [{"qa_id": "a", "candidate": "prediction", "bif_score": 0.75}],
        )


def test_evaluate_files_adds_bif_only_when_requested(tmp_path, monkeypatch):
    predictions_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    details_path = tmp_path / "bif-details.json"
    predictions_path.write_text(
        json.dumps([{"qa_id": "a", "prediction": ["prediction"]}]),
        encoding="utf-8",
    )
    qas_path.write_text(
        json.dumps([{"qa_id": "a", "answer": "reference"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr("evaluation.run.BIFScorer", _FakeBIFScorer)

    report = evaluate_files(
        predictions_path,
        qas_path,
        metrics=["em", "bif"],
        bif_config=BIFConfig(nli_model_path="unused"),
        bif_details_path=details_path,
    )

    assert report["metrics"]["em"] == {"count": 1, "value": 0.0}
    assert report["metrics"]["bif"]["value"] == 0.75
    assert report["metric_provenance"]["bif"] == {"formula": "verified"}
    assert json.loads(details_path.read_text(encoding="utf-8"))[0]["qa_id"] == "a"
