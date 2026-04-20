from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_v1_assets import build_release_v1_assets
from tools.validate_manifest import resolve_image_path, validate_manifest

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
class PreparationSummary:
    stage: str
    output_dir: Path
    summary: dict[str, object]


def validate_or_raise(manifest_path: Path, taxonomy_path: Path) -> None:
    result = validate_manifest(manifest_path, taxonomy_path)
    if result.errors:
        raise ValueError("\n".join(result.errors))


def load_taxonomy_rows(taxonomy_path: Path) -> list[dict[str, str]]:
    with taxonomy_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted(rows, key=lambda row: int(row["class_id"]))


def load_manifest_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized = dict(row)
        normalized["_resolved_image_path"] = str(
            resolve_image_path(manifest_path, row["image_path"].strip()).resolve()
        )
        normalized_rows.append(normalized)
    return normalized_rows


def split_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    return {
        split: [row for row in rows if row["split"].strip() == split]
        for split in ("train", "val", "test")
    }


def rows_to_counter(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counter = Counter(row[key].strip() for row in rows if row.get(key, "").strip())
    return dict(sorted(counter.items()))


def make_output_relative_path(output_file: Path, resolved_image_path: str) -> str:
    relative_path = os.path.relpath(
        Path(resolved_image_path).resolve(),
        start=output_file.parent.resolve(),
    )
    return Path(relative_path).as_posix()


def write_manifest_rows(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            serialized = {column: row.get(column, "") for column in OUTPUT_COLUMNS}
            serialized["image_path"] = make_output_relative_path(
                output_path,
                row["_resolved_image_path"],
            )
            writer.writerow(serialized)


def write_label_map(taxonomy_rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [
                {
                    "class_id": int(row["class_id"]),
                    "class_name": row["class_name"],
                    "class_group": row["class_group"],
                    "status": row["status"],
                }
                for row in taxonomy_rows
            ],
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_summary(
    taxonomy_rows: list[dict[str, str]],
    rows: list[dict[str, str]],
    asset_summary: dict[str, object],
) -> dict[str, object]:
    taxonomy_classes = [row["class_name"] for row in taxonomy_rows]
    observed_classes = sorted({row["mapped_label"].strip() for row in rows})
    return {
        "stage": "stage_a",
        "taxonomy_class_count": len(taxonomy_classes),
        "observed_class_count": len(observed_classes),
        "observed_classes": observed_classes,
        "missing_classes": [name for name in taxonomy_classes if name not in observed_classes],
        "rows_total": len(rows),
        "rows_by_split": {split: len(split_rows(rows)[split]) for split in ("train", "val", "test")},
        "rows_by_source": rows_to_counter(rows, "source"),
        "rows_by_class": rows_to_counter(rows, "mapped_label"),
        "asset_summary": asset_summary,
    }


def write_summary(summary: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def prepare_stage_a(args: argparse.Namespace) -> PreparationSummary:
    asset_result = build_release_v1_assets(
        release_spec_path=args.release_spec,
        catalog_path=args.catalog,
        taxonomy_output_path=args.taxonomy_output,
        manifest_output_path=args.manifest_output,
        grocery_root=args.grocery_root,
        freiburg_root=args.freiburg_root,
    )

    validate_or_raise(args.manifest_output, args.taxonomy_output)
    taxonomy_rows = load_taxonomy_rows(args.taxonomy_output)
    manifest_rows = load_manifest_rows(args.manifest_output)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_label_map(taxonomy_rows, args.output_dir / "label_map.json")

    split_map = split_rows(manifest_rows)
    for split, rows in split_map.items():
        write_manifest_rows(rows, args.output_dir / f"{split}.csv")

    summary = build_summary(taxonomy_rows, manifest_rows, asset_result.summary)
    write_summary(summary, args.output_dir / "summary.json")
    return PreparationSummary(stage="stage_a", output_dir=args.output_dir, summary=summary)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build V1 public assets and prepare Stage A split files."
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    stage_a = subparsers.add_parser("stage_a", help="Prepare V1 public-data Stage A inputs")
    stage_a.add_argument(
        "--release-spec",
        type=Path,
        default=Path("specs/labels/release_v1.json"),
        help="Path to the V1 release selection JSON",
    )
    stage_a.add_argument(
        "--catalog",
        type=Path,
        default=Path("specs/labels/discovered_label_catalog.json"),
        help="Path to the discovery catalog JSON",
    )
    stage_a.add_argument(
        "--taxonomy-output",
        type=Path,
        default=Path("data/labels/release_v1_taxonomy.csv"),
        help="Output taxonomy CSV path",
    )
    stage_a.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("data/manifests/public_release_v1.csv"),
        help="Output public manifest CSV path",
    )
    stage_a.add_argument(
        "--grocery-root",
        type=Path,
        default=Path("data/external_datasets/GroceryStoreDataset"),
        help="Path to the local GroceryStoreDataset root",
    )
    stage_a.add_argument(
        "--freiburg-root",
        type=Path,
        default=Path("data/external_datasets/freiburg_groceries_dataset"),
        help="Path to the local Freiburg dataset root",
    )
    stage_a.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/runs/v1_stage_a_prep"),
        help="Directory where prepared Stage A artifacts will be written",
    )

    args = parser.parse_args()
    result = prepare_stage_a(args)
    print(f"prepared {result.stage} inputs under {result.output_dir}")
    print(json.dumps(result.summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
