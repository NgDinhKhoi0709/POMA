from src.kaggle_eval.selection import select_pilot_qas, table_length_bucket


def _qa(index, hint, table_id):
    return {"qa_id": str(index), "hints": [hint], "table_id": table_id}


def test_table_length_bucket_boundaries():
    assert table_length_bucket(99) == "short"
    assert table_length_bucket(1000) == "medium"
    assert table_length_bucket(5000) == "long"


def test_select_pilot_qas_is_seeded_and_unique():
    qas = [_qa(i, "What" if i % 2 else "Who", f"t{i % 4}") for i in range(40)]
    counts = {f"t{i}": i * 1500 for i in range(4)}
    first = select_pilot_qas(qas, table_token_counts=counts, n=12, seed=42)
    second = select_pilot_qas(qas, table_token_counts=counts, n=12, seed=42)
    assert [qa["qa_id"] for qa in first] == [qa["qa_id"] for qa in second]
    assert len({qa["qa_id"] for qa in first}) == 12
    assert {"What", "Who"} <= {qa["hints"][0] for qa in first}
