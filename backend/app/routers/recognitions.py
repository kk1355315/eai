import json
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    CaptureImage,
    FoodItem,
    RecognitionDetection,
    RecognitionEvent,
    UnknownFoodItem,
    utc_now,
)
from app.routers.inventory import merge_inventory_for_recognition

router = APIRouter(tags=["recognitions"])

SessionDep = Annotated[Session, Depends(get_session)]

MIN_CONFIDENCE = 0.60
AUTO_CONFIRM_MODEL_NAMES = {"fruit-yolo11n-imx500"}
UNCERTAIN_CLASS_KEYWORDS = (
    "package",
    "packaged",
    "bag",
    "box",
    "container",
    "carton",
    "unknown",
    "uncertain",
    "包装",
    "袋",
    "盒",
    "不确定",
)


class ImagePayload(BaseModel):
    original_path: str | None = None
    thumbnail_path: str | None = None
    annotated_path: str | None = None
    width: int | None = None
    height: int | None = None
    captured_at: datetime | None = None

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_include_timezone(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return value
        return _require_timezone(value)


class DetectionPayload(BaseModel):
    class_name: str
    confidence: float = Field(ge=0, le=1)
    bbox: Any

    @field_validator("class_name")
    @classmethod
    def class_name_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("class_name cannot be blank")
        return value


class RecognitionCreate(BaseModel):
    camera_id: str
    source: str
    captured_at: datetime
    model_name: str | None = None
    model_version: str | None = None
    image: ImagePayload | None = None
    detections: list[DetectionPayload]

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_include_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class DetectedQuantityResponse(BaseModel):
    food_item_id: int
    class_name: str
    total_count: int
    detected_quantity: int


class RecognitionCreateResponse(BaseModel):
    event_id: int
    image_id: int | None
    total_count: int
    detected_quantities: list[DetectedQuantityResponse]


class ImageResponse(BaseModel):
    id: int
    event_id: int | None
    original_path: str | None
    thumbnail_path: str | None
    annotated_path: str | None
    width: int | None
    height: int | None
    captured_at: datetime | None
    created_at: datetime


class DetectionResponse(BaseModel):
    id: int
    food_item_id: int | None
    class_name: str
    confidence: float
    bbox: dict[str, float | None]
    status: str


class UnknownFoodResponse(BaseModel):
    id: int
    reason: str
    suggested_label: str | None
    confidence: float | None
    status: str


class RecognitionResponse(BaseModel):
    id: int
    camera_id: str
    source: str
    captured_at: datetime
    model_name: str | None
    model_version: str | None
    image: ImageResponse | None
    total_count: int
    detections: list[DetectionResponse]
    unknown_items: list[UnknownFoodResponse]
    created_at: datetime


@router.post("/recognitions", response_model=RecognitionCreateResponse)
def create_recognition(
    payload: RecognitionCreate, session: SessionDep
) -> RecognitionCreateResponse:
    captured_at = _as_utc(payload.captured_at)
    _validate_image_evidence(payload)
    image = _create_image(session, payload.image, captured_at)

    event = RecognitionEvent(
        camera_id=payload.camera_id,
        source=payload.source,
        captured_at=captured_at,
        model_name=payload.model_name,
        model_version=payload.model_version,
        image_id=image.id if image else None,
        total_count=0,
        raw_payload=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
    )
    session.add(event)
    session.flush()

    if image is not None:
        image.event_id = event.id
        session.add(image)

    foods_by_alias = _foods_by_alias(session)
    accepted_counts: dict[str, int] = {}
    accepted_foods: dict[str, FoodItem] = {}

    for detection_payload in payload.detections:
        bbox = _parse_bbox(detection_payload.bbox)
        label = _normalize_label(detection_payload.class_name)
        food = foods_by_alias.get(label)
        status, reason = _classify_detection(detection_payload, food)

        detection = RecognitionDetection(
            event_id=event.id or 0,
            food_item_id=food.id if food else None,
            class_name=detection_payload.class_name,
            confidence=detection_payload.confidence,
            bbox_x1=bbox["x1"],
            bbox_y1=bbox["y1"],
            bbox_x2=bbox["x2"],
            bbox_y2=bbox["y2"],
            bbox_cx_norm=bbox.get("cx_norm"),
            bbox_cy_norm=bbox.get("cy_norm"),
            bbox_w_norm=bbox.get("w_norm"),
            bbox_h_norm=bbox.get("h_norm"),
            status=status,
        )
        session.add(detection)

        if status == "accepted" and food is not None:
            accepted_counts[food.model_label] = accepted_counts.get(food.model_label, 0) + 1
            accepted_foods[food.model_label] = food
        else:
            session.add(
                UnknownFoodItem(
                    event_id=event.id or 0,
                    image_id=image.id if image else None,
                    reason=reason,
                    suggested_label=detection_payload.class_name,
                    confidence=detection_payload.confidence,
                    status="pending_confirm" if food is not None else "unknown",
                )
            )

    event.total_count = sum(accepted_counts.values())
    session.add(event)
    session.flush()

    auto_confirm_inventory = _should_auto_confirm_inventory(payload)
    for label, detected_quantity in accepted_counts.items():
        merge_inventory_for_recognition(
            session=session,
            event=event,
            food=accepted_foods[label],
            detected_quantity=detected_quantity,
            captured_at=captured_at,
            auto_confirm=auto_confirm_inventory,
        )

    session.commit()
    session.refresh(event)
    return RecognitionCreateResponse(
        event_id=event.id or 0,
        image_id=event.image_id,
        total_count=event.total_count,
        detected_quantities=[
            DetectedQuantityResponse(
                food_item_id=accepted_foods[label].id or 0,
                class_name=label,
                total_count=count,
                detected_quantity=count,
            )
            for label, count in sorted(accepted_counts.items())
        ],
    )


@router.get("/recognitions", response_model=list[RecognitionResponse])
def list_recognitions(session: SessionDep) -> list[RecognitionResponse]:
    events = session.exec(
        select(RecognitionEvent).order_by(RecognitionEvent.id)
    ).all()
    return [_serialize_event(session, event) for event in events]


@router.get("/images/{image_id}", response_model=ImageResponse)
def get_image(image_id: int, session: SessionDep) -> ImageResponse:
    image = session.get(CaptureImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return _serialize_image(image)


def _create_image(
    session: Session, image_payload: ImagePayload | None, captured_at: datetime
) -> CaptureImage | None:
    if image_payload is None:
        return None

    image = CaptureImage(
        original_path=image_payload.original_path,
        thumbnail_path=image_payload.thumbnail_path,
        annotated_path=image_payload.annotated_path,
        width=image_payload.width,
        height=image_payload.height,
        captured_at=_as_utc(image_payload.captured_at)
        if image_payload.captured_at
        else captured_at,
    )
    session.add(image)
    session.flush()
    return image


def _validate_image_evidence(payload: RecognitionCreate) -> None:
    if payload.source != "ai_camera":
        return
    if payload.image is None:
        raise HTTPException(status_code=422, detail="ai_camera image evidence is required")
    if not payload.image.original_path or not payload.image.original_path.strip():
        raise HTTPException(status_code=422, detail="image.original_path is required")
    if payload.image.width is None or payload.image.width <= 0:
        raise HTTPException(status_code=422, detail="image.width must be greater than 0")
    if payload.image.height is None or payload.image.height <= 0:
        raise HTTPException(status_code=422, detail="image.height must be greater than 0")


def _classify_detection(
    detection: DetectionPayload, food: FoodItem | None
) -> tuple[str, str]:
    if _is_uncertain_or_packaged(detection.class_name):
        return "pending_confirm", "uncertain_or_packaged"
    if food is None:
        return "unknown", "unknown_class"
    if detection.confidence < MIN_CONFIDENCE:
        return "pending_confirm", "low_confidence"
    return "accepted", ""


def _should_auto_confirm_inventory(payload: RecognitionCreate) -> bool:
    model_name = (payload.model_name or "").strip()
    return payload.source == "ai_camera" and model_name in AUTO_CONFIRM_MODEL_NAMES


def _parse_bbox(value: Any) -> dict[str, float | None]:
    if isinstance(value, list) and len(value) >= 4:
        return {
            "x1": float(value[0]),
            "y1": float(value[1]),
            "x2": float(value[2]),
            "y2": float(value[3]),
            "cx_norm": None,
            "cy_norm": None,
            "w_norm": None,
            "h_norm": None,
        }

    if isinstance(value, dict):
        if {"x1", "y1", "x2", "y2"}.issubset(value):
            x1 = float(value["x1"])
            y1 = float(value["y1"])
            x2 = float(value["x2"])
            y2 = float(value["y2"])
        elif {"xmin", "ymin", "xmax", "ymax"}.issubset(value):
            x1 = float(value["xmin"])
            y1 = float(value["ymin"])
            x2 = float(value["xmax"])
            y2 = float(value["ymax"])
        elif {"x", "y", "width", "height"}.issubset(value):
            x1 = float(value["x"])
            y1 = float(value["y"])
            x2 = x1 + float(value["width"])
            y2 = y1 + float(value["height"])
        else:
            raise HTTPException(status_code=422, detail="bbox must contain coordinates")

        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "cx_norm": _optional_float(value.get("cx_norm")),
            "cy_norm": _optional_float(value.get("cy_norm")),
            "w_norm": _optional_float(value.get("w_norm")),
            "h_norm": _optional_float(value.get("h_norm")),
        }

    raise HTTPException(status_code=422, detail="bbox must be a list or object")


def _serialize_event(session: Session, event: RecognitionEvent) -> RecognitionResponse:
    image = session.get(CaptureImage, event.image_id) if event.image_id else None
    detections = session.exec(
        select(RecognitionDetection)
        .where(RecognitionDetection.event_id == event.id)
        .order_by(RecognitionDetection.id)
    ).all()
    unknown_items = session.exec(
        select(UnknownFoodItem)
        .where(UnknownFoodItem.event_id == event.id)
        .order_by(UnknownFoodItem.id)
    ).all()

    return RecognitionResponse(
        id=event.id or 0,
        camera_id=event.camera_id,
        source=event.source,
        captured_at=event.captured_at,
        model_name=event.model_name,
        model_version=event.model_version,
        image=_serialize_image(image) if image else None,
        total_count=event.total_count,
        detections=[_serialize_detection(detection) for detection in detections],
        unknown_items=[_serialize_unknown(item) for item in unknown_items],
        created_at=event.created_at,
    )


def _serialize_image(image: CaptureImage) -> ImageResponse:
    return ImageResponse(
        id=image.id or 0,
        event_id=image.event_id,
        original_path=image.original_path,
        thumbnail_path=image.thumbnail_path,
        annotated_path=image.annotated_path,
        width=image.width,
        height=image.height,
        captured_at=image.captured_at,
        created_at=image.created_at,
    )


def _serialize_detection(detection: RecognitionDetection) -> DetectionResponse:
    return DetectionResponse(
        id=detection.id or 0,
        food_item_id=detection.food_item_id,
        class_name=detection.class_name,
        confidence=detection.confidence,
        bbox={
            "x1": detection.bbox_x1,
            "y1": detection.bbox_y1,
            "x2": detection.bbox_x2,
            "y2": detection.bbox_y2,
            "cx_norm": detection.bbox_cx_norm,
            "cy_norm": detection.bbox_cy_norm,
            "w_norm": detection.bbox_w_norm,
            "h_norm": detection.bbox_h_norm,
        },
        status=detection.status,
    )


def _serialize_unknown(item: UnknownFoodItem) -> UnknownFoodResponse:
    return UnknownFoodResponse(
        id=item.id or 0,
        reason=item.reason,
        suggested_label=item.suggested_label,
        confidence=item.confidence,
        status=item.status,
    )


def _foods_by_alias(session: Session) -> dict[str, FoodItem]:
    foods = session.exec(select(FoodItem).where(FoodItem.enabled == True)).all()
    result: dict[str, FoodItem] = {}
    for food in foods:
        aliases = _loads(food.aliases, [])
        for alias in [food.model_label, *aliases]:
            result[_normalize_label(str(alias))] = food
    return result


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _is_uncertain_or_packaged(value: str) -> bool:
    normalized = _normalize_label(value)
    return any(keyword in normalized for keyword in UNCERTAIN_CLASS_KEYWORDS)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("captured_at must include timezone")
    return value
