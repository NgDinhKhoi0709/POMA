import json
from collections import Counter
from pathlib import Path

from scripts.create_qas_subset import _hint_key


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_qas(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["qas"] if isinstance(payload, dict) else payload


def test_stratified_test_subset_has_500_items_and_matches_hint_distribution() -> None:
    full_qas = _load_qas(PROJECT_ROOT / "dataset" / "qas_test.json")
    subset_qas = _load_qas(PROJECT_ROOT / "dataset" / "qas_test_500_stratified.json")

    assert len(subset_qas) == 500
    assert {qa["qa_id"] for qa in subset_qas} <= {qa["qa_id"] for qa in full_qas}

    full_counts = Counter(_hint_key(qa, "hint-signature") for qa in full_qas)
    subset_counts = Counter(_hint_key(qa, "hint-signature") for qa in subset_qas)
    for hint, count in full_counts.items():
        assert abs(subset_counts[hint] - count * 500 / len(full_qas)) <= 1
