import csv
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from tools.build_public_manifest import build_public_manifest
from tools.validate_manifest import validate_manifest


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class BuildPublicManifestTests(unittest.TestCase):
    def write_csv(self, directory: Path, name: str, rows: list[str]) -> Path:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_builds_manifest_from_grocery_and_freiburg_roots(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                    "1,milk,dairy_egg,active,27,test",
                    "2,tomato,produce,active,306,test",
                ],
            )
            grocery_mapping = self.write_csv(
                tmpdir,
                "grocery_to_v1.csv",
                [
                    "source_dataset,original_fine_label,original_coarse_label,mapped_label,decision,reason",
                    "GroceryStoreDataset,Golden-Delicious,Apple,apple,KEEP,test",
                    "GroceryStoreDataset,Regular-Tomato,Tomato,tomato,KEEP,test",
                    "GroceryStoreDataset,Kiwi,Kiwi,DROP,DROP,test",
                ],
            )
            freiburg_mapping = self.write_csv(
                tmpdir,
                "freiburg_to_v1.csv",
                [
                    "source_dataset,original_label,mapped_label,decision,reason",
                    "FreiburgGroceriesDataset,MILK,milk,KEEP,test",
                    "FreiburgGroceriesDataset,CANDY,DROP,DROP,test",
                ],
            )

            grocery_root = tmpdir / "GroceryStoreDataset"
            apple_dir = grocery_root / "dataset" / "train" / "Fruit" / "Apple" / "Golden-Delicious"
            tomato_dir = grocery_root / "dataset" / "val" / "Vegetables" / "Tomato" / "Regular-Tomato"
            kiwi_dir = grocery_root / "dataset" / "test" / "Fruit" / "Kiwi" / "Kiwi"
            apple_dir.mkdir(parents=True)
            tomato_dir.mkdir(parents=True)
            kiwi_dir.mkdir(parents=True)
            (apple_dir / "apple.jpg").write_bytes(b"fake")
            (tomato_dir / "tomato.png").write_bytes(b"fake")
            (kiwi_dir / "kiwi.jpg").write_bytes(b"fake")

            freiburg_root = tmpdir / "freiburg_groceries_dataset"
            split_dir = freiburg_root / "splits"
            split_dir.mkdir(parents=True)
            (split_dir / "train0.txt").write_text("MILK/MILK0001.png 7\nCANDY/CANDY0001.png 0\n", encoding="utf-8")
            (split_dir / "test0.txt").write_text("MILK/MILK0002.png 7\n", encoding="utf-8")
            milk_dir = tmpdir / "images" / "MILK"
            candy_dir = tmpdir / "images" / "CANDY"
            milk_dir.mkdir(parents=True)
            candy_dir.mkdir(parents=True)
            (milk_dir / "milk1.jpg").write_bytes(b"fake")
            (milk_dir / "MILK0001.png").write_bytes(b"fake")
            (milk_dir / "MILK0002.png").write_bytes(b"fake")
            (candy_dir / "CANDY0001.png").write_bytes(b"fake")

            output = tmpdir / "public_stage_a.csv"

            result = build_public_manifest(
                output_path=output,
                taxonomy_path=taxonomy,
                grocery_root=grocery_root,
                grocery_mapping_path=grocery_mapping,
                freiburg_root=freiburg_root,
                freiburg_mapping_path=freiburg_mapping,
            )

            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(result.rows_written, 4)
            self.assertEqual(result.warnings, [])
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(not Path(row["image_path"]).is_absolute() for row in rows))
            self.assertEqual(
                {(row["source"], row["mapped_label"]) for row in rows},
                {
                    ("GroceryStoreDataset", "apple"),
                    ("GroceryStoreDataset", "tomato"),
                    ("FreiburgGroceriesDataset", "milk"),
                },
            )
            grocery_rows = [row for row in rows if row["source"] == "GroceryStoreDataset"]
            self.assertEqual({row["split"] for row in grocery_rows}, {"train", "val"})
            freiburg_rows = [row for row in rows if row["source"] == "FreiburgGroceriesDataset"]
            self.assertEqual(len(freiburg_rows), 2)
            self.assertEqual({row["split"] for row in freiburg_rows}, {"test", "train"})
            self.assertEqual(validate_manifest(output, taxonomy).errors, [])

    def test_raises_when_dataset_contains_unmapped_label(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                ],
            )
            grocery_mapping = self.write_csv(
                tmpdir,
                "grocery_to_v1.csv",
                [
                    "source_dataset,original_fine_label,original_coarse_label,mapped_label,decision,reason",
                    "GroceryStoreDataset,Golden-Delicious,Apple,apple,KEEP,test",
                ],
            )
            freiburg_mapping = self.write_csv(
                tmpdir,
                "freiburg_to_v1.csv",
                [
                    "source_dataset,original_label,mapped_label,decision,reason",
                    "FreiburgGroceriesDataset,MILK,DROP,DROP,test",
                ],
            )

            grocery_root = tmpdir / "GroceryStoreDataset"
            kiwi_dir = grocery_root / "dataset" / "train" / "Fruit" / "Kiwi" / "Kiwi"
            kiwi_dir.mkdir(parents=True)
            (kiwi_dir / "kiwi.jpg").write_bytes(b"fake")

            freiburg_root = tmpdir / "freiburg_groceries_dataset"
            split_dir = freiburg_root / "splits"
            split_dir.mkdir(parents=True)
            (split_dir / "train0.txt").write_text("", encoding="utf-8")
            (split_dir / "test0.txt").write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unmapped label 'Kiwi'"):
                build_public_manifest(
                    output_path=tmpdir / "public_stage_a.csv",
                    taxonomy_path=taxonomy,
                    grocery_root=grocery_root,
                    grocery_mapping_path=grocery_mapping,
                    freiburg_root=freiburg_root,
                    freiburg_mapping_path=freiburg_mapping,
                )

    def test_deduplicates_duplicate_freiburg_split_entries(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,milk,dairy_egg,active,27,test",
                ],
            )
            grocery_mapping = self.write_csv(
                tmpdir,
                "grocery_to_v1.csv",
                [
                    "source_dataset,original_fine_label,original_coarse_label,mapped_label,decision,reason",
                ],
            )
            freiburg_mapping = self.write_csv(
                tmpdir,
                "freiburg_to_v1.csv",
                [
                    "source_dataset,original_label,mapped_label,decision,reason",
                    "FreiburgGroceriesDataset,MILK,milk,KEEP,test",
                ],
            )

            freiburg_root = tmpdir / "freiburg_groceries_dataset"
            split_dir = freiburg_root / "splits"
            split_dir.mkdir(parents=True)
            (split_dir / "train0.txt").write_text("MILK/MILK0001.png 7\nMILK/MILK0001.png 7\n", encoding="utf-8")
            (split_dir / "test0.txt").write_text("", encoding="utf-8")
            milk_dir = freiburg_root / "images" / "MILK"
            milk_dir.mkdir(parents=True)
            (milk_dir / "MILK0001.png").write_bytes(b"fake")

            output = tmpdir / "public_stage_a.csv"

            result = build_public_manifest(
                output_path=output,
                taxonomy_path=taxonomy,
                grocery_root=tmpdir / "GroceryStoreDataset",
                grocery_mapping_path=grocery_mapping,
                freiburg_root=freiburg_root,
                freiburg_mapping_path=freiburg_mapping,
            )

            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(result.rows_written, 1)
            self.assertEqual(len(rows), 1)
            self.assertTrue(any("deduplicated duplicate manifest row" in warning for warning in result.warnings))
