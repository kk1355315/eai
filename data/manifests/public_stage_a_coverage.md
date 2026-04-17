# Public Stage A Coverage

## Current Snapshot

- Source manifest: `data/manifests/public_stage_a.csv`
- Public datasets included now:
  - `GroceryStoreDataset`
  - `FreiburgGroceriesDataset`
- Total rows: `3006`
- Covered released V1 classes: `12 / 22`
- Upstream Freiburg split files contain repeated image entries, so the normalized manifest deduplicates identical rows before versioning.

## Covered Classes

| class_name | rows |
| --- | ---: |
| apple | 576 |
| banana | 95 |
| carrot | 90 |
| citrus_fruit | 488 |
| cucumber | 60 |
| milk | 534 |
| mushroom | 83 |
| onion | 80 |
| pepper | 237 |
| potato | 155 |
| tomato | 235 |
| yogurt | 373 |

## Released Classes Still Missing From Stage A

- `berries`
- `broccoli`
- `cheese`
- `egg`
- `fish`
- `leafy_greens`
- `raw_meat`
- `raw_poultry`
- `shrimp`
- `tofu`

## Required Follow-up

- This Stage A manifest is only a public-data bootstrap, not full released-class coverage.
- Every missing released class must enter `target_stage_b.csv` with real fridge images before any V1 deployment claim.
- If a future public dataset can cover one of the missing classes, add a versioned mapping table first, then rebuild `public_stage_a.csv`.
- Keep this file updated whenever the Stage A manifest changes.
