# Training

This directory will hold training entrypoints and configuration notes.

## Intended Contents

- `train_v1.py` or `aitrios_mobilenet_v1.ipynb`
- stage-specific config notes
- adapter code that reads normalized manifests and taxonomy files

## Current State

- `train_v1.py` now prepares validated Stage A and Stage B split files plus label maps
- `fit_pytorch_classifier.py` now fits a PyTorch classifier from those prepared splits
- `config_stage_a.md` records current public-data coverage limits
- `config_stage_b.md` records target-domain collection priorities
- `backend_pytorch.md` records the chosen fitting stack and where it stops
- IMX500 quantization and export are still not implemented in this repository
