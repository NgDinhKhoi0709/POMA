"""Metrics and paired comparison reports for Kaggle runs."""
from __future__ import annotations
import json
from pathlib import Path
from evaluation import f1
from evaluation.io import align_records, load_json_records, load_qas_records
from evaluation.run import evaluate_files

def write_run_report(predictions_path, qas_path, output_path, *, tables_path=None):
    return evaluate_files(predictions_path, qas_path, tables_path=tables_path, output_path=output_path, candidate_policy="first")

def write_comparison_report(poma_path, zero_path, qas_path, output_path):
    references = load_qas_records(qas_path)
    poma, _ = align_records(load_json_records(poma_path), references, candidate_policy="first")
    zero, _ = align_records(load_json_records(zero_path), references, candidate_policy="first")
    by_poma, by_zero = {item.qa_id: item for item in poma}, {item.qa_id: item for item in zero}
    ids = sorted(by_poma.keys() & by_zero.keys())
    wins = losses = ties = 0
    deltas = []
    for qa_id in ids:
        delta = f1.score_sample(by_poma[qa_id]).value - f1.score_sample(by_zero[qa_id]).value
        deltas.append(delta)
        if delta > 0: wins += 1
        elif delta < 0: losses += 1
        else: ties += 1
    report = {"paired": {"count": len(ids), "qa_ids": ids}, "win_tie_loss": {"poma_wins": wins, "zero_wins": losses, "ties": ties}, "bootstrap_ci": {"f1": {"mean_delta": sum(deltas) / len(deltas) if deltas else 0.0}}}
    output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
