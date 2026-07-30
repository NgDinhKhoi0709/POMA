import json
from dataclasses import asdict

import pytest

from src.finalization.finalizers import GroundedSingleAnswerFinalizer
from src.finalization.sources import (
    FinalizationInputError,
    load_finalization_requests,
)


class _RecordingGroundedAgent:
    def __init__(self):
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        raise RuntimeError("stop after recording")


def _write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _table(table_id):
    return {
        "table_id": table_id,
        "table_html": (
            "<table><tr><th>City</th></tr>"
            f"<tr><td>{table_id}</td></tr></table>"
        ),
    }


def _dataset_files(tmp_path, qas=None, tables=None):
    qas = qas or [
        {
            "qa_id": "q1",
            "table_id": "t1",
            "question": "Thành phố nào?",
            "answer": "gold must not leak",
            "hints": ["What"],
        }
    ]
    tables = tables or [_table("t1")]
    return (
        _write_json(tmp_path / "qas.json", {"qas": qas}),
        _write_json(tmp_path / "tables.json", {"table": tables}),
    )


def test_poma_uses_only_ordered_specialist_names_and_raw_answers(tmp_path):
    """Catch extraction from normalized answers or non-specialist metadata."""
    qas_path, tables_path = _dataset_files(
        tmp_path,
        qas=[
            {"qa_id": "q1", "table_id": "t1", "question": "First?"},
            {"qa_id": "q2", "table_id": "t2", "question": "Second?"},
        ],
        tables=[_table("t1"), _table("t2")],
    )
    source_path = _write_json(
        tmp_path / "poma.json",
        [
            {
                "qa_id": "q2",
                "answer": ["wrong top-level answer"],
                "steps": {
                    "1_question_refiner": {
                        "target": "forbidden target",
                        "hints": ["forbidden hint"],
                    },
                    "3_specialists": [
                        {
                            "agent_name": "List",
                            "answer": "raw q2",
                            "evidence": [{"text": "forbidden evidence"}],
                            "confidence": 0.99,
                            "reason": "forbidden reason",
                        }
                    ],
                    "4_answer_normalization": {
                        "raw_answers": ["wrong raw answer"],
                        "normalized_answers": ["wrong normalized answer"],
                    },
                },
            },
            {
                "qa_id": "q1",
                "steps": {
                    "3_specialists": [
                        {"agent_name": "Where", "answer": "raw first"},
                        {"agent_name": "Fallback", "answer": "raw second"},
                    ]
                },
            },
        ],
    )

    requests = load_finalization_requests(
        source_path=source_path,
        source_kind="poma-specialists",
        qas_path=qas_path,
        tables_path=tables_path,
    )

    assert [request.qa_id for request in requests] == ["q1", "q2"]
    assert [
        [(candidate.source_name, candidate.answer) for candidate in request.candidates]
        for request in requests
    ] == [
        [("Where", "raw first"), ("Fallback", "raw second")],
        [("List", "raw q2")],
    ]
    assert requests[0].table_flattened == "City <header>\nt1"
    assert requests[1].table_flattened == "City <header>\nt2"


def test_adapter_does_not_carry_privileged_fields_into_gsa_request(tmp_path):
    """Catch gold, hints, target, or specialist rationale leaking into GSA."""
    qas_path, tables_path = _dataset_files(tmp_path)
    source_path = _write_json(
        tmp_path / "poma.json",
        [
            {
                "qa_id": "q1",
                "groundtruth": "source gold",
                "hints": ["source hint"],
                "steps": {
                    "1_question_refiner": {"target": "source target"},
                    "3_specialists": [
                        {
                            "agent_name": "Where",
                            "answer": "Hà Nội",
                            "evidence": [{"text": "secret"}],
                            "confidence": 1.0,
                            "reason": "secret",
                        }
                    ],
                },
            }
        ],
    )
    request = load_finalization_requests(
        source_path=source_path,
        source_kind="poma-specialists",
        qas_path=qas_path,
        tables_path=tables_path,
    )[0]
    agent = _RecordingGroundedAgent()

    with pytest.raises(RuntimeError, match="stop after recording"):
        GroundedSingleAnswerFinalizer(agent).finalize(request)

    assert request.native_target is None
    assert set(asdict(request)) == {
        "qa_id",
        "table_id",
        "question",
        "table_flattened",
        "candidates",
        "native_target",
    }
    grounded_payload = asdict(agent.requests[0])
    assert set(grounded_payload) == {
        "question",
        "table_flattened",
        "candidates",
    }
    assert set(grounded_payload["candidates"][0]) == {"source_name", "answer"}


