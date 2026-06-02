import json
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.models import FoodItem, InventoryItem, UserFoodEvent, UserFoodHabit, utc_now


CHECK_REQUIRED_EVENT_TYPE = "inventory_check_required"


def record_user_food_event(
    session: Session,
    *,
    food: FoodItem,
    event_type: str,
    quantity: int,
    occurred_at: datetime,
    metadata: dict[str, Any] | None = None,
    refresh_habits: bool = True,
) -> UserFoodEvent:
    event = UserFoodEvent(
        evidence_id="pending",
        user_id=1,
        food_item_id=food.id or 0,
        event_type=event_type,
        quantity=quantity,
        occurred_at=occurred_at,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    session.add(event)
    session.flush()
    event.evidence_id = f"event_{event.id}"
    session.add(event)
    if refresh_habits:
        refresh_user_food_habits(session, food, occurred_at)
    return event


def record_check_required_once(
    session: Session,
    *,
    item: InventoryItem,
    food: FoodItem,
    storage_state: str,
    occurred_at: datetime,
) -> None:
    existing = session.exec(
        select(UserFoodEvent)
        .where(UserFoodEvent.food_item_id == food.id)
        .where(UserFoodEvent.event_type == CHECK_REQUIRED_EVENT_TYPE)
    ).all()
    for event in existing:
        metadata = loads_json(event.metadata_json, {})
        if (
            metadata.get("inventory_id") == item.id
            and metadata.get("storage_state") == storage_state
        ):
            return

    record_user_food_event(
        session,
        food=food,
        event_type=CHECK_REQUIRED_EVENT_TYPE,
        quantity=item.confirmed_quantity,
        occurred_at=occurred_at,
        metadata={
            "inventory_id": item.id,
            "storage_state": storage_state,
            "source": "storage_state_refresh",
        },
        refresh_habits=True,
    )


def refresh_user_food_habits(session: Session, food: FoodItem, as_of: datetime) -> None:
    window_start = as_of - timedelta(days=30)
    events = session.exec(
        select(UserFoodEvent)
        .where(UserFoodEvent.food_item_id == food.id)
        .where(UserFoodEvent.occurred_at >= window_start)
    ).all()
    discarded_count = sum(1 for event in events if event.event_type == "discarded")
    purchased_count = sum(1 for event in events if event.event_type == "purchased")
    consumed_events = [event for event in events if event.event_type == "consumed"]
    check_events = [
        event for event in events if event.event_type == CHECK_REQUIRED_EVENT_TYPE
    ]

    _upsert_or_remove_habit(
        session,
        food,
        "often_wastes",
        discarded_count >= 2,
        discarded_count,
        {"window_days": 30, "discarded_count": discarded_count},
    )
    has_stock = session.exec(
        select(InventoryItem)
        .where(InventoryItem.food_item_id == food.id)
        .where(InventoryItem.status == "available")
        .where(InventoryItem.confirmed_quantity > 0)
    ).first()
    _upsert_or_remove_habit(
        session,
        food,
        "often_overbuys",
        purchased_count >= 3 and has_stock is not None,
        purchased_count,
        {
            "window_days": 30,
            "purchased_count": purchased_count,
            "has_stock": has_stock is not None,
        },
    )

    days_to_consume = [
        loads_json(event.metadata_json, {}).get("days_to_consume")
        for event in consumed_events
    ]
    numeric_days = [
        float(value) for value in days_to_consume if isinstance(value, int | float)
    ]
    avg_days = sum(numeric_days) / len(numeric_days) if numeric_days else None
    _upsert_or_remove_habit(
        session,
        food,
        "often_consumes_fast",
        len(consumed_events) >= 3 and avg_days is not None and avg_days <= 3,
        len(consumed_events),
        {
            "window_days": 30,
            "consumed_count": len(consumed_events),
            "average_days_to_consume": avg_days,
        },
    )

    check_inventory_ids = sorted(
        {
            metadata["inventory_id"]
            for event in check_events
            if isinstance((metadata := loads_json(event.metadata_json, {})), dict)
            and isinstance(metadata.get("inventory_id"), int)
        }
    )
    _upsert_or_remove_habit(
        session,
        food,
        "often_consumes_slow",
        len(consumed_events) <= 1 and len(check_events) >= 2,
        len(check_events),
        {
            "window_days": 30,
            "consumed_count": len(consumed_events),
            "check_required_count": len(check_events),
            "check_required_event_ids": [event.evidence_id for event in check_events],
            "inventory_ids": check_inventory_ids,
        },
    )


def loads_json(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _upsert_or_remove_habit(
    session: Session,
    food: FoodItem,
    habit_type: str,
    active: bool,
    score: float,
    evidence: dict[str, Any],
) -> None:
    habit = session.exec(
        select(UserFoodHabit)
        .where(UserFoodHabit.food_item_id == food.id)
        .where(UserFoodHabit.habit_type == habit_type)
    ).first()
    if not active:
        if habit is not None:
            session.delete(habit)
        return

    if habit is None:
        habit = UserFoodHabit(
            evidence_id=f"habit_{food.model_label}_{habit_type}",
            user_id=1,
            food_item_id=food.id or 0,
            habit_type=habit_type,
        )
    habit.score = score
    habit.evidence_json = json.dumps(evidence, ensure_ascii=False)
    habit.updated_at = utc_now()
    session.add(habit)
