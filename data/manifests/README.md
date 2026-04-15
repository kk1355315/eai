# Manifests

This directory holds normalized CSV manifests used by training and evaluation.

## Contains

- `public_stage_a.csv`: public dataset rows for base training
- `target_stage_b.csv`: real fridge-domain rows for fine-tuning and acceptance
- `manifest_schema.md`: column definitions
- `split_policy.md`: train/val/test policy

## Versioning

- Manifest files are versioned inputs
- Raw image assets live outside this repository unless explicitly added later
