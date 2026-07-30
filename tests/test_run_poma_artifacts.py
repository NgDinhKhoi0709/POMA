import json

import run_poma


def _trace(qa_id, answer):
    return {
        "qa_id": qa_id,
        "question": f"Question {qa_id}",
        "steps": {
            "1_question_refiner": {"normalized_question": qa_id},
            "2_router": {"specialist_names": ["Where"]},
            "3_specialists": [{"agent_name": "Where", "answer": answer}],
            "4_answer_normalization": {"normalized_answers": [answer]},
        },
        "llm_calls": [{"agent_name": "Where", "schema_valid": True}],
    }


def _result(qa_id, answer):
    return {
        "qa_id": qa_id,
        "table_id": "t1",
        "question": f"Question {qa_id}",
        "groundtruth": answer,
        "hints": [],
        "prediction": [answer],
        "hint_source": "dataset",
        "elapsed_s": 0.01,
    }


def _read_ids(path):
    return [record["qa_id"] for record in json.loads(path.read_text(encoding="utf-8"))]


def _read_records(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_resume_merges_all_existing_and_new_traces_and_stage_outputs(tmp_path, monkeypatch):
    output_path = tmp_path / "predictions.json"
    traces_path = tmp_path / "predictions_traces.json"
    output_path.write_text(
        json.dumps({"predictions": [_result("q1", "old-one")]}), encoding="utf-8"
    )
    traces_path.write_text(
        json.dumps([_trace("q1", "old-one"), _trace("q2", "old-two")]),
        encoding="utf-8",
    )

    qas = [
        {"qa_id": "q1", "table_id": "t1", "question": "Question q1", "answer": "old-one"},
        {"qa_id": "q3", "table_id": "t1", "question": "Question q3", "answer": "new-three"},
    ]
    monkeypatch.setattr(run_poma, "load_dataset_pair", lambda *_: (qas, {"t1": {}}))
    monkeypatch.setattr(run_poma, "_print_result", lambda *_: None)
    monkeypatch.setattr(run_poma, "_print_summary", lambda *_: None)

    def fake_process_one(qa, *_args, **_kwargs):
        record = _result(qa["qa_id"], "new-three")
        record["_trace"] = _trace(qa["qa_id"], "new-three")
        return record

    monkeypatch.setattr(run_poma, "process_one", fake_process_one)

    run_poma.run_batch(
        tmp_path / "qas.json",
        tmp_path / "tables.json",
        output_path,
        None,
        traces_path=traces_path,
        auto_evaluate=False,
    )

    assert _read_ids(traces_path) == ["q1", "q2", "q3"]
    assert all(record["llm_calls"][0]["schema_valid"] for record in _read_records(traces_path))
    for stage_name in run_poma.STAGE_TO_STEP_KEYS:
        stage_path = output_path.parent / stage_name / output_path.name
        assert _read_ids(stage_path) == ["q1", "q2", "q3"]

    qas[:] = qas[:1]
    run_poma.run_batch(
        tmp_path / "qas.json",
        tmp_path / "tables.json",
        output_path,
        None,
        traces_path=traces_path,
        auto_evaluate=False,
    )

    assert _read_ids(traces_path) == ["q1", "q2", "q3"]
    assert all(record["llm_calls"][0]["schema_valid"] for record in _read_records(traces_path))
    for stage_name in run_poma.STAGE_TO_STEP_KEYS:
        stage_path = output_path.parent / stage_name / output_path.name
        assert _read_ids(stage_path) == ["q1", "q2", "q3"]


def test_canonical_prediction_reader_prefers_prediction_and_accepts_legacy():
    assert run_poma._record_candidates(
        {"prediction": ["canonical"], "predicted_answer": ["legacy"]}
    ) == ["canonical"]
    assert run_poma._record_candidates({"predicted_answer": ["legacy"]}) == ["legacy"]
    stage = run_poma._build_stage_record(
        "normalization",
        _trace("q1", "legacy"),
        {"q1": {"predicted_answer": ["legacy"]}},
    )
    assert stage["prediction"] == ["legacy"]
    assert "predicted_answer" not in stage
    assert run_poma._merge_trace_lists(
        [_trace("q1", "old")], [_trace("q1", "new")]
    )[0]["steps"]["3_specialists"][0]["answer"] == "new"


def test_process_one_emits_prediction_not_predicted_answer(monkeypatch):
    monkeypatch.setattr(run_poma, "_get_table_str", lambda _table: "table")
    monkeypatch.setattr(
        run_poma,
        "run_pipeline",
        lambda *_args, **_kwargs: {"answer": ["Hà Nội"], "trace": {"steps": {}}},
    )

    record = run_poma.process_one(
        {"qa_id": "q1", "table_id": "t1", "question": "Where?", "answer": "Hà Nội"},
        {"t1": {}},
    )

    assert record["prediction"] == ["Hà Nội"]
    assert "predicted_answer" not in record
