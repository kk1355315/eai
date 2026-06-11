from datetime import datetime, timedelta, timezone
import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import AdviceRecord, CaptureImage, FoodItem, FoodStorageRule, InventoryItem, RecognitionEvent
from app.services.advice_context import build_advice_context


def test_today_advice_handles_four_fruit_mixed_states_and_quantities() -> None:
    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(
                counts={"banana": 3, "pear": 1, "apple": 2, "litchi": 1}
            ),
        )
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age("banana", "refrigerate", 3)
        _set_inventory_age("pear", "freeze", 1)
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        _set_inventory_age(
            "litchi",
            "refrigerate",
            int(_safe_days("litchi", "refrigerate") * 1.5) + 1,
        )

        response = client.get("/advice/today")

    assert response.status_code == 200
    data = response.json()
    assert [item["food"] for item in data["today_priority"]] == ["banana", "pear"]
    assert [item["storage_state"] for item in data["today_priority"]] == ["eat_soon", "fresh"]
    assert [item["food"] for item in data["check_required"]] == ["apple", "litchi"]
    assert [item["storage_state"] for item in data["check_required"]] == [
        "check_required",
        "not_recommended",
    ]


def test_advice_context_includes_profile_and_search_filtered_evidence() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "减少浪费",
                "diet_preference": "少糖",
                "cooking_condition": "宿舍",
                "avoid_foods": ["荔枝"],
            },
        )
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2, "pear": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

    with Session(engine) as session:
        context = build_advice_context(session, "宿舍 控糖 香蕉 哪些不用买")

    assert context["profile"] == {
        "goal": "减少浪费",
        "diet_preference": "少糖",
        "cooking_condition": "宿舍",
        "avoid_foods": ["荔枝"],
        "allergies_optional": None,
        "health_notes_optional": None,
    }
    assert context["search_query"] == "宿舍 控糖 香蕉 哪些不用买"
    assert any(item["food"] == "banana" for item in context["inventory"])
    assert any(item["evidence_id"] == "rule_sugar_moderation_001" for item in context["guideline_rules"])
    assert any(
        hint["food"] == "banana" and hint["action_type"] == "avoid_duplicate_purchase"
        for hint in context["evidence_hints"]
    )


