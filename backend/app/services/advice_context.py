import json
import re
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


ACTIVE_INVENTORY_STATUSES = {"available", "pending_confirm"}
SEARCH_SECTION_LIMITS = {
    "inventory": 4,
    "storage_rules": 8,
    "nutrition_facts": 4,
    "guideline_rules": 4,
    "habits": 3,
}
SEARCH_TOTAL_LIMIT = 24
QUERY_ALIASES = {
    "苹果": ["apple"],
    "香蕉": ["banana"],
    "梨": ["pear"],
    "荔枝": ["litchi", "lychee"],
    "控糖": ["sugar", "少糖", "糖"],
    "减糖": ["sugar", "少糖", "糖"],
    "库存": ["confirmed_quantity", "available", "storage_state"],
    "补买": ["shopping", "购买", "买"],
}


def build_advice_context(session: Session, query: str | None = None) -> dict[str, Any]:
    foods = session.exec(select(FoodItem).where(FoodItem.enabled == True)).all()
    inventory = session.exec(
        select(InventoryItem)
        .where(InventoryItem.status.in_(sorted(ACTIVE_INVENTORY_STATUSES)))
        .order_by(InventoryItem.id)
    ).all()
    _refresh_storage_states(session, inventory)
    session.commit()

    food_by_id = {food.id: food for food in foods}
    profile = session.get(UserProfile, 1)
    storage_rules = session.exec(select(FoodStorageRule)).all()
    nutrition_facts = session.exec(select(NutritionFact)).all()
    guideline_rules = session.exec(
        select(GuidelineRule).where(GuidelineRule.enabled == True)
    ).all()
    habits = session.exec(select(UserFoodHabit)).all()

    context: dict[str, Any] = {
        "profile": _profile_payload(profile),
        "supported_foods": [food.model_label for food in foods],
        "inventory": [_inventory_payload(item, food_by_id[item.food_item_id]) for item in inventory],
        "storage_rules": [_storage_rule_payload(rule, food_by_id[rule.food_item_id]) for rule in storage_rules],
        "nutrition_facts": [
            _nutrition_payload(fact, food_by_id[fact.food_item_id]) for fact in nutrition_facts
        ],
        "guideline_rules": [_guideline_payload(rule) for rule in guideline_rules],
        "habits": [_habit_payload(habit, food_by_id[habit.food_item_id]) for habit in habits],
    }
    context["profile_blocked_foods"] = sorted(_profile_blocked_foods(context["profile"], foods))
    context["evidence_hints"] = _evidence_hints(context)
    if query:
        results = search_evidence(context, query)
        trimmed = {
            "profile": context["profile"],
            "profile_blocked_foods": context["profile_blocked_foods"],
            "supported_foods": context["supported_foods"],
            "search_query": query,
            "search_results": results,
        }
        for section in SEARCH_SECTION_LIMITS:
            trimmed[section] = [
                result["item"] for result in results if result["section"] == section
            ]
        trimmed["evidence_hints"] = _evidence_hints(trimmed)
        return trimmed
    return context


def search_evidence(context: dict[str, Any], query: str) -> list[dict[str, Any]]:
    tokens = _query_tokens(query)
    if not tokens:
        tokens = [query.lower()]

    by_section: dict[str, list[dict[str, Any]]] = {}
    for section in ("inventory", "storage_rules", "nutrition_facts", "guideline_rules", "habits"):
        for item in context.get(section, []):
            text = json.dumps(item, ensure_ascii=False).lower()
            score = sum(1 for token in tokens if token and token in text)
            if score > 0:
                by_section.setdefault(section, []).append(
                    {"section": section, "score": score, "item": item}
                )

    candidates: list[dict[str, Any]] = []
    for section, limit in SEARCH_SECTION_LIMITS.items():
        section_candidates = by_section.get(section, [])
        section_candidates.sort(key=lambda item: item["score"], reverse=True)
        candidates.extend(section_candidates[:limit])

    candidates = _expand_food_evidence_coverage(context, query, candidates)
    candidates.sort(key=lambda item: (item["score"], -_section_order(item["section"])), reverse=True)
    return candidates[:SEARCH_TOTAL_LIMIT]


