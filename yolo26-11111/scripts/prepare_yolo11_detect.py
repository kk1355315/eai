#!/usr/bin/env python3
"""Build a detection-only view of the mixed Roboflow labels."""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path


SPLITS = ("train", "valid", "test")


def xyxy_to_xywh(
    xmin: float, ymin: float, xmax: float, ymax: float
) -> tuple[float, float, float, float] | None:
    xmin, ymin = max(0.0, xmin), max(0.0, ymin)
    xmax, ymax = min(1.0, xmax), min(1.0, ymax)
    width, height = xmax - xmin, ymax - ymin
    if width <= 0 or height <= 0:
        return None
    return (xmin + xmax) / 2, (ymin + ymax) / 2, width, height


def clip_xywh(values: list[float]) -> tuple[float, float, float, float] | None:
    x_center, y_center, width, height = values
    return xyxy_to_xywh(
        x_center - width / 2,
        y_center - height / 2,
        x_center + width / 2,
        y_center + height / 2,
    )


def polygon_to_xywh(values: list[float]) -> tuple[float, float, float, float] | None:
    xs = values[0::2]
    ys = values[1::2]
    return xyxy_to_xywh(min(xs), min(ys), max(xs), max(ys))


def format_box(class_id: int, box: tuple[float, float, float, float]) -> str:
    if class_id < 0:
        raise ValueError(f"Class id must be non-negative, got {class_id}.")
    if not all(0 <= value <= 1 for value in box):
        raise ValueError(f"Box values must be normalized to [0, 1], got {box}.")
    if box[2] <= 0 or box[3] <= 0:
        raise ValueError(f"Box width and height must be positive, got {box}.")
    return f"{class_id} " + " ".join(f"{value:.8f}" for value in box)


def convert_label(source: Path, target: Path, stats: Counter[str]) -> None:
    converted: list[str] = []
    for line_number, raw_line in enumerate(source.read_text().splitlines(), start=1):
        parts = raw_line.split()
        if not parts:
            continue

        try:
            class_id = int(float(parts[0]))
            coords = [float(value) for value in parts[1:]]
        except ValueError as exc:
            raise ValueError(f"{source}:{line_number} is not numeric.") from exc

        if len(parts) == 5:
            box = clip_xywh(coords)
            stats["box_rows"] += 1
        elif len(parts) >= 7 and len(coords) % 2 == 0:
            box = polygon_to_xywh(coords)
            stats["polygon_rows"] += 1
        else:
            raise ValueError(
                f"{source}:{line_number} has {len(parts)} columns; "
                "expected a YOLO box or polygon row."
            )

        if box is None:
            stats["dropped_rows"] += 1
            continue

        converted.append(format_box(class_id, box))
        stats[f"class_{class_id}"] += 1

    target.write_text("\n".join(converted) + ("\n" if converted else ""))
    stats["label_files"] += 1


def materialize_images(source: Path, target: Path) -> None:
    if target.is_symlink():
        target.unlink()
    target.mkdir(parents=True, exist_ok=True)
    for source_image in source.glob("*.jpg"):
        target_image = target / source_image.name
        if target_image.exists():
            continue
        try:
            target_image.hardlink_to(source_image)
        except OSError:
            shutil.copy2(source_image, target_image)


def build_dataset(root: Path, output: Path) -> Counter[str]:
    stats: Counter[str] = Counter()
    for split in SPLITS:
        source_split = root / split
        source_labels = source_split / "labels"
        source_images = source_split / "images"
        if not source_labels.is_dir() or not source_images.is_dir():
            raise FileNotFoundError(f"Missing images or labels for split '{split}'.")

        target_split = output / split
        target_labels = target_split / "labels"
        target_labels.mkdir(parents=True, exist_ok=True)
        materialize_images(source_images, target_split / "images")

        for source_label in sorted(source_labels.glob("*.txt")):
            convert_label(source_label, target_labels / source_label.name, stats)
        stats[f"{split}_labels"] = len(list(source_labels.glob("*.txt")))
        stats[f"{split}_images"] = len(list(source_images.glob("*.jpg")))
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert mixed box/polygon YOLO labels into detection labels."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset root that contains train, valid, and test folders.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Detection dataset output directory. Defaults to <root>/detect_yolo11.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output = (args.output or root / "detect_yolo11").resolve()
    stats = build_dataset(root, output)
    print(f"Detection dataset: {output}")
    for key in (
        "train_images",
        "valid_images",
        "test_images",
        "label_files",
        "box_rows",
        "polygon_rows",
        "dropped_rows",
        "class_0",
        "class_1",
        "class_2",
        "class_3",
    ):
        print(f"{key}: {stats[key]}")


if __name__ == "__main__":
    main()
