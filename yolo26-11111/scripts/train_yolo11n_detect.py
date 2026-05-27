#!/usr/bin/env python3
"""Train a YOLO11n fruit detector from the detection-only dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLO11n on this fruit dataset.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--name", default="yolo11n-fruit-detect")
    return parser.parse_args()


def default_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def main() -> None:
    args = parse_args()
    model = YOLO("yolo11n.pt")
    model.train(
        data=str(ROOT / "data_yolo11_detect.yaml"),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or default_device(),
        workers=args.workers,
        project=str(ROOT / "runs"),
        name=args.name,
    )


if __name__ == "__main__":
    main()
