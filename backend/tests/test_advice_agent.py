from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.advice_agent import _parse_final_json


def test_llm_generation_uses_openai_tool_call_loop(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_request_chat_completion(**kwargs):
        calls.append(kwargs)
        assert "tools" not in kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        assert len(kwargs["messages"]) == 2
        user_content = kwargs["messages"][1]["content"]
        assert "get_advice_context" in user_content
        assert "inventory_1" in user_content
        assert "今天吃什么" in user_content
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"summary":"今天先吃香蕉。","recommendations":[{'
                            '"title":"优先吃香蕉",'
                            '"content":"香蕉处于 fresh 状态，可以优先安排。",'
                            '"action_type":"eat_first",'
                            '"related_foods":["banana"],'
                            '"basis":["香蕉有可食用库存","水果建议适量"],'
                            '"evidence_ids":["inventory_1","storage_banana_251_pantry",'
                            '"nutri_banana_usda","rule_fruit_moderation_001"],'
                            '"confidence":"high"}]}'
                        ),
                    },
                    "finish_reason": "stop",
                }
            ]
        }

    monkeypatch.setattr("app.services.advice_agent.request_chat_completion", fake_request_chat_completion)

    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/advice/llm",
            json={"question": "今天吃什么", "enable_thinking": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["errors"] == []
    assert data["advice"]["recommendations"][0]["evidence_ids"][0] == "inventory_1"
    assert len(calls) == 1


def test_agent_final_json_parser_accepts_wrapped_json() -> None:
    content = '说明文字\n```json\n{"summary":"ok","recommendations":[]}\n```\n'

    assert _parse_final_json(content) == {"summary": "ok", "recommendations": []}


def _tool_call(call_id: str, name: str, arguments: dict) -> dict:
    import json

    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _recognition_payload(
    *,
    counts: dict[str, int],
    captured_at: datetime | None = None,
) -> dict:
    captured_at = captured_at or datetime.now(timezone.utc)
    detections = []
    for class_name, count in counts.items():
        for index in range(count):
            detections.append(
                {
                    "class_name": class_name,
                    "confidence": 0.92,
                    "bbox": [10 + index, 20 + index, 110 + index, 220 + index],
                }
            )
    return {
        "camera_id": "cam-kitchen",
        "source": "ai_camera",
        "captured_at": captured_at.isoformat(),
        "model_name": "yolo",
        "model_version": "mvp",
        "image": {"original_path": "/tmp/frame.jpg", "width": 640, "height": 480},
        "detections": detections,
    }
