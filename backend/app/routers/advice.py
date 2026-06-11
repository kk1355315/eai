import json
import re
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    AdviceRecord,
    FoodItem,
    FoodStorageRule,
    GuidelineRule,
    InventoryItem,
    NutritionFact,
    NutritionReference,
    UserFoodHabit,
    UserProfile,
)
from app.config import settings
from app.routers.inventory import CHECK_REQUIRED_MESSAGE, _refresh_storage_states
from app.services.advice_context import build_advice_context, collect_evidence_ids, search_evidence
from app.services.llm_client import LlmClientError, request_llm_json
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt

router = APIRouter(tags=["advice"])

SessionDep = Annotated[Session, Depends(get_session)]
ActionType = Literal[
    "eat_first",
    "check_food",
    "avoid_duplicate_purchase",
    "portion_control",
    "variety",
    "general",
]

UNSAFE_TEXT_TERMS = (
    "腐败判断",
    "腐败",
    "腐烂",
    "变质",
    "发霉",
    "霉变",
    "医疗诊断",
    "诊断",
    "治疗",
    "坏了",
    "还能吃",
    "不能吃",
    "改库存",
    "修改库存",
    "删除记录",
    "自动确认",
    "写数据库",
    "写入数据库",
)
EAT_INTENT_TERMS = (
    "今天吃",
    "优先吃",
    "早餐吃",
    "加餐吃",
    "晚餐吃",
    "午餐吃",
    "eat",
    "eating",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
)
FOOD_RECOMMENDATION_ACTIONS = {"eat_first", "portion_control", "variety"}
FOOD_RECOMMENDATION_TEXT_TERMS = (
    "吃",
    "食用",
    "入口",
    "即食",
    "早餐",
    "午餐",
    "晚餐",
    "加餐",
    "搭配",
    "当作",
    "份量",
    "分量",
    "一份",
    "适量",
    "eat",
    "eating",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "pair",
    "pairing",
    "portion",
    "serving",
    "serve",
    "use as",
    "with yogurt",
)
PURCHASE_INTENT_TERMS = ("购买", "补买", "买", "buy", "purchase", "restock")
HOW_TO_EAT_TERMS = (
    "早餐",
    "午餐",
    "晚餐",
    "加餐",
    "搭配",
    "份量",
    "分量",
    "一根",
    "一个",
    "一份",
    "适量",
    "控制",
    "克",
    "g",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "pair",
    "pairing",
    "portion",
    "serving",
    "serve",
    "use as",
    "with yogurt",
)
HABIT_CLAIM_TERMS = ("习惯", "经常", "多次", "常常", "容易", "often")
NO_KITCHEN_TERMS = ("宿舍", "无厨房")
SIMPLE_COOKING_TERMS = ("简单烹饪",)
COOKING_ACTION_TERMS = ("煮", "炒", "烤", "炖", "蒸", "焗", "煲", "榨汁", "打汁", "果酱")
SUGAR_SENSITIVE_TERMS = ("控糖", "少糖", "减糖", "reduce_sugar")
HIGH_SUGAR_FOODS = {"litchi"}
EXCESS_SUGAR_TERMS = ("不限量", "多吃", "大量", "多喝", "果汁", "榨汁", "甜品")


class AdviceItem(BaseModel):
    title: str
    content: str
    action_type: ActionType
    related_foods: list[str]
    basis: list[str]
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class TodayAdviceResponse(BaseModel):
    today_priority: list[dict[str, Any]]
    check_required: list[dict[str, Any]]


class ShoppingAdviceResponse(BaseModel):
    recommendations: list[AdviceItem]


class LlmAdvicePayload(BaseModel):
    summary: str
    recommendations: list[AdviceItem] = Field(default_factory=list)


class LlmAdviceRequest(BaseModel):
    llm_output: LlmAdvicePayload


class LlmGenerateRequest(BaseModel):
    question: str | None = None
    enable_thinking: bool | None = None
    search_query: str | None = None


