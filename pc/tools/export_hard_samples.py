from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

from ultralytics import YOLO


def xywhn_to_xyxy(x: float, y: float, w: float, h: float, iw: int, ih: int) -> Tuple[float, float, float, float]:
    cx = x * iw
    cy = y * ih
    bw = w * iw
    bh = h * ih
    x1 = cx - bw / 2.0
    y1 = cy - bh / 2.0
    x2 = cx + bw / 2.0
    y2 = cy + bh / 2.0
    return x1, y1, x2, y2


def iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def read_gt_boxes(label_file: Path, iw: int, ih: int) -> List[Tuple[float, float, float, float]]:
    boxes: List[Tuple[float, float, float, float]] = []
    if not label_file.exists():
        return boxes
    for line in label_file.read_text(encoding="utf-8").splitlines():
        p = line.strip().split()
        if len(p) != 5:
            continue
        _, x, y, w, h = p
        boxes.append(xywhn_to_xyxy(float(x), float(y), float(w), float(h), iw, ih))
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser(description="Export hard samples by model confidence and IoU")
    parser.add_argument("--model", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--conf", type=float, default=0.001)
    parser.add_argument("--miss-iou", type=float, default=0.30)
    parser.add_argument("--low-conf", type=float, default=0.35)
    parser.add_argument("--topk", type=int, default=500)
    args = parser.parse_args()

    model = YOLO(str(Path(args.model).resolve()))
    images_dir = Path(args.images).resolve()
    labels_dir = Path(args.labels).resolve()
    out_csv = Path(args.out_csv).resolve()

    imgs = sorted([p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}])

    hard_rows = []

    for img_path in imgs:
        res = model.predict(source=str(img_path), conf=args.conf, verbose=False, device="cpu")[0]
        ih, iw = res.orig_shape

        label_file = labels_dir / (img_path.stem + ".txt")
        gt_boxes = read_gt_boxes(label_file, iw, ih)
        if not gt_boxes:
            continue

        pred_boxes = []
        pred_conf = []
        if res.boxes is not None and len(res.boxes) > 0:
            for i in range(len(res.boxes)):
                p = res.boxes.xyxy[i].tolist()
                pred_boxes.append((float(p[0]), float(p[1]), float(p[2]), float(p[3])))
                pred_conf.append(float(res.boxes.conf[i].item()))

        min_best_iou = 1.0
        min_best_conf = 1.0
        miss_count = 0

        for gt in gt_boxes:
            best_iou = 0.0
            best_conf = 0.0
            for pb, pc in zip(pred_boxes, pred_conf):
                ov = iou(gt, pb)
                if ov > best_iou:
                    best_iou = ov
                    best_conf = pc
            min_best_iou = min(min_best_iou, best_iou)
            min_best_conf = min(min_best_conf, best_conf if best_iou > 0.0 else 0.0)
            if best_iou < args.miss_iou:
                miss_count += 1

        reason = "ok"
        if miss_count > 0:
            reason = "miss"
        elif min_best_conf < args.low_conf:
            reason = "low_conf"

        if reason != "ok":
            priority = (0 if reason == "miss" else 1, min_best_iou, min_best_conf)
            hard_rows.append([
                img_path.name,
                reason,
                f"{min_best_iou:.4f}",
                f"{min_best_conf:.4f}",
                len(gt_boxes),
                len(pred_boxes),
                miss_count,
                priority,
            ])

    hard_rows.sort(key=lambda r: r[-1])
    if args.topk > 0:
        hard_rows = hard_rows[: args.topk]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "reason", "min_best_iou", "min_best_conf", "gt_count", "pred_count", "miss_count"])
        for r in hard_rows:
            w.writerow(r[:-1])

    miss_n = sum(1 for r in hard_rows if r[1] == "miss")
    low_n = sum(1 for r in hard_rows if r[1] == "low_conf")
    print(f"images={len(imgs)} hard={len(hard_rows)} miss={miss_n} low_conf={low_n}")
    print(f"output={out_csv}")


if __name__ == "__main__":
    main()
