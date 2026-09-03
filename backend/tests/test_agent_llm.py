import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.agent.llm import GenerationModelConfig, get_model


@pytest.mark.parametrize(
    ("provider", "expected_base_url"),
    [
        ("openai", None),
        ("groq", "https://api.groq.com/openai/v1"),
        ("xai", "https://api.x.ai/v1"),
        ("mistral", "https://api.mistral.ai/v1"),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai"),
        ("ollama", "http://localhost:11434/v1"),
        ("deepseek", "https://api.deepseek.com/v1"),
    ],
)
def test_openai_compatible_providers_use_chatopenai(provider, expected_base_url):
    model = get_model(
        tier="fast",
        model_config=GenerationModelConfig(provider=provider, api_key="provider-key"),
    )

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == expected_base_url


def test_anthropic_provider_uses_chatanthropic():
    model = get_model(
        tier="fast",
        model_config=GenerationModelConfig(
            provider="anthropic",
            api_key="provider-key",
        ),
    )

    assert isinstance(model, ChatAnthropic)


def test_model_name_can_be_overridden_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COURSE_GEN_MODEL_DEEPSEEK_STANDARD", "deepseek-chat-custom")
    model = get_model(
        tier="standard",
        model_config=GenerationModelConfig(provider="deepseek", api_key="provider-key"),
    )

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "deepseek-chat-custom"


def test_provider_base_url_can_be_overridden_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GROQ_BASE_URL", "https://proxy.internal/openai")
    model = get_model(
        tier="fast",
        model_config=GenerationModelConfig(provider="groq", api_key="provider-key"),
    )

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "https://proxy.internal/openai"
