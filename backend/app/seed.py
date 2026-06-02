import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.config import settings
from app.models import (
    FoodItem,
    FoodStorageRule,
    GuidelineRule,
    NutritionFact,
    NutritionReference,
    UserProfile,
    utc_now,
)


SUPPORTED_FOODS = [
    {
        "model_label": "apple",
        "display_name": "苹果",
        "foodkeeper_product_id": 248,
        "aliases": ["apple", "apples", "苹果"],
    },
    {
        "model_label": "banana",
        "display_name": "香蕉",
        "foodkeeper_product_id": 251,
        "aliases": ["banana", "bananas", "香蕉"],
    },
    {
        "model_label": "pear",
        "display_name": "梨",
        "foodkeeper_product_id": 266,
        "aliases": ["pear", "pears", "梨"],
    },
    {
        "model_label": "litchi",
        "display_name": "荔枝",
        "foodkeeper_product_id": 252,
        "aliases": ["litchi", "lychee", "荔枝"],
    },
]

TARGET_PRODUCT_IDS = {food["foodkeeper_product_id"] for food in SUPPORTED_FOODS}

MANUAL_WHEN_RIPE_SAFE_DAYS = {
    ("banana", "pantry"): 2,
    ("pear", "pantry"): 1,
}

NUTRITION_FACTS = {
    "apple": {
        "fdc_id": 171688,
        "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/171688/nutrients",
        "calories": 52,
        "carbs_g": 13.8,
        "sugars_g": 10.4,
        "fiber_g": 2.4,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "key_nutrients": ["fiber", "vitamin C", "potassium"],
    },
    "banana": {
        "fdc_id": 173944,
        "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/173944/nutrients",
        "calories": 89,
        "carbs_g": 22.8,
        "sugars_g": 12.2,
        "fiber_g": 2.6,
        "protein_g": 1.1,
        "fat_g": 0.3,
        "key_nutrients": ["potassium", "vitamin B6", "fiber"],
    },
    "pear": {
        "fdc_id": 169118,
        "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/169118/nutrients",
        "calories": 57,
        "carbs_g": 15.2,
        "sugars_g": 9.8,
        "fiber_g": 3.1,
        "protein_g": 0.4,
        "fat_g": 0.1,
        "key_nutrients": ["fiber", "vitamin C", "potassium"],
    },
    "litchi": {
        "fdc_id": 169086,
        "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/169086/nutrients",
        "calories": 66,
        "carbs_g": 16.5,
        "sugars_g": 15.2,
        "fiber_g": 1.3,
        "protein_g": 0.8,
        "fat_g": 0.4,
        "key_nutrients": ["vitamin C", "potassium", "copper"],
    },
}

