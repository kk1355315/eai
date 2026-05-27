#!/usr/bin/env python3
"""Export trained weights to NCNN for Raspberry Pi inference."""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export YOLO11 weights to NCNN.")
    parser.add_argument(
        "--weights",
        type=Path,
        default=ROOT / "runs" / "yolo11n-fruit-detect" / "weights" / "best.pt",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    YOLO(str(args.weights)).export(format="ncnn", imgsz=args.imgsz)


if __name__ == "__main__":
    main()
