import json
from pathlib import Path


def test_kaggle_notebook_runs_zero_shot_on_full_test_set():
    data = json.loads(
        Path("notebooks/kaggle_sea_lion_poma.ipynb").read_text(encoding="utf-8")
    )
    sources = "\n".join(
        "".join(cell.get("source", [])) for cell in data["cells"]
    )

    assert data["nbformat"] == 4
    assert 'MODEL_ID = "aisingapore/Llama-SEA-LION-v3-8B-IT"' in sources
    assert '"--phase", "test"' in sources
    assert '"--mode", "zero_shot"' in sources
    assert "qas_test.json" in sources
    assert "test500" not in sources
    assert "--limit" not in sources
    assert "POMA_PROMPT_PROFILE" in sources
    assert 'POMA_LOCAL_BACKEND": "vllm"' in sources
    assert "run_sea_lion_kaggle_eval.py" in sources
    assert "/kaggle/working" in sources
    assert all(not cell.get("outputs") for cell in data["cells"])
    assert all(cell.get("execution_count") is None for cell in data["cells"] if cell["cell_type"] == "code")
