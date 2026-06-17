import json
from typing import Any

from sqlmodel import Session, select

from app.models import (
    FoodItem,
    FoodStorageRule,
    GuidelineRule,
    InventoryItem,
    NutritionFact,
    UserFoodHabit,
    UserProfile,
)
from app.routers.inventory import _refresh_storage_states
from app.services.llm_client import LlmClientError, request_chat_completion


SUPPORTED_FOODS = ["apple", "banana", "pear", "litchi"]
STORAGE_STATES = ["fresh", "eat_soon", "check_required", "not_recommended"]
STORAGE_LOCATIONS = ["pantry", "refrigerate", "freeze"]
RULE_TYPES = [
    "fruit_intake",
    "sugar_moderation",
    "diversity",
    "shopping_duplicate",
    "medical_boundary",
]

MAX_TOOL_CALLS_PER_REQUEST = 1


AGENT_SYSTEM_PROMPT = """你是一个水果库存与膳食建议 agent。

工作方式：
1. 你会收到 get_advice_context 工具结果，只能基于这份工具结果回答。
2. 不要凭记忆编库存、保存期、营养或规则。
3. 食用建议只能推荐 storage_state 为 fresh 或 eat_soon 的具体库存批次。
4. 每条建议必须引用工具返回的 evidence_ids。
5. 不判断腐败，不说“坏了”“还能吃”“不能吃”，不做医疗诊断，不写数据库。
6. 用户问“今天吃什么”时，最多输出 3 条建议，只写食用相关建议，不写购物建议。
7. 每条 content 控制在 45 个中文字符左右，basis 最多 2 条，evidence_ids 最多 4 个。
8. 不要输出 evidence_sources，后端会自动补。

最终输出必须是 JSON 对象，结构如下：
{
  "summary": "一句话摘要",
  "recommendations": [
    {
      "title": "短标题",
      "content": "具体建议",
      "action_type": "eat_first | check_food | avoid_duplicate_purchase | portion_control | variety | general",
      "related_foods": ["banana"],
      "basis": ["依据说明"],
      "evidence_ids": ["inventory_1", "storage_banana_251_refrigerate"],
      "confidence": "low | medium | high"
    }
  ]
}
"""


ADVICE_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_advice_context",
            "description": "Get the compact task context needed for fruit inventory and diet advice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "purpose": {
                        "type": "string",
                        "enum": ["eating", "shopping", "general"],
                        "description": "The user's main intent.",
                    },
                    "query": {
                        "type": "string",
                        "description": "The original user question or search query.",
                    },
                },
                "required": ["purpose", "query"],
                "additionalProperties": False,
            },
        },
    },
]


def request_agent_advice_json(
    *,
    session: Session,
    question: str | None,
    search_query: str | None = None,
    enable_thinking: bool,
    validation_errors: list[str] | None = None,
) -> dict[str, Any]:
    query = search_query or question or "请根据当前库存生成水果建议。"
    context = _tool_get_advice_context(
        session,
        {"purpose": _infer_purpose(query), "query": query},
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _agent_user_prompt(
                question,
                search_query,
                validation_errors,
                context,
            ),
        },
    ]
    data = request_chat_completion(
        messages=messages,
        enable_thinking=enable_thinking,
        response_format={"type": "json_object"},
    )
    return _parse_final_json(_first_message(data).get("content"))


def execute_advice_tool(session: Session, call: dict[str, Any]) -> dict[str, Any]:
    try:
        name = call["function"]["name"]
        arguments = json.loads(call["function"].get("arguments") or "{}")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"error": f"invalid tool call: {exc}"}

    handlers = {
        "get_advice_context": _tool_get_advice_context,
        "list_inventory_batches": _tool_list_inventory_batches,
        "get_storage_rules": _tool_get_storage_rules,
        "get_nutrition_facts": _tool_get_nutrition_facts,
        "get_guideline_rules": _tool_get_guideline_rules,
        "get_user_profile": _tool_get_user_profile,
        "get_user_habits": _tool_get_user_habits,
    }
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"unknown tool: {name}"}
    return handler(session, arguments)


def _agent_user_prompt(
    question: str | None,
    search_query: str | None,
    validation_errors: list[str] | None,
    context: dict[str, Any],
) -> str:
    payload: dict[str, Any] = {
        "user_question": question or "请根据当前库存生成水果建议。",
        "supported_foods": SUPPORTED_FOODS,
        "tool_result": {
            "name": "get_advice_context",
            "content": context,
        },
    }
    if search_query:
        payload["optional_search_context"] = search_query
    if validation_errors:
        payload["previous_validation_errors"] = validation_errors
    return json.dumps(payload, ensure_ascii=False)


