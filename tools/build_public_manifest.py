from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
OUTPUT_COLUMNS = [
    "image_path",
    "source",
    "original_label",
    "mapped_label",
    "split",
    "is_target_domain",
    "capture_condition",
    "container_type",
    "notes",
]


@dataclass
class BuildResult:
    rows_written: int
    warnings: list[str]


def load_taxonomy_labels(taxonomy_path: Path) -> set[str]:
    with taxonomy_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row["class_name"].strip()
            for row in reader
            if row.get("class_name") and row["class_name"].strip()
        }


def load_mapping_table(
    mapping_path: Path,
    key_column: str,
    taxonomy_labels: set[str],
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with mapping_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            key = row[key_column].strip()
            if key in mapping:
                raise ValueError(f"{mapping_path} has duplicate mapping for '{key}' on row {row_number}")

            decision = row["decision"].strip()
            mapped_label = row["mapped_label"].strip()
            if decision not in {"KEEP", "DROP"}:
                raise ValueError(f"{mapping_path} row {row_number} has invalid decision '{decision}'")
            if decision == "KEEP" and mapped_label not in taxonomy_labels:
                raise ValueError(
                    f"{mapping_path} row {row_number} maps '{key}' to unknown class '{mapped_label}'"
                )
            mapping[key] = row
    return mapping


def iter_image_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def deterministic_split(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def deterministic_train_val_split(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 90:
        return "train"
    return "val"


def build_grocery_rows(
    grocery_root: Path,
    mapping_path: Path,
    taxonomy_labels: set[str],
) -> tuple[list[dict[str, str]], list[str]]:
    warnings: list[str] = []
    if not grocery_root.exists():
        return [], [f"missing GroceryStoreDataset root: {grocery_root}"]

    mapping = load_mapping_table(mapping_path, "original_fine_label", taxonomy_labels)
    rows: list[dict[str, str]] = []

    for split in ("train", "val", "test"):
        split_root = None
        for candidate in (grocery_root / "dataset" / split, grocery_root / split):
            if candidate.is_dir():
                split_root = candidate
                break
        if split_root is None:
            warnings.append(f"missing GroceryStoreDataset split directory: {split}")
            continue

        for image_path in iter_image_files(split_root):
            original_label = image_path.parent.name
            mapping_row = mapping.get(original_label)
            if mapping_row is None:
                raise ValueError(
                    f"GroceryStoreDataset image '{image_path}' uses unmapped label '{original_label}'"
                )
            if mapping_row["decision"].strip() != "KEEP":
                continue

            container_type = "packaged" if "Packages" in image_path.parts else "loose"
            rows.append(
                {
                    "image_path": str(image_path.resolve()),
                    "source": "GroceryStoreDataset",
                    "original_label": original_label,
                    "mapped_label": mapping_row["mapped_label"].strip(),
                    "split": split,
                    "is_target_domain": "false",
                    "capture_condition": "public_store_scene",
                    "container_type": container_type,
                    "notes": "official_grocery_split",
                }
            )

    return rows, warnings


def resolve_freiburg_images_root(freiburg_root: Path) -> Path | None:
    candidates = [
        freiburg_root / "images",
        freiburg_root.parent / "images",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def parse_freiburg_split_file(split_path: Path) -> list[str]:
    relative_paths: list[str] = []
    for line in split_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        relative_paths.append(stripped.split()[0])
    return relative_paths


def build_freiburg_rows(
    freiburg_root: Path,
    mapping_path: Path,
    taxonomy_labels: set[str],
) -> tuple[list[dict[str, str]], list[str]]:
    warnings: list[str] = []
    if not freiburg_root.exists():
        return [], [f"missing Freiburg dataset root: {freiburg_root}"]

    images_root = resolve_freiburg_images_root(freiburg_root)
    if images_root is None:
        return [], [f"missing Freiburg images directory near: {freiburg_root}"]

    split_root = freiburg_root / "splits"
    train_split_path = split_root / "train0.txt"
    test_split_path = split_root / "test0.txt"
    if not train_split_path.is_file() or not test_split_path.is_file():
        return [], [f"missing Freiburg split files in: {split_root}"]

    mapping = load_mapping_table(mapping_path, "original_label", taxonomy_labels)
    rows: list[dict[str, str]] = []
    split_entries: list[tuple[str, str, str]] = []
    split_entries.extend(
        ("train0", relative_path, deterministic_train_val_split(relative_path))
        for relative_path in parse_freiburg_split_file(train_split_path)
    )
    split_entries.extend(
        ("test0", relative_path, "test")
        for relative_path in parse_freiburg_split_file(test_split_path)
    )

    for source_split, relative_path_str, final_split in split_entries:
        relative_path = Path(relative_path_str)
        image_path = images_root / relative_path
        original_label = relative_path.parts[0] if relative_path.parts else ""
        mapping_row = mapping.get(original_label)
        if mapping_row is None:
            raise ValueError(
                f"Freiburg split entry '{relative_path_str}' uses unmapped label '{original_label}'"
            )
        if not image_path.exists():
            raise ValueError(f"Freiburg split entry '{relative_path_str}' is missing image data")
        if mapping_row["decision"].strip() != "KEEP":
            continue

        rows.append(
            {
                "image_path": str(image_path.resolve()),
                "source": "FreiburgGroceriesDataset",
                "original_label": original_label,
                "mapped_label": mapping_row["mapped_label"].strip(),
                "split": final_split,
                "is_target_domain": "false",
                "capture_condition": "public_packaged_scene",
                "container_type": "packaged",
                "notes": f"official_{source_split}",
            }
        )

    return rows, warnings


def write_manifest(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_public_manifest(
    output_path: Path,
    taxonomy_path: Path,
    grocery_root: Path,
    grocery_mapping_path: Path,
    freiburg_root: Path,
    freiburg_mapping_path: Path,
) -> BuildResult:
    taxonomy_labels = load_taxonomy_labels(taxonomy_path)
    rows: list[dict[str, str]] = []
    warnings: list[str] = []

    grocery_rows, grocery_warnings = build_grocery_rows(
        grocery_root,
        grocery_mapping_path,
        taxonomy_labels,
    )
    freiburg_rows, freiburg_warnings = build_freiburg_rows(
        freiburg_root,
        freiburg_mapping_path,
        taxonomy_labels,
    )

    rows.extend(grocery_rows)
    rows.extend(freiburg_rows)
    warnings.extend(grocery_warnings)
    warnings.extend(freiburg_warnings)

    rows.sort(key=lambda row: (row["source"], row["split"], row["mapped_label"], row["image_path"]))
    write_manifest(rows, output_path)
    return BuildResult(rows_written=len(rows), warnings=warnings)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Stage A public manifest from local public dataset folders."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/public_stage_a.csv"),
        help="Output manifest CSV path",
    )
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=Path("docs/taxonomy/v1_labels.csv"),
        help="Path to taxonomy CSV",
    )
    parser.add_argument(
        "--grocery-root",
        type=Path,
        default=Path("data/external_datasets/GroceryStoreDataset"),
        help="Path to the local GroceryStoreDataset root",
    )
    parser.add_argument(
        "--grocery-mapping",
        type=Path,
        default=Path("docs/mappings/grocery_to_v1.csv"),
        help="Path to the GroceryStoreDataset mapping CSV",
    )
    parser.add_argument(
        "--freiburg-root",
        type=Path,
        default=Path("data/external_datasets/freiburg_groceries_dataset"),
        help="Path to the local Freiburg Groceries dataset root",
    )
    parser.add_argument(
        "--freiburg-mapping",
        type=Path,
        default=Path("docs/mappings/freiburg_to_v1.csv"),
        help="Path to the Freiburg mapping CSV",
    )
    args = parser.parse_args()

    result = build_public_manifest(
        output_path=args.output,
        taxonomy_path=args.taxonomy,
        grocery_root=args.grocery_root,
        grocery_mapping_path=args.grocery_mapping,
        freiburg_root=args.freiburg_root,
        freiburg_mapping_path=args.freiburg_mapping,
    )

    for warning in result.warnings:
        print(f"warning: {warning}")
    print(f"wrote {result.rows_written} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
