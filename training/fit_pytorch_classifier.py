from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_manifest import resolve_image_path
from training.train_v1 import prepare_stage_a


@dataclass
class FitResult:
    stage: str
    prepared_dir: Path
    fit_dir: Path
    metrics: dict[str, object]


def find_missing_training_dependencies() -> list[str]:
    required = ["torch", "torchvision"]
    return [name for name in required if importlib.util.find_spec(name) is None]


def ensure_pytorch_dependencies() -> None:
    missing = find_missing_training_dependencies()
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            "missing training dependencies: "
            f"{names}. Install them with `pip install -r training/requirements-pytorch.txt`."
        )


def import_pytorch_stack() -> dict[str, Any]:
    ensure_pytorch_dependencies()

    import torch
    from torch import nn, optim
    from torch.utils.data import DataLoader
    from torchvision import models, transforms

    return {
        "torch": torch,
        "nn": nn,
        "optim": optim,
        "DataLoader": DataLoader,
        "models": models,
        "transforms": transforms,
    }


def read_label_map(label_map_path: Path) -> list[dict[str, object]]:
    return json.loads(label_map_path.read_text(encoding="utf-8"))


def read_manifest_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized = dict(row)
        normalized["resolved_image_path"] = str(
            resolve_image_path(manifest_path, row["image_path"].strip()).resolve()
        )
        normalized_rows.append(normalized)
    return normalized_rows


class ManifestImageDataset:
    def __init__(
        self,
        rows: list[dict[str, str]],
        label_to_index: dict[str, int],
        transform: Any,
    ) -> None:
        self.rows = rows
        self.label_to_index = label_to_index
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        from PIL import Image

        row = self.rows[index]
        image_path = Path(row["resolved_image_path"])
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            if self.transform is not None:
                rgb_image = self.transform(rgb_image)
        label = self.label_to_index[row["mapped_label"].strip()]
        return rgb_image, label


def set_random_seed(seed: int, torch: Any) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(transforms: Any, image_size: int, is_train: bool) -> Any:
    steps: list[Any] = [transforms.Resize((image_size, image_size))]
    if is_train:
        steps.append(transforms.RandomHorizontalFlip())
    steps.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )
    return transforms.Compose(steps)


def build_model(models: Any, nn: Any, model_name: str, num_classes: int, weights: str) -> Any:
    use_pretrained = weights == "imagenet"

    if model_name == "mobilenet_v2":
        if hasattr(models, "MobileNet_V2_Weights"):
            model = models.mobilenet_v2(
                weights=models.MobileNet_V2_Weights.DEFAULT if use_pretrained else None
            )
        else:
            model = models.mobilenet_v2(pretrained=use_pretrained)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
        return model

    if model_name == "resnet18":
        if hasattr(models, "ResNet18_Weights"):
            model = models.resnet18(
                weights=models.ResNet18_Weights.DEFAULT if use_pretrained else None
            )
        else:
            model = models.resnet18(pretrained=use_pretrained)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model

    raise ValueError(f"unsupported model_name '{model_name}'")


def evaluate_loader(
    loader: Any,
    model: Any,
    criterion: Any,
    device: Any,
    torch: Any,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)

            total_loss += float(loss.item()) * labels.size(0)
            predictions = logits.argmax(dim=1)
            total_correct += int((predictions == labels).sum().item())
            total_examples += int(labels.size(0))

    if total_examples == 0:
        return {"loss": 0.0, "accuracy": 0.0}

    return {
        "loss": total_loss / total_examples,
        "accuracy": total_correct / total_examples,
    }


