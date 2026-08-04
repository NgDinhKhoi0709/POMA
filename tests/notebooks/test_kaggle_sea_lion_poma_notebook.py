import json
from pathlib import Path
def test_kaggle_notebook_is_valid_json_and_has_required_config_cells():
    data = json.loads(Path("notebooks/kaggle_sea_lion_poma.ipynb").read_text(encoding="utf-8"))
    sources = "\n".join("".join(cell.get("source", [])) for cell in data["cells"])
    assert data["nbformat"] == 4
    assert 'MODEL_ID = "aisingapore/Llama-SEA-LION-v3-8B-IT"' in sources
    assert "RUN_FINAL_543 = False" in sources
    assert "POMA_PROMPT_PROFILE" in sources
    assert "run_sea_lion_kaggle_eval.py" in sources
    assert "/kaggle/working" in sources
