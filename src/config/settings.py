"""
Centralised configuration for the multi-agent orchestration pipeline.

Runtime knobs live here and can be overridden via environment variables
prefixed with ``POMA_``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def _env_float(key: str, default: float) -> float:
    v = os.environ.get(key)
    return float(v) if v is not None else default


def _env_int(key: str, default: int) -> int:
    v = os.environ.get(key)
    return int(v) if v is not None else default


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.lower() in ("true", "1", "yes", "on")


def _split_env_list(value: str) -> list[str]:
    items: list[str] = []
    for part in value.replace(";", ",").replace("\n", ",").split(","):
        item = part.strip()
        if item:
            items.append(item)
    return items


def _env_openrouter_provider(key: str) -> Optional[dict[str, Any]]:
    value = os.environ.get(key)
    if not value:
        return None
    providers = _split_env_list(value)
    if not providers:
        return None
    return {"only": providers}


@dataclass(frozen=True)
class LLMConfig:
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 4
    retry_delay: int = 15
    openrouter_provider: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class Settings:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    prompts_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "prompts")

    llm: LLMConfig = field(default_factory=LLMConfig)
    parallel_max_workers: int = 10
    answer_language: str = "vi"
    use_consensus_fusion: bool = False
    use_agent_hints: bool = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return a singleton ``Settings`` populated from env vars."""
    global _settings
    if _settings is not None:
        return _settings

    _settings = Settings(
        llm=LLMConfig(
            model=_env_str("POMA_LLM_MODEL", LLMConfig.model),
            temperature=_env_float("POMA_LLM_TEMPERATURE", LLMConfig.temperature),
            top_p=_env_float("POMA_LLM_TOP_P", LLMConfig.top_p),
            max_tokens=_env_int("POMA_LLM_MAX_TOKENS", LLMConfig.max_tokens),
            timeout=_env_int("POMA_LLM_TIMEOUT", LLMConfig.timeout),
            max_retries=_env_int("POMA_LLM_MAX_RETRIES", LLMConfig.max_retries),
            retry_delay=_env_int("POMA_LLM_RETRY_DELAY", LLMConfig.retry_delay),
            openrouter_provider=_env_openrouter_provider("POMA_OPENROUTER_PROVIDER"),
        ),
        parallel_max_workers=_env_int("POMA_PARALLEL_WORKERS", Settings.parallel_max_workers),
        answer_language=_env_str("POMA_ANSWER_LANGUAGE", Settings.answer_language),
        use_consensus_fusion=_env_bool("POMA_USE_CONSENSUS_FUSION", Settings.use_consensus_fusion),
        use_agent_hints=_env_bool("POMA_USE_AGENT_HINTS", Settings.use_agent_hints),
    )
    return _settings
