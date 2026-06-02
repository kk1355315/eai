from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FoodItem(SQLModel, table=True):
    __tablename__ = "food_items"

    id: int | None = Field(default=None, primary_key=True)
    model_label: str = Field(index=True)
    display_name: str
    foodkeeper_product_id: int = Field(index=True)
    aliases: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    enabled: bool = True


class FoodStorageRule(SQLModel, table=True):
    __tablename__ = "food_storage_rules"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    food_item_id: int = Field(foreign_key="food_items.id", index=True)
    source_product_id: int = Field(index=True)
    storage_location: str
    safe_days: int | None = None
    source_min_value: float | None = None
    source_max_value: float | None = None
    source_metric: str | None = None
    source_text: str = Field(sa_column=Column(Text, nullable=False))
    pantry_text: str | None = Field(default=None, sa_column=Column(Text))
    refrigerate_text: str | None = Field(default=None, sa_column=Column(Text))
    freeze_text: str | None = Field(default=None, sa_column=Column(Text))
    tips: str | None = Field(default=None, sa_column=Column(Text))
    raw_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))


class NutritionReference(SQLModel, table=True):
    __tablename__ = "nutrition_references"

    id: int | None = Field(default=None, primary_key=True)
    source_name: str
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    version: str | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)


class NutritionFact(SQLModel, table=True):
    __tablename__ = "nutrition_facts"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    food_item_id: int = Field(foreign_key="food_items.id", index=True)
    reference_id: int = Field(foreign_key="nutrition_references.id", index=True)
    fdc_id: int | None = Field(default=None, index=True)
    source_url: str | None = Field(default=None, sa_column=Column(Text))
    serving_size_text: str
    calories: float | None = None
    carbs_g: float | None = None
    sugars_g: float | None = None
    fiber_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    key_nutrients_json: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    notes: str | None = Field(default=None, sa_column=Column(Text))


class GuidelineRule(SQLModel, table=True):
    __tablename__ = "guideline_rules"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    source_name: str
    source_url: str = Field(sa_column=Column(Text, nullable=False))
    rule_type: str
    applies_to_json: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    tags_json: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    condition_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    recommendation_template: str = Field(sa_column=Column(Text, nullable=False))
    evidence_summary: str = Field(sa_column=Column(Text, nullable=False))
    enabled: bool = True


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: int | None = Field(default=None, primary_key=True)
    goal: str = "健康饮食"
    diet_preference: str = "简单烹饪"
    cooking_condition: str = "家庭"
    avoid_foods: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    allergies_optional: str | None = Field(default=None, sa_column=Column(Text))
    health_notes_optional: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RecognitionEvent(SQLModel, table=True):
    __tablename__ = "recognition_events"

    id: int | None = Field(default=None, primary_key=True)
    camera_id: str = Field(index=True)
    source: str
    captured_at: datetime = Field(index=True)
    model_name: str | None = None
    model_version: str | None = None
    image_id: int | None = Field(default=None, foreign_key="capture_images.id")
    total_count: int = 0
    raw_payload: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class RecognitionDetection(SQLModel, table=True):
    __tablename__ = "recognition_detections"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="recognition_events.id", index=True)
    food_item_id: int | None = Field(default=None, foreign_key="food_items.id", index=True)
    class_name: str = Field(index=True)
    confidence: float
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float
    bbox_cx_norm: float | None = None
    bbox_cy_norm: float | None = None
    bbox_w_norm: float | None = None
    bbox_h_norm: float | None = None
    status: str = Field(default="accepted", index=True)


class CaptureImage(SQLModel, table=True):
    __tablename__ = "capture_images"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int | None = Field(default=None, foreign_key="recognition_events.id", index=True)
    original_path: str | None = Field(default=None, sa_column=Column(Text))
    thumbnail_path: str | None = Field(default=None, sa_column=Column(Text))
    annotated_path: str | None = Field(default=None, sa_column=Column(Text))
    width: int | None = None
    height: int | None = None
    captured_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_items"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    user_id: int = Field(default=1, index=True)
    camera_id: str | None = Field(default=None, index=True)
    food_item_id: int = Field(foreign_key="food_items.id", index=True)
    detected_quantity: int = 0
    confirmed_quantity: int = 0
    unit: str = "piece"
    storage_location: str = Field(default="pantry", index=True)
    first_seen_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now, index=True)
    days_stored: int | None = None
    safe_days: int | None = None
    remaining_days: int | None = None
    storage_state: str | None = Field(default=None, index=True)
    eat_priority_rank: int | None = None
    status: str = Field(default="pending_confirm", index=True)
    source_event_id: int | None = Field(default=None, foreign_key="recognition_events.id", index=True)
    pending_change_type: str = Field(default="none", index=True)
    pending_detected_quantity: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UnknownFoodItem(SQLModel, table=True):
    __tablename__ = "unknown_food_items"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="recognition_events.id", index=True)
    image_id: int | None = Field(default=None, foreign_key="capture_images.id", index=True)
    reason: str
    suggested_label: str | None = None
    confidence: float | None = None
    status: str = Field(default="pending_confirm", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class UserFoodEvent(SQLModel, table=True):
    __tablename__ = "user_food_events"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    user_id: int = Field(default=1, index=True)
    food_item_id: int = Field(foreign_key="food_items.id", index=True)
    event_type: str = Field(index=True)
    quantity: int = 0
    occurred_at: datetime = Field(default_factory=utc_now, index=True)
    metadata_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))


class UserFoodHabit(SQLModel, table=True):
    __tablename__ = "user_food_habits"

    id: int | None = Field(default=None, primary_key=True)
    evidence_id: str = Field(index=True)
    user_id: int = Field(default=1, index=True)
    food_item_id: int = Field(foreign_key="food_items.id", index=True)
    habit_type: str = Field(index=True)
    score: float = 0
    evidence_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    updated_at: datetime = Field(default_factory=utc_now)


class AdviceRecord(SQLModel, table=True):
    __tablename__ = "advice_records"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    advice_type: str = Field(index=True)
    content_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    basis_json: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    evidence_ids_json: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    llm_checked: bool = False
    created_at: datetime = Field(default_factory=utc_now)
