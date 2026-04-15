# Mappings

This directory maps raw dataset labels into the product taxonomy and links product classes to FoodKeeper rows.

## Contains

- `grocery_to_v1.csv`
- `freiburg_to_v1.csv`
- `chinesefoodnet_to_v1.csv`
- `foodkeeper_target_map.csv`
- `mapping_rules.md`

## Versioning

- Mapping tables are source-of-truth and versioned
- A source label must map to one V1 label or `DROP`
- A V1 label may map to one or more FoodKeeper `Product.ID` rows
