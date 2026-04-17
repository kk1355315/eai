# Manifests

This directory holds normalized CSV manifests used by training and evaluation.

## Contains

- `public_stage_a.csv`: public dataset rows for base training
- `public_stage_a_coverage.md`: current Stage A public-data coverage and known class gaps
- `target_stage_b.csv`: real fridge-domain rows for fine-tuning and acceptance
- `manifest_schema.md`: column definitions
- `split_policy.md`: train/val/test policy

## Versioning

- Manifest files are versioned inputs
- `image_path` values must stay relative to the manifest location so the CSV works across machines
- Raw image assets live outside this repository unless explicitly added later
