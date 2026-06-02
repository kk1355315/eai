from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import FoodStorageRule


def test_foods_are_seeded_for_supported_fruits_only() -> None:
    with TestClient(app) as client:
        response = client.get("/foods")

    assert response.status_code == 200
    foods = response.json()
    assert [food["model_label"] for food in foods] == [
        "apple",
        "banana",
        "pear",
        "litchi",
    ]
    assert {food["foodkeeper_product_id"] for food in foods} == {248, 251, 252, 266}


def test_storage_rules_use_target_foodkeeper_products_and_safe_days() -> None:
    with TestClient(app) as client:
        banana = client.get("/foods/banana/storage")
        pear = client.get("/foods/pear/storage")

    assert banana.status_code == 200
    banana_rules = {
        rule["storage_location"]: rule
        for rule in banana.json()["storage_rules"]
    }
    assert banana_rules["pantry"]["safe_days"] == 2
    assert banana_rules["pantry"]["source_metric"] == "When Ripe"
    assert "When Ripe" in banana_rules["pantry"]["source_text"]
    assert banana_rules["pantry"]["evidence_id"] == "storage_banana_251_pantry"
    assert banana_rules["refrigerate"]["safe_days"] == 3
    assert banana_rules["freeze"]["safe_days"] == 60

    assert pear.status_code == 200
    pear_rules = {
        rule["storage_location"]: rule
        for rule in pear.json()["storage_rules"]
    }
    assert pear_rules["refrigerate"]["safe_days"] == 3
    assert pear_rules["freeze"]["safe_days"] == 60

    with Session(engine) as session:
        product_ids = {
            rule.source_product_id
            for rule in session.exec(select(FoodStorageRule)).all()
        }

    assert product_ids == {248, 251, 252, 266}


def test_guideline_rules_have_required_evidence_fields() -> None:
    with TestClient(app) as client:
        response = client.get("/guideline-rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 6
    assert all(rule["evidence_id"] for rule in rules)
    assert all(rule["source_url"] for rule in rules)
    assert all(rule["evidence_summary"] for rule in rules)
    assert "rule_medical_boundary_001" in {rule["evidence_id"] for rule in rules}


def test_guideline_rule_conditions_keep_goal_and_diet_preference_separate() -> None:
    with TestClient(app) as client:
        response = client.get("/guideline-rules")

    assert response.status_code == 200
    conditions = {
        rule["evidence_id"]: rule["condition"]
        for rule in response.json()
    }
    sugar_condition = conditions["rule_sugar_moderation_001"]
    whole_fruit_condition = conditions["rule_whole_fruit_001"]

    assert sugar_condition["user_goal_any"] == ["减脂"]
    assert sugar_condition["diet_preference_any"] == ["少糖", "reduce_sugar"]
    assert whole_fruit_condition["diet_preference_any"] == ["少糖", "reduce_sugar"]
    assert "少糖" not in sugar_condition["user_goal_any"]
    assert "reduce_sugar" not in sugar_condition["user_goal_any"]


def test_nutrition_facts_are_seeded_for_four_fruits() -> None:
    with TestClient(app) as client:
        response = client.get("/nutrition-facts")

    assert response.status_code == 200
    facts = response.json()
    assert len(facts) == 4
    assert {fact["food"]["model_label"] for fact in facts} == {
        "apple",
        "banana",
        "pear",
        "litchi",
    }
    assert all(fact["reference"]["source_name"] for fact in facts)
    assert all(fact["reference"]["source_url"] for fact in facts)
    expected_sources = {
        "apple": (
            171688,
            "https://fdc.nal.usda.gov/fdc-app.html#/food-details/171688/nutrients",
        ),
        "banana": (
            173944,
            "https://fdc.nal.usda.gov/fdc-app.html#/food-details/173944/nutrients",
        ),
        "pear": (
            169118,
            "https://fdc.nal.usda.gov/fdc-app.html#/food-details/169118/nutrients",
        ),
        "litchi": (
            169086,
            "https://fdc.nal.usda.gov/fdc-app.html#/food-details/169086/nutrients",
        ),
    }
    for fact in facts:
        fdc_id, source_url = expected_sources[fact["food"]["model_label"]]
        assert fact["fdc_id"] == fdc_id
        assert fact["source_url"] == source_url


def test_profile_can_be_read_and_patched() -> None:
    with TestClient(app) as client:
        initial = client.get("/profile")
        updated = client.patch(
            "/profile",
            json={
                "goal": "减少浪费",
                "diet_preference": "少糖",
                "cooking_condition": "宿舍",
                "avoid_foods": ["litchi"],
            },
        )
        after = client.get("/profile")

    assert initial.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["goal"] == "减少浪费"
    assert updated.json()["avoid_foods"] == ["litchi"]
    assert after.json()["diet_preference"] == "少糖"


def test_profile_rejects_null_required_patch_fields() -> None:
    with TestClient(app) as client:
        before = client.get("/profile").json()
        for field_name in ("goal", "diet_preference", "cooking_condition"):
            response = client.patch("/profile", json={field_name: None})
            assert response.status_code == 422
        after = client.get("/profile").json()

    assert after["goal"] == before["goal"]
    assert after["diet_preference"] == before["diet_preference"]
    assert after["cooking_condition"] == before["cooking_condition"]


def test_profile_defaults_are_isolated_between_tests() -> None:
    with TestClient(app) as client:
        response = client.get("/profile")

    assert response.status_code == 200
    assert response.json()["goal"] == "健康饮食"
    assert response.json()["diet_preference"] == "简单烹饪"
    assert response.json()["cooking_condition"] == "家庭"
