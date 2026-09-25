"""D13: build the 200-question subset for the header-filter experiment.

Coverage rule (fixed before any run): every table in ``dataset/table.json`` matching one of the
three structural criteria below and present in ``qas_test.json`` contributes one question. The rest
of the budget is filled so that the hint-signature distribution of the whole subset is as close as
possible to the full test split (largest-remainder allocation on the residual budget).

Criteria, computed on the raw HTML grid (row order as authored, before the parser hoists header
rows):

* ``clusters``  - number of 4-connected components of ``<th>`` cells; >= 2 means disjoint header blocks.
* ``mid_header``- a majority-``<th>`` row appears after at least one body row.
* ``merged``    - number of cells carrying ``rowspan``/``colspan`` > 1; >= 5.

The merged-cell counts reproduce the author's table exactly (73 tables with >= 5, 183 with >= 1).
The other two definitions give 17 and 14 where the author's note says 12 and 10, so this subset uses
a **superset** of the author's structural set and records both numbers in the manifest.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NO_HINT = "__NO_HINT__"


def hint_key(qa: dict) -> str:
    hints = [str(h).strip() for h in (qa.get("hints") or []) if str(h).strip()]
    return " | ".join(sorted(hints)) if hints else NO_HINT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats", type=Path, default=PROJECT_ROOT / "outputs/table_structure_stats.json")
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_test.json")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "outputs/d13/qas_d13_200.json")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    qualifying = {
        tid for tid, v in stats.items()
        if v["clusters"] >= 2 or v["mid_header"] or v["merged"] >= 5
    }
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    by_table = defaultdict(list)
    for qa in qas:
        by_table[str(qa["table_id"])].append(qa)

    rng = random.Random(args.seed)
    covered = sorted(qualifying & set(by_table))
    missing = sorted(qualifying - set(by_table))

    forced = []
    for tid in covered:
        pool = sorted(by_table[tid], key=lambda q: str(q["qa_id"]))
        forced.append(rng.choice(pool))
    forced_ids = {str(q["qa_id"]) for q in forced}

    # Target the full-test hint distribution over the whole subset, then subtract what coverage gave.
    full = Counter(hint_key(q) for q in qas)
    target = {}
    for key, count in full.items():
        target[key] = count / len(qas) * args.size
    have = Counter(hint_key(q) for q in forced)
    remaining = args.size - len(forced)
    deficits = {k: max(0.0, target.get(k, 0.0) - have.get(k, 0)) for k in target}
    total_deficit = sum(deficits.values()) or 1.0
    quota = {k: deficits[k] / total_deficit * remaining for k in deficits}
    take = {k: int(v) for k, v in quota.items()}
    for key, _ in sorted(quota.items(), key=lambda kv: -(kv[1] - int(kv[1])))[: remaining - sum(take.values())]:
        take[key] += 1

    pool = defaultdict(list)
    for qa in qas:
        if str(qa["qa_id"]) not in forced_ids:
            pool[hint_key(qa)].append(qa)
    for key in pool:
        pool[key].sort(key=lambda q: str(q["qa_id"]))
        rng.shuffle(pool[key])

    filler = []
    for key, n in take.items():
        filler.extend(pool.get(key, [])[:n])
    leftovers = [q for key in pool for q in pool[key][take.get(key, 0):]]
    rng.shuffle(leftovers)
    while len(forced) + len(filler) < args.size and leftovers:
        filler.append(leftovers.pop())

    subset = sorted(forced + filler, key=lambda q: str(q["qa_id"]))
    assert len({str(q["qa_id"]) for q in subset}) == len(subset) == args.size, (len(subset), args.size)

    manifest = {
        "size": len(subset),
        "seed": args.seed,
        "criteria": {
            "clusters>=2": sum(1 for v in stats.values() if v["clusters"] >= 2),
            "mid_header": sum(1 for v in stats.values() if v["mid_header"]),
            "merged>=5": sum(1 for v in stats.values() if v["merged"] >= 5),
            "merged>=1": sum(1 for v in stats.values() if v["merged"] >= 1),
            "author_reported": {"clusters>=2": 12, "mid_header": 10, "merged>=5": 73, "merged>=1": 183},
        },
        "qualifying_tables": len(qualifying),
        "qualifying_tables_in_test": len(covered),
        "qualifying_tables_absent_from_test": missing,
        "forced_questions": len(forced),
        "filler_questions": len(filler),
        "structural_questions_total": sum(1 for q in subset if str(q["table_id"]) in qualifying),
        "hint_distribution_full_test": {k: round(v / len(qas), 4) for k, v in full.items()},
        "hint_distribution_subset": {
            k: round(v / len(subset), 4) for k, v in Counter(hint_key(q) for q in subset).items()
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"qas": subset}, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out.parent / "subset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in manifest.items() if not k.startswith("hint_")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
