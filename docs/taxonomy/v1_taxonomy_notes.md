# V1 Taxonomy Notes

## Inclusion Rules

- Prefer categories that are common in a household refrigerator.
- Prefer classes that can be separated by vision alone.
- Use medium granularity for prepared foods.
- Keep ingredient classes relatively specific when appearance is stable.

## Exclusion Rules

- Exclude classes that require smell, recipe knowledge, or packaging text.
- Exclude rare classes that do not justify initial labeling cost.
- Exclude unstable dish-name classes from public datasets when they overlap multiple product classes.

## Status Field

- `active`: in V1 now
- `candidate`: reserved for review after real fridge samples are collected

## Expansion Rule

- Never renumber released class IDs.
- New classes append to the end of the table.
- Every expansion release must retrain on old and new classes together.