class LlmAdviceResponse(BaseModel):
    accepted: bool
    errors: list[str]
    advice: LlmAdvicePayload
    record_id: int | None = None


class EvidenceSearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class AdviceRecordResponse(BaseModel):
    id: int
    user_id: int
    advice_type: str
    content: dict[str, Any]
    basis: list[Any]
    evidence_ids: list[str]
    llm_checked: bool
    created_at: datetime


@router.get("/advice/today", response_model=TodayAdviceResponse)
def get_today_advice(session: SessionDep) -> TodayAdviceResponse:
    foods = _food_map(session)
    storage_rules = _storage_rule_map(session)
    items = session.exec(
        select(InventoryItem)
        .where(InventoryItem.status.in_(["available", "pending_confirm"]))
        .order_by(InventoryItem.id)
    ).all()
    _refresh_storage_states(session, items)
    session.commit()

    priority_items = [
        item
        for item in items
        if item.status == "available"
        and item.confirmed_quantity > 0
        and item.storage_state in {"fresh", "eat_soon"}
    ]
    priority_items.sort(
        key=lambda item: (
            0 if item.storage_state == "eat_soon" else 1,
            item.remaining_days if item.remaining_days is not None else 9999,
            -item.confirmed_quantity,
        )
    )

    check_items = [
        item
        for item in items
        if item.status == "available"
        and item.confirmed_quantity > 0
        if item.storage_state in {"check_required", "not_recommended"}
    ]

    return TodayAdviceResponse(
        today_priority=[
            _priority_item(item, foods[item.food_item_id], storage_rules) for item in priority_items
        ],
        check_required=[
            _check_item(item, foods[item.food_item_id], storage_rules) for item in check_items
        ],
    )


@router.get("/advice/shopping", response_model=ShoppingAdviceResponse)
def get_shopping_advice(session: SessionDep) -> ShoppingAdviceResponse:
    foods = _food_map(session)
    inventory = session.exec(
        select(InventoryItem)
        .where(InventoryItem.status == "available")
        .where(InventoryItem.confirmed_quantity > 0)
        .order_by(InventoryItem.id)
    ).all()
    habits = session.exec(select(UserFoodHabit)).all()
    habit_map = {(habit.food_item_id, habit.habit_type): habit for habit in habits}
    recommendations: list[AdviceItem] = []

    for item in inventory:
        food = foods[item.food_item_id]
        evidence_ids = [item.evidence_id]
        basis = [f"{food.display_name} 当前库存 {item.confirmed_quantity} {item.unit}"]
        habit = habit_map.get((item.food_item_id, "often_overbuys"))
        if habit is not None:
            evidence_ids.append(habit.evidence_id)
            basis.append("30 天内多次购买且仍有库存")
        recommendations.append(
            AdviceItem(
                title=f"{food.display_name} 暂时不用重复购买",
                content="当前仍有库存，建议先处理已有水果，再决定是否补买。",
                action_type="avoid_duplicate_purchase",
                related_foods=[food.model_label],
                basis=basis,
                evidence_ids=evidence_ids,
                confidence="high",
            )
        )

    advice = LlmAdvicePayload(summary="", recommendations=recommendations)
    return ShoppingAdviceResponse(
        recommendations=_attach_evidence_sources(advice, session).recommendations
    )


@router.post("/advice/llm/validate", response_model=LlmAdviceResponse)
def validate_llm_advice(payload: LlmAdviceRequest, session: SessionDep) -> LlmAdviceResponse:
    context = _advice_context(session)
    errors = _validate_llm_output(payload.llm_output, context)
    if errors:
        return LlmAdviceResponse(
            accepted=False,
            errors=errors,
            advice=_fallback_advice(session),
            record_id=None,
        )
    return LlmAdviceResponse(
        accepted=True,
        errors=[],
        advice=_attach_evidence_sources(payload.llm_output, session),
        record_id=None,
    )


