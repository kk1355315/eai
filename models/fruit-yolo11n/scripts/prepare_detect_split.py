#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import shutil
from collections import Counter
from pathlib import Path


NAMES = ["apple", "banana", "litchi", "pear"]


def xyxy_to_xywh(xmin: float, ymin: float, xmax: float, ymax: float):
    xmin, ymin = max(0.0, xmin), max(0.0, ymin)
    xmax, ymax = min(1.0, xmax), min(1.0, ymax)
    width, height = xmax - xmin, ymax - ymin
    if width <= 0 or height <= 0:
        return None
    return (xmin + xmax) / 2, (ymin + ymax) / 2, width, height


def convert_row(parts: list[str]):
    class_id = int(float(parts[0]))
    coords = [float(value) for value in parts[1:]]
    if len(parts) == 5:
        x, y, w, h = coords
        box = xyxy_to_xywh(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    elif len(parts) >= 7 and len(coords) % 2 == 0:
        xs = coords[0::2]
        ys = coords[1::2]
        box = xyxy_to_xywh(min(xs), min(ys), max(xs), max(ys))
    else:
        raise ValueError(f"Unsupported label row with {len(parts)} columns.")
    if box is None:
        return None
    return class_id, box


def convert_label(source: Path, target: Path, stats: Counter[str]) -> None:
    converted: list[str] = []
    for raw in source.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = raw.split()
        if not parts:
            continue
        row = convert_row(parts)
        if row is None:
            stats["dropped"] += 1
            continue
        class_id, box = row
        converted.append(f"{class_id} " + " ".join(f"{value:.8f}" for value in box))
        stats[f"class_{class_id}"] += 1
    target.write_text("\n".join(converted) + ("\n" if converted else ""), encoding="utf-8")
    stats["labels"] += 1
    if not converted:
        stats["empty_labels"] += 1


def split_images(images: list[Path], seed: int):
    rng = random.Random(seed)
    shuffled = images[:]
    rng.shuffle(shuffled)
    total = len(shuffled)
    train_end = round(total * 0.8)
    valid_end = train_end + round(total * 0.1)
    return {
        "train": shuffled[:train_end],
        "valid": shuffled[train_end:valid_end],
        "test": shuffled[valid_end:],
    }


def write_yaml(output: Path) -> None:
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(NAMES))
    (output / "data_detect.yaml").write_text(
        f"path: {output.as_posix()}\n"
        "train: train/images\n"
        "val: valid/images\n"
        "test: test/images\n\n"
        f"nc: {len(NAMES)}\n"
        f"names:\n{names}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    root = args.root.resolve()
    output = (args.output or root / "detect_split").resolve()
    source_images = sorted((root / "train" / "images").glob("*.jpg"))
    source_labels = root / "train" / "labels"
    if not source_images:
        raise FileNotFoundError("No source images found in train/images.")

    if output.exists():
        shutil.rmtree(output)
    stats: Counter[str] = Counter()
    splits = split_images(source_images, args.seed)
    for split, images in splits.items():
        image_dir = output / split / "images"
        label_dir = output / split / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(image, image_dir / image.name)
            label = source_labels / f"{image.stem}.txt"
            if label.exists():
                convert_label(label, label_dir / label.name, stats)
            else:
                (label_dir / f"{image.stem}.txt").write_text("", encoding="utf-8")
                stats["labels"] += 1
                stats["empty_labels"] += 1
        stats[f"{split}_images"] = len(images)
    write_yaml(output)

    print(f"output={output}")
    for key in ["train_images", "valid_images", "test_images", "labels", "empty_labels", "dropped"]:
        print(f"{key}={stats[key]}")
    for i, name in enumerate(NAMES):
        print(f"{name}={stats[f'class_{i}']}")


if __name__ == "__main__":
    main()
