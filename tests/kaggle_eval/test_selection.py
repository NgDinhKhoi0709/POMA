from src.kaggle_eval.selection import (
    select_longest_table_qa,
    select_pilot_qas,
    table_length_bucket,
)


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


def test_select_pilot_qas_preserves_joint_stratum_distribution():
    qas = [
        *[_qa(index, "What", "short") for index in range(50)],
        *[_qa(index + 50, "Who", "medium") for index in range(30)],
        *[_qa(index + 80, "Why", "long") for index in range(20)],
    ]
    selected = select_pilot_qas(
        qas,
        table_token_counts={"short": 99, "medium": 1000, "long": 4000},
        n=10,
        seed=42,
    )

    strata = [
        (qa["hints"][0], table_length_bucket({"short": 99, "medium": 1000, "long": 4000}[qa["table_id"]]))
        for qa in selected
    ]
    assert strata.count(("What", "short")) == 5
    assert strata.count(("Who", "medium")) == 3
    assert strata.count(("Why", "long")) == 2


def test_select_longest_table_qa_uses_longest_question_as_stress_case():
    qas = [
        {"qa_id": "short-question", "table_id": "long", "question": "Who?"},
        {
            "qa_id": "long-question",
            "table_id": "long",
            "question": "Who is the person named in this complete table?",
        },
        {"qa_id": "other", "table_id": "short", "question": "What?"},
    ]

    selected = select_longest_table_qa(
        qas,
        table_char_counts={"long": 50_000, "short": 100},
    )

    assert selected["qa_id"] == "long-question"
