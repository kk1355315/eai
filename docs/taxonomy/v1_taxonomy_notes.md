# V1 Taxonomy Notes

## Scope

- V1 is ingredient-first and excludes prepared-food classes.
- Every released class must anchor to one or more FoodKeeper `Product.ID` rows.
- Exact FoodKeeper row expansion lives in `docs/mappings/foodkeeper_target_map.csv`.

## Class Group Semantics

- `produce`: fruits and vegetables commonly stored in the fridge
- `dairy_egg`: shell eggs and dairy staples
- `plant_protein`: tofu-like plant proteins
- `animal_protein`: raw meat poultry and seafood classes that need conservative storage guidance

## Inclusion Rules

- Prefer categories that are common in a household refrigerator.
- Prefer classes that can be separated by vision alone without recipe knowledge or OCR.
- Keep granularity coarse enough that each class can map cleanly to FoodKeeper advice.
- Allow packaged staples like milk yogurt tofu and cheese only when container appearance is stable in the target domain.

## Exclusion Rules

- Exclude prepared foods in V1 even if public datasets contain them.
- Exclude classes that require smell recipe context or packaging text.
- Exclude rare classes that do not justify initial labeling cost.
- Exclude labels that would force one visual class to span incompatible FoodKeeper advice without a conservative rule.

## Status Field

- `active`: in V1 now
- `candidate`: reserved for later review if target-domain images justify the class

## FoodKeeper Targets Field

- `foodkeeper_targets` stores pipe-delimited FoodKeeper `Product.ID` values.
- If a class maps to multiple FoodKeeper rows the runtime should choose the most conservative refrigerator guidance.

## Expansion Rule

- Never renumber released class IDs.
- New classes append to the end of the table.
- Every expansion release must update the FoodKeeper mapping and retrain on old and new classes together.
