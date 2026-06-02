from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models import FoodItem, InventoryItem, UserFoodEvent, UserFoodHabit, utc_now
from app.services.user_food_tracking import (
    loads_json,
    record_user_food_event,
    refresh_user_food_habits,
)

router = APIRouter(tags=["user events"])

SessionDep = Annotated[Session, Depends(get_session)]
EventType = Literal["consumed", "discarded", "purchased"]


class UserFoodEventCreate(BaseModel):
    food_id: str
    event_type: EventType
    quantity: int = Field(default=1, ge=0)
    inventory_id: int | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserFoodEventResponse(BaseModel):
    id: int
    evidence_id: str
    user_id: int
    food: str
    event_type: str
    quantity: int
    occurred_at: datetime
    metadata: dict[str, Any]


class UserFoodHabitResponse(BaseModel):
    id: int
    evidence_id: str
    user_id: int
    food: str
    habit_type: str
    score: float
    evidence: dict[str, Any]
    updated_at: datetime


@router.post("/user-food-events", response_model=UserFoodEventResponse)
def create_user_food_event(
    payload: UserFoodEventCreate, session: SessionDep
) -> UserFoodEventResponse:
    food = _find_food(session, payload.food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    if payload.inventory_id is not None:
        item = session.get(InventoryItem, payload.inventory_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        if item.food_item_id != food.id:
            raise HTTPException(
                status_code=400,
                detail="food_id does not match inventory_id",
            )

    occurred_at = _as_utc(payload.occurred_at or utc_now())
    event = record_user_food_event(
        session,
        food=food,
        event_type=payload.event_type,
        quantity=payload.quantity,
        occurred_at=occurred_at,
        metadata=payload.metadata
        | ({"inventory_id": payload.inventory_id} if payload.inventory_id is not None else {}),
        refresh_habits=False,
    )

    if payload.inventory_id is not None:
        _apply_inventory_event(session, payload, occurred_at)

    refresh_user_food_habits(session, food, occurred_at)
    session.commit()
    session.refresh(event)
    return _serialize_event(event, food)


@router.get("/habits", response_model=list[UserFoodHabitResponse])
def list_habits(session: SessionDep) -> list[UserFoodHabitResponse]:
    habits = session.exec(select(UserFoodHabit).order_by(UserFoodHabit.id)).all()
    foods = {food.id: food for food in session.exec(select(FoodItem)).all()}
    return [_serialize_habit(habit, foods[habit.food_item_id]) for habit in habits]


def _apply_inventory_event(
    session: Session, payload: UserFoodEventCreate, occurred_at: datetime
) -> None:
    item = session.get(InventoryItem, payload.inventory_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if payload.event_type == "consumed":
        _reject_over_inventory_quantity(item, payload)
        item.confirmed_quantity = max(0, item.confirmed_quantity - payload.quantity)
        item.detected_quantity = item.confirmed_quantity
        item.status = "consumed" if item.confirmed_quantity == 0 else "available"
    elif payload.event_type == "discarded":
        _reject_over_inventory_quantity(item, payload)
        item.confirmed_quantity = max(0, item.confirmed_quantity - payload.quantity)
        item.detected_quantity = item.confirmed_quantity
        item.status = "discarded" if item.confirmed_quantity == 0 else "available"
    elif payload.event_type == "purchased":
        item.confirmed_quantity += payload.quantity
        item.detected_quantity = item.confirmed_quantity
        item.status = "available"

    item.pending_change_type = "none"
    item.pending_detected_quantity = None
    item.last_seen_at = occurred_at
    item.updated_at = utc_now()
    session.add(item)


def _reject_over_inventory_quantity(
    item: InventoryItem, payload: UserFoodEventCreate
) -> None:
    if payload.quantity > item.confirmed_quantity:
        raise HTTPException(
            status_code=400,
            detail="quantity exceeds confirmed inventory quantity",
        )


def _find_food(session: Session, food_id: str) -> FoodItem | None:
    if food_id.isdigit():
        food = session.get(FoodItem, int(food_id))
        if food is not None:
            return food
    return session.exec(select(FoodItem).where(FoodItem.model_label == food_id)).first()


def _serialize_event(event: UserFoodEvent, food: FoodItem) -> UserFoodEventResponse:
    return UserFoodEventResponse(
        id=event.id or 0,
        evidence_id=event.evidence_id,
        user_id=event.user_id,
        food=food.model_label,
        event_type=event.event_type,
        quantity=event.quantity,
        occurred_at=event.occurred_at,
        metadata=loads_json(event.metadata_json, {}),
    )


def _serialize_habit(habit: UserFoodHabit, food: FoodItem) -> UserFoodHabitResponse:
    return UserFoodHabitResponse(
        id=habit.id or 0,
        evidence_id=habit.evidence_id,
        user_id=habit.user_id,
        food=food.model_label,
        habit_type=habit.habit_type,
        score=habit.score,
        evidence=loads_json(habit.evidence_json, {}),
        updated_at=habit.updated_at,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