@pytest.mark.parametrize(
    ("question", "search_query", "expected_action"),
    [
        ("今天吃什么", "banana apple", "eat_first"),
        ("控糖怎么吃", "控糖 香蕉", "portion_control"),
        ("宿舍没厨房怎么吃", "宿舍 香蕉", "general"),
        ("哪些不用买", "不用买 香蕉", "avoid_duplicate_purchase"),
    ],
)
def test_llm_generation_uses_profile_question_and_search_query_for_prompt_and_storage(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    search_query: str,
    expected_action: str,
) -> None:
    captured: dict[str, str] = {}

    def fake_request_llm_json(*, system_prompt: str, user_prompt: str, enable_thinking: bool):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        prompt_payload = json.loads(user_prompt.split("\n\n", 1)[1])
        inventory_ids = prompt_payload["可用 evidence_ids"]["inventory"]
        storage_ids = prompt_payload["可用 evidence_ids"]["storage"]
        nutri_ids = prompt_payload["可用 evidence_ids"]["nutri"]
        rule_ids = prompt_payload["可用 evidence_ids"]["rule"]
        banana_inventory_id = next(
            evidence_id
            for evidence_id in inventory_ids
            if any(item.get("food") == "banana" and item.get("evidence_id") == evidence_id for item in prompt_payload["context"]["inventory"])
        )
        banana_storage_id = next(
            evidence_id
            for evidence_id in storage_ids
            if "banana" in evidence_id
        )
        if expected_action == "avoid_duplicate_purchase":
            return {
                "summary": "先处理已有香蕉，不用重复购买。",
                "recommendations": [
                    {
                        "title": "香蕉暂时不用买",
                        "content": "当前已有香蕉，先处理现有库存。",
                        "action_type": "avoid_duplicate_purchase",
                        "related_foods": ["banana"],
                        "basis": ["香蕉当前有库存", "库存充足时避免重复购买"],
                        "evidence_ids": [banana_inventory_id, "rule_shopping_duplicate_001"],
                        "confidence": "high",
                    }
                ],
            }
        if expected_action == "portion_control":
            return {
                "summary": "控糖时注意香蕉份量。",
                "recommendations": [
                    {
                        "title": "香蕉控制份量",
                        "content": "香蕉可以吃，但要控制份量，作为加餐更稳妥。",
                        "action_type": "portion_control",
                        "related_foods": ["banana"],
                        "basis": ["用户希望少糖", "水果建议适量"],
                        "evidence_ids": [nutri_ids[0], "rule_sugar_moderation_001"],
                        "confidence": "high",
                    }
                ],
            }
        if expected_action == "general":
            return {
                "summary": "宿舍场景优先选不用做饭的吃法。",
                "recommendations": [
                    {
                        "title": "直接吃香蕉",
                        "content": "宿舍没厨房时，香蕉可直接吃，省步骤。",
                        "action_type": "general",
                        "related_foods": ["banana"],
                        "basis": ["宿舍场景适合即食", "水果建议适量"],
                        "evidence_ids": [nutri_ids[0], rule_ids[0]],
                        "confidence": "high",
                    }
                ],
            }
        return {
            "summary": "今天先处理香蕉。",
            "recommendations": [
                {
                    "title": "优先吃香蕉",
                    "content": "香蕉接近参考保存期，可作为今天的加餐。",
                    "action_type": "eat_first",
                    "related_foods": ["banana"],
                    "basis": ["香蕉当前处于 eat_soon 状态", "水果建议适量食用"],
                    "evidence_ids": [banana_inventory_id, banana_storage_id, nutri_ids[0], rule_ids[0]],
                    "confidence": "high",
                }
            ],
        }

    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "健康饮食",
                "diet_preference": "少糖",
                "cooking_condition": "宿舍",
                "avoid_foods": ["荔枝"],
            },
        )
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2, "apple": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})
        _set_inventory_age("banana", "refrigerate", 3)

        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={"question": question, "search_query": search_query, "enable_thinking": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    with Session(engine) as session:
        record = session.get(AdviceRecord, data["record_id"])
        assert record is not None
        saved = json.loads(record.content_json)
    prompt_payload = json.loads(captured["user_prompt"].split("\n\n", 1)[1])
    assert prompt_payload["user_question"] == question
    assert prompt_payload["context"]["search_query"] == search_query
    assert prompt_payload["context"]["profile"]["diet_preference"] == "少糖"
    assert prompt_payload["context"]["profile"]["cooking_condition"] == "宿舍"
    assert saved["recommendations"][0]["action_type"] == expected_action


def test_llm_validation_rejects_no_kitchen_cooking_steps() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "健康饮食",
                "diet_preference": "简单烹饪",
                "cooking_condition": "无厨房",
                "avoid_foods": [],
            },
        )
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "给一个宿舍建议。",
                    "recommendations": [
                        {
                            "title": "煮香蕉燕麦",
                            "content": "把香蕉煮成燕麦粥再吃。",
                            "action_type": "general",
                            "related_foods": ["banana"],
                            "basis": ["用户在宿舍", "想要简单处理"],
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
    assert any("cooking condition" in error for error in data["errors"])


def test_llm_validation_rejects_sugar_sensitive_profile_with_excess_litchi() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "控糖",
                "diet_preference": "少糖",
                "cooking_condition": "家庭",
                "avoid_foods": [],
            },
        )
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "控糖场景测试。",
                    "recommendations": [
                        {
                            "title": "多吃荔枝",
                            "content": "荔枝可以多吃，还能榨汁喝。",
                            "action_type": "general",
                            "related_foods": ["litchi"],
                            "basis": ["只是示例"],
                            "evidence_ids": ["nutri_litchi_usda", "rule_sugar_moderation_001"],
                            "confidence": "medium",
                        }
                    ],
                }
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert any("sugar-sensitive" in error for error in data["errors"])


