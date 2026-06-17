import json
from typing import Any

import httpx

from app.config import settings


class LlmClientError(RuntimeError):
    pass


def request_llm_json(
    *,
    system_prompt: str,
    user_prompt: str,
    enable_thinking: bool,
) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise LlmClientError("LLM_API_KEY is not configured.")

    data = request_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        enable_thinking=enable_thinking,
        response_format={"type": "json_object"},
    )

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmClientError("LLM response missing choices[0].message.content.") from exc

    return _parse_json_content(content)


def request_chat_completion(
    *,
    messages: list[dict[str, Any]],
    enable_thinking: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise LlmClientError("LLM_API_KEY is not configured.")

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if response_format is not None:
        payload["response_format"] = response_format
    if enable_thinking:
        payload["extra_body"] = {"enable_thinking": True}

    url = _chat_completions_url(settings.llm_api_base)
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LlmClientError(f"LLM request failed: {exc}") from exc
    return response.json()


def _parse_json_content(content: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise LlmClientError("LLM response is not valid JSON.") from exc


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"
