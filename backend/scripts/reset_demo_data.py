import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import engine, init_db
from app.models import (
    AdviceRecord,
    CaptureImage,
    FoodItem,
    InventoryItem,
    RecognitionDetection,
    RecognitionEvent,
    UnknownFoodItem,
    UserFoodEvent,
    UserFoodHabit,
    UserProfile,
    utc_now,
)
from app.routers.inventory import _apply_storage_state
from app.seed import seed_reference_data
from app.services.user_food_tracking import record_user_food_event, refresh_user_food_habits


@dataclass(frozen=True)
class DemoInventorySpec:
    food: str
    quantity: int
    storage_location: str
    days_stored: int
    status: str
    label: str


DEMO_INVENTORY: tuple[DemoInventorySpec, ...] = (
    DemoInventorySpec("apple", 4, "pantry", 2, "available", "fresh"),
    DemoInventorySpec("apple", 2, "pantry", 17, "available", "eat-soon"),
    DemoInventorySpec("apple", 3, "pantry", 23, "available", "check-required"),
    DemoInventorySpec("apple", 1, "pantry", 29, "available", "not-recommended"),
    DemoInventorySpec("apple", 5, "refrigerate", 0, "pending_confirm", "pending"),
    DemoInventorySpec("banana", 6, "refrigerate", 1, "available", "fresh"),
    DemoInventorySpec("banana", 2, "refrigerate", 3, "available", "eat-soon"),
    DemoInventorySpec("banana", 3, "refrigerate", 4, "available", "not-recommended"),
    DemoInventorySpec("banana", 4, "refrigerate", 0, "pending_confirm", "pending"),
    DemoInventorySpec("pear", 5, "refrigerate", 1, "available", "fresh"),
    DemoInventorySpec("pear", 2, "refrigerate", 3, "available", "eat-soon"),
    DemoInventorySpec("pear", 3, "refrigerate", 4, "available", "not-recommended"),
    DemoInventorySpec("pear", 4, "refrigerate", 0, "pending_confirm", "pending"),
    DemoInventorySpec("litchi", 8, "refrigerate", 1, "available", "fresh"),
    DemoInventorySpec("litchi", 3, "refrigerate", 6, "available", "eat-soon"),
    DemoInventorySpec("litchi", 2, "refrigerate", 8, "available", "check-required"),
    DemoInventorySpec("litchi", 1, "refrigerate", 10, "available", "not-recommended"),
    DemoInventorySpec("litchi", 6, "refrigerate", 0, "pending_confirm", "pending"),
)


BUSINESS_TABLES = (
    AdviceRecord,
    UserFoodHabit,
    UserFoodEvent,
    InventoryItem,
    UnknownFoodItem,
    RecognitionDetection,
    RecognitionEvent,
    CaptureImage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset local SQLite data and load deterministic demo inventory."
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip SQLite file backup before resetting data.",
    )
    args = parser.parse_args()

    init_db()
    if not args.no_backup:
        backup_database()

    with Session(engine) as session:
        seed_reference_data(session)
        clear_business_data(session)
        reset_demo_profile(session)
        rows = seed_demo_inventory(session)
        session.commit()

    print(f"reset complete: {len(rows)} inventory rows")
    for row in rows:
        print(
            f"{row['id']}: {row['food']} "
            f"{row['confirmed_quantity']}/{row['detected_quantity']} "
            f"{row['storage_location']} {row['status']} {row['storage_state']} "
            f"remaining={row['remaining_days']}"
        )


def backup_database() -> None:
    database_path = sqlite_database_path()
    if database_path is None or not database_path.exists():
        return

    timestamp = utc_now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(f"{database_path.name}.backup-{timestamp}-before-demo-reset")
    shutil.copy2(database_path, backup_path)
    print(f"backup: {backup_path}")


def sqlite_database_path() -> Path | None:
    url = engine.url
    if url.drivername != "sqlite" or url.database in {None, "", ":memory:"}:
        return None
    return Path(url.database).resolve()


