import json, sys, unicodedata, collections
from pathlib import Path
sys.path.insert(0, r"D:\.UIT\KLTN\github\POMA")
from preprocessing.variants import Grid, render_v1
from evaluation import exact_match
from evaluation.io import align_records, load_json_records, load_qas_records
ROOT = Path(r"D:\.UIT\KLTN\github\POMA")
tables = {str(t["table_id"]): t for t in json.loads((ROOT / "dataset/table.json").read_text(encoding="utf-8"))["table"]}
qs = json.loads((ROOT / "dataset/qas_test.json").read_text(encoding="utf-8"))["qas"]
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", local_files_only=True)
grids = {tid: Grid.from_table_data(t) for tid, t in tables.items()}
ntok = {tid: len(tok.encode(render_v1(g), add_special_tokens=False)) for tid, g in grids.items()}
norm = lambda s: " ".join(unicodedata.normalize("NFC", str(s)).lower().split())
SKIP = {"có", "không", "null", "yes", "no"}
def extractive(q):
    g = grids[str(q["table_id"])]; a = norm(q["answer"])
    if len(a) < 3 or a in SKIP: return False
    return any(a == norm(c) for r in g.rows[g.n_head:] for c in r)
ext = {str(q["qa_id"]): extractive(q) for q in qs}
tid = {str(q["qa_id"]): str(q["table_id"]) for q in qs}
tot = sum(ntok[tid[i]] for i in tid); long_ = sum(ntok[tid[i]] for i in tid if ntok[tid[i]] > 2000)
print("share of total table tokens from >2k tables", round(long_ / tot, 3), "questions", sum(ntok[tid[i]] > 2000 for i in tid))
D01 = ROOT / "outputs/d01/openrouter_qwen_qwen3-8b"; D04 = ROOT / "outputs/d04/openrouter_qwen_qwen3-8b/full"
for name, path in {"zero_shot_v1zs": D04 / "zero_shot_adapted.json", "few_shot": D01 / "few_shot_adapted.json"}.items():
    samples, _ = align_records(load_json_records(path), load_qas_records(ROOT / "dataset/qas_test.json"), candidate_policy="single-required")
    corr = {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}
    for label, cond in (("<=2k", lambda i: ntok[tid[i]] <= 2000), (">2k", lambda i: ntok[tid[i]] > 2000)):
        for e in (True, False):
            ids = [i for i in corr if cond(i) and ext[i] == e]
            print(name, label, "extractive" if e else "other", len(ids), round(sum(corr[i] for i in ids) / max(1, len(ids)), 3))
