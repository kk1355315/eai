# Training

This directory contains the rebuilt V1 public-data baseline training entrypoints.

## Main Flow

1. Build release-layer taxonomy and public manifest assets from:
   - `specs/labels/discovered_label_catalog.json`
   - `specs/labels/release_v1.json`
2. Prepare normalized Stage A split files.
3. Fit a PyTorch `MobileNetV2` baseline on the selected V1 labels.

## Commands

Build V1 label assets:

```bash
python tools/release_v1_assets.py
```

Prepare Stage A inputs:

```bash
python training/train_v1.py stage_a
```

Fit the Stage A baseline:

```bash
python training/fit_pytorch_classifier.py stage_a
```