def test_image_metadata_is_consistent_between_recognition_list_and_image_detail() -> None:
    captured_at = datetime(2026, 5, 31, 8, 30, tzinfo=timezone.utc)
    with TestClient(app) as client:
        created = client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=captured_at, counts={"pear": 1}),
        ).json()
        listed = client.get("/recognitions").json()[0]
        image = client.get(f"/images/{created['image_id']}").json()

    assert listed["id"] == created["event_id"]
    assert listed["image"]["id"] == created["image_id"]
    assert listed["image"]["event_id"] == created["event_id"]
    assert listed["image"]["captured_at"] == image["captured_at"]
    assert listed["image"]["original_path"] == image["original_path"]
    assert listed["image"]["thumbnail_path"] == image["thumbnail_path"]
    assert listed["image"]["annotated_path"] == image["annotated_path"]


def test_same_recognition_event_links_image_metadata_and_inventory_items() -> None:
    captured_at = datetime(2026, 5, 31, 8, 45, tzinfo=timezone.utc)
    with TestClient(app) as client:
        created = client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=captured_at, counts={"banana": 2, "pear": 1}),
        ).json()

    with Session(engine) as session:
        event = session.get(RecognitionEvent, created["event_id"])
        image = session.get(CaptureImage, created["image_id"])
        inventory = session.exec(
            select(InventoryItem).where(InventoryItem.source_event_id == created["event_id"])
        ).all()

    assert event is not None
    assert image is not None
    assert event.image_id == image.id
    assert image.event_id == event.id
    assert image.captured_at is not None
    assert image.captured_at.replace(tzinfo=timezone.utc) == captured_at
    assert {item.evidence_id for item in inventory} == {"inventory_1", "inventory_2"}
    assert {item.camera_id for item in inventory} == {"cam-kitchen"}
    assert {item.status for item in inventory} == {"pending_confirm"}


def test_evidence_search_query_focuses_on_requested_food_and_shopping_rule() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2, "pear": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})
        response = client.get("/advice/evidence-search", params={"query": "梨 不用买"})

    assert response.status_code == 200
    results = response.json()["results"]
    inventory_foods = {
        result["item"]["food"]
        for result in results
        if result["section"] == "inventory"
    }
    rule_ids = {
        result["item"]["evidence_id"]
        for result in results
        if result["section"] == "guideline_rules"
    }
    assert inventory_foods == {"pear"}
    assert "rule_shopping_duplicate_001" in rule_ids


def test_llm_prompt_uses_search_query_to_trim_context_for_requested_food(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_request_llm_json(*, system_prompt: str, user_prompt: str, enable_thinking: bool):
        captured["user_prompt"] = user_prompt
        prompt_payload = json.loads(user_prompt.split("\n\n", 1)[1])
        pear_inventory_id = next(
            item["evidence_id"]
            for item in prompt_payload["context"]["inventory"]
            if item["food"] == "pear"
        )
        return {
            "summary": "已有梨，先不重复购买。",
            "recommendations": [
                {
                    "title": "梨暂时不用买",
                    "content": "当前已有梨，先处理现有库存。",
                    "action_type": "avoid_duplicate_purchase",
                    "related_foods": ["pear"],
                    "basis": ["梨当前有库存", "库存充足时避免重复购买"],
                    "evidence_ids": [pear_inventory_id, "rule_shopping_duplicate_001"],
                    "confidence": "high",
                }
            ],
        }

    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2, "pear": 1}))
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})
        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={
                "question": "今天怎么安排水果",
                "search_query": "梨 不用买",
                "enable_thinking": False,
            },
        )

    assert response.status_code == 200
    prompt_payload = json.loads(captured["user_prompt"].split("\n\n", 1)[1])
    assert prompt_payload["context"]["search_query"] == "梨 不用买"
    assert [item["food"] for item in prompt_payload["context"]["inventory"]] == ["pear"]
    assert any(
        item["evidence_id"] == "rule_shopping_duplicate_001"
        for item in prompt_payload["context"]["guideline_rules"]
    )


