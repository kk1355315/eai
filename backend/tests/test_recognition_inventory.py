from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import FoodItem, FoodStorageRule, InventoryItem, UserFoodEvent
from app.routers.inventory import CHECK_REQUIRED_MESSAGE


def test_post_recognition_saves_banana_and_apple_with_bbox() -> None:
    with TestClient(app) as client:
        response = client.post("/recognitions", json=_recognition_payload())
        recognitions = client.get("/recognitions")

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] > 0
    assert data["total_count"] == 3
    assert {
        item["class_name"]: item["detected_quantity"]
        for item in data["detected_quantities"]
    } == {"apple": 1, "banana": 2}

    assert recognitions.status_code == 200
    detections = recognitions.json()[0]["detections"]
    assert detections[0]["bbox"]["x1"] == 10
    assert detections[0]["bbox"]["y1"] == 20
    assert detections[0]["bbox"]["x2"] == 110
    assert detections[0]["bbox"]["y2"] == 220


def test_low_confidence_and_unknown_class_do_not_enter_available_inventory() -> None:
    payload = _recognition_payload(
        detections=[
            {"class_name": "banana", "confidence": 0.59, "bbox": [1, 2, 3, 4]},
            {"class_name": "mango", "confidence": 0.95, "bbox": [5, 6, 7, 8]},
            {"class_name": "banana package", "confidence": 0.95, "bbox": [9, 10, 11, 12]},
        ]
    )

    with TestClient(app) as client:
        response = client.post("/recognitions", json=payload)
        inventory = client.get("/inventory")
        recognitions = client.get("/recognitions")

    assert response.status_code == 200
    assert response.json()["total_count"] == 0
    assert inventory.status_code == 200
    assert inventory.json() == []

    unknown_items = recognitions.json()[0]["unknown_items"]
    assert {item["reason"] for item in unknown_items} == {
        "low_confidence",
        "unknown_class",
        "uncertain_or_packaged",
    }


def test_duplicate_recognition_within_ten_minutes_does_not_add_inventory() -> None:
    first_time = datetime(2026, 5, 31, 8, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(minutes=5)

    with TestClient(app) as client:
        first = client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=first_time, counts={"banana": 2}),
        )
        item_id = client.get("/inventory").json()[0]["id"]
        client.post(f"/inventory/{item_id}/confirm-change", json={})
        second = client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=second_time, counts={"banana": 3}),
        )
        inventory = client.get("/inventory")

    assert first.status_code == 200
    assert second.status_code == 200
    items = inventory.json()
    assert len(items) == 1
    assert items[0]["last_seen_at"].startswith("2026-05-31T08:05:00")
    assert items[0]["confirmed_quantity"] == 2
    assert items[0]["pending_change_type"] == "none"


def test_quantity_changes_are_pending_until_confirmed() -> None:
    base_time = datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc)

    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=base_time, counts={"banana": 2}),
        )
        item = client.get("/inventory").json()[0]
        item_id = item["id"]
        assert item["confirmed_quantity"] == 0
        assert item["pending_change_type"] == "new_quantity"
        assert item["pending_detected_quantity"] == 2
        client.post(f"/inventory/{item_id}/confirm-change", json={})

        client.post(
            "/recognitions",
            json=_recognition_payload(
                captured_at=base_time + timedelta(minutes=11), counts={"banana": 3}
            ),
        )
        inventory_after_added = client.get("/inventory").json()
        assert len(inventory_after_added) == 1
        added = inventory_after_added[0]
        assert added["confirmed_quantity"] == 2
        assert added["pending_change_type"] == "possible_added"
        assert added["pending_detected_quantity"] == 3

        confirmed_added = client.post(f"/inventory/{item_id}/confirm-change", json={})
        assert confirmed_added.json()["confirmed_quantity"] == 3
        assert confirmed_added.json()["pending_change_type"] == "none"

        client.post(
            "/recognitions",
            json=_recognition_payload(
                captured_at=base_time + timedelta(minutes=22), counts={"banana": 1}
            ),
        )
        consumed = client.get("/inventory").json()[0]
        assert consumed["confirmed_quantity"] == 3
        assert consumed["pending_change_type"] == "possible_consumed"
        assert consumed["pending_detected_quantity"] == 1

        confirmed_consumed = client.post(
            f"/inventory/{item_id}/confirm-change",
            json={"new_quantity": 1, "status": "available"},
        )

    assert confirmed_consumed.status_code == 200
    assert confirmed_consumed.json()["confirmed_quantity"] == 1
    assert confirmed_consumed.json()["pending_change_type"] == "none"


