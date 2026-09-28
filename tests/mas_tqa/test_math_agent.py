import json

import pytest

from mas_tqa import math_agent as ma
from mas_tqa.client import Usage


def test_safe_eval_allows_arithmetic_and_aggregates_only():
    assert ma.safe_eval("4512 - 2999") == 1513
    assert ma.safe_eval("avg([1, 2, 3]) * 2") == 4
    assert ma.safe_eval("round(10 / 3, 2)") == 3.33
    for bad in ("__import__('os')", "open('x')", "2 ** 1000", "(1).__class__"):
        with pytest.raises(ValueError):
            ma.safe_eval(bad)


def test_execute_types():
    cells = [{"label": "A", "text": "4.512", "value": 4512}, {"label": "B", "text": "2.999", "value": 2999}]
    assert ma.execute({"type": "tính", "cells": cells, "expr": "4512 - 2999"}) == ("1.513", "")
    assert ma.execute({"type": "dem", "cells": cells}) == ("2", "")
    assert ma.execute({"type": "chọn", "cells": cells, "select": "min"}) == ("B", "")
    assert ma.execute({"type": "xếp_hạng", "cells": cells, "select": "max", "target": "B"}) == ("2", "")
    assert ma.execute({"type": "lookup", "cells": []}) == (None, "lookup")
    assert ma.execute({"type": "tính", "cells": [{"text": "121,84"}], "expr": "121.84 / 2"})[0] == "60,92"


def test_grounding_requires_cited_cells_in_table():
    table = "## Hàng 1\nTên: Ireland\nSố lượng: 4.512"
    assert ma.grounded({"cells": [{"text": "4.512"}]}, table)
    assert not ma.grounded({"cells": [{"text": "4.712"}]}, table)


class Fake:
    def __init__(self, plan, verdict):
        self.plan, self.verdict, self.calls = plan, verdict, []

    def chat(self, prompt, **kw):
        kind = "V" if "KIỂM TRA" in prompt else "M"
        self.calls.append(kind)
        return [json.dumps(self.plan if kind == "M" else self.verdict, ensure_ascii=False)], Usage(1, 10, 1)


def test_solve_uses_verifier_fix_and_skips_lookup():
    plan = {"type": "tính", "cells": [{"text": "4.512", "value": 4512}], "expr": "4512 - 2799"}
    fix = {**plan, "expr": "4512 - 2999"}
    out = ma.solve(Fake(plan, {"ok": False, "reason": "sai ô", "fix": fix}), {"question": "Hơn bao nhiêu?"}, "P\n", "4.512 2.999")
    assert out["M"] == "1.713" and out["V_ok"] is False and out["V"] == "1.513" and out["M_grounded"]
    lk = Fake({"type": "lookup", "cells": []}, {})
    out = ma.solve(lk, {"question": "Cao bao nhiêu?"}, "P\n", "")
    assert out["M"] == "" and lk.calls == ["M"]
