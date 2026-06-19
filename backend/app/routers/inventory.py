from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    FoodItem,
    FoodStorageRule,
    InventoryItem,
    RecognitionEvent,
    utc_now,
)
from app.services.user_food_tracking import record_check_required_once, record_user_food_event

router = APIRouter(tags=["inventory"])

SessionDep = Annotated[Session, Depends(get_session)]

CHECK_REQUIRED_MESSAGE = "已超过参考保存期，系统不推荐直接食用。请检查外观、气味和实际状态后再决定。"
DUPLICATE_WINDOW_SECONDS = 10 * 60

StorageLocation = Literal["pantry", "refrigerate", "freeze"]
InventoryStatus = Literal["pending_confirm", "available", "consumed", "discarded", "unknown"]


class FoodSummary(BaseModel):
    id: int
    model_label: str
    display_name: str


class InventoryResponse(BaseModel):
    id: int
    evidence_id: str
    user_id: int
    camera_id: str | None
    food: FoodSummary
    detected_quantity: int
    confirmed_quantity: int
    unit: str
    storage_location: str
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    days_stored: int | None
    safe_days: int | None
    remaining_days: int | None
    storage_state: str | None
    eat_priority_rank: int | None
    status: str
    source_event_id: int | None
    pending_change_type: str
    pending_detected_quantity: int | None
    check_snoozed_until: datetime | None = None
    message: str | None = None


class InventoryPatch(BaseModel):
    confirmed_quantity: int | None = Field(default=None, ge=0)
    detected_quantity: int | None = Field(default=None, ge=0)
    unit: str | None = None
    storage_location: StorageLocation | None = None
    status: InventoryStatus | None = None


class ConfirmChangeRequest(BaseModel):
    new_quantity: int | None = Field(default=None, ge=0)
    status: InventoryStatus | None = "available"
    as_new_batch: bool = False
    snooze_days: int | None = Field(default=None, ge=1, le=30)


@router.get("/inventory", response_model=list[InventoryResponse])
def list_inventory(session: SessionDep) -> list[InventoryResponse]:
    items = session.exec(select(InventoryItem).order_by(InventoryItem.id)).all()
    foods = _food_map(session)
    _refresh_storage_states(session, items)
    session.commit()
    return [_serialize_inventory(item, foods[item.food_item_id]) for item in items]


@router.patch("/inventory/{item_id}", response_model=InventoryResponse)
def patch_inventory(
    item_id: int, payload: InventoryPatch, session: SessionDep
) -> InventoryResponse:
    item = session.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    food = session.get(FoodItem, item.food_item_id)
    if food is None:
        raise HTTPException(status_code=500, detail="Food item missing")

    old_quantity = item.confirmed_quantity
    old_status = item.status
    updates = payload.model_dump(exclude_unset=True)
    if "confirmed_quantity" in updates:
        item.confirmed_quantity = updates["confirmed_quantity"]
        item.pending_change_type = "none"
        item.pending_detected_quantity = None
    if "detected_quantity" in updates:
        item.detected_quantity = updates["detected_quantity"]
    if "unit" in updates:
        item.unit = updates["unit"]
    if "storage_location" in updates:
        item.storage_location = updates["storage_location"]
    if "status" in updates:
        item.status = updates["status"]

    item.updated_at = utc_now()
    _apply_storage_state(session, item)
    session.add(item)
    _record_inventory_truth_change(
        session=session,
        item=item,
        food=food,
        old_quantity=old_quantity,
        old_status=old_status,
        change_source="inventory_patch",
    )
    session.commit()
    session.refresh(item)
    return _serialize_inventory(item, food)


