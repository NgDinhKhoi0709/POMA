"""Lazy dispatch to one vendored baseline per Python process."""

from __future__ import annotations

from typing import Any


def dispatch_run(method: str, **kwargs: Any) -> dict[str, Any]:
    if method == "coagt":
        from baselines.coagt.agent_approach_open_vitabqa import run_open_vitabqa
    elif method == "coq":
        from baselines.chain_of_query.run_open_vitabqa import run_open_vitabqa
    else:
        raise ValueError(f"unsupported baseline: {method}")
    return run_open_vitabqa(**kwargs)
