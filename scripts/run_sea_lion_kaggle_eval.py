from __future__ import annotations
import argparse
import sys
from pathlib import Path

def resolve_repo_root(value: str | Path) -> Path:
    root = Path(value).resolve()
    required = [root / "dataset" / name for name in ("qas_dev.json", "qas_test.json", "table.json")]
    if not all(path.exists() for path in required):
        raise FileNotFoundError(f"Repository root must contain dataset/qas_dev.json, qas_test.json and table.json: {root}")
    return root

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--phase",
        choices=("smoke", "pilot100", "pilot", "test500", "final", "longest_test"),
        default="pilot",
    )
    parser.add_argument("--mode", choices=("zero_shot", "poma", "both"), default="both")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--final-ids-path", type=Path)
    parser.add_argument("--confirm-final-543", action="store_true")
    parser.add_argument("--model", default="local/sea-lion-v3-8b-it")
    return parser

def main() -> int:
    args = build_parser().parse_args()
    root = resolve_repo_root(args.repo_root)
    if args.phase == "final" and not args.confirm_final_543:
        raise SystemExit("Final is locked: pass --confirm-final-543 after reviewing the pilot.")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from src.kaggle_eval.runner import RunConfig, prepare_run_dirs, run_poma, run_zero_shot, select_qas
    from src.kaggle_eval.reporting import write_comparison_report, write_run_report
    config = RunConfig(repo_root=root, output_root=Path(args.output_root), phase=args.phase, mode=args.mode, model=args.model, final_ids_path=args.final_ids_path, limit=args.limit)
    selected, tables = select_qas(config)
    if args.phase == "test500":
        qas_path = root / "dataset" / "qas_test_500_stratified.json"
    else:
        use_test = args.phase in {"final", "longest_test"}
        qas_path = root / "dataset" / ("qas_test.json" if use_test else "qas_dev.json")
    dirs = prepare_run_dirs(config)
    if args.mode in ("zero_shot", "both"):
        zero_path = run_zero_shot(config, selected, tables)
        write_run_report(zero_path, qas_path, dirs["zero_shot"] / "metrics.json")
    if args.mode in ("poma", "both"):
        poma_path = run_poma(config, selected, tables)
        write_run_report(poma_path, qas_path, dirs["poma"] / "metrics.json")
    if args.mode == "both":
        write_comparison_report(dirs["poma"] / "predictions.jsonl", dirs["zero_shot"] / "predictions.jsonl", qas_path, dirs["poma"].parent / "comparison.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
