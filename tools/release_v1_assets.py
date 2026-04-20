from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TAXONOMY_COLUMNS = [
    "class_id",
    "class_name",
    "class_group",
    "status",
    "foodkeeper_ids",
    "storage_field",
    "storage_min_days",
    "storage_max_days",
    "source_datasets",
    "notes",
]
MANIFEST_COLUMNS = [
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
class ReleaseBuildResult:
    taxonomy_rows_written: int
    manifest_rows_written: int
    summary: dict[str, object]


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_selected_labels(release_spec_path: Path) -> list[str]:
    payload = read_json(release_spec_path)
    selected_labels = payload.get("selected_labels", [])
    if not isinstance(selected_labels, list):
        raise ValueError("release spec 'selected_labels' must be a list")

    normalized: list[str] = []
    for label in selected_labels:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("release spec contains an empty or non-string label")
        normalized.append(label.strip())

    if len(normalized) != len(set(normalized)):
        raise ValueError("release spec contains duplicate labels")
    if not normalized:
        raise ValueError("release spec selected_labels is empty")
    return normalized


def load_catalog_entries(catalog_path: Path) -> dict[str, dict[str, object]]:
    payload = read_json(catalog_path)
    labels = payload.get("labels", [])
    if not isinstance(labels, list):
        raise ValueError("catalog 'labels' must be a list")

    entries: dict[str, dict[str, object]] = {}
    for entry in labels:
        if not isinstance(entry, dict):
            raise ValueError("catalog label entry must be an object")
        label_name = str(entry.get("label_name", "")).strip()
        if not label_name:
            raise ValueError("catalog label entry is missing label_name")
        if label_name in entries:
            raise ValueError(f"catalog contains duplicate label '{label_name}'")
        entries[label_name] = entry
    return entries


def infer_class_group(label_name: str) -> str:
    if label_name in {"packaged_dairy_milk", "dairy_yoghurt"}:
        return "dairy"
    return "produce"


def build_taxonomy_rows(
    selected_labels: list[str],
    catalog_entries: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for class_id, label_name in enumerate(selected_labels):
        entry = catalog_entries.get(label_name)
        if entry is None:
            raise ValueError(f"selected label '{label_name}' is missing from the discovery catalog")

        foodkeeper_ids = entry.get("foodkeeper_ids", [])
        source_datasets = entry.get("source_datasets", [])
        rows.append(
            {
                "class_id": str(class_id),
                "class_name": label_name,
                "class_group": infer_class_group(label_name),
                "status": "active",
                "foodkeeper_ids": json.dumps(foodkeeper_ids, ensure_ascii=True),
                "storage_field": str(entry.get("storage_field", "")),
                "storage_min_days": str(entry.get("storage_min_days", "")),
                "storage_max_days": str(entry.get("storage_max_days", "")),
                "source_datasets": json.dumps(source_datasets, ensure_ascii=True),
                "notes": str(entry.get("notes", "")),
            }
        )
    return rows


def write_taxonomy(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TAXONOMY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def iter_image_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def to_manifest_relative_path(image_path: Path, manifest_dir: Path) -> str:
    return Path(os.path.relpath(image_path.resolve(), start=manifest_dir.resolve())).as_posix()


def deterministic_train_val_split(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 90:
        return "train"
    return "val"


def parse_fine_group(value: str) -> tuple[str, set[str]]:
    if ":{" not in value or not value.endswith("}"):
        raise ValueError(f"invalid fine_group value '{value}'")
    coarse_label, raw_members = value.split(":{", maxsplit=1)
    members = {member.strip() for member in raw_members[:-1].split(",") if member.strip()}
    if not coarse_label.strip() or not members:
        raise ValueError(f"invalid fine_group value '{value}'")
    return coarse_label.strip(), members


def grocery_image_labels(split_root: Path, image_path: Path) -> tuple[str, str]:
    relative_parts = image_path.relative_to(split_root).parts
    if len(relative_parts) < 3:
        raise ValueError(f"unexpected GroceryStoreDataset path shape: {image_path}")
    coarse_label = relative_parts[1]
    fine_label = relative_parts[2] if len(relative_parts) > 3 else ""
    return coarse_label, fine_label


def matches_grocery_source_class(source_class: dict[str, object], coarse: str, fine: str) -> bool:
    if source_class.get("dataset") != "GroceryStoreDataset":
        return False
    level = str(source_class.get("level", "")).strip()
    value = str(source_class.get("value", "")).strip()

    if level == "coarse":
        return coarse == value
    if level == "fine_group":
        expected_coarse, allowed_fines = parse_fine_group(value)
        return coarse == expected_coarse and fine in allowed_fines
    return False


def build_grocery_rows(
    selected_labels: list[str],
    catalog_entries: dict[str, dict[str, object]],
    grocery_root: Path,
    manifest_output_path: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    manifest_dir = manifest_output_path.parent
    source_classes_by_label: dict[str, list[dict[str, object]]] = {
        label_name: [
            source_class
            for source_class in catalog_entries[label_name].get("source_classes", [])
            if isinstance(source_class, dict) and source_class.get("dataset") == "GroceryStoreDataset"
        ]
        for label_name in selected_labels
    }

    for split in ("train", "val", "test"):
        split_root = None
        for candidate in (grocery_root / "dataset" / split, grocery_root / split):
            if candidate.is_dir():
                split_root = candidate
                break
        if split_root is None:
            raise ValueError(f"missing GroceryStoreDataset split directory for '{split}'")

        for image_path in iter_image_files(split_root):
            coarse_label, fine_label = grocery_image_labels(split_root, image_path)
            matched_label: str | None = None
            for label_name in selected_labels:
                source_classes = source_classes_by_label[label_name]
                if any(
                    matches_grocery_source_class(source_class, coarse_label, fine_label)
                    for source_class in source_classes
                ):
                    matched_label = label_name
                    break

            if matched_label is None:
                continue

            original_label = fine_label or coarse_label
            rows.append(
                {
                    "image_path": to_manifest_relative_path(image_path, manifest_dir),
                    "source": "GroceryStoreDataset",
                    "original_label": original_label,
                    "mapped_label": matched_label,
                    "split": split,
                    "is_target_domain": "false",
                    "capture_condition": "public_store_scene",
                    "container_type": "packaged" if "Packages" in image_path.parts else "loose",
                    "notes": "official_grocery_split",
                }
            )

    return rows


def resolve_freiburg_images_root(freiburg_root: Path) -> Path:
    candidates = [freiburg_root / "images", freiburg_root.parent / "images"]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise ValueError(f"missing Freiburg images directory near: {freiburg_root}")


def parse_freiburg_split_file(split_path: Path) -> list[str]:
    relative_paths: list[str] = []
    for line in split_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        relative_paths.append(stripped.split()[0])
    return relative_paths


def build_freiburg_rows(
    selected_labels: list[str],
    catalog_entries: dict[str, dict[str, object]],
    freiburg_root: Path,
    manifest_output_path: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    manifest_dir = manifest_output_path.parent
    images_root = resolve_freiburg_images_root(freiburg_root)
    split_root = freiburg_root / "splits"
    train_split_path = split_root / "train0.txt"
    test_split_path = split_root / "test0.txt"
    if not train_split_path.is_file() or not test_split_path.is_file():
        raise ValueError(f"missing Freiburg split files in: {split_root}")

    folder_to_label: dict[str, str] = {}
    for label_name in selected_labels:
        for source_class in catalog_entries[label_name].get("source_classes", []):
            if not isinstance(source_class, dict):
                continue
            if source_class.get("dataset") != "Freiburg Groceries":
                continue
            if str(source_class.get("level", "")).strip() != "folder":
                continue
            folder_name = str(source_class.get("value", "")).strip()
            if not folder_name:
                continue
            if folder_name in folder_to_label and folder_to_label[folder_name] != label_name:
                raise ValueError(
                    f"Freiburg folder '{folder_name}' maps to multiple labels: "
                    f"{folder_to_label[folder_name]}, {label_name}"
                )
            folder_to_label[folder_name] = label_name

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
        if not relative_path.parts:
            continue
        folder_name = relative_path.parts[0]
        mapped_label = folder_to_label.get(folder_name)
        if mapped_label is None:
            continue
        image_path = images_root / relative_path
        if not image_path.exists():
            raise ValueError(f"Freiburg split entry '{relative_path_str}' is missing image data")
        rows.append(
            {
                "image_path": to_manifest_relative_path(image_path, manifest_dir),
                "source": "FreiburgGroceriesDataset",
                "original_label": folder_name,
                "mapped_label": mapped_label,
                "split": final_split,
                "is_target_domain": "false",
                "capture_condition": "public_packaged_scene",
                "container_type": "packaged",
                "notes": f"official_{source_split}",
            }
        )

    return rows


def deduplicate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique_rows: list[dict[str, str]] = []
    seen: dict[tuple[str, str], dict[str, str]] = {}

    for row in rows:
        key = (row["source"], row["image_path"])
        existing = seen.get(key)
        if existing is None:
            seen[key] = row
            unique_rows.append(row)
            continue
        if any(existing[column] != row[column] for column in MANIFEST_COLUMNS):
            raise ValueError(
                f"conflicting manifest rows found for source '{row['source']}' and image "
                f"'{row['image_path']}'"
            )

    return unique_rows


def write_manifest(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "rows_total": len(rows),
        "rows_by_source": dict(sorted(Counter(row["source"] for row in rows).items())),
        "rows_by_split": dict(sorted(Counter(row["split"] for row in rows).items())),
        "rows_by_class": dict(sorted(Counter(row["mapped_label"] for row in rows).items())),
    }


def build_release_v1_assets(
    release_spec_path: Path,
    catalog_path: Path,
    taxonomy_output_path: Path,
    manifest_output_path: Path,
    grocery_root: Path,
    freiburg_root: Path,
) -> ReleaseBuildResult:
    selected_labels = load_selected_labels(release_spec_path)
    catalog_entries = load_catalog_entries(catalog_path)
    taxonomy_rows = build_taxonomy_rows(selected_labels, catalog_entries)
    write_taxonomy(taxonomy_rows, taxonomy_output_path)

    manifest_rows = build_grocery_rows(
        selected_labels,
        catalog_entries,
        grocery_root,
        manifest_output_path,
    )
    manifest_rows.extend(
        build_freiburg_rows(
            selected_labels,
            catalog_entries,
            freiburg_root,
            manifest_output_path,
        )
    )
    manifest_rows = deduplicate_rows(manifest_rows)
    manifest_rows.sort(
        key=lambda row: (row["source"], row["split"], row["mapped_label"], row["image_path"])
    )
    write_manifest(manifest_rows, manifest_output_path)

    summary = build_summary(manifest_rows)
    return ReleaseBuildResult(
        taxonomy_rows_written=len(taxonomy_rows),
        manifest_rows_written=len(manifest_rows),
        summary=summary,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build taxonomy and public manifest assets for the current V1 release labels."
    )
    parser.add_argument(
        "--release-spec",
        type=Path,
        default=Path("specs/labels/release_v1.json"),
        help="Path to the V1 release selection JSON",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("specs/labels/discovered_label_catalog.json"),
        help="Path to the discovery catalog JSON",
    )
    parser.add_argument(
        "--taxonomy-output",
        type=Path,
        default=Path("data/labels/release_v1_taxonomy.csv"),
        help="Output taxonomy CSV path",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("data/manifests/public_release_v1.csv"),
        help="Output public manifest CSV path",
    )
    parser.add_argument(
        "--grocery-root",
        type=Path,
        default=Path("data/external_datasets/GroceryStoreDataset"),
        help="Path to the local GroceryStoreDataset root",
    )
    parser.add_argument(
        "--freiburg-root",
        type=Path,
        default=Path("data/external_datasets/freiburg_groceries_dataset"),
        help="Path to the local Freiburg dataset root",
    )
    args = parser.parse_args()

    result = build_release_v1_assets(
        release_spec_path=args.release_spec,
        catalog_path=args.catalog,
        taxonomy_output_path=args.taxonomy_output,
        manifest_output_path=args.manifest_output,
        grocery_root=args.grocery_root,
        freiburg_root=args.freiburg_root,
    )

    print(
        json.dumps(
            {
                "taxonomy_rows_written": result.taxonomy_rows_written,
                "manifest_rows_written": result.manifest_rows_written,
                "summary": result.summary,
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
