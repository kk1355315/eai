# Stage A Config Notes

## Purpose

- Stage A uses public data to teach the model coarse ingredient appearance first.
- This stage is allowed to have incomplete class coverage before Stage B.

## Inputs

- `data/manifests/public_stage_a.csv`
- `docs/taxonomy/v1_labels.csv`
- `training/train_v1.py stage_a`
- `training/fit_pytorch_classifier.py stage_a`

## Current Coverage

- Public Stage A currently covers `12/22` released classes.
- Missing classes are `berries`, `broccoli`, `cheese`, `egg`, `fish`, `leafy_greens`, `raw_meat`, `raw_poultry`, `shrimp`, and `tofu`.

## Output Artifacts

- `training/runs/stage_a_prep/label_map.json`
- `training/runs/stage_a_prep/train.csv`
- `training/runs/stage_a_prep/val.csv`
- `training/runs/stage_a_prep/test.csv`
- `training/runs/stage_a_prep/summary.json`

## Command

```powershell
python training\train_v1.py stage_a
```

## Notes

- `train_v1.py` prepares validated split files and label maps.
- `fit_pytorch_classifier.py` uses those files to fit a floating-point classifier baseline.
- Stage A can still miss classes because public data coverage is incomplete.