@router.post("/advice/llm/generate", response_model=LlmAdviceResponse)
@router.post("/advice/llm", response_model=LlmAdviceResponse)
def generate_llm_advice(
    payload: LlmGenerateRequest, session: SessionDep
) -> LlmAdviceResponse:
    context = build_advice_context(session, payload.search_query)
    enable_thinking = (
        settings.llm_enable_thinking_default
        if payload.enable_thinking is None
        else payload.enable_thinking
    )
    try:
        advice = _request_llm_advice(context, payload.question, enable_thinking)
    except (LlmClientError, ValueError) as exc:
        return LlmAdviceResponse(
            accepted=False,
            errors=[str(exc)],
            advice=_fallback_advice(session),
            record_id=None,
        )

    validation_context = _advice_context(session)
    advice = _enrich_llm_evidence(advice, validation_context)
    errors = _validate_llm_output(advice, validation_context)
    if errors:
        try:
            advice = _request_llm_advice(
                context,
                payload.question,
                enable_thinking,
                validation_errors=errors,
            )
        except (LlmClientError, ValueError) as exc:
            return LlmAdviceResponse(
                accepted=False,
                errors=[*errors, str(exc)],
                advice=_fallback_advice(session),
                record_id=None,
            )
        validation_context = _advice_context(session)
        advice = _enrich_llm_evidence(advice, validation_context)
    return _store_checked_advice(advice, session)


@router.get("/advice/evidence-search", response_model=EvidenceSearchResponse)
def search_advice_evidence(query: str, session: SessionDep) -> EvidenceSearchResponse:
    context = build_advice_context(session)
    return EvidenceSearchResponse(query=query, results=search_evidence(context, query))