def test_direct_baseline_produces_exactly_one_raw_candidate(tmp_path):
    """Catch list expansion or legacy reasoning fields becoming candidates."""
    qas_path, tables_path = _dataset_files(tmp_path)
    source_path = _write_json(
        tmp_path / "baseline.json",
        {
            "predictions": [
                {
                    "qa_id": "q1",
                    "prediction": ["  Hà Nội  "],
                    "structured_output": {
                        "final_answer": "wrong structured answer",
                        "reasoning": "must not leak",
                    },
                    "groundtruth": "wrong gold answer",
                }
            ]
        },
    )

    requests = load_finalization_requests(
        source_path=source_path,
        source_kind="direct-baseline",
        qas_path=qas_path,
        tables_path=tables_path,
    )

    assert len(requests) == 1
    assert [
        (candidate.source_name, candidate.answer)
        for candidate in requests[0].candidates
    ] == [("direct-baseline", "  Hà Nội  ")]


@pytest.mark.parametrize(
    ("source_kind", "record"),
    [
        (
            "poma-specialists",
            {"steps": {"3_specialists": [{"agent_name": "Where", "answer": "x"}]}},
        ),
        (
            "poma-specialists",
            {"qa_id": "q1", "steps": {"3_specialists": []}},
        ),
        (
            "poma-specialists",
            {
                "qa_id": "q1",
                "steps": {
                    "3_specialists": [{"agent_name": "Where", "answer": "  "}]
                },
            },
        ),
        ("direct-baseline", {"qa_id": "q1", "prediction": []}),
        ("direct-baseline", {"qa_id": "q1", "prediction": ["a", "b"]}),
        (
            "direct-baseline",
            {"qa_id": "q1", "answer": "gold is not a raw prediction"},
        ),
    ],
)
def test_missing_id_or_raw_answer_raises_typed_input_error(
    tmp_path,
    source_kind,
    record,
):
    """Catch malformed source records being silently skipped or gold-backed."""
    qas_path, tables_path = _dataset_files(tmp_path)
    source_path = _write_json(tmp_path / "source.json", [record])

    with pytest.raises(FinalizationInputError):
        load_finalization_requests(
            source_path=source_path,
            source_kind=source_kind,
            qas_path=qas_path,
            tables_path=tables_path,
        )


def test_missing_table_raises_typed_input_error(tmp_path):
    """Catch dataset entries proceeding without the exact Flatten V1 table."""
    qas_path, tables_path = _dataset_files(tmp_path, tables=[_table("other")])
    source_path = _write_json(
        tmp_path / "source.json",
        [{"qa_id": "q1", "prediction": ["Hà Nội"]}],
    )

    with pytest.raises(FinalizationInputError, match="table"):
        load_finalization_requests(
            source_path=source_path,
            source_kind="direct-baseline",
            qas_path=qas_path,
            tables_path=tables_path,
        )

@pytest.mark.parametrize("duplicate_kind", ["qas", "tables", "source"])
def test_duplicate_ids_are_rejected(tmp_path, duplicate_kind):
    """Catch later duplicate records silently overwriting earlier records."""
    qas = [{"qa_id": "q1", "table_id": "t1", "question": "Where?"}]
    tables = [_table("t1")]
    source = [{"qa_id": "q1", "prediction": ["Hà Nội"]}]
    if duplicate_kind == "qas":
        qas.append(dict(qas[0]))
    elif duplicate_kind == "tables":
        tables.append(dict(tables[0]))
    else:
        source.append(dict(source[0]))
    qas_path, tables_path = _dataset_files(tmp_path, qas=qas, tables=tables)
    source_path = _write_json(tmp_path / "source.json", source)

    with pytest.raises(FinalizationInputError, match="Duplicate"):
        load_finalization_requests(
            source_path=source_path,
            source_kind="direct-baseline",
            qas_path=qas_path,
            tables_path=tables_path,
        )
