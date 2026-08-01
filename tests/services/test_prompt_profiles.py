from pathlib import Path

import src.config.settings as settings_module
import src.services.prompt_loader as prompt_loader


def _reset_settings(monkeypatch, project_root: Path) -> None:
    monkeypatch.setattr(settings_module, "_settings", None)
    monkeypatch.setenv("POMA_PROJECT_ROOT", str(project_root))
    prompt_loader.reset_prompt_cache()


def test_default_prompt_profile_uses_src_prompts(monkeypatch, tmp_path):
    root = tmp_path
    (root / "src" / "prompts").mkdir(parents=True)
    (root / "src" / "prompts" / "sample.md").write_text("default {x}", encoding="utf-8")
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompt_profile == "default"
    assert prompt_loader.load_prompt("sample", x="A") == "default A"


def test_compact_prompt_profile_uses_src_prompts_compact(monkeypatch, tmp_path):
    root = tmp_path
    (root / "src" / "prompts_compact").mkdir(parents=True)
    (root / "src" / "prompts_compact" / "sample.md").write_text("compact {x}", encoding="utf-8")
    monkeypatch.setenv("POMA_PROMPT_PROFILE", "compact")
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompts_dir == root / "src" / "prompts_compact"
    assert prompt_loader.load_prompt("sample", x="B") == "compact B"


def test_prompt_dir_override_wins_over_profile(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    custom = tmp_path / "custom_prompts"
    custom.mkdir(parents=True)
    (custom / "sample.md").write_text("custom {x}", encoding="utf-8")
    monkeypatch.setenv("POMA_PROMPT_PROFILE", "compact")
    monkeypatch.setenv("POMA_PROMPTS_DIR", str(custom))
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompts_dir == custom
    assert prompt_loader.load_prompt("sample", x="C") == "custom C"