def train_one_epoch(
    loader: Any,
    model: Any,
    criterion: Any,
    optimizer: Any,
    device: Any,
) -> dict[str, float]:
    model.train()
    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        total_loss += float(loss.item()) * labels.size(0)
        predictions = logits.argmax(dim=1)
        total_correct += int((predictions == labels).sum().item())
        total_examples += int(labels.size(0))

    if total_examples == 0:
        return {"loss": 0.0, "accuracy": 0.0}

    return {
        "loss": total_loss / total_examples,
        "accuracy": total_correct / total_examples,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def choose_device(torch: Any, requested_device: str) -> Any:
    if requested_device == "cpu":
        return torch.device("cpu")
    if requested_device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("cuda requested but torch.cuda.is_available() is false")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def fit_classifier(args: argparse.Namespace) -> FitResult:
    prep_result = prepare_stage_a(args)
    prepared_dir = prep_result.output_dir

    stack = import_pytorch_stack()
    torch = stack["torch"]
    nn = stack["nn"]
    optim = stack["optim"]
    DataLoader = stack["DataLoader"]
    models = stack["models"]
    transforms = stack["transforms"]

    label_map = read_label_map(prepared_dir / "label_map.json")
    class_names = [str(entry["class_name"]) for entry in label_map]
    label_to_index = {name: index for index, name in enumerate(class_names)}

    train_rows = read_manifest_rows(prepared_dir / "train.csv")
    val_rows = read_manifest_rows(prepared_dir / "val.csv")
    test_rows = read_manifest_rows(prepared_dir / "test.csv")

    if not train_rows:
        raise ValueError("prepared train split has no rows")
    if not val_rows:
        raise ValueError("prepared val split has no rows")

    set_random_seed(args.seed, torch)
    device = choose_device(torch, args.device)

    train_dataset = ManifestImageDataset(
        train_rows,
        label_to_index=label_to_index,
        transform=build_transforms(transforms, args.image_size, is_train=True),
    )
    val_dataset = ManifestImageDataset(
        val_rows,
        label_to_index=label_to_index,
        transform=build_transforms(transforms, args.image_size, is_train=False),
    )
    test_dataset = ManifestImageDataset(
        test_rows,
        label_to_index=label_to_index,
        transform=build_transforms(transforms, args.image_size, is_train=False),
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    model = build_model(
        models=models,
        nn=nn,
        model_name=args.model_name,
        num_classes=len(class_names),
        weights=args.weights,
    )
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )

    history: list[dict[str, float | int]] = []
    best_val_accuracy = -1.0
    best_epoch = 0
    args.fit_output_dir.mkdir(parents=True, exist_ok=True)
    best_checkpoint_path = args.fit_output_dir / "best.pt"
    last_checkpoint_path = args.fit_output_dir / "last.pt"

    for epoch in range(1, args.epochs + 1):
        train_metrics = train_one_epoch(
            loader=train_loader,
            model=model,
            criterion=criterion,
            optimizer=optimizer,
            device=device,
        )
        val_metrics = evaluate_loader(
            loader=val_loader,
            model=model,
            criterion=criterion,
            device=device,
            torch=torch,
        )
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_accuracy": train_metrics["accuracy"],
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_metrics["accuracy"],
        }
        history.append(epoch_metrics)

        checkpoint_payload = {
            "epoch": epoch,
            "model_name": args.model_name,
            "weights": args.weights,
            "class_names": class_names,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": epoch_metrics,
        }
        torch.save(checkpoint_payload, last_checkpoint_path)

        if val_metrics["accuracy"] >= best_val_accuracy:
            best_val_accuracy = val_metrics["accuracy"]
            best_epoch = epoch
            torch.save(checkpoint_payload, best_checkpoint_path)

    best_checkpoint = torch.load(best_checkpoint_path, map_location=device)
    model.load_state_dict(best_checkpoint["model_state_dict"])

    test_metrics = evaluate_loader(
        loader=test_loader,
        model=model,
        criterion=criterion,
        device=device,
        torch=torch,
    )

    prepared_summary = json.loads((prepared_dir / "summary.json").read_text(encoding="utf-8"))
    metrics = {
        "stage": "stage_a",
        "model_name": args.model_name,
        "weights": args.weights,
        "device": str(device),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "image_size": args.image_size,
        "num_classes": len(class_names),
        "prepared_summary": prepared_summary,
        "rows": {
            "train": len(train_rows),
            "val": len(val_rows),
            "test": len(test_rows),
        },
        "best_epoch": best_epoch,
        "best_val_accuracy": best_val_accuracy,
        "test_loss": test_metrics["loss"],
        "test_accuracy": test_metrics["accuracy"],
    }

    write_json(args.fit_output_dir / "history.json", history)
    write_json(args.fit_output_dir / "metrics.json", metrics)
    return FitResult(
        stage="stage_a",
        prepared_dir=prepared_dir,
        fit_dir=args.fit_output_dir,
        metrics=metrics,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare V1 release assets and fit a PyTorch image classifier."
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    stage_a = subparsers.add_parser("stage_a", help="Fit a public-data V1 Stage A classifier")
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
    stage_a.add_argument(
        "--fit-output-dir",
        type=Path,
        default=Path("training/runs/v1_stage_a_fit"),
        help="Directory where fitted Stage A artifacts will be written",
    )
    stage_a.add_argument(
        "--model-name",
        choices=("mobilenet_v2", "resnet18"),
        default="mobilenet_v2",
        help="Backbone architecture",
    )
    stage_a.add_argument(
        "--weights",
        choices=("none", "imagenet"),
        default="none",
        help="Initialization weights",
    )
    stage_a.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Number of training epochs",
    )
    stage_a.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Mini-batch size",
    )
    stage_a.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="AdamW learning rate",
    )
    stage_a.add_argument(
        "--weight-decay",
        type=float,
        default=1e-4,
        help="AdamW weight decay",
    )
    stage_a.add_argument(
        "--image-size",
        type=int,
        default=224,
        help="Square input image size",
    )
    stage_a.add_argument(
        "--num-workers",
        type=int,
        default=0,
        help="PyTorch DataLoader worker count",
    )
    stage_a.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Execution device",
    )
    stage_a.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = fit_classifier(args)
    except RuntimeError as error:
        print(str(error))
        return 1

    print(f"prepared inputs under {result.prepared_dir}")
    print(f"wrote fit artifacts under {result.fit_dir}")
    print(json.dumps(result.metrics, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