GUIDELINE_RULES = [
    {
        "evidence_id": "rule_fruit_moderation_001",
        "source_name": "Chinese Dietary Guidelines 2022",
        "source_url": "https://dg.cnsoc.org/",
        "rule_type": "fruit_intake",
        "applies_to": ["apple", "banana", "pear", "litchi"],
        "tags": ["fruit", "moderation", "daily_intake"],
        "condition": {"user_goal_any": ["健康饮食", "减脂", "减少浪费"]},
        "recommendation_template": "建议适量食用水果，并保持总量合适。",
        "evidence_summary": "膳食指南建议日常饮食包含水果，但应注意适量。",
    },
    {
        "evidence_id": "rule_diversity_001",
        "source_name": "USDA MyPlate",
        "source_url": "https://www.myplate.gov/eat-healthy/fruits",
        "rule_type": "diversity",
        "applies_to": ["apple", "banana", "pear", "litchi"],
        "tags": ["fruit", "diversity"],
        "condition": {"inventory_food_any": ["apple", "banana", "pear", "litchi"]},
        "recommendation_template": "水果可以轮换吃，避免长期只吃一种。",
        "evidence_summary": "MyPlate 建议在水果选择上保持多样化。",
    },
    {
        "evidence_id": "rule_whole_fruit_001",
        "source_name": "WHO Healthy diet",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "rule_type": "fruit_intake",
        "applies_to": ["apple", "banana", "pear", "litchi"],
        "tags": ["fruit", "whole_fruit", "juice"],
        "condition": {
            "user_goal_any": ["健康饮食", "减脂"],
            "diet_preference_any": ["少糖", "reduce_sugar"],
        },
        "recommendation_template": "优先吃完整水果，不用果汁替代完整水果。",
        "evidence_summary": "健康饮食建议包含水果和蔬菜，并限制游离糖摄入。",
    },
    {
        "evidence_id": "rule_sugar_moderation_001",
        "source_name": "WHO Healthy diet",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "rule_type": "sugar_moderation",
        "applies_to": ["banana", "litchi"],
        "tags": ["fruit", "sugar", "fat_loss"],
        "condition": {
            "user_goal_any": ["减脂"],
            "diet_preference_any": ["少糖", "reduce_sugar"],
        },
        "recommendation_template": "少糖或减脂目标下，香蕉、荔枝这类较甜水果建议适量。",
        "evidence_summary": "健康饮食建议减少糖摄入；较甜水果应控制份量。",
    },
    {
        "evidence_id": "rule_shopping_duplicate_001",
        "source_name": "Fruit Health MVP Plan",
        "source_url": "internal://fruit-health-product-plan#shopping_duplicate",
        "rule_type": "shopping_duplicate",
        "applies_to": ["apple", "banana", "pear", "litchi"],
        "tags": ["shopping", "inventory"],
        "condition": {"inventory_status_any": ["available"]},
        "recommendation_template": "库存充足时，不建议重复购买同类水果。",
        "evidence_summary": "业务规则要求购物建议引用库存依据，避免重复购买。",
    },
    {
        "evidence_id": "rule_medical_boundary_001",
        "source_name": "Fruit Health MVP Plan",
        "source_url": "internal://fruit-health-product-plan#medical_boundary",
        "rule_type": "medical_boundary",
        "applies_to": ["apple", "banana", "pear", "litchi"],
        "tags": ["medical_boundary", "safety"],
        "condition": {},
        "recommendation_template": "系统只提供饮食参考，不做医疗诊断。",
        "evidence_summary": "MVP 边界要求不替代医生或营养师。",
    },
]


def seed_reference_data(session: Session) -> None:
    foods = _seed_food_items(session)
    products = _load_target_foodkeeper_products()
    _seed_storage_rules(session, foods, products)
    reference = _seed_nutrition_reference(session)
    _seed_nutrition_facts(session, foods, reference)
    _seed_guideline_rules(session)
    _seed_default_profile(session)
    session.commit()


def _seed_food_items(session: Session) -> dict[str, FoodItem]:
    foods: dict[str, FoodItem] = {}
    for data in SUPPORTED_FOODS:
        food = session.exec(
            select(FoodItem).where(FoodItem.model_label == data["model_label"])
        ).first()
        if food is None:
            food = FoodItem()

        food.model_label = str(data["model_label"])
        food.display_name = str(data["display_name"])
        food.foodkeeper_product_id = int(data["foodkeeper_product_id"])
        food.aliases = json.dumps(data["aliases"], ensure_ascii=False)
        food.enabled = True
        session.add(food)
        foods[food.model_label] = food

    session.flush()
    return foods


