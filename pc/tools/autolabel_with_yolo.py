from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto label bbox with YOLO model")
    parser.add_argument("--model", required=True, help="Path to best.pt")
    parser.add_argument("--images-dir", required=True, help="Input images directory")
    parser.add_argument("--out-csv", required=True, help="Output csv path")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    images_dir = Path(args.images_dir).resolve()
    out_csv = Path(args.out_csv).resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Images dir not found: {images_dir}")

    model = YOLO(str(model_path))
    image_files = sorted([p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[list[object]] = []

    for p in image_files:
        # Use stream=False for deterministic one-image result list
        results = model.predict(source=str(p), conf=args.conf, verbose=False, device="cpu")

        x = y = w = h = 0
        score = 0.0
        note = "no_det"

        if results and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            # Pick highest-confidence bbox as plate bbox
            best_idx = int(boxes.conf.argmax().item())
            xyxy = boxes.xyxy[best_idx].tolist()
            score = float(boxes.conf[best_idx].item())
            x1, y1, x2, y2 = xyxy
            x = int(round(x1))
            y = int(round(y1))
            w = int(round(max(0.0, x2 - x1)))
            h = int(round(max(0.0, y2 - y1)))
            note = "auto_yolo"

        rows.append([p.name, "", x, y, w, h, f"{note};conf={score:.4f}"])

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "plate_text", "x", "y", "w", "h", "notes"])
        writer.writerows(rows)

    valid = sum(1 for r in rows if int(r[4]) > 1 and int(r[5]) > 1)
    print(f"images={len(rows)}")
    print(f"valid_bbox={valid}")
    print(f"output={out_csv}")


if __name__ == "__main__":
    main()
