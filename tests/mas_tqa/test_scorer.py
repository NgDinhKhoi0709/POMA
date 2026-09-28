import json

from mas_tqa import scorer
from mas_tqa.client import Usage


def test_parse_scores_normalizes_and_falls_back_to_uniform():
    assert scorer.parse_scores('{"scores": [{"id": 0, "p": 3}, {"id": 1, "p": 1}]}', 2) == [0.75, 0.25]
    assert scorer.parse_scores('{"scores": {"1": 0.5}}', 2) == [0.0, 1.0]
    assert scorer.parse_scores("không phải JSON", 3) == [1 / 3] * 3


def test_candidates_dedupe_and_count_votes():
    trace = {"samples": ["X", "x", "Y"], "B": "", "A2": "Y", "B2": "Z"}
    cands, votes = scorer.candidates(trace, "Ai là chủ tịch?")
    assert cands == ["X", "Y", "Z"] and votes == [2, 2, 1]


class Fake:
    def chat(self, prompt, **kw):
        listing = prompt.split("CÁC ỨNG VIÊN:\n")[1].split("\nĐẦU RA")[0].splitlines()
        best = next(i for i, line in enumerate(listing) if line.endswith("] Y"))
        return [json.dumps({"scores": [{"id": best, "p": 0.9}]})], Usage(1, 10, 1)


def test_score_maps_shuffled_order_back():
    p, _ = scorer.score(Fake(), {"qa_id": "q7", "question": "?"}, "P\n", ["X", "Y", "Z"])
    assert p == [0.0, 1.0, 0.0]


def test_suite_v9_scores_with_and_without_reasons(monkeypatch):
    from mas_tqa import methods

    monkeypatch.setattr(methods, "flat_prefix", lambda qa, k=8: "FLAT\n")
    monkeypatch.setattr(methods, "kv_prefix", lambda qa, k=8: methods._KV_HEADER + "KV\n")
    monkeypatch.setattr(scorer, "prefix_flat", lambda qa: "SF\n")
    monkeypatch.setattr(scorer, "prefix_kv", lambda qa: "SK\n")

    class C:
        calls = []

        def chat(self, prompt, **kw):
            if "CÁC ỨNG VIÊN" in prompt:
                self.calls.append("score_reason" if "Lý do của agent" in prompt else "score")
                listing = prompt.split("CÁC ỨNG VIÊN:\n")[1].split("\nĐẦU RA")[0]
                best = [ln for ln in listing.splitlines() if ln.startswith("[")].index(next(ln for ln in listing.splitlines() if ln.endswith("] Y")))
                return [json.dumps({"scores": [{"id": best, "p": 1}]})], Usage(1, 1, 1)
            if "chuyên gia kia" in prompt:
                self.calls.append("rebut")
                return ['{"final_answer": "X"}'], Usage(1, 1, 1)
            if prompt.startswith(methods._KV_HEADER):
                self.calls.append("B")
                return ['{"reason": "ô Y", "evidence": ["Y"], "final_answer": "Y"}'], Usage(1, 1, 1)
            self.calls.append("A")
            return ['{"reason": "r1", "final_answer": "X"}', '{"reason": "r2", "final_answer": "Y"}',
                    '{"reason": "r3", "final_answer": "Z"}'], Usage(1, 1, 1)

    c = C()
    out = methods.suite_v9(c, {"qa_id": "q1", "table_id": "t", "question": "Ai?"})
    assert out["memview_r"]["trace"]["route"] == "debate"
    assert c.calls.count("score") == 2 and c.calls.count("score_reason") == 2
    assert out["score_r"]["prediction"] == ["Y"]
    assert "ô Y" in out["score_r"]["trace"]["notes"][out["score_r"]["trace"]["cands"].index("Y")]