def test_inventory_confirmation_writes_user_food_events_and_refreshes_habits() -> None:
    with TestClient(app) as client:
        for index in range(3):
            client.post(
                "/recognitions",
                json=_recognition_payload(
                    captured_at=datetime(2026, 5, 31, 8 + index, 0, tzinfo=timezone.utc),
                    counts={"banana": 1},
                    camera_id=f"cam-{index}",
                ),
            )
            item = client.get("/inventory").json()[-1]
            response = client.post(f"/inventory/{item['id']}/confirm-change", json={})
            assert response.status_code == 200

        habits = client.get("/habits").json()

    with Session(engine) as session:
        events = session.exec(
            select(UserFoodEvent).where(UserFoodEvent.event_type == "purchased")
        ).all()

    assert len(events) == 3
    assert {event.quantity for event in events} == {1}
    assert any(
        habit["food"] == "banana" and habit["habit_type"] == "often_overbuys"
        for habit in habits
    )


def test_possible_added_as_new_batch_does_not_inherit_old_first_seen_at() -> None:
    base_time = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    second_time = base_time + timedelta(days=5)

    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=base_time, counts={"banana": 2}),
        )
        old_item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{old_item['id']}/confirm-change", json={})

        client.post(
            "/recognitions",
            json=_recognition_payload(captured_at=second_time, counts={"banana": 3}),
        )
        pending = client.get("/inventory").json()[0]
        response = client.post(
            f"/inventory/{pending['id']}/confirm-change",
            json={"as_new_batch": True},
        )
        inventory = client.get("/inventory").json()

    assert response.status_code == 200
    assert len(inventory) == 2
    old_batch, new_batch = inventory
    assert old_batch["confirmed_quantity"] == 2
    assert old_batch["first_seen_at"].startswith("2026-05-01T08:00:00")
    assert new_batch["confirmed_quantity"] == 1
    assert new_batch["first_seen_at"].startswith("2026-05-06T08:00:00")
    assert new_batch["first_seen_at"] != old_batch["first_seen_at"]


def test_pending_confirm_inventory_does_not_get_eat_priority_rank() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 2}))
        before_confirm = client.get("/inventory/storage-states").json()[0]

        assert before_confirm["status"] == "pending_confirm"
        assert before_confirm["confirmed_quantity"] == 0
        assert before_confirm["eat_priority_rank"] is None

        client.post(f"/inventory/{before_confirm['id']}/confirm-change", json={})
        after_confirm = client.get("/inventory/storage-states").json()[0]

    assert after_confirm["status"] == "available"
    assert after_confirm["confirmed_quantity"] == 2
    assert after_confirm["eat_priority_rank"] == 1


def test_storage_states_use_thresholds_and_fixed_check_message() -> None:
    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(
                counts={"apple": 1, "banana": 1, "pear": 1},
            ),
        )
        inventory = client.get("/inventory").json()
        for item in inventory:
            client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age("pear", "freeze", days_ago=10)
        _set_inventory_age("banana", "refrigerate", days_ago=3)
        _set_inventory_age(
            "apple",
            "pantry",
            days_ago=_safe_days("apple", "pantry") + 1,
        )

        response = client.get("/inventory/storage-states")

    assert response.status_code == 200
    states = {item["food"]["model_label"]: item for item in response.json()}
    assert states["pear"]["storage_state"] == "fresh"
    assert states["banana"]["storage_state"] == "eat_soon"
    assert states["apple"]["storage_state"] == "check_required"
    assert states["apple"]["message"] == CHECK_REQUIRED_MESSAGE
    assert states["apple"]["eat_priority_rank"] is None


def test_confirm_change_can_snooze_check_required_inventory() -> None:
    with TestClient(app) as client:
        client.post(
            "/recognitions",
            json=_recognition_payload(counts={"apple": 1}),
        )
        item = client.get("/inventory").json()[0]
        client.post(f"/inventory/{item['id']}/confirm-change", json={})

        _set_inventory_age(
            "apple",
            "pantry",
            days_ago=_safe_days("apple", "pantry") + 1,
        )
        check_item = client.get("/inventory/storage-states").json()[0]
        response = client.post(
            f"/inventory/{check_item['id']}/confirm-change",
            json={
                "new_quantity": check_item["confirmed_quantity"],
                "status": "available",
                "snooze_days": 3,
            },
        )
        after = client.get("/inventory/storage-states").json()[0]

    assert response.status_code == 200
    assert response.json()["check_snoozed_until"] is not None
    assert response.json()["storage_state"] == "eat_soon"
    assert response.json()["remaining_days"] == 3
    assert response.json()["message"] is None
    assert after["storage_state"] == "eat_soon"
    assert after["message"] is None


