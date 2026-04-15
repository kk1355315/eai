# Mapping Rules

- A raw source label maps to exactly one V1 label or `DROP`.
- A source class is dropped if it is visually unstable, too rare, or spans multiple V1 labels.
- Do not force full dataset coverage.
- Keep the reason column populated for every dropped class.
- Mapping quality is more important than public dataset recall.
- A V1 class may map to one or more FoodKeeper `Product.ID` rows.
- Multi-target FoodKeeper mappings must default to the most conservative refrigerator guidance.
