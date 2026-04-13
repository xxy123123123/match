from __future__ import annotations

import argparse
import csv
import random
import shutil
from pathlib import Path

import cv2
import numpy as np


CLASS_NAMES = ["legal_common", "legal_special", "illegal"]


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


def normalize_text(v: str) -> str:
    return (v or "").strip().lower()


def normalize_row_keys(row: dict[str, str]) -> dict[str, str]:
    fixed: dict[str, str] = {}
    for k, v in row.items():
        nk = (k or "").replace("\ufeff", "").strip().strip('"')
        fixed[nk] = v
    return fixed


def resolve_class_id(legality: str, plate_type: str) -> int | None:
    lg = normalize_text(legality)
    pt = normalize_text(plate_type)

    if lg in {"unknown", "unk", "none", "", "未标注", "未知"} or pt in {"unknown", "unk", "none", "", "未标注", "未知", "no_plate", "nobox", "无框"}:
        return None

    if lg in {"illegal", "0", "false", "f", "no", "n", "非法"}:
        return 2
    if lg in {"legal", "1", "true", "t", "yes", "y", "合法"}:
        if pt in {"special", "特殊"}:
            return 1
        return 0

    # Fallback: allow inferring from plate_type when legality not filled.
    if pt in {"illegal", "非法"}:
        return 2
    if pt in {"special", "特殊"}:
        return 1
    if pt in {"common", "normal", "常见", "普通"}:
        return 0

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare YOLO multi-class dataset for legal/common/special/illegal")
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260410)
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
    unknown_rows = []
    skipped_class = 0
    with labels_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row = normalize_row_keys(raw_row)
            fn = str(row.get("filename", "")).strip()
            if not fn:
                continue

            try:
                x = float(row.get("x", "0"))
                y = float(row.get("y", "0"))
                w = float(row.get("w", "0"))
                h = float(row.get("h", "0"))
            except ValueError:
                continue
            if w <= 1 or h <= 1:
                unknown_rows.append((fn, "no_bbox"))
                continue

            class_id = resolve_class_id(str(row.get("legality", "")), str(row.get("plate_type", "")))
            if class_id is None:
                unknown_rows.append((fn, "unknown_class"))
                skipped_class += 1
                continue

            rows.append((fn, x, y, w, h, class_id))

    random.Random(args.seed).shuffle(rows)
    val_count = int(len(rows) * args.val_ratio)
    val_set = set(fn for fn, *_ in rows[:val_count])

    used = 0
    per_class = {0: 0, 1: 0, 2: 0}
    for fn, x, y, w, h, class_id in rows:
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
            lf.write(f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

        used += 1
        per_class[class_id] += 1

    data_yaml = out_dir / "plate_legal_data.yaml"
    out_dir_unix = str(out_dir).replace("\\", "/")
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {out_dir_unix}",
                "train: images/train",
                "val: images/val",
                "names:",
                "  0: legal_common",
                "  1: legal_special",
                "  2: illegal",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    unknown_csv = out_dir / "unknown_samples.csv"
    with unknown_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "reason"])
        writer.writerows(unknown_rows)

    print(f"Total valid rows: {len(rows)}")
    print(f"Prepared samples: {used}")
    print(f"Skipped rows without class mapping: {skipped_class}")
    print(f"Class count legal_common: {per_class[0]}")
    print(f"Class count legal_special: {per_class[1]}")
    print(f"Class count illegal: {per_class[2]}")
    print(f"Unknown/no_bbox samples: {len(unknown_rows)}")
    print(f"Output dir: {out_dir}")
    print(f"Data yaml: {data_yaml}")
    print(f"Unknown CSV: {unknown_csv}")


if __name__ == "__main__":
    main()
