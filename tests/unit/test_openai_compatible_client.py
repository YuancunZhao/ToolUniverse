import sys
from types import SimpleNamespace

import pytest

from tooluniverse.llm_clients import OpenAICompatibleClient


class FakeRateLimitError(Exception):
    pass


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="hel"))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))]
                ),
            ]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )


class FakeOpenAIClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=self.completions.create,
                parse=self.completions.create,
            )
        )
        FakeOpenAIClient.instances.append(self)


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    FakeOpenAIClient.instances = []
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=FakeOpenAIClient, RateLimitError=FakeRateLimitError),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


def test_openai_compatible_client_uses_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    assert FakeOpenAIClient.instances[0].kwargs == {
        "api_key": "test-key",
        "base_url": "https://example.test/v1",
    }
    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=True,
        max_retries=1,
        retry_delay=0,
    )
    assert result == "ok"


def test_openai_compatible_default_max_tokens_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_TOKENS_BY_MODEL", '{"gpt-4o": 123}')
    client = OpenAICompatibleClient(
        "gpt-4o-mini",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=None,
        max_tokens=None,
        return_json=False,
        max_retries=1,
        retry_delay=0,
    )

    assert result == "ok"
    assert FakeOpenAIClient.instances[0].completions.calls[0]["max_tokens"] == 123


def test_openai_reasoning_model_uses_completion_tokens(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_TOKENS_BY_MODEL", '{"o4-mini": 321}')
    client = OpenAICompatibleClient(
        "provider/o4-mini",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0.7,
        max_tokens=None,
        return_json=False,
        max_retries=1,
        retry_delay=0,
    )

    assert result == "ok"
    call = FakeOpenAIClient.instances[0].completions.calls[0]
    assert call["max_completion_tokens"] == 321
    assert "max_tokens" not in call
    assert "temperature" not in call


def test_openai_compatible_streaming():
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    chunks = list(
        client.infer_stream(
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=16,
            return_json=False,
            max_retries=1,
            retry_delay=0,
        )
    )

    assert chunks == ["hel", "lo"]
    call = FakeOpenAIClient.instances[0].completions.calls[0]
    assert call["stream"] is True
    assert call["max_tokens"] == 16
