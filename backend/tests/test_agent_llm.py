import pytest
from langchain_anthropic import ChatAnthropic

from app.agent.llm import GenerationModelConfig, get_model


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
    monkeypatch.setenv("COURSE_GEN_MODEL_ANTHROPIC_STANDARD", "claude-custom")
    model = get_model(
        tier="standard",
        model_config=GenerationModelConfig(
            provider="anthropic", api_key="provider-key"
        ),
    )

    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-custom"  # ChatAnthropic aliases model_name -> model
