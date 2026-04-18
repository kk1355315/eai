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


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


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
    stage: str,
    taxonomy_rows: list[dict[str, str]],
    rows: list[dict[str, str]],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    taxonomy_classes = [row["class_name"] for row in taxonomy_rows]
    observed_classes = sorted({row["mapped_label"].strip() for row in rows})
    rows_by_split = {split: len(split_rows(rows)[split]) for split in ("train", "val", "test")}
    summary: dict[str, object] = {
        "stage": stage,
        "taxonomy_class_count": len(taxonomy_classes),
        "observed_class_count": len(observed_classes),
        "observed_classes": observed_classes,
        "missing_classes": [name for name in taxonomy_classes if name not in observed_classes],
        "rows_total": len(rows),
        "rows_by_split": rows_by_split,
        "rows_by_source": rows_to_counter(rows, "source"),
        "rows_by_class": rows_to_counter(rows, "mapped_label"),
    }
    if extra:
        summary.update(extra)
    return summary


def write_summary(summary: dict[str, object], output_path: Path) -> None:
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def prepare_stage_a(
    public_manifest_path: Path,
    taxonomy_path: Path,
    output_dir: Path,
) -> PreparationSummary:
    validate_or_raise(public_manifest_path, taxonomy_path)
    taxonomy_rows = load_taxonomy_rows(taxonomy_path)
    public_rows = load_manifest_rows(public_manifest_path)

    non_public_rows = [row for row in public_rows if parse_bool(row["is_target_domain"])]
    if non_public_rows:
        raise ValueError("stage_a public manifest contains target-domain rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_label_map(taxonomy_rows, output_dir / "label_map.json")

    split_map = split_rows(public_rows)
    for split, rows in split_map.items():
        write_manifest_rows(rows, output_dir / f"{split}.csv")

    summary = build_summary(
        "stage_a",
        taxonomy_rows,
        public_rows,
        extra={"coverage_note": "public-only coverage may be partial before Stage B fine-tuning"},
    )
    write_summary(summary, output_dir / "summary.json")
    return PreparationSummary(stage="stage_a", output_dir=output_dir, summary=summary)


def prepare_stage_b(
    target_manifest_path: Path,
    taxonomy_path: Path,
    output_dir: Path,
    public_manifest_path: Path | None = None,
    mix_public_train: bool = False,
) -> PreparationSummary:
    validate_or_raise(target_manifest_path, taxonomy_path)
    taxonomy_rows = load_taxonomy_rows(taxonomy_path)
    target_rows = load_manifest_rows(target_manifest_path)

    if not target_rows:
        raise ValueError("target manifest has no rows")

    non_target_rows = [row for row in target_rows if not parse_bool(row["is_target_domain"])]
    if non_target_rows:
        raise ValueError("stage_b target manifest contains non-target rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_label_map(taxonomy_rows, output_dir / "label_map.json")

    split_map = split_rows(target_rows)
    for split, rows in split_map.items():
        write_manifest_rows(rows, output_dir / f"{split}.csv")

    extra: dict[str, object] = {
        "coverage_note": "Stage B should carry the classes that public data does not cover well",
        "mixed_public_train_rows": 0,
    }

    if mix_public_train:
        if public_manifest_path is None:
            raise ValueError("mix_public_train requires a public manifest path")

        validate_or_raise(public_manifest_path, taxonomy_path)
        public_rows = load_manifest_rows(public_manifest_path)
        public_train_rows = [
            row
            for row in public_rows
            if row["split"].strip() == "train" and not parse_bool(row["is_target_domain"])
        ]
        mixed_train_rows = split_map["train"] + public_train_rows
        write_manifest_rows(mixed_train_rows, output_dir / "train_mixed.csv")
        extra["mixed_public_train_rows"] = len(public_train_rows)

    summary = build_summary("stage_b", taxonomy_rows, target_rows, extra=extra)
    write_summary(summary, output_dir / "summary.json")
    return PreparationSummary(stage="stage_b", output_dir=output_dir, summary=summary)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Stage A or Stage B training inputs from normalized manifests."
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    stage_a = subparsers.add_parser("stage_a", help="Prepare public-data Stage A inputs")
    stage_a.add_argument(
        "--public-manifest",
        type=Path,
        default=Path("data/manifests/public_stage_a.csv"),
        help="Path to the public Stage A manifest",
    )
    stage_a.add_argument(
        "--taxonomy",
        type=Path,
        default=Path("docs/taxonomy/v1_labels.csv"),
        help="Path to the taxonomy CSV",
    )
    stage_a.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/runs/stage_a_prep"),
        help="Directory where prepared Stage A artifacts will be written",
    )

    stage_b = subparsers.add_parser("stage_b", help="Prepare fridge-domain Stage B inputs")
    stage_b.add_argument(
        "--target-manifest",
        type=Path,
        default=Path("data/manifests/target_stage_b.csv"),
        help="Path to the target-domain Stage B manifest",
    )
    stage_b.add_argument(
        "--taxonomy",
        type=Path,
        default=Path("docs/taxonomy/v1_labels.csv"),
        help="Path to the taxonomy CSV",
    )
    stage_b.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/runs/stage_b_prep"),
        help="Directory where prepared Stage B artifacts will be written",
    )
    stage_b.add_argument(
        "--public-manifest",
        type=Path,
        default=Path("data/manifests/public_stage_a.csv"),
        help="Optional public manifest path used when mixing public train rows into Stage B",
    )
    stage_b.add_argument(
        "--mix-public-train",
        action="store_true",
        help="Append public train rows into a train_mixed.csv output for Stage B",
    )

    args = parser.parse_args()

    if args.stage == "stage_a":
        result = prepare_stage_a(args.public_manifest, args.taxonomy, args.output_dir)
    else:
        result = prepare_stage_b(
            target_manifest_path=args.target_manifest,
            taxonomy_path=args.taxonomy,
            output_dir=args.output_dir,
            public_manifest_path=args.public_manifest,
            mix_public_train=args.mix_public_train,
        )

    print(f"prepared {result.stage} inputs under {result.output_dir}")
    print(json.dumps(result.summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
