from datetime import datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import AdviceRecord, FoodItem, FoodStorageRule, InventoryItem
from app.routers.inventory import CHECK_REQUIRED_MESSAGE
from app.services.advice_context import build_advice_context


def test_today_advice_splits_priority_and_check_required() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1, "apple": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age("banana", "refrigerate", 3)
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        response = client.get("/advice/today")

    assert response.status_code == 200
    data = response.json()
    assert [item["food"] for item in data["today_priority"]] == ["banana"]
    assert data["today_priority"][0]["storage_state"] == "eat_soon"
    assert [item["food"] for item in data["check_required"]] == ["apple"]
    assert data["check_required"][0]["basis"] == [CHECK_REQUIRED_MESSAGE]


def test_not_recommended_does_not_enter_today_priority() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        response = client.get("/advice/today")

    assert response.status_code == 200
    data = response.json()
    assert data["today_priority"] == []
    assert data["check_required"][0]["food"] == "banana"
    assert data["check_required"][0]["storage_state"] == "not_recommended"


def test_today_advice_excludes_pending_or_zero_quantity_check_required_items() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1, "banana": 1}))
        with Session(engine) as session:
            food = session.exec(select(FoodItem).where(FoodItem.model_label == "banana")).one()
            banana = session.exec(
                select(InventoryItem).where(InventoryItem.food_item_id == food.id)
            ).one()
        client.post(f"/inventory/{banana.id}/confirm-change", json={})

        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        with Session(engine) as session:
            food = session.exec(select(FoodItem).where(FoodItem.model_label == "banana")).one()
            item = session.exec(
                select(InventoryItem).where(InventoryItem.food_item_id == food.id)
            ).one()
            item.confirmed_quantity = 0
            session.add(item)
            session.commit()

        response = client.get("/advice/today")

    assert response.status_code == 200
    data = response.json()
    assert data["today_priority"] == []
    assert data["check_required"] == []


def test_shopping_advice_warns_against_duplicate_purchase() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"pear": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.get("/advice/shopping")

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert recommendations[0]["action_type"] == "avoid_duplicate_purchase"
    assert recommendations[0]["related_foods"] == ["pear"]
    assert item["evidence_id"] in recommendations[0]["evidence_ids"]


def test_user_habit_requires_two_discards_in_30_days() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/user-food-events",
            json={"food_id": "banana", "event_type": "discarded", "quantity": 1},
        )
        after_first = client.get("/habits")
        second = client.post(
            "/user-food-events",
            json={"food_id": "banana", "event_type": "discarded", "quantity": 1},
        )
        after_second = client.get("/habits")

    assert first.status_code == 200
    assert second.status_code == 200
    assert after_first.json() == []
    habits = after_second.json()
    assert len(habits) == 1
    assert habits[0]["food"] == "banana"
    assert habits[0]["habit_type"] == "often_wastes"
    assert habits[0]["evidence"]["discarded_count"] == 2


def test_user_food_event_rejects_mismatched_food_and_inventory() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/user-food-events",
            json={
                "food_id": "apple",
                "event_type": "consumed",
                "quantity": 1,
                "inventory_id": item["id"],
            },
        )

    assert response.status_code == 400
    with Session(engine) as session:
        food = session.exec(select(FoodItem).where(FoodItem.model_label == "apple")).one()
        assert (
            session.exec(
                select(InventoryItem).where(InventoryItem.food_item_id == food.id)
            ).first()
            is None
        )


def test_user_food_event_rejects_quantity_above_confirmed_inventory() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/user-food-events",
            json={
                "food_id": "banana",
                "event_type": "consumed",
                "quantity": 3,
                "inventory_id": item["id"],
            },
        )
        after = client.get("/inventory").json()[0]

    assert response.status_code == 400
    assert response.json()["detail"] == "quantity exceeds confirmed inventory quantity"
    assert after["confirmed_quantity"] == 2
    assert after["status"] == "available"


