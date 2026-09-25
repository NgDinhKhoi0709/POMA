import json, math, re, statistics, sys, unicodedata, collections
from pathlib import Path
sys.path.insert(0, r"D:\.UIT\KLTN\github\POMA")
from preprocessing.variants import Grid, render_v1
from evaluation import exact_match
from evaluation.io import align_records, load_json_records, load_qas_records

ROOT = Path(r"D:\.UIT\KLTN\github\POMA")
tables = {str(t["table_id"]): t for t in json.loads((ROOT / "dataset/table.json").read_text(encoding="utf-8"))["table"]}
qs = {n: json.loads((ROOT / f"dataset/qas_{n}.json").read_text(encoding="utf-8"))["qas"] for n in ("train", "dev", "test")}

from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", local_files_only=True)
grids = {tid: Grid.from_table_data(t) for tid, t in tables.items()}
ntok = {tid: len(tok.encode(render_v1(g), add_special_tokens=False)) for tid, g in grids.items()}
nrows = {tid: len(g.rows) - g.n_head for tid, g in grids.items()}
ncols = {tid: g.width for tid, g in grids.items()}


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


out = {}
# 1. size distribution, question-weighted
for name in ("dev", "test"):
    v = [ntok[str(q["table_id"])] for q in qs[name]]
    r = [nrows[str(q["table_id"])] for q in qs[name]]
    out[f"size_{name}"] = {
        "tokens_median": statistics.median(v), "p75": pct(v, .75), "p90": pct(v, .9), "p95": pct(v, .95), "max": max(v),
        "gt2k": sum(x > 2000 for x in v), "gt4k": sum(x > 4000 for x in v), "gt8k": sum(x > 8000 for x in v),
        "rows_median": statistics.median(r), "rows_p90": pct(r, .9), "rows_gt30": sum(x > 30 for x in r), "rows_gt60": sum(x > 60 for x in r),
        "n": len(v),
    }

# 2. accuracy vs table size on the 992 test questions for existing full-test systems
D01 = ROOT / "outputs/d01/openrouter_qwen_qwen3-8b"
D04 = ROOT / "outputs/d04/openrouter_qwen_qwen3-8b/full"
systems = {"zero_shot_v1zs": D04 / "zero_shot_adapted.json", "few_shot": D01 / "few_shot_adapted.json", "poma_first": D01 / "poma_first.json"}
qas_test = ROOT / "dataset/qas_test.json"
bins = [(0, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 10 ** 9)]
acc = {}
for sname, path in systems.items():
    if not path.exists():
        continue
    samples, _ = align_records(load_json_records(path), load_qas_records(qas_test), candidate_policy="single-required")
    corr = {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}
    tid = {str(q["qa_id"]): str(q["table_id"]) for q in qs["test"]}
    row = {}
    for lo, hi in bins:
        ids = [i for i in corr if lo <= ntok[tid[i]] < hi]
        row[f"{lo}-{hi if hi < 10**9 else 'inf'}"] = (len(ids), round(sum(corr[i] for i in ids) / max(1, len(ids)), 3))
    acc[sname] = row
out["em_by_table_tokens_test"] = acc

# 3. row retrieval recall (gold-answer-derived evidence, extractive questions only) on dev
def norm(s):
    return " ".join(unicodedata.normalize("NFC", str(s)).lower().split())


def toks(s):
    w = re.findall(r"\w+", norm(s))
    return w + [a + "_" + b for a, b in zip(w, w[1:])]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs; self.k1 = k1; self.b = b
        self.N = len(docs); self.avg = sum(map(len, docs)) / max(1, self.N)
        df = collections.Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (self.N - n + .5) / (n + .5)) for t, n in df.items()}
        self.tf = [collections.Counter(d) for d in docs]

    def score(self, q):
        s = []
        for d, tf in zip(self.docs, self.tf):
            v = 0.0
            for t in set(q):
                if t in tf:
                    v += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            s.append(v)
        return s


SKIP = {"có", "không", "null", "yes", "no"}
res = {}
for name in ("dev",):
    rows_stat = collections.defaultdict(lambda: collections.Counter())
    n_ext = 0
    for q in qs[name]:
        tid = str(q["table_id"]); g = grids[tid]
        gold = norm(q["answer"])
        if len(gold) < 3 or gold in SKIP:
            continue
        body = [r for r in g.rows[g.n_head:]]
        gold_rows = [i for i, r in enumerate(body) if gold in [norm(c) for c in r]]
        if not gold_rows:
            continue
        n_ext += 1
        n = len(body)
        docs = [toks(" ".join(r)) for r in body]
        scores = BM25(docs).score(toks(q["question"]))
        order = sorted(range(n), key=lambda i: -scores[i])
        rank = min(order.index(i) for i in gold_rows)
        for k in (3, 5, 10, 20):
            rows_stat[k]["hit"] += rank < k
            rows_stat[k]["n_gt_k"] += n > k
            rows_stat[k]["hit_when_gt_k"] += (rank < k) and n > k
    res[name] = {"extractive_questions": n_ext,
                 **{f"recall@{k}": round(c["hit"] / n_ext, 3) for k, c in rows_stat.items()},
                 **{f"tables_longer_than_{k}_rows": c["n_gt_k"] for k, c in rows_stat.items()},
                 **{f"recall@{k}_on_long": round(c["hit_when_gt_k"] / max(1, c["n_gt_k"]), 3) for k, c in rows_stat.items()}}
out["bm25_row_recall"] = res

# 4. column structure: how many columns, share of gold in a single column
out["cols"] = {"median": statistics.median(ncols.values()), "p90": pct(list(ncols.values()), .9), "max": max(ncols.values())}
print(json.dumps(out, ensure_ascii=False, indent=1))
