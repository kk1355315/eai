# Stage B Config Notes

## Purpose

- Stage B uses real fridge-domain images to close the gap between public data and deployment.
- This is the stage that should cover the classes missing from public data first.

## Priority Missing Classes

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

## Split Rules

- Keep `train`, `val`, and `test` rows separate from the start.
- Only target-domain rows belong in `data/manifests/target_stage_b.csv`.
- Reserve held-out `val` and `test` rows before any model fitting.

## Suggested Capture Conditions

- fridge light on and off
- front angle and top-down angle
- loose ingredient and packaged ingredient
- partial occlusion by containers or bags
- clean background and cluttered shelf background

## Output Artifacts

- `training/runs/stage_b_prep/label_map.json`
- `training/runs/stage_b_prep/train.csv`
- `training/runs/stage_b_prep/val.csv`
- `training/runs/stage_b_prep/test.csv`
- `training/runs/stage_b_prep/summary.json`
- `training/runs/stage_b_prep/train_mixed.csv` when public train mixing is enabled

## Commands

Prepare target-only Stage B inputs:

```powershell
python training\train_v1.py stage_b
```

Prepare Stage B inputs and also append public train rows:

```powershell
python training\train_v1.py stage_b --mix-public-train
```

Fit a Stage B classifier:

```powershell
python training\fit_pytorch_classifier.py stage_b
```