def test_user_food_event_rejects_discard_quantity_above_confirmed_inventory() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/user-food-events",
            json={
                "food_id": "banana",
                "event_type": "discarded",
                "quantity": 3,
                "inventory_id": item["id"],
            },
        )
        after = client.get("/inventory").json()[0]

    assert response.status_code == 400
    assert response.json()["detail"] == "quantity exceeds confirmed inventory quantity"
    assert after["confirmed_quantity"] == 2
    assert after["status"] == "available"


def test_often_consumes_slow_forms_from_repeated_check_required_with_low_consumption() -> None:
    with TestClient(app) as client:
        for index in range(2):
            client.post(
                "/recognitions",
                json=_recognition_payload(
                    captured_at=datetime(2026, 5, 1 + index, 8, 0, tzinfo=timezone.utc),
                    counts={"apple": 1},
                    camera_id=f"slow-cam-{index}",
                ),
            )
            item = client.get("/inventory").json()[-1]
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        inventory = client.get("/inventory").json()
        for item in inventory:
            _set_inventory_age_by_id(
                item["id"],
                "pantry",
                _safe_days("apple", "pantry") + 1,
            )

        client.get("/inventory/storage-states")
        habits = client.get("/habits").json()

    slow = [
        habit for habit in habits if habit["habit_type"] == "often_consumes_slow"
    ]
    assert len(slow) == 1
    assert slow[0]["food"] == "apple"
    assert slow[0]["evidence"]["consumed_count"] == 0
    assert slow[0]["evidence"]["check_required_count"] == 2


