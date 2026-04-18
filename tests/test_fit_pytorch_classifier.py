import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from training.fit_pytorch_classifier import (
    ensure_pytorch_dependencies,
    find_missing_training_dependencies,
    read_label_map,
    read_manifest_rows,
    resolve_split_paths,
)


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class FitPyTorchClassifierTests(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[str]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_dependency_probe_reports_missing_modules(self) -> None:
        with patch("training.fit_pytorch_classifier.importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.side_effect = lambda name: None if name == "torch" else object()
            self.assertEqual(find_missing_training_dependencies(), ["torch"])

    def test_dependency_guard_raises_clear_message(self) -> None:
        with patch(
            "training.fit_pytorch_classifier.find_missing_training_dependencies",
            return_value=["torchvision"],
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "pip install -r training/requirements-pytorch.txt",
            ):
                ensure_pytorch_dependencies()

    def test_read_manifest_rows_resolves_relative_paths(self) -> None:
        with workspace_tempdir() as tmpdir:
            manifests_dir = tmpdir / "data" / "manifests"
            images_dir = tmpdir / "data" / "images"
            images_dir.mkdir(parents=True)
            image_path = images_dir / "apple.jpg"
            image_path.write_bytes(b"fake")

            manifest_path = self.write_csv(
                manifests_dir / "train.csv",
                [
                    "image_path,source,original_label,mapped_label,split,is_target_domain,capture_condition,container_type,notes",
                    "../images/apple.jpg,GroceryStoreDataset,Golden-Delicious,apple,train,false,public_store_scene,loose,test",
                ],
            )

            rows = read_manifest_rows(manifest_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(Path(rows[0]["resolved_image_path"]), image_path.resolve())

    def test_read_label_map_returns_json_payload(self) -> None:
        with workspace_tempdir() as tmpdir:
            label_map_path = tmpdir / "label_map.json"
            label_map_path.write_text(
                json.dumps(
                    [
                        {"class_id": 0, "class_name": "apple", "class_group": "produce"},
                        {"class_id": 1, "class_name": "milk", "class_group": "dairy_egg"},
                    ]
                ),
                encoding="utf-8",
            )
            payload = read_label_map(label_map_path)
            self.assertEqual(payload[1]["class_name"], "milk")

    def test_resolve_split_paths_uses_mixed_train_name(self) -> None:
        prepared_dir = Path("training/runs/stage_b_prep")
        split_paths = resolve_split_paths(prepared_dir, use_mixed_train=True)
        self.assertEqual(split_paths["train"], prepared_dir / "train_mixed.csv")
