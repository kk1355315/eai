import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from training.fit_pytorch_classifier import ensure_pytorch_dependencies, find_missing_training_dependencies


@contextmanager
def workspace_tempdir() -> Path:
    path = Path.cwd() / ".tmp_testdirs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class FitPyTorchClassifierTests(unittest.TestCase):
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
