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
class LocalModelConfig:
    model_id: str = "aisingapore/Llama-SEA-LION-v3-8B-IT"
    max_model_len: int = 32768
    max_input_tokens: int = 28672
    quantization: str = "nf4"
    max_new_tokens: int = 512
    hint_preview_tokens: int = 1024


@dataclass(frozen=True)
class Settings:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    prompts_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "prompts")
    prompt_profile: str = "default"

    llm: LLMConfig = field(default_factory=LLMConfig)
    local_model: LocalModelConfig = field(default_factory=LocalModelConfig)
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

    project_root = Path(
        _env_str(
            "POMA_PROJECT_ROOT",
            str(Path(__file__).resolve().parent.parent.parent),
        )
    )
    prompt_profile = _env_str("POMA_PROMPT_PROFILE", "default").strip().lower() or "default"
    prompt_dir_override = os.environ.get("POMA_PROMPTS_DIR")
    if prompt_dir_override:
        prompts_dir = Path(prompt_dir_override)
    elif prompt_profile == "compact":
        prompts_dir = project_root / "src" / "prompts_compact"
    else:
        prompts_dir = project_root / "src" / "prompts"

    _settings = Settings(
        project_root=project_root,
        prompts_dir=prompts_dir,
        prompt_profile=prompt_profile,
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
        local_model=LocalModelConfig(
            model_id=_env_str("POMA_LOCAL_MODEL_ID", LocalModelConfig.model_id),
            max_model_len=_env_int("POMA_LOCAL_MAX_MODEL_LEN", LocalModelConfig.max_model_len),
            max_input_tokens=_env_int("POMA_LOCAL_MAX_INPUT_TOKENS", LocalModelConfig.max_input_tokens),
            quantization=_env_str("POMA_LOCAL_QUANTIZATION", LocalModelConfig.quantization),
            max_new_tokens=_env_int("POMA_LOCAL_MAX_NEW_TOKENS", LocalModelConfig.max_new_tokens),
            hint_preview_tokens=_env_int("POMA_HINT_PREVIEW_TOKENS", LocalModelConfig.hint_preview_tokens),
        ),
        parallel_max_workers=_env_int("POMA_PARALLEL_WORKERS", Settings.parallel_max_workers),
        answer_language=_env_str("POMA_ANSWER_LANGUAGE", Settings.answer_language),
        use_consensus_fusion=_env_bool("POMA_USE_CONSENSUS_FUSION", Settings.use_consensus_fusion),
        use_agent_hints=_env_bool("POMA_USE_AGENT_HINTS", Settings.use_agent_hints),
    )
    return _settings