@router.post("/inventory/{item_id}/confirm-change", response_model=InventoryResponse)
def confirm_inventory_change(
    item_id: int, payload: ConfirmChangeRequest, session: SessionDep
) -> InventoryResponse:
    item = session.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    food = session.get(FoodItem, item.food_item_id)
    if food is None:
        raise HTTPException(status_code=500, detail="Food item missing")

    if payload.new_quantity is not None:
        confirmed_quantity = payload.new_quantity
    elif item.pending_detected_quantity is not None:
        confirmed_quantity = item.pending_detected_quantity
    else:
        confirmed_quantity = item.confirmed_quantity

    old_quantity = item.confirmed_quantity
    old_status = item.status
    pending_change_type = item.pending_change_type
    if payload.as_new_batch:
        if pending_change_type != "possible_added":
            raise HTTPException(
                status_code=400,
                detail="as_new_batch is only valid for possible_added changes",
            )
        added_quantity = confirmed_quantity - old_quantity
        if added_quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="new batch quantity must be greater than current quantity",
            )
        item.detected_quantity = old_quantity
        item.pending_change_type = "none"
        item.pending_detected_quantity = None
        item.updated_at = utc_now()
        _apply_storage_state(session, item)
        session.add(item)

        new_item = InventoryItem(
            evidence_id="pending",
            user_id=item.user_id,
            camera_id=item.camera_id,
            food_item_id=item.food_item_id,
            detected_quantity=added_quantity,
            confirmed_quantity=added_quantity,
            unit=item.unit,
            storage_location=item.storage_location,
            first_seen_at=item.last_seen_at,
            last_seen_at=item.last_seen_at,
            status=payload.status or "available",
            source_event_id=item.source_event_id,
            pending_change_type="none",
            pending_detected_quantity=None,
        )
        session.add(new_item)
        session.flush()
        new_item.evidence_id = f"inventory_{new_item.id}"
        _apply_storage_state(session, new_item)
        session.add(new_item)
        record_user_food_event(
            session,
            food=food,
            event_type="purchased",
            quantity=added_quantity,
            occurred_at=_as_utc(new_item.first_seen_at),
            metadata={
                "inventory_id": new_item.id,
                "source": "inventory_confirm_change",
                "pending_change_type": pending_change_type,
                "as_new_batch": True,
                "old_inventory_id": item.id,
            },
            refresh_habits=True,
        )
        session.commit()
        session.refresh(new_item)
        return _serialize_inventory(new_item, food)

    item.confirmed_quantity = confirmed_quantity
    item.detected_quantity = confirmed_quantity
    item.status = payload.status or "available"
    item.pending_change_type = "none"
    item.pending_detected_quantity = None
    item.updated_at = utc_now()
    _apply_storage_state(session, item)
    if payload.snooze_days is not None:
        item.check_snoozed_until = item.updated_at + timedelta(days=payload.snooze_days)
    else:
        item.check_snoozed_until = None
    session.add(item)
    _record_inventory_truth_change(
        session=session,
        item=item,
        food=food,
        old_quantity=old_quantity,
        old_status=old_status,
        change_source="inventory_confirm_change",
        pending_change_type=pending_change_type,
    )
    session.commit()
    session.refresh(item)
    return _serialize_inventory(item, food)


@router.get("/inventory/storage-states", response_model=list[InventoryResponse])
def list_storage_states(session: SessionDep) -> list[InventoryResponse]:
    items = session.exec(
        select(InventoryItem)
        .where(InventoryItem.status.notin_(["consumed", "discarded", "unknown"]))
        .order_by(InventoryItem.id)
    ).all()
    foods = _food_map(session)
    _refresh_storage_states(session, items)
    session.commit()
    return [_serialize_inventory(item, foods[item.food_item_id]) for item in items]


def merge_inventory_for_recognition(
    session: Session,
    event: RecognitionEvent,
    food: FoodItem,
    detected_quantity: int,
    captured_at: datetime,
    auto_confirm: bool = False,
) -> InventoryItem:
    item, is_duplicate_window = _find_merge_target(
        session, event.camera_id, food.id or 0, captured_at
    )
    if item is None:
        item = InventoryItem(
            evidence_id="pending",
            user_id=1,
            camera_id=event.camera_id,
            food_item_id=food.id or 0,
            detected_quantity=detected_quantity,
            confirmed_quantity=detected_quantity if auto_confirm else 0,
            unit="piece",
            storage_location="pantry",
            first_seen_at=captured_at,
            last_seen_at=captured_at,
            status="available" if auto_confirm else "pending_confirm",
            source_event_id=event.id,
            pending_change_type="none" if auto_confirm else "new_quantity",
            pending_detected_quantity=None if auto_confirm else detected_quantity,
        )
        session.add(item)
        session.flush()
        item.evidence_id = f"inventory_{item.id}"
        _apply_storage_state(session, item, captured_at)
        session.add(item)
        if auto_confirm:
            _record_inventory_truth_change(
                session=session,
                item=item,
                food=food,
                old_quantity=0,
                old_status="pending_confirm",
                change_source="recognition_auto_confirm",
                pending_change_type="new_quantity",
            )
        return item

    old_quantity = item.confirmed_quantity
    old_status = item.status
    pending_change_type: str | None = None
    item.last_seen_at = captured_at
    item.source_event_id = event.id
    if auto_confirm and (not is_duplicate_window or item.status == "pending_confirm"):
        pending_change_type = (
            item.pending_change_type
            if item.pending_change_type != "none"
            else _quantity_change_type(old_quantity, detected_quantity)
        )
        item.detected_quantity = detected_quantity
        item.confirmed_quantity = detected_quantity
        item.status = "available"
        item.pending_change_type = "none"
        item.pending_detected_quantity = None
    elif not is_duplicate_window:
        item.detected_quantity = detected_quantity
        _apply_pending_quantity_change(item, detected_quantity)
    item.updated_at = utc_now()
    _apply_storage_state(session, item, captured_at)
    session.add(item)
    if auto_confirm and pending_change_type is not None:
        session.flush()
        _record_inventory_truth_change(
            session=session,
            item=item,
            food=food,
            old_quantity=old_quantity,
            old_status=old_status,
            change_source="recognition_auto_confirm",
            pending_change_type=pending_change_type,
        )
    return item


