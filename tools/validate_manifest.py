from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REQUIRED_MANIFEST_COLUMNS = {
    "image_path",
    "source",
    "original_label",
    "mapped_label",
    "split",
    "is_target_domain",
}

ALLOWED_SPLIT_VALUES = {"train", "val", "test"}


@dataclass
class ValidationResult:
    errors: list[str]


def load_taxonomy_labels(taxonomy_path: Path) -> set[str]:
    with taxonomy_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row["class_name"].strip()
            for row in reader
            if row.get("class_name") and row["class_name"].strip()
        }


def resolve_image_path(manifest_path: Path, image_path_value: str) -> Path:
    candidate = Path(image_path_value)
    if candidate.is_absolute():
        return candidate
    return manifest_path.parent / candidate


def validate_manifest(manifest_path: Path, taxonomy_path: Path) -> ValidationResult:
    taxonomy_labels = load_taxonomy_labels(Path(taxonomy_path))
    errors: list[str] = []
    image_splits: dict[str, list[str]] = defaultdict(list)

    with Path(manifest_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_MANIFEST_COLUMNS - fieldnames)
        if missing_columns:
            return ValidationResult(
                [f"manifest is missing required columns: {', '.join(missing_columns)}"]
            )

        for row_number, row in enumerate(reader, start=2):
            image_path = row["image_path"].strip()
            mapped_label = row["mapped_label"].strip()
            split = row["split"].strip()
            resolved_image_path = resolve_image_path(Path(manifest_path), image_path)

            if not image_path:
                errors.append(f"row {row_number}: image_path is empty")
            elif not resolved_image_path.exists():
                errors.append(
                    f"row {row_number}: image_path '{image_path}' does not exist"
                )

            if mapped_label not in taxonomy_labels:
                errors.append(
                    f"row {row_number}: mapped_label '{mapped_label}' is not present in taxonomy"
                )

            if split not in ALLOWED_SPLIT_VALUES:
                errors.append(
                    f"row {row_number}: split '{split}' is not one of train, val, test"
                )

            dedupe_key = str(resolved_image_path)
            if split and split not in image_splits[dedupe_key]:
                image_splits[dedupe_key].append(split)

        for image_path, splits in image_splits.items():
            if len(splits) > 1:
                errors.append(
                    f"image '{image_path}' appears in multiple splits: {', '.join(splits)}"
                )

    return ValidationResult(errors=errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a normalized manifest CSV.")
    parser.add_argument("manifest", type=Path, help="Path to manifest CSV")
    parser.add_argument("taxonomy", type=Path, help="Path to taxonomy CSV")
    args = parser.parse_args()

    result = validate_manifest(args.manifest, args.taxonomy)
    if result.errors:
        for error in result.errors:
            print(error)
        return 1

    print("manifest validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