def test_get_image_returns_capture_image_metadata() -> None:
    with TestClient(app) as client:
        recognition = client.post("/recognitions", json=_recognition_payload())
        image_id = recognition.json()["image_id"]
        response = client.get(f"/images/{image_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == image_id
    assert data["event_id"] == recognition.json()["event_id"]
    assert data["original_path"] == "/tmp/frame.jpg"
    assert data["thumbnail_path"] == "/tmp/frame-thumb.jpg"
    assert data["annotated_path"] == "/tmp/frame-annotated.jpg"


def test_ai_camera_recognition_requires_image_evidence() -> None:
    payload = _recognition_payload()
    payload["image"] = None

    with TestClient(app) as client:
        response = client.post("/recognitions", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "ai_camera image evidence is required"


def test_ai_camera_recognition_rejects_incomplete_image_evidence() -> None:
    payload = _recognition_payload()
    payload["image"]["original_path"] = ""
    with TestClient(app) as client:
        missing_path = client.post("/recognitions", json=payload)

    payload = _recognition_payload()
    payload["image"]["width"] = 0
    with TestClient(app) as client:
        bad_width = client.post("/recognitions", json=payload)

    payload = _recognition_payload()
    payload["image"]["height"] = 0
    with TestClient(app) as client:
        bad_height = client.post("/recognitions", json=payload)

    assert missing_path.status_code == 422
    assert missing_path.json()["detail"] == "image.original_path is required"
    assert bad_width.status_code == 422
    assert bad_width.json()["detail"] == "image.width must be greater than 0"
    assert bad_height.status_code == 422
    assert bad_height.json()["detail"] == "image.height must be greater than 0"


def test_inventory_patch_rejects_invalid_status_and_location() -> None:
    with TestClient(app) as client:
        client.post("/recognitions", json=_recognition_payload(counts={"banana": 1}))
        item_id = client.get("/inventory").json()[0]["id"]

        bad_status = client.patch(f"/inventory/{item_id}", json={"status": "bad"})
        bad_location = client.patch(
            f"/inventory/{item_id}", json={"storage_location": "shelf"}
        )
        bad_confirm_status = client.post(
            f"/inventory/{item_id}/confirm-change", json={"status": "bad"}
        )

    assert bad_status.status_code == 422
    assert bad_location.status_code == 422
    assert bad_confirm_status.status_code == 422


def test_recognition_rejects_captured_at_without_timezone() -> None:
    payload = _recognition_payload()
    payload["captured_at"] = "2026-05-31T08:00:00"

    with TestClient(app) as client:
        response = client.post("/recognitions", json=payload)

    assert response.status_code == 422


def _recognition_payload(
    *,
    captured_at: datetime | None = None,
    counts: dict[str, int] | None = None,
    detections: list[dict] | None = None,
    camera_id: str = "cam-kitchen",
) -> dict:
    captured_at = captured_at or datetime.now(timezone.utc)
    if detections is None:
        detections = []
        for class_name, count in (counts or {"banana": 2, "apple": 1}).items():
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
        food = session.exec(
            select(FoodItem).where(FoodItem.model_label == label)
        ).one()
        item = session.exec(
            select(InventoryItem).where(InventoryItem.food_item_id == food.id)
        ).one()
        seen_at = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=5)
        item.first_seen_at = seen_at
        item.last_seen_at = seen_at
        item.storage_location = storage_location
        session.add(item)
        session.commit()


def _safe_days(label: str, storage_location: str) -> int:
    with Session(engine) as session:
        food = session.exec(
            select(FoodItem).where(FoodItem.model_label == label)
        ).one()
        rule = session.exec(
            select(FoodStorageRule)
            .where(FoodStorageRule.food_item_id == food.id)
            .where(FoodStorageRule.storage_location == storage_location)
        ).one()
        assert rule.safe_days is not None
        return rule.safe_days