def _find_merge_target(
    session: Session, camera_id: str, food_item_id: int, captured_at: datetime
) -> tuple[InventoryItem | None, bool]:
    item = session.exec(
        select(InventoryItem)
        .where(InventoryItem.camera_id == camera_id)
        .where(InventoryItem.food_item_id == food_item_id)
        .where(InventoryItem.status.notin_(["consumed", "discarded", "unknown"]))
        .order_by(desc(InventoryItem.last_seen_at))
    ).first()
    if item is None:
        return None, False

    seconds = abs((_as_utc(captured_at) - _as_utc(item.last_seen_at)).total_seconds())
    return item, seconds <= DUPLICATE_WINDOW_SECONDS


def _apply_pending_quantity_change(item: InventoryItem, detected_quantity: int) -> None:
    if detected_quantity > item.confirmed_quantity:
        item.pending_change_type = "possible_added"
        item.pending_detected_quantity = detected_quantity
    elif detected_quantity < item.confirmed_quantity:
        item.pending_change_type = "possible_consumed"
        item.pending_detected_quantity = detected_quantity
    elif item.pending_change_type != "new_quantity":
        item.pending_change_type = "none"
        item.pending_detected_quantity = None


def _quantity_change_type(old_quantity: int, detected_quantity: int) -> str | None:
    if detected_quantity > old_quantity:
        return "possible_added"
    if detected_quantity < old_quantity:
        return "possible_consumed"
    return None


def _refresh_storage_states(session: Session, items: list[InventoryItem]) -> None:
    foods = _food_map(session)
    for item in items:
        _apply_storage_state(session, item)
        food = foods.get(item.food_item_id)
        if (
            food is not None
            and item.status == "available"
            and item.confirmed_quantity > 0
            and item.storage_state == "check_required"
            and not _is_check_snoozed(item)
        ):
            record_check_required_once(
                session,
                item=item,
                food=food,
                storage_state=item.storage_state,
                occurred_at=utc_now(),
            )

    candidates = [
        item
        for item in items
        if item.storage_state in {"fresh", "eat_soon"}
        and item.status == "available"
        and item.confirmed_quantity > 0
    ]
    candidates.sort(
        key=lambda item: (
            0 if item.storage_state == "eat_soon" else 1,
            item.remaining_days if item.remaining_days is not None else 9999,
            -item.confirmed_quantity,
        )
    )
    for rank, item in enumerate(candidates, start=1):
        item.eat_priority_rank = rank
    for item in items:
        if item not in candidates:
            item.eat_priority_rank = None
        session.add(item)