def _seed_storage_rules(
    session: Session, foods: dict[str, FoodItem], products: dict[int, dict[str, Any]]
) -> None:
    for data in SUPPORTED_FOODS:
        label = str(data["model_label"])
        product_id = int(data["foodkeeper_product_id"])
        product = products[product_id]
        food = foods[label]

        for location in ("pantry", "refrigerate", "freeze"):
            rule_data = _build_storage_rule(label, location, product)
            if rule_data is None:
                continue

            evidence_id = f"storage_{label}_{product_id}_{location}"
            rule = session.exec(
                select(FoodStorageRule).where(FoodStorageRule.evidence_id == evidence_id)
            ).first()
            if rule is None:
                rule = FoodStorageRule(evidence_id=evidence_id, food_item_id=food.id or 0)

            rule.food_item_id = food.id or 0
            rule.source_product_id = product_id
            rule.storage_location = location
            rule.safe_days = rule_data["safe_days"]
            rule.source_min_value = rule_data["source_min_value"]
            rule.source_max_value = rule_data["source_max_value"]
            rule.source_metric = rule_data["source_metric"]
            rule.source_text = rule_data["source_text"]
            rule.pantry_text = _storage_text(product, "pantry", label)
            rule.refrigerate_text = _storage_text(product, "refrigerate", label)
            rule.freeze_text = _storage_text(product, "freeze", label)
            rule.tips = rule_data["tips"]
            rule.raw_json = json.dumps(product, ensure_ascii=False, default=str)
            session.add(rule)


def _seed_nutrition_reference(session: Session) -> NutritionReference:
    source_name = "USDA FoodData Central"
    reference = session.exec(
        select(NutritionReference).where(NutritionReference.source_name == source_name)
    ).first()
    if reference is None:
        reference = NutritionReference(source_name=source_name)

    reference.source_url = "https://fdc.nal.usda.gov/"
    reference.version = "MVP seed with exact FDC food IDs"
    session.add(reference)
    session.flush()
    return reference


def _seed_nutrition_facts(
    session: Session, foods: dict[str, FoodItem], reference: NutritionReference
) -> None:
    for label, data in NUTRITION_FACTS.items():
        evidence_id = f"nutri_{label}_usda"
        fact = session.exec(
            select(NutritionFact).where(NutritionFact.evidence_id == evidence_id)
        ).first()
        if fact is None:
            fact = NutritionFact(
                evidence_id=evidence_id,
                food_item_id=foods[label].id or 0,
                reference_id=reference.id or 0,
                serving_size_text="100 g edible portion",
            )

        fact.food_item_id = foods[label].id or 0
        fact.reference_id = reference.id or 0
        fact.fdc_id = int(data["fdc_id"])
        fact.source_url = str(data["source_url"])
        fact.serving_size_text = "100 g edible portion"
        fact.calories = data["calories"]
        fact.carbs_g = data["carbs_g"]
        fact.sugars_g = data["sugars_g"]
        fact.fiber_g = data["fiber_g"]
        fact.protein_g = data["protein_g"]
        fact.fat_g = data["fat_g"]
        fact.key_nutrients_json = json.dumps(data["key_nutrients"], ensure_ascii=False)
        fact.notes = "Values are per 100 g edible portion from the linked USDA FoodData Central record."
        session.add(fact)


def _seed_guideline_rules(session: Session) -> None:
    for data in GUIDELINE_RULES:
        rule = session.exec(
            select(GuidelineRule).where(GuidelineRule.evidence_id == data["evidence_id"])
        ).first()
        if rule is None:
            rule = GuidelineRule(evidence_id=data["evidence_id"])

        rule.source_name = data["source_name"]
        rule.source_url = data["source_url"]
        rule.rule_type = data["rule_type"]
        rule.applies_to_json = json.dumps(data["applies_to"], ensure_ascii=False)
        rule.tags_json = json.dumps(data["tags"], ensure_ascii=False)
        rule.condition_json = json.dumps(data["condition"], ensure_ascii=False)
        rule.recommendation_template = data["recommendation_template"]
        rule.evidence_summary = data["evidence_summary"]
        rule.enabled = True
        session.add(rule)


