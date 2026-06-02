#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ultralytics import YOLO


def image_files(source: Path) -> list[Path]:
    return sorted(
        path
        for path in source.rglob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    args.weights = args.weights.resolve()
    args.source = args.source.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    images = image_files(args.source)
    model = YOLO(str(args.weights))
    results = model.predict(
        source=[str(path) for path in images],
        imgsz=args.imgsz,
        conf=args.conf,
        device=args.device,
        save=True,
        save_txt=True,
        save_conf=True,
        project=str(args.output.parent),
        name=args.output.name,
        exist_ok=True,
        verbose=False,
    )

    records = []
    overall_counts: Counter[str] = Counter()
    for image_path, result in zip(images, results):
        width, height = int(result.orig_shape[1]), int(result.orig_shape[0])
        detections = []
        counts: Counter[str] = Counter()
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy().tolist()
            xywhn = boxes.xywhn.cpu().numpy().tolist()
            classes = boxes.cls.cpu().numpy().astype(int).tolist()
            confidences = boxes.conf.cpu().numpy().tolist()
            for idx, (class_id, confidence, box_xyxy, box_xywhn) in enumerate(
                zip(classes, confidences, xyxy, xywhn),
                start=1,
            ):
                class_name = model.names[class_id]
                counts[class_name] += 1
                overall_counts[class_name] += 1
                detections.append(
                    {
                        "detection_id": idx,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(float(confidence), 6),
                        "bbox_xyxy_px": [round(float(value), 2) for value in box_xyxy],
                        "bbox_xywh_norm": [round(float(value), 8) for value in box_xywhn],
                    }
                )
        records.append(
            {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "image_width": width,
                "image_height": height,
                "total_count": sum(counts.values()),
                "counts_by_class": dict(sorted(counts.items())),
                "detections": detections,
            }
        )

    summary = {
        "weights": str(args.weights),
        "source": str(args.source),
        "image_count": len(images),
        "conf_threshold": args.conf,
        "imgsz": args.imgsz,
        "overall_counts": dict(sorted(overall_counts.items())),
        "images_without_detection": sum(1 for record in records if record["total_count"] == 0),
    }
    (args.output / "predictions_db.json").write_text(
        json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