def collect_evidence_ids(context: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    for section in ("inventory", "storage_rules", "nutrition_facts", "guideline_rules", "habits"):
        for item in context.get(section, []):
            evidence_id = item.get("evidence_id")
            if evidence_id:
                evidence_ids.add(str(evidence_id))
    return evidence_ids


def _evidence_hints(context: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    profile_blocked_foods = {str(food) for food in context.get("profile_blocked_foods", [])}
    storage_by_food_location = {
        (item.get("food"), item.get("storage_location")): str(item.get("evidence_id"))
        for item in context.get("storage_rules", [])
        if item.get("food") and item.get("storage_location") and item.get("evidence_id")
    }
    nutri_by_food = {
        item.get("food"): str(item.get("evidence_id"))
        for item in context.get("nutrition_facts", [])
        if item.get("food") and item.get("evidence_id")
    }
    rules_by_type: dict[str, list[dict[str, Any]]] = {}
    for item in context.get("guideline_rules", []):
        rules_by_type.setdefault(str(item.get("rule_type")), []).append(item)

    for item in context.get("inventory", []):
        if item.get("status") != "available" or int(item.get("confirmed_quantity") or 0) <= 0:
            continue
        food = str(item.get("food"))
        if food in profile_blocked_foods:
            continue
        inventory_id = str(item.get("evidence_id"))
        storage_id = storage_by_food_location.get((food, item.get("storage_location")))
        nutri_id = nutri_by_food.get(food)
        food_rules = _rule_ids_for_food(rules_by_type, food, ("fruit_intake", "sugar_moderation"))
        shopping_rules = _rule_ids_for_food(rules_by_type, food, ("shopping_duplicate",))

        eat_first_ids = _compact_ids([inventory_id, storage_id, nutri_id, *food_rules])
        if item.get("storage_state") in {"fresh", "eat_soon"} and storage_id and (
            nutri_id or food_rules
        ):
            hints.append(
                {
                    "food": food,
                    "action_type": "eat_first",
                    "use_evidence_ids": eat_first_ids,
                    "instruction": (
                        "吃已有库存时使用这组证据。必须同时有库存或保存证据，并且有营养或规则证据。"
                    ),
                }
            )

        duplicate_ids = _compact_ids([inventory_id, *shopping_rules])
        if duplicate_ids:
            hints.append(
                {
                    "food": food,
                    "action_type": "avoid_duplicate_purchase",
                    "use_evidence_ids": duplicate_ids,
                    "instruction": (
                        "该食物已有库存。禁止建议购买、补买或再买。购物相关内容只能写 avoid_duplicate_purchase。"
                    ),
                }
            )
    return hints


def _rule_ids_for_food(
    rules_by_type: dict[str, list[dict[str, Any]]],
    food: str,
    rule_types: tuple[str, ...],
) -> list[str]:
    ids: list[str] = []
    for rule_type in rule_types:
        for rule in rules_by_type.get(rule_type, []):
            if food in {str(value) for value in rule.get("applies_to", [])}:
                ids.append(str(rule.get("evidence_id")))
    return ids


def _compact_ids(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _profile_payload(profile: UserProfile | None) -> dict[str, Any]:
    if profile is None:
        return {}
    return {
        "goal": profile.goal,
        "diet_preference": profile.diet_preference,
        "cooking_condition": profile.cooking_condition,
        "avoid_foods": _loads(profile.avoid_foods, []),
        "allergies_optional": profile.allergies_optional,
        "health_notes_optional": profile.health_notes_optional,
    }


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


def _food_aliases(food: FoodItem) -> set[str]:
    aliases = {food.model_label.lower(), food.display_name.lower()}
    try:
        aliases.update(str(alias).lower() for alias in json.loads(food.aliases))
    except json.JSONDecodeError:
        pass
    return aliases


def _mentions_any(text: str, aliases: set[str]) -> bool:
    return any(_mentions_alias(text, alias) for alias in aliases)


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


def _inventory_payload(item: InventoryItem, food: FoodItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "food": food.model_label,
        "display_name": food.display_name,
        "confirmed_quantity": item.confirmed_quantity,
        "detected_quantity": item.detected_quantity,
        "status": item.status,
        "storage_location": item.storage_location,
        "storage_state": item.storage_state,
        "days_stored": item.days_stored,
        "safe_days": item.safe_days,
        "remaining_days": item.remaining_days,
        "eat_priority_rank": item.eat_priority_rank,
        "pending_change_type": item.pending_change_type,
    }


def _storage_rule_payload(rule: FoodStorageRule, food: FoodItem) -> dict[str, Any]:
    return {
        "evidence_id": rule.evidence_id,
        "food": food.model_label,
        "storage_location": rule.storage_location,
        "safe_days": rule.safe_days,
        "source_text": rule.source_text,
        "source_product_id": rule.source_product_id,
    }


def _nutrition_payload(fact: NutritionFact, food: FoodItem) -> dict[str, Any]:
    return {
        "evidence_id": fact.evidence_id,
        "food": food.model_label,
        "serving_size_text": fact.serving_size_text,
        "calories": fact.calories,
        "carbs_g": fact.carbs_g,
        "sugars_g": fact.sugars_g,
        "fiber_g": fact.fiber_g,
        "protein_g": fact.protein_g,
        "fat_g": fact.fat_g,
        "fdc_id": fact.fdc_id,
        "source_url": fact.source_url,
    }


def _guideline_payload(rule: GuidelineRule) -> dict[str, Any]:
    return {
        "evidence_id": rule.evidence_id,
        "source_name": rule.source_name,
        "source_url": rule.source_url,
        "rule_type": rule.rule_type,
        "applies_to": _loads(rule.applies_to_json, []),
        "tags": _loads(rule.tags_json, []),
        "condition": _loads(rule.condition_json, {}),
        "recommendation_template": rule.recommendation_template,
        "evidence_summary": rule.evidence_summary,
    }


def _habit_payload(habit: UserFoodHabit, food: FoodItem) -> dict[str, Any]:
    return {
        "evidence_id": habit.evidence_id,
        "food": food.model_label,
        "habit_type": habit.habit_type,
        "score": habit.score,
        "evidence": _loads(habit.evidence_json, {}),
    }


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _query_tokens(query: str) -> list[str]:
    normalized = query.lower().replace("，", " ").replace("、", " ")
    tokens = [token for token in re.split(r"\s+", normalized) if token]
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]+", normalized)
    for chunk in cjk_chunks:
        tokens.append(chunk)
        if len(chunk) > 1:
            tokens.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
    for key, aliases in QUERY_ALIASES.items():
        if key in query:
            tokens.extend(aliases)
    return list(dict.fromkeys(tokens))


def _expand_food_evidence_coverage(
    context: dict[str, Any],
    query: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    foods = _query_food_labels(context, query)
    if not foods:
        return candidates

    expanded = list(candidates)
    section_counts: dict[str, int] = {}
    for candidate in expanded:
        section_counts[candidate["section"]] = section_counts.get(candidate["section"], 0) + 1

    current_storage_pairs = {
        (item.get("food"), item.get("storage_location"))
        for item in context.get("inventory", [])
        if item.get("food") in foods and item.get("storage_location")
    }
    for item in context.get("storage_rules", []):
        pair = (item.get("food"), item.get("storage_location"))
        if pair in current_storage_pairs and _append_candidate(
            expanded, "storage_rules", 95, item
        ):
            section_counts["storage_rules"] = section_counts.get("storage_rules", 0) + 1

    for section, score in (
        ("inventory", 80),
        ("storage_rules", 70),
        ("nutrition_facts", 70),
        ("guideline_rules", 60),
    ):
        limit = SEARCH_SECTION_LIMITS[section]
        for item in context.get(section, []):
            if section_counts.get(section, 0) >= limit:
                break
            if item.get("food") in foods or _rule_applies_to_food(item, foods):
                if section == "guideline_rules" and not _rule_should_expand_for_query(item, query):
                    continue
                if _append_candidate(expanded, section, score, item):
                    section_counts[section] = section_counts.get(section, 0) + 1

    return expanded


def _query_food_labels(context: dict[str, Any], query: str) -> set[str]:
    normalized = query.lower()
    tokens = set(_query_tokens(query))
    display_names = {
        item.get("food"): str(item.get("display_name", "")).lower()
        for item in context.get("inventory", [])
    }
    labels: set[str] = set()
    for food in context.get("supported_foods", []):
        label = str(food)
        if label.lower() in normalized or label.lower() in tokens:
            labels.add(label)
        if display_names.get(label) and display_names[label] in normalized:
            labels.add(label)
    return labels


def _rule_applies_to_food(rule: dict[str, Any], foods: set[str]) -> bool:
    applies_to = {str(food) for food in rule.get("applies_to", [])}
    return bool(applies_to & foods)


def _rule_matches_query(rule: dict[str, Any], query: str) -> bool:
    text = json.dumps(rule, ensure_ascii=False).lower()
    return any(token and token in text for token in _query_tokens(query))


def _rule_should_expand_for_query(rule: dict[str, Any], query: str) -> bool:
    if _rule_matches_query(rule, query):
        return True
    rule_type = str(rule.get("rule_type") or "")
    if rule_type in {"fruit_intake", "diversity"}:
        return True
    if rule_type == "sugar_moderation":
        return any(term in query for term in ("控糖", "少糖", "减糖", "糖"))
    if rule_type == "shopping_duplicate":
        return any(term in query for term in ("买", "购买", "补买", "补货", "购物"))
    return False


def _append_candidate(
    candidates: list[dict[str, Any]],
    section: str,
    score: int,
    item: dict[str, Any],
) -> bool:
    evidence_id = item.get("evidence_id")
    for candidate in candidates:
        candidate_item = candidate["item"]
        if evidence_id and candidate_item.get("evidence_id") == evidence_id:
            candidate["score"] = max(candidate["score"], score)
            return False
        if candidate_item is item:
            candidate["score"] = max(candidate["score"], score)
            return False
    candidates.append({"section": section, "score": score, "item": item})
    return True


def _section_order(section: str) -> int:
    order = {
        "inventory": 0,
        "storage_rules": 1,
        "nutrition_facts": 2,
        "guideline_rules": 3,
        "habits": 4,
    }
    return order.get(section, 99)
