import pytest

from src.services import llm_client as llm_client_module


@pytest.fixture(autouse=True)
def _reset_shared_client(monkeypatch):
    monkeypatch.setattr(llm_client_module, "_shared_client", None)
    yield
    llm_client_module._shared_client = None


def test_default_api_base_is_openrouter(monkeypatch):
    monkeypatch.delenv("POMA_OPENROUTER_API_BASE", raising=False)
    client = llm_client_module._get_shared_client()
    assert client._openrouter_api_base == "https://openrouter.ai/api/v1"


def test_env_overrides_api_base(monkeypatch):
    monkeypatch.setenv("POMA_OPENROUTER_API_BASE", "http://1.2.3.4:5678/v1/")
    client = llm_client_module._get_shared_client()
    assert client._openrouter_api_base == "http://1.2.3.4:5678/v1"


def test_blank_env_keeps_default(monkeypatch):
    monkeypatch.setenv("POMA_OPENROUTER_API_BASE", "   ")
    client = llm_client_module._get_shared_client()
    assert client._openrouter_api_base == "https://openrouter.ai/api/v1"
