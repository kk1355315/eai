# Expansion Policy

## Adding New Classes

- Append new `class_id` values only.
- Do not rename or repurpose an existing released class ID.
- Update mapping tables and manifests before retraining.

## Minimum Evidence Before Adding A Class

- Clear product value for the new class
- Enough public or target-domain samples to avoid one-shot overfitting
- A held-out regression set for existing high-value classes

## Release Gate

Every expansion release must ship together:
- updated taxonomy
- updated manifests
- updated training run
- updated evaluation report
- updated exported model artifact