def test_llm_validation_rejects_avoided_litchi_profile_recommendation() -> None:
    with TestClient(app) as client:
        client.patch(
            "/profile",
            json={
                "goal": "减少浪费",
                "diet_preference": "正常",
                "cooking_condition": "家庭",
                "avoid_foods": ["荔枝"],
            },
        )
        response = client.post(
            "/advice/llm/validate",
            json={
                "llm_output": {
                    "summary": "给一个水果建议。",
                    "recommendations": [
                        {
                            "title": "把荔枝当加餐",
                            "content": "今天可以优先吃荔枝。",
                            "action_type": "general",
                            "related_foods": ["litchi"],
                            "basis": ["用户有库存"],
                            "evidence_ids": ["nutri_litchi_usda", "rule_fruit_moderation_001"],
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


def test_pending_quantity_change_keeps_old_shopping_advice_until_user_confirms() -> None:
    base_time = datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc)
    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=base_time, counts={"banana": 2}),
        )
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})
        before_change = client.get("/advice/shopping").json()["recommendations"][0]

        client.post(
            "/recognitions",
            json=_recognition_payload(
                captured_at=base_time + timedelta(minutes=11),
                counts={"banana": 1},
            ),
        )
        pending_item = client.get("/inventory").json()[0]
        while_pending = client.get("/advice/shopping").json()["recommendations"][0]

        client.post(
            f"/inventory/{item['id']}/confirm-change",
            json={"new_quantity": 1, "status": "available"},
        )
        after_confirm = client.get("/advice/shopping").json()["recommendations"][0]

    assert pending_item["pending_change_type"] == "possible_consumed"
    assert pending_item["pending_detected_quantity"] == 1
    assert before_change["basis"] == ["香蕉 当前库存 2 piece"]
    assert while_pending["basis"] == ["香蕉 当前库存 2 piece"]
    assert after_confirm["basis"] == ["香蕉 当前库存 1 piece"]


def test_llm_prompt_does_not_offer_eat_first_hint_for_check_required_foods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_request_llm_json(*, system_prompt: str, user_prompt: str, enable_thinking: bool):
        captured["user_prompt"] = user_prompt
        prompt_payload = json.loads(user_prompt.split("\n\n", 1)[1])
        banana_inventory_id = next(
            item["evidence_id"]
            for item in prompt_payload["context"]["inventory"]
            if item["food"] == "banana"
        )
        banana_storage_id = next(
            item
            for item in prompt_payload["可用 evidence_ids"]["storage"]
            if "storage_banana_251_" in item
        )
        return {
            "summary": "今天先处理香蕉和梨。",
            "recommendations": [
                {
                    "title": "优先吃香蕉",
                    "content": "香蕉接近参考保存期，可作为今天加餐。",
                    "action_type": "eat_first",
                    "related_foods": ["banana"],
                    "basis": ["香蕉处于 eat_soon 状态", "水果建议适量"],
                    "evidence_ids": [
                        banana_inventory_id,
                        banana_storage_id,
                        "nutri_banana_usda",
                        "rule_fruit_moderation_001",
                    ],
                    "confidence": "high",
                }
            ],
        }

    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(
                counts={"banana": 3, "pear": 1, "apple": 2, "litchi": 1}
            ),
        )
        for item in client.get("/inventory").json():
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age("banana", "refrigerate", 3)
        _set_inventory_age("pear", "freeze", 1)
        _set_inventory_age("apple", "pantry", _safe_days("apple", "pantry") + 1)
        _set_inventory_age(
            "litchi",
            "refrigerate",
            int(_safe_days("litchi", "refrigerate") * 1.5) + 1,
        )

        monkeypatch.setattr("app.routers.advice.request_llm_json", fake_request_llm_json)
        response = client.post(
            "/advice/llm",
            json={
                "question": "今天怎么安排水果",
                "search_query": "香蕉 梨 苹果 荔枝",
                "enable_thinking": False,
            },
        )

    assert response.status_code == 200
    prompt_payload = json.loads(captured["user_prompt"].split("\n\n", 1)[1])
    eat_first_foods = {
        hint["food"]
        for hint in prompt_payload["推荐 evidence_hints"]
        if hint["action_type"] == "eat_first"
    }
    assert eat_first_foods == {"banana", "pear"}