@router.get("/advice/{record_id}", response_model=AdviceRecordResponse)
def get_advice_record(record_id: int, session: SessionDep) -> AdviceRecordResponse:
    record = session.get(AdviceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Advice record not found")
    return AdviceRecordResponse(
        id=record.id or 0,
        user_id=record.user_id,
        advice_type=record.advice_type,
        content=_loads(record.content_json, {}),
        basis=_loads(record.basis_json, []),
        evidence_ids=_loads(record.evidence_ids_json, []),
        llm_checked=record.llm_checked,
        created_at=record.created_at,
    )


def _priority_item(
    item: InventoryItem,
    food: FoodItem,
    storage_rules: dict[tuple[int, str], FoodStorageRule],
) -> dict[str, Any]:
    rule = storage_rules.get((item.food_item_id, item.storage_location))
    evidence_ids = [item.evidence_id]
    if rule is not None:
        evidence_ids.append(rule.evidence_id)
    return {
        "food": food.model_label,
        "display_name": food.display_name,
        "storage_state": item.storage_state,
        "days_stored": item.days_stored,
        "safe_days": item.safe_days,
        "remaining_days": item.remaining_days,
        "eat_priority_rank": item.eat_priority_rank,
        "basis": [f"{food.display_name} 处于 {item.storage_state} 状态"],
        "evidence_ids": evidence_ids,
    }


def _check_item(
    item: InventoryItem,
    food: FoodItem,
    storage_rules: dict[tuple[int, str], FoodStorageRule],
) -> dict[str, Any]:
    rule = storage_rules.get((item.food_item_id, item.storage_location))
    evidence_ids = [item.evidence_id]
    if rule is not None:
        evidence_ids.append(rule.evidence_id)
    return {
        "food": food.model_label,
        "display_name": food.display_name,
        "storage_state": item.storage_state,
        "days_stored": item.days_stored,
        "safe_days": item.safe_days,
        "remaining_days": item.remaining_days,
        "basis": [CHECK_REQUIRED_MESSAGE],
        "evidence_ids": evidence_ids,
    }


def _fallback_advice(session: Session) -> LlmAdvicePayload:
    today = get_today_advice(session)
    foods = session.exec(select(FoodItem)).all()
    profile = session.get(UserProfile, 1)
    profile_blocked_foods = _profile_blocked_foods(_profile_payload(profile), foods)
    priority_items = [
        item for item in today.today_priority if item["food"] not in profile_blocked_foods
    ]
    recommendations = [
        AdviceItem(
            title=f"优先处理 {item['display_name']}",
            content=f"{item['display_name']} 处于 {item['storage_state']} 状态，可以优先安排。",
            action_type="eat_first",
            related_foods=[item["food"]],
            basis=item["basis"],
            evidence_ids=item["evidence_ids"],
            confidence="medium",
        )
        for item in priority_items[:3]
    ]
    if not recommendations:
        return LlmAdvicePayload(
            summary="没有符合用户资料和库存状态的规则版建议。",
            recommendations=[],
        )
    return _attach_evidence_sources(
        LlmAdvicePayload(summary="LLM 输出未通过校验，已返回规则版建议。", recommendations=recommendations),
        session,
    )


def _validate_llm_output(advice: LlmAdvicePayload, context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    profile = context.get("profile", {})
    if _contains_unsafe_text(advice.summary):
        errors.append("summary contains unsafe medical, spoilage, or database wording")
    if not advice.recommendations:
        errors.append("recommendations cannot be empty")
    for index, item in enumerate(advice.recommendations):
        prefix = f"recommendations[{index}]"
        actions = _effective_action_types(item)
        evidence_types = _evidence_types(item.evidence_ids)
        item_text = _item_text(item)
        mentioned_blocked_foods = _mentioned_food_labels(
            item_text,
            context["blocked_food_aliases"],
        )

        if _contains_unsafe_text(item_text):
            errors.append(f"{prefix} contains unsafe medical, spoilage, or database wording")
        if not item.evidence_ids:
            errors.append(f"{prefix}.evidence_ids is required")
        for evidence_id in item.evidence_ids:
            if evidence_id not in context["evidence_ids"]:
                errors.append(f"{prefix} references unknown evidence_id: {evidence_id}")
        for food in item.related_foods:
            if food not in context["supported_foods"]:
                errors.append(f"{prefix} references unsupported food: {food}")
            if food in context["avoid_foods"]:
                errors.append(f"{prefix} recommends avoided food: {food}")
            if food in context["profile_blocked_foods"]:
                errors.append(f"{prefix} recommends profile-blocked food: {food}")
        if _is_food_recommendation(item):
            blocked_food_mentions = (
                set(item.related_foods) | mentioned_blocked_foods
            ) & context["blocked_foods"]
            for food in sorted(blocked_food_mentions):
                errors.append(f"{prefix} recommends checked food for eating: {food}")
        if _conflicts_with_cooking_condition(item_text, profile):
            errors.append(f"{prefix} conflicts with cooking condition: {profile.get('cooking_condition')}")
        if _conflicts_with_sugar_sensitive_profile(item.related_foods, item_text, profile):
            errors.append(
                f"{prefix} conflicts with sugar-sensitive goal or diet preference"
            )
        if "eat_first" in actions:
            _require_evidence_types(
                errors,
                prefix,
                evidence_types,
                required_any=[{"inventory"}, {"storage"}],
                required_one_of={"nutri", "rule"},
                message="eat_first requires inventory/storage evidence and nutri or rule evidence",
            )
            if _has_how_to_eat_detail(item_text):
                _require_evidence_types(
                    errors,
                    prefix,
                    evidence_types,
                    required_any=[{"nutri"}, {"rule"}],
                    message="specific eating, pairing, or portion advice requires both nutri and rule evidence",
                )
        if "check_food" in actions:
            _require_evidence_types(
                errors,
                prefix,
                evidence_types,
                required_any=[{"inventory"}, {"storage"}],
                message="check_food requires inventory and storage evidence",
            )
        if _has_positive_purchase_intent(item_text):
            for food in item.related_foods:
                if food in context["stocked_foods"]:
                    errors.append(f"{prefix} recommends buying stocked food: {food}")
        if "avoid_duplicate_purchase" in actions:
            _require_evidence_types(
                errors,
                prefix,
                evidence_types,
                required_any=[{"inventory"}],
                message="avoid_duplicate_purchase requires inventory evidence",
            )
            if any(term in item_text for term in HABIT_CLAIM_TERMS) and "habit" not in evidence_types:
                errors.append(f"{prefix} habit-based purchase advice requires habit evidence")
        if "portion_control" in actions or "variety" in actions:
            _require_evidence_types(
                errors,
                prefix,
                evidence_types,
                required_any=[{"nutri"}, {"rule"}],
                message="portion_control and variety require nutri and rule evidence",
            )
    return errors


def _request_llm_advice(
    context: dict[str, Any],
    question: str | None,
    enable_thinking: bool,
    validation_errors: list[str] | None = None,
) -> LlmAdvicePayload:
    user_prompt = build_user_prompt(context, question, validation_errors=validation_errors)
    raw_output = request_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        enable_thinking=enable_thinking,
    )
    return LlmAdvicePayload.model_validate(raw_output)


def _enrich_llm_evidence(
    advice: LlmAdvicePayload, context: dict[str, Any]
) -> LlmAdvicePayload:
    known_evidence_ids = context["evidence_ids"]
    for item in advice.recommendations:
        inferred_foods = _infer_item_foods(item, context)
        if inferred_foods:
            item.related_foods = _merge_food_labels(item.related_foods, sorted(inferred_foods))
        inferred_ids = _infer_evidence_ids_from_hints(item, context, inferred_foods)
        if not inferred_ids:
            continue
        item.evidence_ids = _merge_evidence_ids(
            item.evidence_ids,
            [evidence_id for evidence_id in inferred_ids if evidence_id in known_evidence_ids],
        )
    return advice


def _infer_evidence_ids_from_hints(
    item: AdviceItem, context: dict[str, Any], related_foods: set[str] | None = None
) -> list[str]:
    foods = related_foods if related_foods is not None else _infer_item_foods(item, context)
    if not foods:
        return []

    actions = _effective_action_types(item)
    evidence_ids: list[str] = []
    for hint in context.get("evidence_hints", []):
        if hint.get("food") not in foods:
            continue
        if hint.get("action_type") not in actions:
            continue
        evidence_ids.extend(str(value) for value in hint.get("use_evidence_ids", []))
    return evidence_ids


def _infer_item_foods(item: AdviceItem, context: dict[str, Any]) -> set[str]:
    supported_foods = set(context["supported_foods"])
    alias_to_food = _alias_to_food(context)
    foods: set[str] = set()

    for food in item.related_foods:
        normalized = alias_to_food.get(food.lower(), food)
        if normalized in supported_foods:
            foods.add(normalized)

    item_text = _item_text(item).lower()
    for alias, food in alias_to_food.items():
        if food in supported_foods and _mentions_alias(item_text, alias):
            foods.add(food)
    return foods


def _alias_to_food(context: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for food, food_aliases in context.get("food_aliases", {}).items():
        aliases[str(food).lower()] = str(food)
        for alias in food_aliases:
            aliases[str(alias).lower()] = str(food)
    return aliases


def _merge_food_labels(current: list[str], inferred: list[str]) -> list[str]:
    return list(dict.fromkeys([*current, *inferred]))


def _merge_evidence_ids(current: list[str], inferred: list[str]) -> list[str]:
    return list(dict.fromkeys([*current, *inferred]))


def _store_checked_advice(advice: LlmAdvicePayload, session: Session) -> LlmAdviceResponse:
    context = _advice_context(session)
    errors = _validate_llm_output(advice, context)
    if errors:
        return LlmAdviceResponse(
            accepted=False,
            errors=errors,
            advice=_fallback_advice(session),
            record_id=None,
        )

    evidence_ids = sorted(
        {
            evidence_id
            for item in advice.recommendations
            for evidence_id in item.evidence_ids
        }
    )
    evidence_sources = _evidence_source_map(session)
    for item in advice.recommendations:
        item.evidence_sources = _sources_for_evidence_ids(
            item.evidence_ids,
            evidence_sources,
        )
    record = AdviceRecord(
        user_id=1,
        advice_type="llm",
        content_json=advice.model_dump_json(),
        basis_json=json.dumps([item.basis for item in advice.recommendations], ensure_ascii=False),
        evidence_ids_json=json.dumps(evidence_ids, ensure_ascii=False),
        llm_checked=True,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return LlmAdviceResponse(accepted=True, errors=[], advice=advice, record_id=record.id)


def _attach_evidence_sources(advice: LlmAdvicePayload, session: Session) -> LlmAdvicePayload:
    evidence_sources = _evidence_source_map(session)
    for item in advice.recommendations:
        item.evidence_sources = _sources_for_evidence_ids(item.evidence_ids, evidence_sources)
    return advice


def _sources_for_evidence_ids(
    evidence_ids: list[str],
    evidence_sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for evidence_id in evidence_ids:
        source = evidence_sources.get(evidence_id)
        if source is None:
            continue
        key = (str(source.get("title")), source.get("url"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(source)
    return sources


def _evidence_source_map(session: Session) -> dict[str, dict[str, Any]]:
    foods = _food_map(session)
    sources: dict[str, dict[str, Any]] = {}

    for item in session.exec(select(InventoryItem)).all():
        food = foods.get(item.food_item_id)
        if food is None:
            continue
        sources[item.evidence_id] = {
            "type": "inventory",
            "title": f"{food.display_name} 库存记录",
            "source": "用户确认库存",
            "summary": f"当前库存 {item.confirmed_quantity} {item.unit}，状态 {item.storage_state or 'unknown'}。",
            "url": None,
        }

    for rule in session.exec(select(FoodStorageRule)).all():
        food = foods.get(rule.food_item_id)
        if food is None:
            continue
        sources[rule.evidence_id] = {
            "type": "storage",
            "title": f"{food.display_name} 保存建议",
            "source": "USDA FoodKeeper",
            "summary": rule.source_text,
            "url": "https://www.foodsafety.gov/keep-food-safe/foodkeeper-app",
        }

    references = {
        reference.id: reference
        for reference in session.exec(select(NutritionReference)).all()
    }
    for fact in session.exec(select(NutritionFact)).all():
        food = foods.get(fact.food_item_id)
        reference = references.get(fact.reference_id)
        if food is None:
            continue
        source_name = reference.source_name if reference else "USDA FoodData Central"
        source_url = fact.source_url or (reference.source_url if reference else None)
        sources[fact.evidence_id] = {
            "type": "nutrition",
            "title": f"{food.display_name} 营养数据",
            "source": source_name,
            "summary": f"{fact.serving_size_text}；碳水 {fact.carbs_g}g，膳食纤维 {fact.fiber_g}g。",
            "url": source_url,
        }

    for rule in session.exec(select(GuidelineRule)).all():
        sources[rule.evidence_id] = {
            "type": "guideline",
            "title": rule.source_name,
            "source": rule.source_name,
            "summary": rule.evidence_summary,
            "url": rule.source_url,
        }

    for habit in session.exec(select(UserFoodHabit)).all():
        food = foods.get(habit.food_item_id)
        if food is None:
            continue
        sources[habit.evidence_id] = {
            "type": "habit",
            "title": f"{food.display_name} 使用习惯",
            "source": "用户历史记录",
            "summary": f"{habit.habit_type}，置信分 {habit.score:.2f}。",
            "url": None,
        }

    return sources


def _advice_context(session: Session) -> dict[str, Any]:
    context = build_advice_context(session)
    foods = session.exec(select(FoodItem)).all()
    inventory = session.exec(
        select(InventoryItem).where(InventoryItem.status.in_(["available", "pending_confirm"]))
    ).all()
    _refresh_storage_states(session, inventory)
    session.commit()
    food_by_id = {food.id: food for food in foods}
    blocked_foods = {
        food_by_id[item.food_item_id].model_label
        for item in inventory
        if item.status == "available"
        and item.confirmed_quantity > 0
        and item.storage_state in {"check_required", "not_recommended"}
    }
    stocked_foods = {
        food_by_id[item.food_item_id].model_label
        for item in inventory
        if item.status == "available" and item.confirmed_quantity > 0
    }
    avoid_foods = _normalize_food_labels(context.get("profile", {}).get("avoid_foods", []), foods)
    profile_blocked_foods = _profile_blocked_foods(context.get("profile", {}), foods)
    return {
        "evidence_ids": collect_evidence_ids(context),
        "supported_foods": {food.model_label for food in foods},
        "blocked_foods": blocked_foods,
        "blocked_food_aliases": {
            food.model_label: _food_aliases(food)
            for food in foods
            if food.model_label in blocked_foods
        },
        "food_aliases": {
            food.model_label: _food_aliases(food)
            for food in foods
        },
        "stocked_foods": stocked_foods,
        "avoid_foods": avoid_foods,
        "profile_blocked_foods": profile_blocked_foods,
        "profile": context.get("profile", {}),
        "evidence_hints": context.get("evidence_hints", []),
    }


def _food_map(session: Session) -> dict[int, FoodItem]:
    return {food.id or 0: food for food in session.exec(select(FoodItem)).all()}


def _storage_rule_map(session: Session) -> dict[tuple[int, str], FoodStorageRule]:
    rules = session.exec(select(FoodStorageRule)).all()
    return {(rule.food_item_id, rule.storage_location): rule for rule in rules}


def _item_text(item: AdviceItem) -> str:
    return " ".join([item.title, item.content, *item.basis])


def _contains_unsafe_text(text: str) -> bool:
    return any(term in text for term in UNSAFE_TEXT_TERMS)


def _effective_action_types(item: AdviceItem) -> set[str]:
    actions = {item.action_type}
    text = _item_text(item)
    if _contains_text_term(text, EAT_INTENT_TERMS):
        actions.add("eat_first")
    if any(term in text for term in PURCHASE_INTENT_TERMS) or item.action_type == "avoid_duplicate_purchase":
        actions.add("avoid_duplicate_purchase")
    return actions


def _is_food_recommendation(item: AdviceItem) -> bool:
    if item.action_type in FOOD_RECOMMENDATION_ACTIONS:
        return True
    text = _item_text(item)
    return _contains_text_term(text, FOOD_RECOMMENDATION_TEXT_TERMS)


def _evidence_types(evidence_ids: list[str]) -> set[str]:
    types: set[str] = set()
    for evidence_id in evidence_ids:
        prefix = evidence_id.split("_", 1)[0]
        if prefix in {"inventory", "storage", "nutri", "rule", "habit"}:
            types.add(prefix)
    return types


def _require_evidence_types(
    errors: list[str],
    prefix: str,
    evidence_types: set[str],
    *,
    required_any: list[set[str]],
    message: str,
    required_one_of: set[str] | None = None,
) -> None:
    for required in required_any:
        if not required <= evidence_types:
            errors.append(f"{prefix} {message}")
            return
    if required_one_of is not None and not (required_one_of & evidence_types):
        errors.append(f"{prefix} {message}")


def _has_how_to_eat_detail(text: str) -> bool:
    return _contains_text_term(text, HOW_TO_EAT_TERMS)


def _contains_text_term(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.lower()
    for term in terms:
        normalized_term = term.lower().strip()
        if not normalized_term:
            continue
        if normalized_term.isascii():
            pattern = re.escape(normalized_term)
            if normalized_term[0].isalnum():
                pattern = rf"(?<![a-z0-9_]){pattern}"
            if normalized_term[-1].isalnum():
                pattern = rf"{pattern}(?![a-z0-9_])"
            if re.search(pattern, normalized):
                return True
            continue
        if normalized_term in normalized:
            return True
    return False


def _has_positive_purchase_intent(text: str) -> bool:
    normalized = text.lower()
    if not any(term in normalized for term in PURCHASE_INTENT_TERMS):
        return False
    negative_terms = (
        "不用买",
        "不用购买",
        "不用补买",
        "无需买",
        "无需购买",
        "无需补买",
        "不要买",
        "不要购买",
        "不要补买",
        "不需要买",
        "不需要购买",
        "不需要补买",
        "不必买",
        "不必购买",
        "不买",
        "不建议买",
        "不建议购买",
        "暂时不用买",
        "暂时无需购买",
        "暂不购买",
        "先不买",
        "不用重复购买",
        "不建议重复购买",
        "避免购买",
        "避免重复购买",
        "do not buy",
        "don't buy",
        "dont buy",
        "no need to buy",
        "no need to purchase",
        "avoid buying",
        "avoid purchase",
    )
    return not any(term in normalized for term in negative_terms)


def _normalize_food_labels(values: list[str], foods: list[FoodItem]) -> set[str]:
    aliases: dict[str, str] = {}
    for food in foods:
        aliases[food.model_label.lower()] = food.model_label
        aliases[food.display_name.lower()] = food.model_label
        try:
            for alias in json.loads(food.aliases):
                aliases[str(alias).lower()] = food.model_label
        except json.JSONDecodeError:
            pass
    return {aliases.get(str(value).lower(), str(value).lower()) for value in values}


def _profile_blocked_foods(profile: dict[str, Any], foods: list[FoodItem]) -> set[str]:
    blocked = set(_normalize_food_labels(profile.get("avoid_foods", []), foods))
    allergy_text = str(profile.get("allergies_optional") or "").lower()
    health_text = str(profile.get("health_notes_optional") or "").lower()

    for food in foods:
        aliases = _food_aliases(food)
        if _mentions_any(allergy_text, aliases):
            blocked.add(food.model_label)
        if _mentions_any(health_text, aliases) and any(
            marker in health_text
            for marker in ("过敏", "避免", "不吃", "不要吃", "不能吃", "忌口", "不适合", "avoid")
        ):
            blocked.add(food.model_label)
    return blocked


def _profile_payload(profile: UserProfile | None) -> dict[str, Any]:
    if profile is None:
        return {}
    return {
        "avoid_foods": _loads(profile.avoid_foods, []),
        "allergies_optional": profile.allergies_optional,
        "health_notes_optional": profile.health_notes_optional,
    }


def _food_aliases(food: FoodItem) -> set[str]:
    aliases = {food.model_label.lower(), food.display_name.lower()}
    try:
        aliases.update(str(alias).lower() for alias in json.loads(food.aliases))
    except json.JSONDecodeError:
        pass
    return aliases


def _mentions_any(text: str, aliases: set[str]) -> bool:
    return any(_mentions_alias(text, alias) for alias in aliases)


def _mentioned_food_labels(text: str, aliases_by_food: dict[str, set[str]]) -> set[str]:
    normalized = text.lower()
    return {
        food
        for food, aliases in aliases_by_food.items()
        if _mentions_any(normalized, aliases)
    }


def _mentions_alias(text: str, alias: str) -> bool:
    normalized_alias = alias.lower().strip()
    if not normalized_alias:
        return False
    if normalized_alias.isascii() and re.fullmatch(r"[a-z0-9_]+", normalized_alias):
        return (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(normalized_alias)}(?![a-z0-9_])",
                text,
            )
            is not None
        )
    return normalized_alias in text


def _conflicts_with_cooking_condition(item_text: str, profile: dict[str, Any]) -> bool:
    cooking_condition = str(profile.get("cooking_condition") or "")
    diet_preference = str(profile.get("diet_preference") or "")
    if not any(term in item_text for term in COOKING_ACTION_TERMS):
        return False
    return any(term in cooking_condition for term in NO_KITCHEN_TERMS) or any(
        term in diet_preference for term in SIMPLE_COOKING_TERMS
    )


def _conflicts_with_sugar_sensitive_profile(
    related_foods: list[str], item_text: str, profile: dict[str, Any]
) -> bool:
    profile_text = " ".join(
        str(profile.get(key) or "") for key in ("goal", "diet_preference", "health_notes_optional")
    )
    if not any(term in profile_text for term in SUGAR_SENSITIVE_TERMS):
        return False
    if not (HIGH_SUGAR_FOODS & set(related_foods)):
        return False
    return any(term in item_text for term in EXCESS_SUGAR_TERMS)


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
