from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tools.ccpd_autolabel import parse_bbox, parse_plate

VALID_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def bbox_to_yolo(x: int, y: int, w: int, h: int, img_w: int, img_h: int) -> Tuple[float, float, float, float]:
    cx = (x + w / 2.0) / img_w
    cy = (y + h / 2.0) / img_h
    nw = w / float(img_w)
    nh = h / float(img_h)
    return (
        clamp(cx, 0.0, 1.0),
        clamp(cy, 0.0, 1.0),
        clamp(nw, 0.0, 1.0),
        clamp(nh, 0.0, 1.0),
    )


def parse_ccpd_name(name: str) -> Tuple[Tuple[int, int, int, int], str]:
    stem = Path(name).stem
    parts = stem.split("-")
    if len(parts) < 5:
        raise ValueError(f"Unexpected CCPD filename: {name}")
    bbox = parse_bbox(parts[2])
    plate = parse_plate(parts[4])
    return bbox, plate


def collect_images(ccpd_root: Path) -> List[Tuple[Path, str]]:
    items: List[Tuple[Path, str]] = []
    for p in ccpd_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in VALID_SUFFIX:
            continue
        parent = p.parent.name.lower()
        if parent.startswith("ccpd"):
            subset = parent
        else:
            # fallback: infer from any path segment containing ccpd
            subset = "ccpd-unknown"
            for seg in p.parts:
                s = str(seg).lower()
                if s.startswith("ccpd"):
                    subset = s
                    break
        items.append((p, subset))
    return items


def image_shape_fast(path: Path) -> Tuple[int, int]:
    # Read JPEG/PNG shape without heavy deps.
    import imghdr
    import struct

    kind = imghdr.what(path)
    with path.open("rb") as f:
        data = f.read(26)

    if kind == "png" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)

    if kind == "jpeg":
        with path.open("rb") as f:
            f.read(2)
            b = f.read(1)
            while b and b != b"\xDA":
                while b != b"\xFF":
                    b = f.read(1)
                while b == b"\xFF":
                    b = f.read(1)
                if b in {b"\xC0", b"\xC1", b"\xC2", b"\xC3", b"\xC9", b"\xCA", b"\xCB"}:
                    _len = f.read(2)
                    _prec = f.read(1)
                    h = struct.unpack(">H", f.read(2))[0]
                    w = struct.unpack(">H", f.read(2))[0]
                    return int(w), int(h)
                seg_len = struct.unpack(">H", f.read(2))[0]
                f.read(seg_len - 2)
                b = f.read(1)

    raise ValueError(f"Unsupported image format for fast size read: {path}")


def choose_split(
    src: Path,
    subset: str,
    val_ratio: float,
    rng: random.Random,
) -> str:
    # Following CCPD convention: CCPD-Base for train/val, others for test.
    if subset == "ccpd-base":
        return "val" if rng.random() < val_ratio else "train"
    return "test"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert CCPD images to YOLO detection dataset")
    parser.add_argument("--ccpd-root", required=True, help="Root folder of extracted CCPD dataset")
    parser.add_argument("--out-dir", required=True, help="Output YOLO dataset directory")
    parser.add_argument("--class-id", type=int, default=0, help="Class id for plate detection")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation ratio in CCPD-Base")
    parser.add_argument("--seed", type=int, default=20260414)
    parser.add_argument("--limit", type=int, default=0, help="Optional max images for debug")
    args = parser.parse_args()

    ccpd_root = Path(args.ccpd_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    if not ccpd_root.exists():
        raise FileNotFoundError(f"CCPD root not found: {ccpd_root}")

    for split in ["train", "val", "test"]:
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    items = collect_images(ccpd_root)
    if args.limit > 0:
        items = items[: args.limit]

    rng = random.Random(args.seed)
    stats: Dict[str, int] = {"train": 0, "val": 0, "test": 0, "skipped": 0}

    for i, (img_path, subset) in enumerate(items):
        try:
            (x, y, w, h), _plate = parse_ccpd_name(img_path.name)
            img_w, img_h = image_shape_fast(img_path)
            cx, cy, nw, nh = bbox_to_yolo(x, y, w, h, img_w, img_h)
        except Exception:
            stats["skipped"] += 1
            continue

        split = choose_split(img_path, subset, args.val_ratio, rng)
        dst_img = out_dir / "images" / split / img_path.name
        dst_lbl = out_dir / "labels" / split / (img_path.stem + ".txt")

        shutil.copy2(img_path, dst_img)
        with dst_lbl.open("w", encoding="utf-8") as f:
            f.write(f"{args.class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

        stats[split] += 1
        if (i + 1) % 5000 == 0:
            print(f"Processed {i + 1}/{len(items)}")

    yaml_path = out_dir / "ccpd_plate_data.yaml"
    out_unix = str(out_dir).replace("\\", "/")
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {out_unix}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                f"  {args.class_id}: plate",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print("Done converting CCPD -> YOLO")
    print(f"Total images found: {len(items)}")
    print(f"train={stats['train']} val={stats['val']} test={stats['test']} skipped={stats['skipped']}")
    print(f"Output: {out_dir}")
    print(f"YAML: {yaml_path}")


if __name__ == "__main__":
    main()
