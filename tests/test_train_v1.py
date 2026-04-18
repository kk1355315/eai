import csv
import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from training.train_v1 import prepare_stage_a, prepare_stage_b
from tools.validate_manifest import resolve_image_path


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class TrainV1PreparationTests(unittest.TestCase):
    def write_csv(self, directory: Path, name: str, rows: list[str]) -> Path:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_prepare_stage_a_writes_split_manifests_and_summary(self) -> None:
        with workspace_tempdir() as tmpdir:
            manifests_dir = tmpdir / "data" / "manifests"
            image_dir = tmpdir / "data" / "images"
            image_dir.mkdir(parents=True)
            train_image = image_dir / "apple.jpg"
            val_image = image_dir / "milk.jpg"
            train_image.write_bytes(b"fake")
            val_image.write_bytes(b"fake")

            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                    "1,milk,dairy_egg,active,27,test",
                    "2,shrimp,animal_protein,active,151,test",
                ],
            )
            public_manifest = self.write_csv(
                manifests_dir,
                "public_stage_a.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain,capture_condition,container_type,notes",
                    "../images/apple.jpg,GroceryStoreDataset,Golden-Delicious,apple,train,false,public_store_scene,loose,test",
                    "../images/milk.jpg,FreiburgGroceriesDataset,MILK,milk,val,false,public_packaged_scene,packaged,test",
                ],
            )

            output_dir = tmpdir / "training_output"
            result = prepare_stage_a(public_manifest, taxonomy, output_dir)

            self.assertEqual(result.summary["stage"], "stage_a")
            self.assertEqual(result.summary["rows_total"], 2)
            self.assertEqual(result.summary["missing_classes"], ["shrimp"])

            train_rows = self.read_csv(output_dir / "train.csv")
            self.assertEqual(len(train_rows), 1)
            self.assertFalse(Path(train_rows[0]["image_path"]).is_absolute())
            self.assertTrue(
                resolve_image_path(output_dir / "train.csv", train_rows[0]["image_path"]).exists()
            )

            label_map = json.loads((output_dir / "label_map.json").read_text(encoding="utf-8"))
            self.assertEqual(label_map[0]["class_name"], "apple")
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["observed_class_count"], 2)

    def test_prepare_stage_b_requires_non_empty_target_manifest(self) -> None:
        with workspace_tempdir() as tmpdir:
            manifests_dir = tmpdir / "data" / "manifests"
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                ],
            )
            target_manifest = self.write_csv(
                manifests_dir,
                "target_stage_b.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain,capture_condition,container_type,notes",
                ],
            )

            with self.assertRaisesRegex(ValueError, "target manifest has no rows"):
                prepare_stage_b(target_manifest, taxonomy, tmpdir / "training_output")

    def test_prepare_stage_b_can_mix_public_train_rows(self) -> None:
        with workspace_tempdir() as tmpdir:
            manifests_dir = tmpdir / "data" / "manifests"
            image_dir = tmpdir / "data" / "images"
            image_dir.mkdir(parents=True)
            (image_dir / "egg.jpg").write_bytes(b"fake")
            (image_dir / "apple.jpg").write_bytes(b"fake")

            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                    "1,egg,dairy_egg,active,21,test",
                ],
            )
            target_manifest = self.write_csv(
                manifests_dir,
                "target_stage_b.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain,capture_condition,container_type,notes",
                    "../images/egg.jpg,FridgeCam,egg,egg,train,true,fridge_light,carton,test",
                ],
            )
            public_manifest = self.write_csv(
                manifests_dir,
                "public_stage_a.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain,capture_condition,container_type,notes",
                    "../images/apple.jpg,GroceryStoreDataset,Golden-Delicious,apple,train,false,public_store_scene,loose,test",
                ],
            )

            output_dir = tmpdir / "training_output"
            result = prepare_stage_b(
                target_manifest_path=target_manifest,
                taxonomy_path=taxonomy,
                output_dir=output_dir,
                public_manifest_path=public_manifest,
                mix_public_train=True,
            )

            self.assertEqual(result.summary["stage"], "stage_b")
            self.assertEqual(result.summary["mixed_public_train_rows"], 1)
            mixed_rows = self.read_csv(output_dir / "train_mixed.csv")
            self.assertEqual(len(mixed_rows), 2)