def _seed_default_profile(session: Session) -> None:
    profile = session.get(UserProfile, 1)
    if profile is not None:
        return

    session.add(
        UserProfile(
            id=1,
            goal="健康饮食",
            diet_preference="简单烹饪",
            cooking_condition="家庭",
            avoid_foods="[]",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )


def _build_storage_rule(
    label: str, location: str, product: dict[str, Any]
) -> dict[str, Any] | None:
    prefix = {
        "pantry": "Pantry",
        "refrigerate": "Refrigerate",
        "freeze": "Freeze",
    }[location]

    min_value = product.get(f"{prefix}_Min")
    max_value = product.get(f"{prefix}_Max")
    metric = product.get(f"{prefix}_Metric")
    tips = product.get(f"{prefix}_tips") or product.get(f"{prefix}_Tips")

    if metric is None and location in {"pantry", "refrigerate", "freeze"}:
        dop_prefix = f"DOP_{prefix}"
        min_value = product.get(f"{dop_prefix}_Min")
        max_value = product.get(f"{dop_prefix}_Max")
        metric = product.get(f"{dop_prefix}_Metric")
        tips = tips or product.get(f"{dop_prefix}_tips") or product.get(f"{dop_prefix}_Tips")

    if metric is None and min_value is None and max_value is None:
        return None

    source_text = _source_text(location, min_value, max_value, metric, tips)
    safe_days = _safe_days(label, location, min_value, metric)

    return {
        "safe_days": safe_days,
        "source_min_value": min_value,
        "source_max_value": max_value,
        "source_metric": metric,
        "source_text": source_text,
        "tips": tips,
    }


def _safe_days(
    label: str, location: str, min_value: float | None, metric: str | None
) -> int | None:
    if metric == "When Ripe":
        return MANUAL_WHEN_RIPE_SAFE_DAYS.get((label, location))
    if min_value is None:
        return None
    if metric == "Days":
        return int(min_value)
    if metric == "Weeks":
        return int(min_value * 7)
    if metric == "Months":
        return int(min_value * 30)
    return None


def _storage_text(product: dict[str, Any], location: str, label: str) -> str | None:
    data = _build_storage_rule(label, location, product)
    if data is None:
        return None
    return str(data["source_text"])


def _source_text(
    location: str,
    min_value: float | None,
    max_value: float | None,
    metric: str | None,
    tips: str | None,
) -> str:
    parts = [location]
    if metric == "When Ripe":
        parts.append("When Ripe")
    elif min_value is not None and max_value is not None:
        parts.append(f"{_format_number(min_value)}-{_format_number(max_value)} {metric}")
    elif min_value is not None:
        parts.append(f"{_format_number(min_value)} {metric}")
    elif metric:
        parts.append(str(metric))
    if tips:
        parts.append(str(tips))
    return ". ".join(parts)


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _load_target_foodkeeper_products() -> dict[int, dict[str, Any]]:
    path = _foodkeeper_path()
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    product_sheet = next(
        sheet for sheet in payload["sheets"] if sheet.get("name") == "Product"
    )
    products: dict[int, dict[str, Any]] = {}
    for row in product_sheet["data"]:
        product = _flatten_foodkeeper_row(row)
        product_id = int(product["ID"])
        if product_id in TARGET_PRODUCT_IDS:
            products[product_id] = product

    missing = TARGET_PRODUCT_IDS - set(products)
    if missing:
        raise RuntimeError(f"FoodKeeper products missing: {sorted(missing)}")

    return products


def _flatten_foodkeeper_row(row: list[dict[str, Any]]) -> dict[str, Any]:
    product: dict[str, Any] = {}
    for cell in row:
        product.update(cell)
    return product


def _foodkeeper_path() -> Path:
    configured = settings.foodkeeper_json_path
    if configured.exists():
        return configured

    repo_fallback = Path(__file__).resolve().parents[2] / "data" / "foodkeeper.json"
    if repo_fallback.exists():
        return repo_fallback

    raise FileNotFoundError(f"FoodKeeper JSON not found: {repo_fallback}")
