from __future__ import annotations

import argparse
import csv
import random
import shutil
from pathlib import Path

import cv2
import numpy as np


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def to_yolo(x: float, y: float, w: float, h: float, img_w: int, img_h: int) -> tuple[float, float, float, float]:
    cx = (x + w / 2.0) / img_w
    cy = (y + h / 2.0) / img_h
    nw = w / img_w
    nh = h / img_h
    return (
        clamp(cx, 0.0, 1.0),
        clamp(cy, 0.0, 1.0),
        clamp(nw, 0.0, 1.0),
        clamp(nh, 0.0, 1.0),
    )


def imread_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare YOLO dataset from CCPD labels CSV")
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260408)
    args = parser.parse_args()

    labels_csv = Path(args.labels_csv).resolve()
    images_dir = Path(args.images_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    train_img_dir = out_dir / "images" / "train"
    val_img_dir = out_dir / "images" / "val"
    train_lbl_dir = out_dir / "labels" / "train"
    val_lbl_dir = out_dir / "labels" / "val"

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    rows = []
    with labels_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = str(row["filename"]).strip()
            if not fn:
                continue
            try:
                x = float(row["x"])
                y = float(row["y"])
                w = float(row["w"])
                h = float(row["h"])
            except ValueError:
                continue
            if w <= 1 or h <= 1:
                continue
            rows.append((fn, x, y, w, h))

    random.Random(args.seed).shuffle(rows)
    val_count = int(len(rows) * args.val_ratio)
    val_set = set(fn for fn, *_ in rows[:val_count])

    used = 0
    for fn, x, y, w, h in rows:
        src_img = images_dir / fn
        if not src_img.exists():
            continue

        img = imread_unicode(src_img)
        if img is None:
            continue
        ih, iw = img.shape[:2]
        cx, cy, nw, nh = to_yolo(x, y, w, h, iw, ih)

        split = "val" if fn in val_set else "train"
        if split == "train":
            dst_img = train_img_dir / fn
            dst_lbl = train_lbl_dir / (Path(fn).stem + ".txt")
        else:
            dst_img = val_img_dir / fn
            dst_lbl = val_lbl_dir / (Path(fn).stem + ".txt")

        shutil.copy2(src_img, dst_img)
        with dst_lbl.open("w", encoding="utf-8") as lf:
            lf.write(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")
        used += 1

    print(f"Total valid rows: {len(rows)}")
    print(f"Prepared samples: {used}")
    print(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
