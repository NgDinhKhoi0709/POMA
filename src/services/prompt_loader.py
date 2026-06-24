"""
Load prompt templates from the ``prompts/`` directory tree.

Templates are plain Markdown files.  Variable substitution uses
``{variable_name}`` placeholders resolved via ``str.format_map``.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Dict, Optional

from src.config.settings import get_settings

_cache: Dict[str, str] = {}


def _prompts_dir() -> Path:
    return get_settings().prompts_dir


def load_prompt(name: str, **kwargs: str) -> str:
    """Load ``prompts/<name>.md`` and substitute ``{key}`` placeholders.

    Parameters
    ----------
    name:
        Dot-separated or slash-separated path relative to ``prompts/``,
        **without** the ``.md`` extension.
        E.g. ``"question_refiner"`` → ``prompts/question_refiner.md``
             ``"specialists/what"`` → ``prompts/specialists/what.md``
             ``"specialists.what"`` → ``prompts/specialists/what.md``
    """
    key = name.replace(".", "/")
    if key not in _cache:
        path = _prompts_dir() / f"{key}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        _cache[key] = path.read_text(encoding="utf-8")

    template = _cache[key]
    if kwargs:
        template = template.format_map(_SafeDict(kwargs))
    return template


class _SafeDict(dict):
    """dict subclass that returns the key literal for missing placeholders."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
