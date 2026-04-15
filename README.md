# Fridge Main Object Classifier

Single-main-object image classification project for refrigerator foods and ingredients.

## Goal

Build a deployable V1 classifier for Sony Aitrios AI camera workflows using:
- public food and grocery datasets for base visual learning
- real fridge-domain images for target-domain fine-tuning

## Planned Training Flow

1. Define a product-owned taxonomy in `docs/taxonomy/`
2. Map public dataset labels in `docs/mappings/`
3. Build unified manifests in `data/manifests/`
4. Train a base classifier with public data
5. Fine-tune with real fridge images
6. Export and validate on device

## References

- ChineseFoodNet paper: `https://arxiv.org/abs/1705.02743`
- GroceryStoreDataset: `https://github.com/marcusklasson/GroceryStoreDataset`
- Sony Aitrios training tutorials: `https://github.com/SonySemiconductorSolutions/aitrios-rpi-tutorials-ai-model-training/tree/main`

## Repository Conventions

- `docs/` holds source-of-truth design artifacts and label policy
- `data/manifests/` holds CSV manifests, not raw image assets
- `training/` holds entrypoints and config notes
- `reports/` holds run outputs promoted to durable documentation
- `exports/` holds deployable model outputs by version
- `tools/` holds lightweight project utilities
- `tests/` holds automated checks for reusable utilities