def _first_message(data: dict[str, Any]) -> dict[str, Any]:
    try:
        return data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmClientError("LLM response missing choices[0].message.") from exc


def _assistant_tool_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls") or [],
    }


def _parse_final_json(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or not content.strip():
        raise LlmClientError("LLM response missing final JSON content.")
    content = _strip_code_fence(content.strip())
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise LlmClientError("LLM response is not valid JSON.") from exc


def _strip_code_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return content


def _tool_get_advice_context(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or "")
    purpose = str(arguments.get("purpose") or "general")
    is_shopping = purpose == "shopping" or _looks_like_shopping_query(query)
    is_eating = purpose == "eating" or _looks_like_eating_query(query)
    foods = _food_map(session)
    items = session.exec(select(InventoryItem).order_by(InventoryItem.id)).all()
    _refresh_storage_states(session, items)
    session.commit()

    available_batches = [
        item
        for item in items
        if item.status == "available" and item.confirmed_quantity > 0
    ]
    edible_batches = [
        item for item in available_batches if item.storage_state in {"fresh", "eat_soon"}
    ]
    edible_batches.sort(
        key=lambda item: (
            0 if item.storage_state == "eat_soon" else 1,
            item.remaining_days if item.remaining_days is not None else 9999,
            -item.confirmed_quantity,
        )
    )
    check_required_batches = [
        item
        for item in available_batches
        if item.storage_state in {"check_required", "not_recommended"}
    ]

    target_batches = edible_batches if is_eating or not is_shopping else available_batches
    relevant_foods = {
        foods[item.food_item_id].model_label
        for item in [*target_batches[:4], *check_required_batches]
        if item.food_item_id in foods
    }
    relevant_foods.update(_mentioned_foods(query, foods.values()))
    if not relevant_foods:
        relevant_foods = {food.model_label for food in foods.values()}

    current_locations = {
        (foods[item.food_item_id].model_label, item.storage_location)
        for item in available_batches
        if item.food_item_id in foods and foods[item.food_item_id].model_label in relevant_foods
    }
    rule_types = {"fruit_intake", "diversity", "sugar_moderation", "medical_boundary"}
    if is_shopping:
        rule_types.add("shopping_duplicate")

    profile = _tool_get_user_profile(session, {})["profile"]
    if is_eating and not is_shopping:
        return _eating_context_payload(
            session,
            query,
            profile,
            foods,
            edible_batches[:3],
            check_required_batches,
        )

    context = {
        "purpose": purpose,
        "query": query,
        "profile": profile,
        "supported_foods": SUPPORTED_FOODS,
        "edible_batches": [
            _inventory_item_payload(item, foods[item.food_item_id])
            for item in edible_batches[:4]
            if item.food_item_id in foods
        ],
        "not_for_eating_batches": [
            _inventory_item_payload(item, foods[item.food_item_id])
            for item in check_required_batches
            if item.food_item_id in foods
        ],
        "storage_rules": [
            rule
            for rule in _tool_get_storage_rules(
                session,
                {"foods": sorted(relevant_foods)},
            )["storage_rules"]
            if (rule["food"], rule["storage_location"]) in current_locations
        ],
        "nutrition_facts": _tool_get_nutrition_facts(
            session,
            {"foods": sorted(relevant_foods)},
        )["nutrition_facts"],
        "guideline_rules": _tool_get_guideline_rules(
            session,
            {"foods": sorted(relevant_foods), "rule_types": sorted(rule_types)},
        )["guideline_rules"],
        "instructions": [
            "推荐食用时只能使用 edible_batches 里的具体 evidence_id。",
            "not_for_eating_batches 只能作为约束或提醒，不要推荐食用。",
            "今天吃什么最多输出 3 条食用建议，不要输出购物建议。",
            "每条建议至少引用库存 evidence_id，并尽量引用保存、营养或规则 evidence_id。",
        ],
    }
    if is_shopping:
        context["stocked_batches"] = [
            _inventory_item_payload(item, foods[item.food_item_id])
            for item in available_batches
            if item.food_item_id in foods
        ]
        context["habits"] = _tool_get_user_habits(session, {"foods": sorted(relevant_foods)})["habits"]
    return context


def _eating_context_payload(
    session: Session,
    query: str,
    profile: dict[str, Any],
    foods: dict[int, FoodItem],
    edible_batches: list[InventoryItem],
    check_required_batches: list[InventoryItem],
) -> dict[str, Any]:
    storage_rules = _tool_get_storage_rules(session, {})["storage_rules"]
    storage_by_pair = {
        (rule["food"], rule["storage_location"]): rule
        for rule in storage_rules
    }
    nutrition_by_food = {
        fact["food"]: fact
        for fact in _tool_get_nutrition_facts(session, {})["nutrition_facts"]
    }
    guideline_rules = _tool_get_guideline_rules(
        session,
        {"rule_types": ["fruit_intake", "sugar_moderation", "diversity", "medical_boundary"]},
    )["guideline_rules"]
    rule_ids_by_type: dict[str, list[str]] = {}
    for rule in guideline_rules:
        rule_ids_by_type.setdefault(rule["rule_type"], []).append(rule["evidence_id"])

    candidates = []
    for item in edible_batches:
        food = foods.get(item.food_item_id)
        if food is None:
            continue
        storage = storage_by_pair.get((food.model_label, item.storage_location))
        nutrition = nutrition_by_food.get(food.model_label)
        evidence_ids = _compact_ids(
            [
                item.evidence_id,
                storage.get("evidence_id") if storage else None,
                nutrition.get("evidence_id") if nutrition else None,
                *rule_ids_by_type.get("fruit_intake", [])[:1],
            ]
        )[:4]
        candidates.append(
            {
                "food": food.model_label,
                "display_name": food.display_name,
                "batch": _inventory_item_payload(item, food),
                "storage_note": storage.get("source_text") if storage else None,
                "nutrition_note": _nutrition_note(nutrition),
                "use_evidence_ids": evidence_ids,
                "reason": _eating_reason(item, food),
            }
        )

    return {
        "purpose": "eating",
        "query": query,
        "profile": profile,
        "eating_candidates": candidates,
        "not_for_eating_batches": [
            {
                "evidence_id": item.evidence_id,
                "food": foods[item.food_item_id].model_label,
                "display_name": foods[item.food_item_id].display_name,
                "storage_state": item.storage_state,
            }
            for item in check_required_batches
            if item.food_item_id in foods
        ],
        "rules": {
            "max_recommendations": 3,
            "allowed_action_types": ["eat_first", "portion_control", "variety"],
            "avoid_action_types": ["avoid_duplicate_purchase"],
            "evidence_ids": "每条建议只从对应 candidate.use_evidence_ids 里选 2-4 个。",
            "style": "短句，不要展开来源，不要输出 evidence_sources。",
        },
    }


def _tool_list_inventory_batches(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    foods = _food_map(session)
    labels = _normalize_filter(arguments.get("foods"))
    states = _normalize_filter(arguments.get("storage_states"))
    status = str(arguments.get("status") or "available")
    items = session.exec(select(InventoryItem).order_by(InventoryItem.id)).all()
    _refresh_storage_states(session, items)
    session.commit()

    batches = []
    for item in items:
        food = foods.get(item.food_item_id)
        if food is None:
            continue
        if status != "all" and item.status != status:
            continue
        if labels and food.model_label not in labels:
            continue
        if states and item.storage_state not in states:
            continue
        batches.append(
            {
                "evidence_id": item.evidence_id,
                "food": food.model_label,
                "display_name": food.display_name,
                "confirmed_quantity": item.confirmed_quantity,
                "unit": item.unit,
                "status": item.status,
                "storage_location": item.storage_location,
                "storage_state": item.storage_state,
                "days_stored": item.days_stored,
                "safe_days": item.safe_days,
                "remaining_days": item.remaining_days,
                "eat_priority_rank": item.eat_priority_rank,
            }
        )
    return {"batches": batches}


def _tool_get_storage_rules(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    foods = _food_map(session)
    labels = _normalize_filter(arguments.get("foods"))
    locations = _normalize_filter(arguments.get("storage_locations"))
    rules = []
    for rule in session.exec(select(FoodStorageRule).order_by(FoodStorageRule.id)).all():
        food = foods.get(rule.food_item_id)
        if food is None:
            continue
        if labels and food.model_label not in labels:
            continue
        if locations and rule.storage_location not in locations:
            continue
        rules.append(
            {
                "evidence_id": rule.evidence_id,
                "food": food.model_label,
                "storage_location": rule.storage_location,
                "safe_days": rule.safe_days,
                "source_text": rule.source_text,
            }
        )
    return {"storage_rules": rules}


def _tool_get_nutrition_facts(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    foods = _food_map(session)
    labels = _normalize_filter(arguments.get("foods"))
    facts = []
    for fact in session.exec(select(NutritionFact).order_by(NutritionFact.id)).all():
        food = foods.get(fact.food_item_id)
        if food is None:
            continue
        if labels and food.model_label not in labels:
            continue
        facts.append(
            {
                "evidence_id": fact.evidence_id,
                "food": food.model_label,
                "serving_size_text": fact.serving_size_text,
                "calories": fact.calories,
                "carbs_g": fact.carbs_g,
                "sugars_g": fact.sugars_g,
                "fiber_g": fact.fiber_g,
                "protein_g": fact.protein_g,
                "fat_g": fact.fat_g,
            }
        )
    return {"nutrition_facts": facts}


def _tool_get_guideline_rules(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    rule_types = _normalize_filter(arguments.get("rule_types"))
    labels = _normalize_filter(arguments.get("foods"))
    rules = []
    query = select(GuidelineRule).where(GuidelineRule.enabled == True).order_by(GuidelineRule.id)
    for rule in session.exec(query).all():
        applies_to = _loads(rule.applies_to_json, [])
        if rule_types and rule.rule_type not in rule_types:
            continue
        if labels and applies_to and not (set(applies_to) & labels):
            continue
        rules.append(
            {
                "evidence_id": rule.evidence_id,
                "source_name": rule.source_name,
                "rule_type": rule.rule_type,
                "applies_to": applies_to,
                "condition": _loads(rule.condition_json, {}),
                "recommendation_template": rule.recommendation_template,
                "evidence_summary": rule.evidence_summary,
            }
        )
    return {"guideline_rules": rules}


def _tool_get_user_profile(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    del arguments
    profile = session.get(UserProfile, 1)
    if profile is None:
        return {"profile": {}}
    return {
        "profile": {
            "goal": profile.goal,
            "diet_preference": profile.diet_preference,
            "cooking_condition": profile.cooking_condition,
            "avoid_foods": _loads(profile.avoid_foods, []),
            "allergies_optional": profile.allergies_optional,
            "health_notes_optional": profile.health_notes_optional,
        }
    }


def _tool_get_user_habits(session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
    foods = _food_map(session)
    labels = _normalize_filter(arguments.get("foods"))
    habit_types = _normalize_filter(arguments.get("habit_types"))
    habits = []
    for habit in session.exec(select(UserFoodHabit).order_by(UserFoodHabit.id)).all():
        food = foods.get(habit.food_item_id)
        if food is None:
            continue
        if labels and food.model_label not in labels:
            continue
        if habit_types and habit.habit_type not in habit_types:
            continue
        habits.append(
            {
                "evidence_id": habit.evidence_id,
                "food": food.model_label,
                "habit_type": habit.habit_type,
                "score": habit.score,
                "evidence": _loads(habit.evidence_json, {}),
            }
        )
    return {"habits": habits}


def _inventory_item_payload(item: InventoryItem, food: FoodItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "food": food.model_label,
        "display_name": food.display_name,
        "confirmed_quantity": item.confirmed_quantity,
        "unit": item.unit,
        "status": item.status,
        "storage_location": item.storage_location,
        "storage_state": item.storage_state,
        "days_stored": item.days_stored,
        "safe_days": item.safe_days,
        "remaining_days": item.remaining_days,
        "eat_priority_rank": item.eat_priority_rank,
    }


def _nutrition_note(nutrition: dict[str, Any] | None) -> str | None:
    if nutrition is None:
        return None
    parts = []
    if nutrition.get("sugars_g") is not None:
        parts.append(f"sugars_g={nutrition['sugars_g']}")
    if nutrition.get("fiber_g") is not None:
        parts.append(f"fiber_g={nutrition['fiber_g']}")
    if nutrition.get("calories") is not None:
        parts.append(f"calories={nutrition['calories']}")
    return ", ".join(parts) if parts else None


def _eating_reason(item: InventoryItem, food: FoodItem) -> str:
    if item.storage_state == "eat_soon":
        return f"{food.display_name}处于 eat_soon，剩余 {item.remaining_days} 天。"
    return f"{food.display_name}处于 fresh，可作为搭配。"


def _compact_ids(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _mentioned_foods(query: str, foods: Any) -> set[str]:
    normalized = query.lower()
    mentioned: set[str] = set()
    for food in foods:
        aliases = {food.model_label.lower(), food.display_name.lower()}
        try:
            aliases.update(str(alias).lower() for alias in json.loads(food.aliases))
        except json.JSONDecodeError:
            pass
        if any(alias and alias in normalized for alias in aliases):
            mentioned.add(food.model_label)
    return mentioned


def _infer_purpose(query: str) -> str:
    if _looks_like_shopping_query(query):
        return "shopping"
    if _looks_like_eating_query(query):
        return "eating"
    return "general"


def _looks_like_eating_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        term in normalized
        for term in ("今天", "吃", "食用", "早餐", "午餐", "晚餐", "加餐", "eat", "snack")
    )


def _looks_like_shopping_query(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in ("买", "购买", "补买", "补货", "购物", "buy", "purchase"))


def _food_map(session: Session) -> dict[int, FoodItem]:
    return {food.id or 0: food for food in session.exec(select(FoodItem)).all()}


def _normalize_filter(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        return {values}
    if isinstance(values, list):
        return {str(value) for value in values}
    return set()


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
