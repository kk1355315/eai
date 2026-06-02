from app.config import settings
from app.services.llm_client import request_llm_json


def test_openai_compatible_request_payload_thinking_on_and_off(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"summary":"ok"}'}}]}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr("app.services.llm_client.httpx.Client", FakeClient)
    monkeypatch.setattr(settings, "llm_api_base", "https://llm.example.test/v1")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_timeout_seconds", 3.5)

    request_llm_json(system_prompt="system", user_prompt="user", enable_thinking=True)
    request_llm_json(system_prompt="system", user_prompt="user", enable_thinking=False)

    assert calls[0]["url"] == "https://llm.example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"]["model"] == "test-model"
    assert calls[0]["json"]["extra_body"] == {"enable_thinking": True}
    assert "extra_body" not in calls[1]["json"]
    assert calls[0]["timeout"] == 3.5
