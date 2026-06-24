"""Parallel executor for running specialist agents concurrently."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Run a list of callables in parallel using a thread pool."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers or get_settings().parallel_max_workers

    def run(self, tasks: List[Callable[[], Any]]) -> List[Any]:
        if not tasks:
            return []

        if len(tasks) == 1:
            return [tasks[0]()]

        results: List[Any] = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            future_to_idx = {pool.submit(task): idx for idx, task in enumerate(tasks)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception:
                    logger.exception("Task %d failed", idx)
                    for pending in future_to_idx:
                        if pending is not future:
                            pending.cancel()
                    raise

        return results