def test_validate_route_accepts_valid_llm_output_without_saving() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        today = client.get("/advice/today").json()
        evidence_ids = today["today_priority"][0]["evidence_ids"] + [
            "rule_fruit_moderation_001",
            "nutri_banana_usda",
        ]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "今天优先处理香蕉。",
                    "recommendations": [
                        {
                            "title": "早餐吃香蕉",
                            "content": "香蕉处于 fresh 状态，可作为早餐或加餐的一部分。",
                            "action_type": "eat_first",
                            "related_foods": ["banana"],
                            "basis": ["香蕉当前处于 fresh 状态", "水果建议适量食用"],
                            "evidence_ids": evidence_ids,
                            "confidence": "high",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["record_id"] is None
    with Session(engine) as session:
        assert session.exec(select(AdviceRecord)).all() == []


def test_llm_advice_rejects_unknown_evidence_and_blocked_food() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "错误建议。",
                    "recommendations": [
                        {
                            "title": "今天吃苹果",
                            "content": "苹果可以今天吃。",
                            "action_type": "eat_first",
                            "related_foods": ["apple"],
                            "basis": ["无依据"],
                            "evidence_ids": ["missing_evidence"],
                            "confidence": "high",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("unknown evidence_id" in error for error in data["errors"])
    assert any("checked food" in error for error in data["errors"])


def test_evidence_search_returns_relevant_sources() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.get("/advice/evidence-search", params={"query": "banana sugar"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert any(result["section"] in {"inventory", "nutrition_facts", "guideline_rules"} for result in results)


def test_advice_llm_is_generation_entry(monkeypatch) -> None:
    captured = {}

    def fake_request_llm_json(*, system_prompt, user_prompt, enable_thinking):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["enable_thinking"] = enable_thinking
        return {
            "summary": "今天优先处理香蕉。",
            "recommendations": [
                {
                    "title": "早餐吃香蕉",
                    "content": "香蕉处于 fresh 状态，可作为早餐或加餐的一部分。",
                    "action_type": "eat_first",
                    "related_foods": ["banana"],
                    "basis": ["香蕉当前处于 fresh 状态", "水果建议适量食用", "香蕉每 100 g 有营养数据"],
                    "evidence_ids": captured["evidence_ids"],
                    "confidence": "high",
                }
            ],
        }

    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        today = client.get("/advice/today").json()
        captured["evidence_ids"] = today["today_priority"][0]["evidence_ids"] + [
            "rule_fruit_moderation_001",
            "nutri_banana_usda",
        ]

        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={"question": "今天怎么吃？", "enable_thinking": True, "search_query": "banana"},
        )
        saved = client.get(f"/advice/{response.json()['record_id']}")

    assert response.status_code == 200
    assert saved.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["record_id"] is not None
    assert saved.json()["id"] == data["record_id"]
    assert saved.json()["content"]["summary"] == "今天优先处理香蕉。"
    assert item["evidence_id"] in saved.json()["evidence_ids"]
    assert captured["enable_thinking"] is True
    assert "不判断水果是否腐败" in captured["system_prompt"]
    assert "eat_first 必须引用 inventory 或 storage 证据" in captured["system_prompt"]
    assert "portion_control 和 variety 必须同时引用 nutri 和 rule 证据" in captured["system_prompt"]
    assert "check_food 必须同时引用 inventory 和 storage 证据" in captured["system_prompt"]
    assert "avoid_duplicate_purchase 必须引用 inventory 证据" in captured["system_prompt"]
    assert "已有库存的水果只能写 avoid_duplicate_purchase" in captured["system_prompt"]
    assert "banana" in captured["user_prompt"]
    assert "可用 evidence_ids" in captured["user_prompt"]
    assert "推荐 evidence_hints" in captured["user_prompt"]
    prompt_payload = json.loads(captured["user_prompt"].split("\n\n", 1)[1])
    evidence_ids_by_type = prompt_payload["可用 evidence_ids"]
    evidence_hints = prompt_payload["推荐 evidence_hints"]
    assert item["evidence_id"] in evidence_ids_by_type["inventory"]
    assert "storage_banana_251_pantry" in evidence_ids_by_type["storage"]
    assert "nutri_banana_usda" in evidence_ids_by_type["nutri"]
    assert "rule_fruit_moderation_001" in evidence_ids_by_type["rule"]
    eat_first_hint = next(
        hint
        for hint in evidence_hints
        if hint["food"] == "banana" and hint["action_type"] == "eat_first"
    )
    assert item["evidence_id"] in eat_first_hint["use_evidence_ids"]
    assert "storage_banana_251_pantry" in eat_first_hint["use_evidence_ids"]
    assert "nutri_banana_usda" in eat_first_hint["use_evidence_ids"]
    assert "rule_fruit_moderation_001" in eat_first_hint["use_evidence_ids"]


def test_advice_llm_retries_once_with_errors_and_evidence_hints(monkeypatch) -> None:
    calls = []

    def fake_request_llm_json(*, system_prompt, user_prompt, enable_thinking):
        calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "enable_thinking": enable_thinking,
            }
        )
        if len(calls) == 1:
            return {
                "summary": "今天优先处理香蕉，也可以补买香蕉。",
                "recommendations": [
                    {
                        "title": "今天吃香蕉",
                        "content": "香蕉可以作为早餐或加餐的一部分。",
                        "action_type": "eat_first",
                        "related_foods": ["banana"],
                        "basis": ["香蕉当前有库存"],
                        "evidence_ids": ["inventory_1"],
                        "confidence": "high",
                    },
                    {
                        "title": "补买香蕉",
                        "content": "可以补买香蕉。",
                        "action_type": "general",
                        "related_foods": ["banana"],
                        "basis": ["香蕉常用"],
                        "evidence_ids": ["inventory_1"],
                        "confidence": "medium",
                    },
                ],
            }
        return {
            "summary": "今天优先处理已有香蕉，并避免重复购买。",
            "recommendations": [
                {
                    "title": "优先吃已有香蕉",
                    "content": "香蕉处于 fresh 状态，可作为加餐的一部分，并注意适量。",
                    "action_type": "eat_first",
                    "related_foods": ["banana"],
                    "basis": ["香蕉当前有库存", "香蕉有营养数据", "水果建议适量"],
                    "evidence_ids": [
                        "inventory_1",
                        "storage_banana_251_pantry",
                        "nutri_banana_usda",
                        "rule_sugar_moderation_001",
                    ],
                    "confidence": "high",
                },
                {
                    "title": "香蕉不用重复购买",
                    "content": "当前已有香蕉，先处理已有库存。",
                    "action_type": "avoid_duplicate_purchase",
                    "related_foods": ["banana"],
                    "basis": ["香蕉当前有库存", "库存充足时避免重复购买"],
                    "evidence_ids": ["inventory_1", "rule_shopping_duplicate_001"],
                    "confidence": "high",
                },
            ],
        }

    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})

        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={
                "question": "根据当前库存，今天水果怎么吃？请给保守建议。",
                "enable_thinking": False,
                "search_query": "香蕉 控糖 库存",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert len(calls) == 2
    retry_payload = json.loads(calls[1]["user_prompt"].split("\n\n", 1)[1])
    assert "上次输出的校验错误" in retry_payload
    assert any("eat_first requires" in error for error in retry_payload["上次输出的校验错误"])
    assert any("recommends buying stocked food" in error for error in retry_payload["上次输出的校验错误"])
    assert retry_payload["推荐 evidence_hints"]


def test_stocked_banana_prompt_bans_purchase_and_hints_duplicate_evidence(monkeypatch) -> None:
    captured = {}

    def fake_request_llm_json(*, system_prompt, user_prompt, enable_thinking):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return {
            "summary": "已有香蕉，先吃已有库存。",
            "recommendations": [
                {
                    "title": "香蕉不用重复购买",
                    "content": "当前已有香蕉，先处理已有库存。",
                    "action_type": "avoid_duplicate_purchase",
                    "related_foods": ["banana"],
                    "basis": ["香蕉当前有库存", "库存充足时避免重复购买"],
                    "evidence_ids": ["inventory_1", "rule_shopping_duplicate_001"],
                    "confidence": "high",
                }
            ],
        }

    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})

        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={
                "question": "根据当前库存，今天水果怎么吃？请给保守建议。",
                "enable_thinking": False,
                "search_query": "香蕉 控糖 库存",
            },
        )

    assert response.status_code == 200
    assert "禁止输出 buy、purchase、购买、补买、再买、建议买、需要买" in captured["user_prompt"]
    assert "如果要表达不用买已有库存，只能使用 action_type=avoid_duplicate_purchase" in captured["user_prompt"]
    prompt_payload = json.loads(captured["user_prompt"].split("\n\n", 1)[1])
    duplicate_hint = next(
        hint
        for hint in prompt_payload["推荐 evidence_hints"]
        if hint["food"] == "banana" and hint["action_type"] == "avoid_duplicate_purchase"
    )
    assert duplicate_hint["use_evidence_ids"] == [
        item["evidence_id"],
        "rule_shopping_duplicate_001",
    ]
    assert "禁止建议购买、补买或再买" in duplicate_hint["instruction"]