def clear_business_data(session: Session) -> None:
    session.execute(text("PRAGMA foreign_keys=OFF"))
    for model in BUSINESS_TABLES:
        session.execute(text(f"DELETE FROM {model.__tablename__}"))
    has_sqlite_sequence = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
    ).first()
    if has_sqlite_sequence is not None:
        session.execute(
            text(
                "DELETE FROM sqlite_sequence WHERE name IN "
                "('advice_records','user_food_habits','user_food_events',"
                "'inventory_items','unknown_food_items','recognition_detections',"
                "'recognition_events','capture_images')"
            )
        )
    session.execute(text("PRAGMA foreign_keys=ON"))


def reset_demo_profile(session: Session) -> None:
    profile = session.get(UserProfile, 1)
    if profile is None:
        profile = UserProfile(id=1)
    profile.goal = "健康饮食，减少浪费"
    profile.diet_preference = "家常、少糖"
    profile.cooking_condition = "普通冰箱和常温储存"
    profile.avoid_foods = "[]"
    profile.allergies_optional = None
    profile.health_notes_optional = "测试数据：仅用于演示，不代表医疗建议。"
    profile.updated_at = utc_now()
    session.add(profile)


def seed_demo_inventory(session: Session) -> list[dict[str, object]]:
    foods = {food.model_label: food for food in session.exec(select(FoodItem)).all()}
    now = utc_now()
    rows: list[dict[str, object]] = []

    for index, spec in enumerate(DEMO_INVENTORY, start=1):
        food = foods[spec.food]
        captured_at = now - timedelta(days=spec.days_stored)
        event = RecognitionEvent(
            camera_id=f"demo-{spec.food}-{spec.label}-{index}",
            source="demo_reset_script",
            captured_at=captured_at,
            model_name="demo-reset",
            model_version="2026-06-16",
            total_count=spec.quantity,
            raw_payload=json.dumps(
                {
                    "food": spec.food,
                    "quantity": spec.quantity,
                    "storage_location": spec.storage_location,
                    "days_stored": spec.days_stored,
                    "status": spec.status,
                    "label": spec.label,
                },
                ensure_ascii=False,
            ),
        )
        session.add(event)
        session.flush()

        for detection_index in range(spec.quantity):
            session.add(
                RecognitionDetection(
                    event_id=event.id or 0,
                    food_item_id=food.id,
                    class_name=food.model_label,
                    confidence=0.92,
                    bbox_x1=10 + detection_index,
                    bbox_y1=10,
                    bbox_x2=30 + detection_index,
                    bbox_y2=35,
                    status="accepted",
                )
            )

        item = InventoryItem(
            evidence_id="pending",
            user_id=1,
            camera_id=event.camera_id,
            food_item_id=food.id or 0,
            detected_quantity=spec.quantity,
            confirmed_quantity=0 if spec.status == "pending_confirm" else spec.quantity,
            unit="piece",
            storage_location=spec.storage_location,
            first_seen_at=captured_at,
            last_seen_at=captured_at,
            status=spec.status,
            source_event_id=event.id,
            pending_change_type="new_quantity" if spec.status == "pending_confirm" else "none",
            pending_detected_quantity=spec.quantity if spec.status == "pending_confirm" else None,
        )
        session.add(item)
        session.flush()
        item.evidence_id = f"inventory_{item.id}"
        _apply_storage_state(session, item, now)
        session.add(item)
        rows.append(
            {
                "id": item.id,
                "food": food.model_label,
                "confirmed_quantity": item.confirmed_quantity,
                "detected_quantity": item.detected_quantity,
                "storage_location": item.storage_location,
                "status": item.status,
                "storage_state": item.storage_state,
                "remaining_days": item.remaining_days,
            }
        )

        if item.status == "available" and item.confirmed_quantity > 0:
            record_user_food_event(
                session,
                food=food,
                event_type="purchased",
                quantity=item.confirmed_quantity,
                occurred_at=captured_at,
                metadata={
                    "inventory_id": item.id,
                    "source": "demo_reset_script",
                    "storage_location": item.storage_location,
                    "days_stored": spec.days_stored,
                    "label": spec.label,
                },
                refresh_habits=False,
            )

    for food in foods.values():
        refresh_user_food_habits(session, food, now)

    return rows


if __name__ == "__main__":
    main()
