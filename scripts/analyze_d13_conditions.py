# -*- coding: utf-8 -*-
"""Did the columns holding the question's own condition values survive the filter?"""
import json, sys, io, re, statistics, unicodedata
from collections import Counter
sys.path.insert(0,'.'); sys.path.insert(0,'scripts')
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
from analyze_d13 import em_score, answer_survives
from preprocessing.header_filter import prepare
qas={str(q["qa_id"]):q for q in json.load(open('outputs/d13/qas_d13_200.json',encoding='utf-8'))["qas"]}
tabs={t["table_id"]:t for t in json.load(open('dataset/table.json',encoding='utf-8'))["table"]}
latest={}
for l in open('outputs/d13/records.jsonl',encoding='utf-8'):
    r=json.loads(l); latest[(r["arm"],str(r["qa_id"]))]=r
def em(arm,qid):
    r=latest[(arm,qid)]
    if "error" in r:
        return em_score(["Null"],qas[qid]) if "final_answer: None is not of type" in r["error"] else 0.0
    return em_score(r.get("prediction") or [""],qas[qid])
def norm(t): return " ".join(unicodedata.normalize("NFC",str(t or "")).lower().split())
def words(t): return re.findall(r"\w+", norm(t))
def condition_cols(grid, question):
    """Columns holding a body cell whose text is named verbatim in the question."""
    padded=f" {' '.join(words(question))} "
    cols=set()
    for i in range(grid.n_head, len(grid.rows)):
        for j,v in enumerate(grid.rows[i]):
            w=words(v)
            if w and len(norm(v))>=2 and f" {' '.join(w)} " in padded:
                cols.add(j)
    return cols
groups={"win":[],"loss":[],"tie":[]}
for q in sorted(qas):
    a,b=em("hdrfilter",q),em("v1_raw",q)
    groups["win" if a>b else "loss" if a<b else "tie"].append(q)
summary={}
for g,qs in groups.items():
    have=0; lost=0; none=0; ratios=[]
    for q in qs:
        rec=latest[("hdrfilter",q)]
        grid,_=prepare(tabs[qas[q]["table_id"]])
        cond=condition_cols(grid, qas[q]["question"])
        kept=set(rec.get("kept_cols") or [])
        if not cond: none+=1; continue
        ratios.append(len(cond&kept)/len(cond))
        if cond<=kept: have+=1
        else: lost+=1
    summary[g]={"n":len(qs),"no_condition_cell_found":none,"all_condition_cols_kept":have,
                "some_condition_col_dropped":lost,
                "mean_condition_cols_kept":round(statistics.mean(ratios),3) if ratios else None}
print(json.dumps(summary,ensure_ascii=False,indent=2))
# the 14 losses where the answer cell survived
l14=[q for q in groups["loss"] if answer_survives(qas[q],tabs[qas[q]["table_id"]],latest[("hdrfilter",q)])=="kept"]
c=Counter()
for q in l14:
    grid,_=prepare(tabs[qas[q]["table_id"]])
    cond=condition_cols(grid,qas[q]["question"]); kept=set(latest[("hdrfilter",q)].get("kept_cols") or [])
    c["no_condition_cell"]+=not cond
    if cond: c["condition_col_dropped" if not cond<=kept else "condition_cols_all_kept"]+=1
print("losses where answer cell survived (n=%d):"%len(l14), dict(c))
