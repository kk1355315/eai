# Taxonomy

This directory is the source of truth for the product label space.

## Contains

- `v1_labels.csv`: ingredient-first V1 classes with stable IDs and `foodkeeper_targets`
- `v1_taxonomy_notes.md`: scope rules and FoodKeeper alignment guidance
- `expansion_policy.md`: how to add new classes in later versions

## Versioning

- Files here are versioned and reviewed
- Old class IDs must remain stable once released
- Exact per-row FoodKeeper mappings live in `docs/mappings/foodkeeper_target_map.csv`
