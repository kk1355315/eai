import csv
import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from tools.release_v1_assets import build_release_v1_assets, parse_fine_group


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ReleaseV1AssetsTests(unittest.TestCase):
    def write_json(self, path: Path, payload: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def touch(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")
        return path

    def test_parse_fine_group_returns_expected_members(self) -> None:
        coarse, members = parse_fine_group("Potato:{Floury-Potato,Solid-Potato}")
        self.assertEqual(coarse, "Potato")
        self.assertEqual(members, {"Floury-Potato", "Solid-Potato"})

    def test_build_release_v1_assets_writes_taxonomy_and_manifest(self) -> None:
        with workspace_tempdir() as tmpdir:
            release_spec = self.write_json(
                tmpdir / "specs" / "labels" / "release_v1.json",
                {"selected_labels": ["apple", "packaged_dairy_milk"]},
            )
            catalog = self.write_json(
                tmpdir / "specs" / "labels" / "catalog.json",
                {
                    "labels": [
                        {
                            "label_name": "apple",
                            "source_datasets": ["GroceryStoreDataset"],
                            "source_classes": [
                                {
                                    "dataset": "GroceryStoreDataset",
                                    "level": "coarse",
                                    "value": "Apple",
                                }
                            ],
                            "foodkeeper_ids": [1],
                            "storage_field": "DOP_Refrigerate",
                            "storage_min_days": 1,
                            "storage_max_days": 2,
                            "notes": "apple",
                        },
                        {
                            "label_name": "packaged_dairy_milk",
                            "source_datasets": ["Freiburg Groceries"],
                            "source_classes": [
                                {
                                    "dataset": "Freiburg Groceries",
                                    "level": "folder",
                                    "value": "MILK",
                                }
                            ],
                            "foodkeeper_ids": [2],
                            "storage_field": "Refrigerate_After_Opening",
                            "storage_min_days": 5,
                            "storage_max_days": 7,
                            "notes": "milk",
                        },
                    ]
                },
            )

            grocery_root = tmpdir / "data" / "external_datasets" / "GroceryStoreDataset" / "dataset"
            self.touch(grocery_root / "train" / "Fruit" / "Apple" / "Apple_001.jpg")
            self.touch(grocery_root / "val" / "Fruit" / "Apple" / "Apple_002.jpg")
            self.touch(grocery_root / "test" / "Fruit" / "Apple" / "Apple_003.jpg")

            freiburg_root = tmpdir / "data" / "external_datasets" / "freiburg_groceries_dataset"
            self.touch(freiburg_root / "images" / "MILK" / "MILK0001.png")
            splits_dir = freiburg_root / "splits"
            splits_dir.mkdir(parents=True, exist_ok=True)
            (splits_dir / "train0.txt").write_text("MILK/MILK0001.png 7\n", encoding="utf-8")
            (splits_dir / "test0.txt").write_text("", encoding="utf-8")

            taxonomy_output = tmpdir / "data" / "labels" / "release_v1_taxonomy.csv"
            manifest_output = tmpdir / "data" / "manifests" / "public_release_v1.csv"

            result = build_release_v1_assets(
                release_spec_path=release_spec,
                catalog_path=catalog,
                taxonomy_output_path=taxonomy_output,
                manifest_output_path=manifest_output,
                grocery_root=tmpdir / "data" / "external_datasets" / "GroceryStoreDataset",
                freiburg_root=freiburg_root,
            )

            with taxonomy_output.open("r", encoding="utf-8", newline="") as handle:
                taxonomy_rows = list(csv.DictReader(handle))
            with manifest_output.open("r", encoding="utf-8", newline="") as handle:
                manifest_rows = list(csv.DictReader(handle))

            self.assertEqual(result.taxonomy_rows_written, 2)
            self.assertEqual(len(taxonomy_rows), 2)
            self.assertEqual(result.manifest_rows_written, 4)
            self.assertEqual(len(manifest_rows), 4)
            self.assertEqual({row["mapped_label"] for row in manifest_rows}, {"apple", "packaged_dairy_milk"})