def test_llm_validation_accepts_negative_purchase_wording_for_stocked_food() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "当前有香蕉库存，购物时避免重复购买。",
                    "recommendations": [
                        {
                            "title": "香蕉无需购买",
                            "content": "香蕉当前已有库存，暂时无需购买或补买。",
                            "action_type": "avoid_duplicate_purchase",
                            "related_foods": ["banana"],
                            "basis": ["香蕉当前有库存", "避免重复购买"],
                            "evidence_ids": [
                                item["evidence_id"],
                                "rule_shopping_duplicate_001",
                            ],
                            "confidence": "high",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["errors"] == []


def test_llm_validation_rejects_english_purchase_wording_for_stocked_food() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "Buy more banana for later.",
                    "recommendations": [
                        {
                            "title": "Buy banana",
                            "content": "You should purchase and restock banana again.",
                            "action_type": "general",
                            "related_foods": ["banana"],
                            "basis": ["banana is useful"],
                            "evidence_ids": [item["evidence_id"]],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("recommends buying stocked food" in error for error in data["errors"])


def test_validate_route_rejects_invalid_action_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "测试",
                            "content": "测试",
                            "action_type": "buy",
                            "related_foods": ["banana"],
                            "basis": ["测试"],
                            "evidence_ids": ["rule_fruit_moderation_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 422


def test_llm_validation_rejects_summary_unsafe_wording() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "香蕉坏了，不能吃。",
                    "recommendations": [
                        {
                            "title": "只做一般提醒",
                            "content": "请查看当前水果。",
                            "action_type": "general",
                            "related_foods": ["banana"],
                            "basis": ["系统边界"],
                            "evidence_ids": ["rule_medical_boundary_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("summary" in error for error in data["errors"])


def test_general_action_with_eating_text_rejects_check_required_food() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + ["rule_fruit_moderation_001"]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "一般建议",
                            "content": "今天吃苹果。",
                            "action_type": "general",
                            "related_foods": ["apple"],
                            "basis": ["苹果需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "high",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_english_check_required_apple_eating_without_related_foods() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "Test.",
                    "recommendations": [
                        {
                            "title": "Apple breakfast plan",
                            "content": "Eat apple for breakfast.",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["Current inventory needs checking."],
                            "evidence_ids": today["check_required"][0]["evidence_ids"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_english_not_recommended_banana_snack_without_related_foods() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        today = client.get("/advice/today").json()
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "Test.",
                    "recommendations": [
                        {
                            "title": "Banana snack idea",
                            "content": "Use banana as a snack with yogurt.",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["Current inventory needs checking."],
                            "evidence_ids": today["check_required"][0]["evidence_ids"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_english_basis_only_not_recommended_banana_eating_advice() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        today = client.get("/advice/today").json()
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "Test.",
                    "recommendations": [
                        {
                            "title": "Inventory note",
                            "content": "Please review current inventory.",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["Serve banana as a snack portion."],
                            "evidence_ids": today["check_required"][0]["evidence_ids"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_allows_english_check_required_apple_check_only_prompt() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "Check only.",
                    "recommendations": [
                        {
                            "title": "Apple status check",
                            "content": "Inspect apple appearance and smell, then decide the next handling step.",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["Current inventory needs checking."],
                            "evidence_ids": today["check_required"][0]["evidence_ids"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["errors"] == []


def test_llm_validation_rejects_blocked_food_in_general_and_portion_advice() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + [
            "nutri_apple_usda",
            "rule_fruit_moderation_001",
        ]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "苹果早餐安排",
                            "content": "把苹果放进早餐搭配。",
                            "action_type": "general",
                            "related_foods": ["apple"],
                            "basis": ["苹果需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        },
                        {
                            "title": "苹果份量控制",
                            "content": "苹果控制在一份。",
                            "action_type": "portion_control",
                            "related_foods": ["apple"],
                            "basis": ["苹果需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        },
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert sum("checked food" in error for error in data["errors"]) == 2


def test_llm_validation_rejects_not_recommended_food_in_variety_advice() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + [
            "nutri_banana_usda",
            "rule_diversity_001",
        ]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "香蕉轮换安排",
                            "content": "香蕉和其他水果保持多样。",
                            "action_type": "variety",
                            "related_foods": ["banana"],
                            "basis": ["香蕉需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_text_mentioned_check_required_apple_without_related_foods() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + ["rule_fruit_moderation_001"]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "苹果早餐安排",
                            "content": "苹果可以作为早餐食用。",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["当前库存需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_basis_only_check_required_apple_eating_advice() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + ["rule_fruit_moderation_001"]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "库存提醒",
                            "content": "请查看当前库存记录。",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["建议把 apples 当作早餐或加餐。"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_basis_only_not_recommended_banana_eating_advice() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + ["rule_fruit_moderation_001"]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "库存提醒",
                            "content": "请查看当前库存记录。",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["建议把 bananas 当作早餐或加餐。"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_rejects_text_mentioned_not_recommended_banana_label_without_related_foods() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "pantry", _safe_days("banana", "pantry") + 2)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"] + [
            "nutri_banana_usda",
            "rule_diversity_001",
        ]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "Banana rotation",
                            "content": "banana 轮换当加餐。",
                            "action_type": "variety",
                            "related_foods": [],
                            "basis": ["当前库存需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("checked food" in error for error in data["errors"])


def test_llm_validation_allows_text_mentioned_check_required_apple_check_only_prompt() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"apple": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        today = client.get("/advice/today").json()
        evidence_ids = today["check_required"][0]["evidence_ids"]
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "只做检查提醒。",
                    "recommendations": [
                        {
                            "title": "苹果状态检查",
                            "content": "苹果已超过参考保存期，请检查外观和气味，并结合实际状态决定处理方式。",
                            "action_type": "general",
                            "related_foods": [],
                            "basis": ["当前库存需要检查"],
                            "evidence_ids": evidence_ids,
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["errors"] == []


def test_health_advice_requires_nutrition_and_rule_evidence() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "控制份量。",
                    "recommendations": [
                        {
                            "title": "控制香蕉份量",
                            "content": "香蕉作为加餐时注意份量。",
                            "action_type": "portion_control",
                            "related_foods": ["banana"],
                            "basis": ["少糖目标下注意份量"],
                            "evidence_ids": ["rule_sugar_moderation_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("nutri and rule" in error for error in data["errors"])


def test_llm_validation_rejects_avoided_food() -> None:
    with TestClient(app) as client:
        client.patch("/profile", json={"avoid_foods": ["荔枝"]})
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "测试。",
                    "recommendations": [
                        {
                            "title": "一般建议",
                            "content": "查看荔枝库存。",
                            "action_type": "general",
                            "related_foods": ["litchi"],
                            "basis": ["用户信息"],
                            "evidence_ids": ["rule_medical_boundary_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("avoided food" in error for error in data["errors"])


def test_llm_validation_rejects_profile_allergy_food() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "健康饮食",
                "diet_preference": "正常",
                "cooking_condition": "家庭",
                "avoid_foods": [],
                "allergies_optional": "香蕉过敏",
            },
        )
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "给一个水果建议。",
                    "recommendations": [
                        {
                            "title": "香蕉加餐",
                            "content": "今天可以吃香蕉。",
                            "action_type": "general",
                            "related_foods": ["banana"],
                            "basis": ["水果建议适量"],
                            "evidence_ids": ["nutri_banana_usda", "rule_fruit_moderation_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("profile-blocked food" in error for error in data["errors"])


def test_llm_validation_rejects_health_note_blocked_food() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "健康饮食",
                "diet_preference": "正常",
                "cooking_condition": "家庭",
                "avoid_foods": [],
                "health_notes_optional": "最近不要吃梨",
            },
        )
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "给一个水果建议。",
                    "recommendations": [
                        {
                            "title": "梨作为加餐",
                            "content": "今天可以吃梨。",
                            "action_type": "general",
                            "related_foods": ["pear"],
                            "basis": ["水果建议适量"],
                            "evidence_ids": ["nutri_pear_usda", "rule_fruit_moderation_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("profile-blocked food" in error for error in data["errors"])


def test_evidence_search_tokenizes_chinese_query() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.get("/advice/evidence-search", params={"query": "香蕉控糖"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert any(result["item"].get("food") == "banana" for result in results)
    assert any(result["item"].get("evidence_id") == "rule_sugar_moderation_001" for result in results)


def test_evidence_search_for_today_eating_includes_general_fruit_rule() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.get("/advice/evidence-search", params={"query": "今天 香蕉"})

    assert response.status_code == 200
    rule_ids = {
        result["item"]["evidence_id"]
        for result in response.json()["results"]
        if result["section"] == "guideline_rules"
    }
    assert "rule_fruit_moderation_001" in rule_ids


def test_query_context_eat_first_hints_keep_matching_storage_rule() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "减少浪费",
                "diet_preference": "少糖",
                "cooking_condition": "宿舍",
                "avoid_foods": [],
            },
        )
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1, "pear": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

    with Session(engine) as session:
        context = build_advice_context(session, "控糖 香蕉 梨 少糖")

    storage_ids = {
        item["evidence_id"] for item in context["storage_rules"]
    }
    assert "storage_banana_251_pantry" in storage_ids
    assert "storage_pear_266_pantry" in storage_ids
    eat_first_hints = [
        hint for hint in context["evidence_hints"] if hint["action_type"] == "eat_first"
    ]
    assert eat_first_hints
    for hint in eat_first_hints:
        assert any(evidence_id.startswith("storage_") for evidence_id in hint["use_evidence_ids"])


def test_advice_context_query_trims_results_and_filters_inactive_inventory() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1, "apple": 1}))
        inventory = client.get("/inventory").json()
        for item in inventory:
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

    with Session(engine) as session:
        food = session.exec(select(FoodItem).where(FoodItem.model_label == "apple")).one()
        item = session.exec(select(InventoryItem).where(InventoryItem.food_item_id == food.id)).one()
        item.status = "consumed"
        session.add(item)
        session.commit()

        context = build_advice_context(session, "香蕉 控糖 库存")

    assert all(item["status"] in {"available", "pending_confirm"} for item in context["inventory"])
    assert all(item["food"] != "apple" for item in context["inventory"])
    assert len(context["guideline_rules"]) <= 4
    assert "search_results" in context
    assert any(item["food"] == "banana" for item in context["inventory"])
    assert any(item["food"] == "banana" for item in context["storage_rules"])
    assert any(item["evidence_id"] == "nutri_banana_usda" for item in context["nutrition_facts"])
    assert any(
        item["evidence_id"] == "rule_sugar_moderation_001"
        for item in context["guideline_rules"]
    )


def _recognition_payload(
    *,
    captured_at: datetime | None = None,
    counts: dict[str, int] | None = None,
    camera_id: str = "cam-kitchen",
) -> dict:
    captured_at = captured_at or datetime(2026, 5, 31, 8, 0, tzinfo=timezone.utc)
    detections = []
    for class_name, count in (counts or {"banana": 1}).items():
        for index in range(count):
            detections.append(
                {
                    "class_name": class_name,
                    "confidence": 0.92,
                    "bbox": [10 + index, 20 + index, 110 + index, 220 + index],
                }
            )
    return {
        "camera_id": camera_id,
        "source": "ai_camera",
        "captured_at": captured_at.isoformat(),
        "model_name": "yolo",
        "model_version": "mvp",
        "image": {"original_path": "/tmp/frame.jpg", "width": 640, "height": 480},
        "detections": detections,
    }


def _set_inventory_age(label: str, storage_location: str, days_ago: int) -> None:
    with Session(engine) as session:
        food = session.exec(select(FoodItem).where(FoodItem.model_label == label)).one()
        item = session.exec(select(InventoryItem).where(InventoryItem.food_item_id == food.id)).one()
        seen_at = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=5)
        item.first_seen_at = seen_at
        item.last_seen_at = seen_at
        item.storage_location = storage_location
        session.add(item)
        session.commit()


def _set_inventory_age_by_id(item_id: int, storage_location: str, days_ago: int) -> None:
    with Session(engine) as session:
        item = session.get(InventoryItem, item_id)
        assert item is not None
        seen_at = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=5)
        item.first_seen_at = seen_at
        item.last_seen_at = seen_at
        item.storage_location = storage_location
        session.add(item)
        session.commit()


def _safe_days(label: str, storage_location: str) -> int:
    with Session(engine) as session:
        food = session.exec(select(FoodItem).where(FoodItem.model_label == label)).one()
        rule = session.exec(
            select(FoodStorageRule)
            .where(FoodStorageRule.food_item_id == food.id)
            .where(FoodStorageRule.storage_location == storage_location)
        ).one()
        assert rule.safe_days is not None
        return rule.safe_days
