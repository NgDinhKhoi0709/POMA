"""Shared loaders and helpers for the POMA gate-headroom analysis.

Offline only: no LLM/API calls. The repo is imported read-only; the
Answer-Normalization (AN) module is monkeypatched *in memory* to fix the
mojibake in its boolean-TRUE constants (the file on disk is not modified).
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent / "poma_repo"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation import exact_match  # noqa: E402
from evaluation.contracts import AlignedSample  # noqa: E402
from evaluation.io import load_json_records, load_qas_records  # noqa: E402
from evaluation.normalization import (  # noqa: E402
    exact_text_match,
    is_unanswerable_prediction,
    is_unanswerable_reference,
    normalize_text,
    prediction_is_unanswerable,
)
from src.contracts.enums import HINT_ALIASES_TO_CANONICAL  # noqa: E402
import src.agents.answer_normalization as AN  # noqa: E402

# ---------------------------------------------------------------- AN patch
# On disk: _BOOLEAN_TRUE_VARIANTS = ("CĂ³", "ÄĂºng", "Pháº£i") -- UTF-8 read as
# cp1258/latin and re-saved. The recorded outputs contain the correct forms
# ("Có", "Đúng", "Phải"), so the run used an uncorrupted version.
AN_PATCH_NOTE = (
    "evaluation-time patch (in memory only): AN._BOOLEAN_TRUE_VARIANTS "
    "mojibake ('CĂ³','ÄĂºng','Pháº£i') replaced by ('Có','Đúng','Phải'); "
    "unit alias 'ngÆ°á»i/km2' replaced by 'người/km2'"
)
AN._BOOLEAN_TRUE_VARIANTS = ("Có", "Đúng", "Phải")
AN._BOOLEAN_TRUE_NORMALIZED = {
    AN.normalize_match_text(v) for v in (*AN._BOOLEAN_TRUE_VARIANTS, "yes", "true")
}
import re as _re  # noqa: E402

_fixed_aliases = []
for pat, variants in AN._UNIT_ALIASES:
    if "ngÆ°" in pat.pattern:
        pat = _re.compile(r"(?i)người/km(?:2|²)")
        variants = ("người/km2", "người/km²")
    _fixed_aliases.append((pat, variants))
AN._UNIT_ALIASES = tuple(_fixed_aliases)

OUT = HERE
PATHS = {
    "qas": REPO / "dataset/qas_test.json",
    "tables": REPO / "dataset/table.json",
    "hp": REPO / "outputs/poma/qwen/poma_qas_test_qwen3_8b_hp.json",
    "no_hp": REPO / "outputs/poma/qwen/poma_qas_test_qwen3_8b_no_hp.json",
    "hp_traces": REPO / "outputs/poma/qwen/poma_qas_test_qwen3_8b_hp_traces.json",
    "no_hp_traces": REPO / "outputs/poma/qwen/poma_qas_test_qwen3_8b_no_hp_traces.json",
    "abl_hp": REPO / "outputs/poma/ablation/poma_qas_test_gpt4o_hp_without_answer_normalization.json",
    "abl_no_hp": REPO / "outputs/poma/ablation/poma_qas_test_gpt4o_no_hp_without_answer_normalization.json",
    "hint_pred": REPO / "outputs/poma/hint_predictor/qas_test.json",
    "FS": REPO / "outputs/baseline/qwen/full_few_shot/qwen3-8b.json",
    "ZS": REPO / "outputs/baseline/qwen/full_zs/qwen3-8b.json",
    "CoT": REPO / "outputs/baseline/qwen/full_cot/qwen3-8b.json",
    "TD": REPO / "outputs/baseline/qwen/full_td/qwen3-8b.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def qas_by_id():
    return {str(q["qa_id"]): q for q in load_qas_records(PATHS["qas"])}


def preds_by_id(key):
    return {str(p["qa_id"]): p for p in load_json_records(PATHS[key])}


def traces_by_id(key):
    return {str(t["qa_id"]): t for t in load_json(PATHS[key])}


def canon_hint(h: str) -> str:
    c = HINT_ALIASES_TO_CANONICAL.get(h.strip())
    if c is None:
        for a, t in HINT_ALIASES_TO_CANONICAL.items():
            if a.casefold() == h.strip().casefold():
                return t
        raise ValueError(h)
    return c


def gold_canon_hints(q) -> list[str]:
    out = []
    for h in q.get("hints", []) or []:
        c = canon_hint(h)
        if c not in out:
            out.append(c)
    return out


# ------------------------------------------------------------ correctness
def em(cands, q) -> bool:
    """Repo evaluator EM (best-of-K over `cands`) against dataset gold."""
    if isinstance(cands, str):
        cands = [cands]
    cands = [str(c).strip() for c in cands if c is not None]
    s = AlignedSample(
        qa_id=str(q["qa_id"]),
        prediction=cands or [""],
        reference=str(q.get("answer", "")),
        hints=[str(h) for h in q.get("hints", []) or []],
    )
    return exact_match.score_sample(s).value == 1.0


def is_null_answer(a) -> bool:
    """Evaluator's notion of an unanswerable prediction string."""
    return is_unanswerable_prediction("" if a is None else str(a))