def _apply_storage_state(
    session: Session, item: InventoryItem, as_of: datetime | None = None
) -> None:
    as_of_time = _as_utc(as_of or utc_now())
    first_seen = _as_utc(item.first_seen_at)
    days_stored = max(0, int((as_of_time - first_seen).total_seconds() // 86400))
    safe_days = _safe_days_for_item(session, item)

    item.days_stored = days_stored
    item.safe_days = safe_days
    if safe_days is None or safe_days <= 0:
        item.remaining_days = None
        item.storage_state = "check_required"
        return

    item.remaining_days = safe_days - days_stored
    if days_stored < safe_days * 0.7:
        item.storage_state = "fresh"
    elif days_stored <= safe_days:
        item.storage_state = "eat_soon"
    elif days_stored <= safe_days * 1.3:
        item.storage_state = "check_required"
    else:
        item.storage_state = "not_recommended"


def _safe_days_for_item(session: Session, item: InventoryItem) -> int | None:
    rule = session.exec(
        select(FoodStorageRule)
        .where(FoodStorageRule.food_item_id == item.food_item_id)
        .where(FoodStorageRule.storage_location == item.storage_location)
    ).first()
    if rule is not None:
        return rule.safe_days

    fallback_rule = session.exec(
        select(FoodStorageRule).where(FoodStorageRule.food_item_id == item.food_item_id)
    ).first()
    if fallback_rule is None:
        return None
    return fallback_rule.safe_days


def _record_inventory_truth_change(
    *,
    session: Session,
    item: InventoryItem,
    food: FoodItem,
    old_quantity: int,
    old_status: str,
    change_source: str,
    pending_change_type: str | None = None,
) -> None:
    new_quantity = item.confirmed_quantity
    new_status = item.status
    event_type: str | None = None
    quantity = 0

    if new_status == "discarded" and old_status != "discarded":
        event_type = "discarded"
        quantity = old_quantity if old_quantity > 0 else new_quantity
    elif new_status == "consumed" and old_status != "consumed":
        event_type = "consumed"
        quantity = old_quantity if old_quantity > 0 else new_quantity
    elif pending_change_type == "possible_consumed" or new_quantity < old_quantity:
        event_type = "consumed"
        quantity = old_quantity - new_quantity
    elif pending_change_type in {"new_quantity", "possible_added"} or new_quantity > old_quantity:
        event_type = "purchased"
        quantity = new_quantity - old_quantity

    if event_type is None or quantity <= 0:
        return

    metadata = {
        "inventory_id": item.id,
        "source": change_source,
        "old_quantity": old_quantity,
        "new_quantity": new_quantity,
        "old_status": old_status,
        "new_status": new_status,
    }
    if pending_change_type is not None:
        metadata["pending_change_type"] = pending_change_type
    if event_type == "consumed" and item.first_seen_at is not None:
        metadata["days_to_consume"] = max(
            0,
            int((_as_utc(item.updated_at) - _as_utc(item.first_seen_at)).total_seconds() // 86400),
        )

    record_user_food_event(
        session,
        food=food,
        event_type=event_type,
        quantity=quantity,
        occurred_at=_as_utc(item.updated_at),
        metadata=metadata,
        refresh_habits=True,
    )


def _serialize_inventory(item: InventoryItem, food: FoodItem) -> InventoryResponse:
    storage_state = item.storage_state
    remaining_days = item.remaining_days
    message = CHECK_REQUIRED_MESSAGE if item.storage_state == "check_required" else None
    if _is_check_snoozed(item):
        storage_state = "eat_soon"
        remaining_days = _days_until(item.check_snoozed_until)
        message = None

    return InventoryResponse(
        id=item.id or 0,
        evidence_id=item.evidence_id,
        user_id=item.user_id,
        camera_id=item.camera_id,
        food=FoodSummary(
            id=food.id or 0,
            model_label=food.model_label,
            display_name=food.display_name,
        ),
        detected_quantity=item.detected_quantity,
        confirmed_quantity=item.confirmed_quantity,
        unit=item.unit,
        storage_location=item.storage_location,
        first_seen_at=item.first_seen_at,
        last_seen_at=item.last_seen_at,
        created_at=item.created_at,
        days_stored=item.days_stored,
        safe_days=item.safe_days,
        remaining_days=remaining_days,
        storage_state=storage_state,
        eat_priority_rank=item.eat_priority_rank,
        status=item.status,
        source_event_id=item.source_event_id,
        pending_change_type=item.pending_change_type,
        pending_detected_quantity=item.pending_detected_quantity,
        check_snoozed_until=item.check_snoozed_until,
        message=message,
    )


def _food_map(session: Session) -> dict[int, FoodItem]:
    return {food.id or 0: food for food in session.exec(select(FoodItem)).all()}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_check_snoozed(item: InventoryItem, as_of: datetime | None = None) -> bool:
    if item.check_snoozed_until is None:
        return False
    return _as_utc(item.check_snoozed_until) > _as_utc(as_of or utc_now())


def _days_until(value: datetime | None) -> int | None:
    if value is None:
        return None
    seconds = (_as_utc(value) - utc_now()).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, int((seconds + 86399) // 86400))
