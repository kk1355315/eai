import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from tools.validate_manifest import validate_manifest


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ValidateManifestTests(unittest.TestCase):
    def write_csv(self, directory: Path, name: str, rows: list[str]) -> Path:
        path = directory / name
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_accepts_manifest_with_required_columns_and_known_labels(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,notes",
                    "0,apple,ingredient,active,test",
                    "1,fried_rice,prepared_food,active,test",
                ],
            )
            image_path = tmpdir / "sample.jpg"
            image_path.write_bytes(b"fake")
            manifest = self.write_csv(
                tmpdir,
                "manifest.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain",
                    f"{image_path},GroceryStoreDataset,apple,apple,train,false",
                ],
            )

            result = validate_manifest(manifest, taxonomy)

            self.assertEqual(result.errors, [])

    def test_rejects_unknown_labels_and_duplicate_image_across_splits(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,notes",
                    "0,apple,ingredient,active,test",
                ],
            )

    def test_rejects_missing_image_and_invalid_split(self) -> None:
        with workspace_tempdir() as tmpdir:
            taxonomy = self.write_csv(
                tmpdir,
                "labels.csv",
                [
                    "class_id,class_name,class_group,status,foodkeeper_targets,notes",
                    "0,apple,produce,active,248,test",
                ],
            )
            missing_image = tmpdir / "missing.jpg"
            manifest = self.write_csv(
                tmpdir,
                "manifest.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain",
                    f"{missing_image},GroceryStoreDataset,apple,apple,dev,false",
                ],
            )

            result = validate_manifest(manifest, taxonomy)

            self.assertEqual(
                result.errors,
                [
                    f"row 2: image_path '{missing_image}' does not exist",
                    "row 2: split 'dev' is not one of train, val, test",
                ],
            )
            image_path = tmpdir / "duplicate.jpg"
            image_path.write_bytes(b"fake")
            manifest = self.write_csv(
                tmpdir,
                "manifest.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain",
                    f"{image_path},GroceryStoreDataset,apple,apple,train,false",
                    f"{image_path},GroceryStoreDataset,banana,banana,val,false",
                ],
            )

            result = validate_manifest(manifest, taxonomy)

            self.assertEqual(
                result.errors,
                [
                    "row 3: mapped_label 'banana' is not present in taxonomy",
                    f"image '{image_path}' appears in multiple splits: train, val",
                ],
            )


if __name__ == "__main__":
    unittest.main()
