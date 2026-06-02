import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    FoodItem,
    FoodStorageRule,
    GuidelineRule,
    NutritionFact,
    NutritionReference,
)

router = APIRouter(tags=["reference"])

SessionDep = Annotated[Session, Depends(get_session)]


class FoodResponse(BaseModel):
    id: int
    model_label: str
    display_name: str
    foodkeeper_product_id: int
    aliases: list[str]
    enabled: bool


class FoodStorageRuleResponse(BaseModel):
    id: int
    evidence_id: str
    food_item_id: int
    source_product_id: int
    storage_location: str
    safe_days: int | None
    source_min_value: float | None
    source_max_value: float | None
    source_metric: str | None
    source_text: str
    pantry_text: str | None
    refrigerate_text: str | None
    freeze_text: str | None
    tips: str | None


class FoodStorageResponse(BaseModel):
    food: FoodResponse
    storage_rules: list[FoodStorageRuleResponse]


class GuidelineRuleResponse(BaseModel):
    id: int
    evidence_id: str
    source_name: str
    source_url: str
    rule_type: str
    applies_to: list[str]
    tags: list[str]
    condition: dict[str, list[str]]
    recommendation_template: str
    evidence_summary: str
    enabled: bool


class NutritionReferenceResponse(BaseModel):
    id: int
    source_name: str
    source_url: str
    version: str | None
    retrieved_at: datetime


class NutritionFactResponse(BaseModel):
    id: int
    evidence_id: str
    food: FoodResponse | None
    reference: NutritionReferenceResponse | None
    fdc_id: int
    source_url: str
    serving_size_text: str
    calories: float | None
    carbs_g: float | None
    sugars_g: float | None
    fiber_g: float | None
    protein_g: float | None
    fat_g: float | None
    key_nutrients: list[str]
    notes: str | None


@router.get("/foods", response_model=list[FoodResponse])
def list_foods(session: SessionDep) -> list[FoodResponse]:
    foods = session.exec(
        select(FoodItem).where(FoodItem.enabled == True).order_by(FoodItem.id)
    ).all()
    return [_serialize_food(food) for food in foods]


@router.get("/foods/{food_id}/storage", response_model=FoodStorageResponse)
def get_food_storage(food_id: str, session: SessionDep) -> FoodStorageResponse:
    food = _find_food(session, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")

    rules = session.exec(
        select(FoodStorageRule)
        .where(FoodStorageRule.food_item_id == food.id)
        .order_by(FoodStorageRule.storage_location)
    ).all()

    return FoodStorageResponse(
        food=_serialize_food(food),
        storage_rules=[_serialize_storage_rule(rule) for rule in rules],
    )


@router.get("/guideline-rules", response_model=list[GuidelineRuleResponse])
def list_guideline_rules(session: SessionDep) -> list[GuidelineRuleResponse]:
    rules = session.exec(
        select(GuidelineRule)
        .where(GuidelineRule.enabled == True)
        .order_by(GuidelineRule.id)
    ).all()
    return [_serialize_guideline_rule(rule) for rule in rules]


@router.get("/nutrition-facts", response_model=list[NutritionFactResponse])
def list_nutrition_facts(session: SessionDep) -> list[NutritionFactResponse]:
    facts = session.exec(select(NutritionFact).order_by(NutritionFact.id)).all()
    foods = {food.id: food for food in session.exec(select(FoodItem)).all()}
    references = {
        reference.id: reference
        for reference in session.exec(select(NutritionReference)).all()
    }
    return [
        _serialize_nutrition_fact(
            fact,
            foods.get(fact.food_item_id),
            references.get(fact.reference_id),
        )
        for fact in facts
    ]


def _find_food(session: Session, food_id: str) -> FoodItem | None:
    if food_id.isdigit():
        food = session.get(FoodItem, int(food_id))
        if food is not None:
            return food

    return session.exec(
        select(FoodItem).where(FoodItem.model_label == food_id)
    ).first()


def _serialize_food(food: FoodItem) -> FoodResponse:
    return FoodResponse(
        id=food.id or 0,
        model_label=food.model_label,
        display_name=food.display_name,
        foodkeeper_product_id=food.foodkeeper_product_id,
        aliases=_loads(food.aliases, []),
        enabled=food.enabled,
    )


def _serialize_storage_rule(rule: FoodStorageRule) -> FoodStorageRuleResponse:
    return FoodStorageRuleResponse(
        id=rule.id or 0,
        evidence_id=rule.evidence_id,
        food_item_id=rule.food_item_id,
        source_product_id=rule.source_product_id,
        storage_location=rule.storage_location,
        safe_days=rule.safe_days,
        source_min_value=rule.source_min_value,
        source_max_value=rule.source_max_value,
        source_metric=rule.source_metric,
        source_text=rule.source_text,
        pantry_text=rule.pantry_text,
        refrigerate_text=rule.refrigerate_text,
        freeze_text=rule.freeze_text,
        tips=rule.tips,
    )


def _serialize_guideline_rule(rule: GuidelineRule) -> GuidelineRuleResponse:
    return GuidelineRuleResponse(
        id=rule.id or 0,
        evidence_id=rule.evidence_id,
        source_name=rule.source_name,
        source_url=rule.source_url,
        rule_type=rule.rule_type,
        applies_to=_loads(rule.applies_to_json, []),
        tags=_loads(rule.tags_json, []),
        condition=_loads(rule.condition_json, {}),
        recommendation_template=rule.recommendation_template,
        evidence_summary=rule.evidence_summary,
        enabled=rule.enabled,
    )


def _serialize_nutrition_fact(
    fact: NutritionFact,
    food: FoodItem | None,
    reference: NutritionReference | None,
) -> NutritionFactResponse:
    return NutritionFactResponse(
        id=fact.id or 0,
        evidence_id=fact.evidence_id,
        food=_serialize_food(food) if food else None,
        reference=_serialize_nutrition_reference(reference) if reference else None,
        fdc_id=fact.fdc_id or 0,
        source_url=fact.source_url or "",
        serving_size_text=fact.serving_size_text,
        calories=fact.calories,
        carbs_g=fact.carbs_g,
        sugars_g=fact.sugars_g,
        fiber_g=fact.fiber_g,
        protein_g=fact.protein_g,
        fat_g=fact.fat_g,
        key_nutrients=_loads(fact.key_nutrients_json, []),
        notes=fact.notes,
    )


def _serialize_nutrition_reference(
    reference: NutritionReference,
) -> NutritionReferenceResponse:
    return NutritionReferenceResponse(
        id=reference.id or 0,
        source_name=reference.source_name,
        source_url=reference.source_url,
        version=reference.version,
        retrieved_at=reference.retrieved_at,
    )


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
