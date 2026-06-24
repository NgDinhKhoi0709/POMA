from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Bootstrap: ensure the standalone POMA project root is on sys.path.
_PROJECT_ROOT = Path(__file__).resolve().parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from baseline.llm_client import GenConfig
from baseline.prompts import PROMPT_STYLES
from baseline.run import _calculate_batch_stats, run_batch_zeroshot
from evaluation.io import load_json_records
from evaluation.run import evaluate_files


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description='Run LLM zero-shot TableQA (OpenAI, OpenRouter): Flatten V1 table string + question'
    )
    p.add_argument(
        '--qas',
        default='dataset/qas_test.json',
        help='Path to qas_*.json',
    )
    p.add_argument(
        '--tables',
        default='dataset/table.json',
        help='Path to table.json',
    )
    p.add_argument(
        '-id', '--id',
        dest='output_id',
        default=None,
        help="Run folder name under <output_dir>/<id>/ (per-model files: <model>.jsonl/.json). If omitted, the QAs filename stem is used (e.g. qas_test). Use this id to group outputs for one prompt style or experiment.",
    )
    p.add_argument(
        '--models',
        nargs='+',
        default=['openai/gpt-4o-mini'],
        help='Model ids or aliases, e.g. openai/gpt-4o-mini openrouter/qwen/qwen3-8b qwen3-8b llama-3.1-8b-it',
    )
    p.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of QAs for quick runs',
    )
    p.add_argument(
        '--output_dir',
        default='outputs/baseline',
        help='Root output directory; writes to <output_dir>/<id>/ (default: outputs/baseline).',
    )
    p.add_argument(
        '--temperature',
        type=float,
        default=0.0,
        help='Generation temperature',
    )
    p.add_argument(
        '--top_p',
        type=float,
        default=1.0,
        help='Generation top_p',
    )
    p.add_argument(
        '--max_tokens',
        type=int,
        default=10000,
        help='Generation max tokens',
    )
    p.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Request timeout (seconds)',
    )
    p.add_argument(
        '--sleep_s',
        type=float,
        default=0.0,
        help='Sleep between model calls',
    )
    p.add_argument(
        '--max_workers',
        type=int,
        default=4,
        help='Number of parallel workers',
    )
    p.add_argument(
        '--no-eval',
        dest='auto_evaluate',
        action='store_false',
        default=True,
        help='Disable automatic evaluation after generation',
    )
    p.add_argument(
        '--eval-metrics',
        default=None,
        help='Comma-separated evaluation metrics (default: f1,em,rouge1,meteor,f1_by_answerability,rouge1_by_hint)',
    )
    p.add_argument(
        '--eval-threads',
        type=int,
        default=1,
        help='Number of evaluation worker threads (default: 1)',
    )
    p.add_argument(
        '--fail-on-metric-error',
        action='store_true',
        help='Fail on metric runtime errors instead of soft fallback',
    )
    p.add_argument(
        '--provider',
        type=str,
        nargs='+',
        default=None,
        help='OpenRouter provider routing list (mapped to provider.only), e.g. --provider atlas-cloud/fp8 alibaba. Overrides model defaults.',
    )
    p.add_argument(
        '--skip-existing-qas',
        dest='skip_existing_qas',
        action='store_true',
        default=True,
        help='Skip QA items that already exist in current output jsonl (only skips when qa_id exists across all selected model output files; default: on).',
    )
    p.add_argument(
        '--no-skip-existing-qas',
        dest='skip_existing_qas',
        action='store_false',
        help='Re-process all selected QA items and overwrite current output jsonl files.',
    )
    p.add_argument(
        '--prompt-style',
        choices=list(PROMPT_STYLES),
        default='zero_shot',
        help='zero_shot | cot | task_decomposition',
    )
    return p


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass

    args = build_arg_parser().parse_args()

    cfg = GenConfig(
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )

    outputs = run_batch_zeroshot(
        qas_path=args.qas,
        tables_path=args.tables,
        models=args.models,
        output_dir=args.output_dir,
        limit=args.limit,
        sleep_s=args.sleep_s,
        gen_config=cfg,
        max_workers=args.max_workers,
        output_id=args.output_id,
        openrouter_provider=args.provider,
        skip_existing_qas=bool(args.skip_existing_qas),
        prompt_style=args.prompt_style,
    )

    print('')
    print('Wrote outputs:')
    for m, p in outputs.items():
        jsonl_path = Path(p)
        evaluation = None
        if args.auto_evaluate:
            metrics_list = None
            if args.eval_metrics:
                metrics_list = [m.strip() for m in args.eval_metrics.split(',') if m.strip()]
            evaluation = evaluate_files(
                jsonl_path,
                args.qas,
                metrics=metrics_list,
                fail_on_metric_error=args.fail_on_metric_error,
            )
            predictions = load_json_records(jsonl_path)
            payload: dict = {"predictions": predictions, "evaluation": evaluation}
            payload['stats'] = _calculate_batch_stats(predictions)
            
            json_path = jsonl_path.with_suffix('.json')
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write('\n')
            
            print("Evaluation done.")
        
        print(f'  {m}: {jsonl_path}')
        print(f'      {jsonl_path.with_suffix(".json")}')
        
    return 0


if __name__ == '__main__':
    sys.exit(main())
