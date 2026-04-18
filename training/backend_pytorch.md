# PyTorch Backend Notes

## Purpose

- Use a plain PyTorch image classification stack for Stage A and Stage B model fitting.
- Keep this repository focused on model fitting against normalized manifests.
- Keep Aitrios quantization and export as a later step.

## Why This Backend

- Sony's IMX500 training tutorial provides a MobileNetV2 classification path.
- Aitrios model export later relies on Edge-MDT tooling.
- Edge-MDT is better treated as a separate export environment than as the day-to-day training environment for this repo.

## Install

```powershell
pip install -r training\requirements-pytorch.txt
```

## Commands

Train a Stage A baseline:

```powershell
python training\fit_pytorch_classifier.py stage_a
```

Train a Stage B model with only fridge-domain rows:

```powershell
python training\fit_pytorch_classifier.py stage_b
```

Train a Stage B model while also mixing public train rows:

```powershell
python training\fit_pytorch_classifier.py stage_b --mix-public-train
```

## Output Artifacts

- `training/runs/stage_a_fit/best.pt`
- `training/runs/stage_a_fit/last.pt`
- `training/runs/stage_a_fit/history.json`
- `training/runs/stage_a_fit/metrics.json`
- `training/runs/stage_b_fit/best.pt`
- `training/runs/stage_b_fit/last.pt`
- `training/runs/stage_b_fit/history.json`
- `training/runs/stage_b_fit/metrics.json`

## Scope Limits

- This backend trains a floating-point classifier only.
- It does not quantize, convert, or package an IMX500 model.
- Aitrios export should be done later with the official Edge-MDT flow in a supported environment.