def gold_is_null(q) -> bool:
    return is_unanswerable_reference(q.get("answer", ""))


# ------------------------------------------------------- AN reconstruction
class ReplayLLMError(RuntimeError):
    pass


def an_variants_replay(specialists, question, target, an_calls):
    """Re-run AN.run() per specialist with the recorded LLM responses replayed.

    Returns (per_specialist_variant_lists, union_in_run_many_order, ok_flag,
    n_llm_calls_consumed).
    """
    agent = AN.AnswerNormalizationAgent.__new__(AN.AnswerNormalizationAgent)
    queue = list(an_calls)
    consumed = {"n": 0}

    def fake(prompt, prompt_name):
        if not queue:
            raise ReplayLLMError("no recorded AN call left")
        call = queue.pop(0)
        consumed["n"] += 1
        if call.get("prompt_name") != prompt_name:
            raise ReplayLLMError(
                f"prompt mismatch {call.get('prompt_name')} vs {prompt_name}")
        data = call.get("parsed_response")
        if not isinstance(data, dict):
            raise ReplayLLMError("recorded AN call has no parsed_response")
        return data

    agent._call_llm_json_for_prompt = fake
    agent._load_normalization_prompt = lambda name, **kw: ""
    per = []
    for sp in specialists:
        ans = sp.get("answer")
        if AN._is_explicit_null(ans):
            per.append(["Null"])
        elif AN._is_nullish_answer(ans):
            per.append([])
        else:
            per.append(agent.run(AN._strip_terminal_punctuation(str(ans)),
                                 question, target=target,
                                 answer_hint=sp.get("agent_name")))
    merged = []
    for v in per:
        merged.extend(v)
    merged = AN._dedup_match_equivalent(merged)
    return per, merged, (len(queue) == 0), consumed["n"]


def deterministic_variants(answer, question, target=None, agent_name=None):
    """Repo AN deterministic variants only (no LLM); Null handling as AN.run."""
    if answer is None:
        return []
    a = AN._strip_terminal_punctuation(str(answer))
    if not a:
        return []
    if AN._is_explicit_null(a) or is_null_answer(a):
        return ["Null"]
    if AN._should_force_null_why(question):
        return ["Null"]
    kind = AN._infer_answer_kind(a, question, agent_name)
    if AN._should_force_null_why_answer(a, question, kind):
        return ["Null"]
    if AN._should_force_null_how_answer(a, question, kind):
        return ["Null"]
    return AN._deterministic_variants(a, question=question, target=target,
                                      answer_kind=kind)


def deterministic_variants_no_forcing(answer, question, target=None, agent_name=None):
    """Surface variants only (no Why/How force-Null rules): pure canonicalization."""
    if answer is None:
        return []
    a = AN._strip_terminal_punctuation(str(answer))
    if not a:
        return []
    if AN._is_explicit_null(a) or is_null_answer(a):
        return ["Null"]
    kind = AN._infer_answer_kind(a, question, agent_name)
    return AN._deterministic_variants(a, question=question, target=target,
                                      answer_kind=kind)


def old_list_variants(answer):
    """Emulation of the AN list-variant rule that produced the recorded run:
    original + every adjacent swap, each joined with ', ' ',' '; ' ';' ' '.
    (Current repo code returns [answer] only.) Reproduces K = 5n exactly."""
    items = AN._coerce_list_items(answer)
    if not items:
        return [answer]
    perms = [list(items)]
    for i in range(len(items) - 1):
        p = list(items)
        p[i], p[i + 1] = p[i + 1], p[i]
        perms.append(p)
    out = [answer]
    for p in perms:
        for sep in (", ", ",", "; ", ";", " "):
            out.append(sep.join(p))
    return AN._dedup_match_equivalent(out)


class recorded_run_an:
    """Context manager: swap in the recorded-run list-variant rule."""
    def __enter__(self):
        self._saved = AN._list_variants
        AN._list_variants = old_list_variants
    def __exit__(self, *exc):
        AN._list_variants = self._saved


from evaluation.normalization import parse_list_items  # noqa: E402
from collections import Counter as _Counter  # noqa: E402


def canon_equal(a, b) -> bool:
    """Hint-free deterministic equality used for agreement/voting:
    both evaluator-unanswerable -> equal; else repo normalize_text equality
    (NFC, lowercase, whitespace collapse, trailing '.' stripped); else, if both
    parse as lists (repo parse_list_items), order-insensitive multiset equality
    of normalized items."""
    na, nb = is_null_answer(a), is_null_answer(b)
    if na or nb:
        return na and nb
    if normalize_text(a) == normalize_text(b):
        return True
    la, lb = parse_list_items(a), parse_list_items(b)
    if la and lb:
        return _Counter(map(normalize_text, la)) == _Counter(map(normalize_text, lb))
    return False


def variant_sets_agree(va, vb) -> bool:
    """Two variant lists agree if any pair is canon_equal."""
    return any(canon_equal(a, b) for a in va for b in vb)


def auroc(scores, labels):
    """Mann-Whitney AUROC with tie correction; None if one class empty."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def nfc(s):
    return unicodedata.normalize("NFC", s)


def dump(name, obj):
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
