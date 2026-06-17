from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.advice_agent import _parse_final_json, _selection_plan_to_advice


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
                            '{"summary_focus":"今天先吃香蕉。","selected":[{'
                            '"candidate_id":"inventory_1",'
                            '"action_type":"eat_first",'
                            '"reason":"香蕉现在可吃，适合先安排。",'
                            '"evidence_ids":["inventory_1","storage_banana_251_pantry"],'
                            '"title_hint":"优先吃香蕉"}],'
                            '"excluded":[]}'
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
    recommendation = data["advice"]["recommendations"][0]
    assert recommendation["title"] == "优先吃香蕉"
    assert recommendation["action_type"] == "eat_first"
    assert recommendation["related_foods"] == ["banana"]
    assert recommendation["evidence_ids"][0] == "inventory_1"
    assert recommendation["evidence_sources"]
    assert "香蕉现在可吃" in recommendation["basis"][0]
    assert len(calls) == 1


def test_agent_final_json_parser_accepts_wrapped_json() -> None:
    content = '说明文字\n```json\n{"summary":"ok","recommendations":[]}\n```\n'

    assert _parse_final_json(content) == {"summary": "ok", "recommendations": []}


def test_selection_plan_drops_unknown_candidate() -> None:
    advice = _selection_plan_to_advice(
        {
            "summary_focus": "测试",
            "selected": [
                {
                    "candidate_id": "inventory_missing",
                    "reason": "不存在",
                    "evidence_ids": ["inventory_missing"],
                }
            ],
        },
        _selection_context(),
    )

    assert advice == {"summary": "测试", "recommendations": []}


def test_selection_plan_filters_evidence_outside_candidate() -> None:
    advice = _selection_plan_to_advice(
        {
            "summary_focus": "解辣优先清爽温和",
            "selected": [
                {
                    "candidate_id": "inventory_11",
                    "action_type": "eat_first",
                    "reason": "梨含水多、口感清爽，适合缓和辣感。",
                    "evidence_ids": ["inventory_11", "inventory_999", "nutri_pear_usda"],
                    "title_hint": "先吃梨缓一缓",
                }
            ],
        },
        _selection_context(),
    )

    item = advice["recommendations"][0]
    assert item["title"] == "先吃梨缓一缓"
    assert item["related_foods"] == ["pear"]
    assert "inventory_999" not in item["evidence_ids"]
    assert item["evidence_ids"] == [
        "inventory_11",
        "storage_pear_266_refrigerate",
        "nutri_pear_usda",
    ]
    assert "梨含水多" in item["content"]
    assert "梨含水多" in item["basis"][0]


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


def _selection_context() -> dict:
    return {
        "purpose": "eating",
        "query": "我刚吃的太辣了想解辣吃什么",
        "eating_candidates": [
            {
                "candidate_id": "inventory_11",
                "food": "pear",
                "display_name": "梨",
                "batch": {
                    "evidence_id": "inventory_11",
                    "food": "pear",
                    "display_name": "梨",
                    "confirmed_quantity": 2,
                    "unit": "piece",
                    "status": "available",
                    "storage_location": "refrigerate",
                    "storage_state": "eat_soon",
                    "remaining_days": 0,
                },
                "allowed_evidence_ids": [
                    "inventory_11",
                    "storage_pear_266_refrigerate",
                    "nutri_pear_usda",
                ],
                "reason": "梨处于 eat_soon，剩余 0 天。",
            }
        ],
    }
