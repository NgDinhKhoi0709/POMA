"""
Create a QAS subset with hint distribution close to the full dataset.

Examples:
    python scripts/create_qas_subset.py --size 100
    python scripts/create_qas_subset.py --size 300 --seed 7
    python scripts/create_qas_subset.py --size 100 --stratify-by first-hint
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

NO_HINT_LABEL = "__NO_HINT__"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a stratified subset from qas_test.json based on hints.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="dataset/qas_test.json",
        help="Path to source QAS JSON file (relative paths are resolved from project root).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/qas_test_subset_stratified.json",
        help="Path to write subset JSON file (relative paths are resolved from project root).",
    )
    parser.add_argument(
        "--size",
        type=int,
        required=True,
        help="Number of QA items in subset.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling.",
    )
    parser.add_argument(
        "--stratify-by",
        choices=["hint-signature", "first-hint"],
        default="hint-signature",
        help=(
            "hint-signature: stratify by full normalized hint list; "
            "first-hint: stratify by first hint only."
        ),
    )
    return parser.parse_args()


def _normalize_hints(raw_hints: Any) -> List[str]:
    if not isinstance(raw_hints, list):
        return []

    normalized: List[str] = []
    for hint in raw_hints:
        text = str(hint).strip()
        if text:
            normalized.append(text)
    return normalized


def _hint_key(qa: Dict[str, Any], mode: str) -> str:
    hints = _normalize_hints(qa.get("hints", []))
    if not hints:
        return NO_HINT_LABEL

    if mode == "first-hint":
        return hints[0]

    deduped = sorted(set(hints))
    return " || ".join(deduped) if deduped else NO_HINT_LABEL


def _load_qas(path: Path) -> Tuple[Any, List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        qas_raw = payload.get("qas", [])
    else:
        qas_raw = payload

    if not isinstance(qas_raw, list):
        raise ValueError("QAS payload must be a list or a dict with a 'qas' list.")

    qas: List[Dict[str, Any]] = [q for q in qas_raw if isinstance(q, dict)]
    return payload, qas


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _group_indices_by_hint(
    qas: Sequence[Dict[str, Any]],
    stratify_mode: str,
) -> Dict[str, List[int]]:
    grouped: Dict[str, List[int]] = defaultdict(list)
    for idx, qa in enumerate(qas):
        grouped[_hint_key(qa, stratify_mode)].append(idx)
    return grouped


def _allocate_stratum_sizes(
    grouped: Dict[str, List[int]],
    subset_size: int,
) -> Dict[str, int]:
    total = sum(len(v) for v in grouped.values())
    if total == 0:
        return {k: 0 for k in grouped}

    target = min(subset_size, total)
    if target <= 0:
        return {k: 0 for k in grouped}

    ideal: Dict[str, float] = {
        k: (target * len(v) / total) for k, v in grouped.items()
    }

    allocated: Dict[str, int] = {k: math.floor(v) for k, v in ideal.items()}
    assigned = sum(allocated.values())
    remaining = target - assigned

    if remaining > 0:
        # Largest remainder method keeps proportions while guaranteeing exact target size.
        by_remainder = sorted(
            grouped.keys(),
            key=lambda k: (ideal[k] - allocated[k], len(grouped[k])),
            reverse=True,
        )
        for key in by_remainder[:remaining]:
            allocated[key] += 1

    return allocated


def _sample_subset_indices(
    grouped: Dict[str, List[int]],
    allocated: Dict[str, int],
    seed: int,
) -> List[int]:
    rng = random.Random(seed)
    chosen: List[int] = []

    for key in sorted(grouped.keys()):
        indices = grouped[key]
        take = allocated.get(key, 0)

        if take <= 0:
            continue
        if take >= len(indices):
            chosen.extend(indices)
            continue

        chosen.extend(rng.sample(indices, take))

    chosen.sort()
    return chosen


def _distribution(
    qas: Iterable[Dict[str, Any]],
    stratify_mode: str,
) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for qa in qas:
        counts[_hint_key(qa, stratify_mode)] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _safe_print(text: str = "") -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback for terminals that cannot encode some Unicode code points.
        ascii_fallback = text.encode("ascii", errors="replace").decode("ascii")
        print(ascii_fallback)


def _print_distribution_report(
    full_counts: Dict[str, int],
    subset_counts: Dict[str, int],
    full_size: int,
    subset_size: int,
) -> None:
    _safe_print("\nHint distribution report")
    _safe_print(f"- Full set size: {full_size}")
    _safe_print(f"- Subset size:   {subset_size}")
    _safe_print("\n{:<42} {:>8} {:>10} {:>8} {:>10}".format(
        "Hint stratum",
        "full_n",
        "full_%",
        "sub_n",
        "sub_%",
    ))
    _safe_print("-" * 84)

    keys = sorted(full_counts.keys(), key=lambda k: (-full_counts[k], k))
    for key in keys:
        full_n = full_counts.get(key, 0)
        sub_n = subset_counts.get(key, 0)
        full_pct = (100.0 * full_n / full_size) if full_size else 0.0
        sub_pct = (100.0 * sub_n / subset_size) if subset_size else 0.0
        label = key if len(key) <= 42 else key[:39] + "..."
        _safe_print(f"{label:<42} {full_n:>8} {full_pct:>9.2f}% {sub_n:>8} {sub_pct:>9.2f}%")


def _write_subset(
    original_payload: Any,
    subset_qas: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(original_payload, dict):
        out_payload = dict(original_payload)
        out_payload["qas"] = subset_qas
    else:
        out_payload = subset_qas

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(out_payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()

    if args.size <= 0:
        raise ValueError("--size must be a positive integer.")

    input_path = _resolve_path(args.input)
    output_path = _resolve_path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(
            "Input file not found: "
            f"{input_path}. "
            "Use --input to point to your qas JSON file."
        )

    payload, qas = _load_qas(input_path)
    if not qas:
        raise ValueError("No valid QA items found in input file.")

    grouped = _group_indices_by_hint(qas, args.stratify_by)
    allocated = _allocate_stratum_sizes(grouped, args.size)
    chosen_indices = _sample_subset_indices(grouped, allocated, seed=args.seed)

    subset_qas = [qas[idx] for idx in chosen_indices]

    full_counts = _distribution(qas, args.stratify_by)
    subset_counts = _distribution(subset_qas, args.stratify_by)

    _write_subset(payload, subset_qas, output_path)

    _safe_print(f"Saved subset to: {output_path}")
    _safe_print(f"Requested size: {args.size}")
    _safe_print(f"Actual size:    {len(subset_qas)}")
    _safe_print(f"Random seed:    {args.seed}")
    _safe_print(f"Stratify by:    {args.stratify_by}")
    _print_distribution_report(
        full_counts=full_counts,
        subset_counts=subset_counts,
        full_size=len(qas),
        subset_size=len(subset_qas),
    )


if __name__ == "__main__":
    main()
