"""Score one-answer artifacts with one frozen scorer and record provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match
from evaluation.bootstrap import DEFAULT_SAMPLES, DEFAULT_SEED, paired_bootstrap_ci
from evaluation.io import align_records, load_json_records, load_qas_records
from evaluation.run import evaluate_files


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_manifest(path: Path) -> dict[str, object] | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = payload.get("manifest") if isinstance(payload, dict) else None
    if not isinstance(manifest, dict):
        return None
    for source_field in ("source", "fallback_source"):
        source = manifest.get(source_field)
        expected_hash = manifest.get(source_field + "_sha256")
        if source is None:
            continue
        source_path = Path(str(source))
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
        if not source_path.is_file() or _sha256(source_path) != expected_hash:
            raise ValueError(f"Broken {source_field} lineage in {path}")
    return manifest


def _system_spec(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name.strip() or not raw_path.strip():
        raise ValueError(f"Invalid --system {value!r}; use NAME=PATH")
    return name.strip(), Path(raw_path.strip())


def _scores(path: Path, qas: Path) -> tuple[list[str], list[float]]:
    samples, _ = align_records(
        load_json_records(path), load_qas_records(qas), candidate_policy="single-required"
    )
    return (
        [sample.qa_id for sample in samples],
        [exact_match.score_sample(sample).value for sample in samples],
    )


def audit(
    systems: dict[str, Path],
    comparisons: list[tuple[str, str]],
    *,
    qas: Path,
    tables: Path,
    traces: Path | None = None,
    diagnostics: dict[str, Path] | None = None,
    artifacts: dict[str, Path] | None = None,
    bootstrap_samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """Reject incomplete systems before producing any comparison."""
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=PROJECT_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip())
    result: dict[str, object] = {
        "protocol": "d01-one-answer-shared-scorer.v1",
        "git_commit_at_audit": revision,
        "working_tree_dirty_at_audit": dirty,
        "python_version": platform.python_version(),
        "pipeline_code_sha256": {
            relative: _sha256(PROJECT_ROOT / relative)
            for relative in (
                "scripts/audit_d01.py",
                "scripts/prepare_d01_artifacts.py",
                "scripts/run_finalizer.py",
                "src/agents/grounded_single_answer.py",
                "src/finalization/finalizers.py",
                "src/finalization/sources.py",
            )
        },
        "evaluation_settings": {
            "candidate_policy": "single-required",
            "strict": True,
            "metrics": ["em", "f1", "rouge1", "meteor"],
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_seed": seed,
        },
        "qas_sha256": _sha256(qas),
        "tables_sha256": _sha256(tables),
        "scorer_sha256": None,
        "systems": {},
        "comparisons": {},
        "diagnostics_oracle_only": {},
        "artifacts": {},
    }
    for name, path in (artifacts or {}).items():
        result["artifacts"][name] = {
            "path": str(path),
            "sha256": _sha256(path),
            "manifest": _source_manifest(path),
        }
    for name, artifact in result["artifacts"].items():
        manifest = artifact["manifest"]
        if not manifest or "source" in manifest or "source_sha256" not in manifest:
            continue
        upstream = [
            other_name for other_name, other in result["artifacts"].items()
            if other_name != name and other["sha256"] == manifest["source_sha256"]
        ]
        if not upstream:
            raise ValueError(f"No matching source artifact for {name}")
        artifact["matched_source_artifacts"] = upstream
    vectors = {}
    for name, path in systems.items():
        report = evaluate_files(
            path, qas, tables_path=tables,
            metrics=["em", "f1", "rouge1", "meteor"],
            candidate_policy="single-required", strict=True,
        )
        scorer_hash = report["provenance"]["scorer_sha256"]
        if result["scorer_sha256"] not in (None, scorer_hash):
            raise ValueError("Scorer changed during audit")
        result["scorer_sha256"] = scorer_hash
        result["systems"][name] = {
            "path": str(path),
            "sha256": _sha256(path),
            "source_manifest": _source_manifest(path),
            "coverage_count": len(report["coverage"]["evaluated_ids"]),
            "metrics": report["metrics"],
            "source_candidate_statistics": report["source_candidate_statistics"],
        }
        vectors[name] = _scores(path, qas)
    for primary, baseline in comparisons:
        if primary not in vectors or baseline not in vectors:
            raise ValueError(f"Unknown comparison: {primary},{baseline}")
        primary_ids, primary_scores = vectors[primary]
        baseline_ids, baseline_scores = vectors[baseline]
        interval = paired_bootstrap_ci(
            primary_scores, baseline_scores,
            samples=bootstrap_samples, seed=seed,
            system_a_ids=primary_ids, system_b_ids=baseline_ids,
        )
        result["comparisons"][f"{primary}-minus-{baseline}"] = {
            "paired_em": interval,
            "wins": sum(a > b for a, b in zip(primary_scores, baseline_scores)),
            "losses": sum(a < b for a, b in zip(primary_scores, baseline_scores)),
            "ties": sum(a == b for a, b in zip(primary_scores, baseline_scores)),
        }
    for name, path in (diagnostics or {}).items():
        report = evaluate_files(
            path, qas, tables_path=tables, metrics=["em"],
            candidate_policy="all", strict=True,
        )
        result["diagnostics_oracle_only"][name] = {
            "path": str(path),
            "sha256": _sha256(path),
            "em": report["metrics"]["em"],
            "candidate_statistics": report["source_candidate_statistics"],
        }
    if traces is not None:
        trace_records = load_json_records(traces)
        trace_ids = [str(row.get("qa_id")) for row in trace_records]
        if len(trace_ids) != len(set(trace_ids)):
            raise ValueError("Trace artifact has duplicate QA IDs")
        result["traces"] = {
            "path": str(traces),
            "sha256": _sha256(traces),
            "count": len(trace_records),
            "specialist_traces": sum(
                bool(row.get("steps", {}).get("3_specialists"))
                for row in trace_records
            ),
            "model_ids": sorted({
                str(call["model"])
                for row in trace_records
                for call in row.get("llm_calls", [])
                if isinstance(call, dict) and call.get("model")
            }),
            "prompt_names": sorted({
                str(call["prompt_name"])
                for row in trace_records
                for call in row.get("llm_calls", [])
                if isinstance(call, dict) and call.get("prompt_name")
            }),
            "matches_qas_ids": set(trace_ids) == {
                str(row["qa_id"]) for row in load_qas_records(qas)
            },
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--compare", action="append", default=[], help="PRIMARY,BASELINE")
    parser.add_argument("--diagnostic", action="append", default=[], help="NAME=PATH")
    parser.add_argument("--artifact", action="append", default=[], help="NAME=PATH")
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--tables", type=Path, required=True)
    parser.add_argument("--traces", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    systems = dict(_system_spec(value) for value in args.system)
    diagnostics = dict(_system_spec(value) for value in args.diagnostic)
    artifacts = dict(_system_spec(value) for value in args.artifact)
    if (
        len(systems) != len(args.system)
        or len(diagnostics) != len(args.diagnostic)
        or len(artifacts) != len(args.artifact)
    ):
        parser.error("System names must be unique")
    comparisons = []
    for value in args.compare:
        primary, separator, baseline = value.partition(",")
        if not separator or not primary or not baseline:
            parser.error("--compare requires PRIMARY,BASELINE")
        comparisons.append((primary, baseline))
    report = audit(
        systems, comparisons, qas=args.qas, tables=args.tables,
        traces=args.traces, diagnostics=diagnostics,
        artifacts=artifacts,
        bootstrap_samples=args.bootstrap_samples, seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"D01 audit: {args.output}")
    for name, system in report["systems"].items():
        print(f"{name}: EM={system['metrics']['em']['value']:.4%}")
    for name, comparison in report["comparisons"].items():
        ci = comparison["paired_em"]
        print(f"{name}: {ci['point_estimate']:+.4%} [{ci['lower']:+.4%}, {ci['upper']:+.4%}]")


if __name__ == "__main__":
    main()