def test_new_batch_and_partial_lifecycle_keep_only_remaining_batch_in_shopping() -> None:
    base_time = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=base_time, counts={"banana": 2}),
        )
        old_batch = client.get("/inventory").json()[0]
        client.post(f"/inventory/{old_batch['id']}/confirm-change", json={})

        client.post(
            "/recognitions",
            json=_recognition_payload(
                captured_at=base_time + timedelta(days=5), counts={"banana": 4}
            ),
        )
        pending = client.get("/inventory").json()[0]
        client.post(f"/inventory/{pending['id']}/confirm-change", json={"as_new_batch": True})

        inventory = client.get("/inventory").json()
        new_batch = inventory[1]
        client.post(
            "/user-food-events",
            json={
                "food_id": "banana",
                "event_type": "consumed",
                "quantity": 2,
                "inventory_id": old_batch["id"],
            },
        )
        client.post(
            "/user-food-events",
            json={
                "food_id": "banana",
                "event_type": "discarded",
                "quantity": 1,
                "inventory_id": new_batch["id"],
            },
        )
        shopping = client.get("/advice/shopping")
        latest_inventory = client.get("/inventory").json()

    assert shopping.status_code == 200
    recommendations = shopping.json()["recommendations"]
    assert len(recommendations) == 1
    assert recommendations[0]["related_foods"] == ["banana"]
    remaining = {item["id"]: item for item in latest_inventory}
    assert remaining[old_batch["id"]]["status"] == "consumed"
    assert remaining[new_batch["id"]]["confirmed_quantity"] == 1
    assert remaining[new_batch["id"]]["status"] == "available"


def test_often_overbuys_habit_clears_after_stock_is_exhausted() -> None:
    with TestClient(app) as client:
        for index in range(3):
            client.post(
                "/recognitions",
                json=_recognition_payload(
                    captured_at=datetime(2026, 5, 10 + index, 8, 0, tzinfo=timezone.utc),
                    counts={"banana": 1},
                    camera_id=f"habit-cam-{index}",
                ),
            )
            item = client.get("/inventory").json()[-1]
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        habits_before = client.get("/habits").json()
        for item in client.get("/inventory").json():
            client.post(
                "/user-food-events",
                json={
                    "food_id": "banana",
                    "event_type": "consumed",
                    "quantity": item["confirmed_quantity"],
                    "inventory_id": item["id"],
                },
            )
        habits_after = client.get("/habits").json()
        shopping = client.get("/advice/shopping").json()

    assert any(habit["habit_type"] == "often_overbuys" for habit in habits_before)
    assert all(habit["habit_type"] != "often_overbuys" for habit in habits_after)
    assert shopping["recommendations"] == []


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
        "image": {
            "original_path": "/tmp/frame.jpg",
            "thumbnail_path": "/tmp/frame-thumb.jpg",
            "annotated_path": "/tmp/frame-annotated.jpg",
            "width": 640,
            "height": 480,
        },
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
