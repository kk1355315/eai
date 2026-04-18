# Manifests

This directory holds normalized CSV manifests used by training and evaluation.

## Contains

- `public_stage_a.csv`: public dataset rows for base training
- `public_stage_a_coverage.md`: current Stage A public-data coverage and known class gaps
- `target_stage_b.csv`: real fridge-domain rows for fine-tuning and acceptance
- `manifest_schema.md`: column definitions
- `split_policy.md`: train/val/test policy

## Path Policy

- Manifest `image_path` values must stay relative to `data/manifests/`
- Do not commit machine-specific absolute paths such as `D:\...`

## Current Public Coverage

- The current `public_stage_a.csv` covers `12/22` released V1 classes
- Missing classes are `berries`, `broccoli`, `cheese`, `egg`, `fish`, `leafy_greens`, `raw_meat`, `raw_poultry`, `shrimp`, and `tofu`
- Those classes must be supplied by Stage B real fridge images or by adding more public sources before claiming full V1 coverage

## Versioning

- Manifest files are versioned inputs
- `image_path` values must stay relative to the manifest location so the CSV works across machines
- Raw image assets live outside this repository unless explicitly added later
