from __future__ import annotations

import argparse
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


@dataclass
class Sample:
    image_path: Path
    label_path: Path


def read_image_unicode(path: Path) -> np.ndarray | None:
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image_unicode(path: Path, img: np.ndarray) -> bool:
    ext = path.suffix.lower() or ".jpg"
    ok, enc = cv2.imencode(ext, img)
    if not ok:
        return False
    enc.tofile(str(path))
    return True


def read_yolo_labels(path: Path) -> List[Tuple[int, float, float, float, float]]:
    if not path.exists():
        return []
    out: List[Tuple[int, float, float, float, float]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        parts = ln.strip().split()
        if len(parts) != 5:
            continue
        try:
            cls_id = int(float(parts[0]))
            cx = float(parts[1])
            cy = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
            out.append((cls_id, cx, cy, w, h))
        except ValueError:
            continue
    return out


def list_samples(images_dir: Path, labels_dir: Path) -> List[Sample]:
    out: List[Sample] = []
    for p in sorted(images_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            continue
        out.append(Sample(image_path=p, label_path=labels_dir / f"{p.stem}.txt"))
    return out


def rect_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / float(max(union, 1))


def create_multi_image(
    samples: List[Sample],
    out_w: int,
    out_h: int,
    rng: random.Random,
    min_objs: int,
    max_objs: int,
) -> Tuple[np.ndarray, List[Tuple[int, float, float, float, float]]] | None:
    canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    canvas[:, :] = (40, 60, 35)

    k = rng.randint(min_objs, max_objs)
    chosen = rng.sample(samples, k=min(k, len(samples)))
    placed_rects: List[Tuple[int, int, int, int]] = []
    out_labels: List[Tuple[int, float, float, float, float]] = []

    for s in chosen:
        img = read_image_unicode(s.image_path)
        if img is None:
            continue
        ih, iw = img.shape[:2]
        labels = read_yolo_labels(s.label_path)
        if not labels:
            continue

        scale = rng.uniform(0.38, 0.62)
        nw = max(8, int(iw * scale))
        nh = max(8, int(ih * scale))
        if nw >= out_w or nh >= out_h:
            continue

        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)

        pos = None
        for _ in range(25):
            x0 = rng.randint(0, out_w - nw)
            y0 = rng.randint(0, out_h - nh)
            r = (x0, y0, nw, nh)
            if all(rect_iou(r, pr) < 0.35 for pr in placed_rects):
                pos = (x0, y0)
                placed_rects.append(r)
                break
        if pos is None:
            continue

        x0, y0 = pos
        canvas[y0 : y0 + nh, x0 : x0 + nw] = resized

        for cls_id, cx, cy, w, h in labels:
            abs_cx = x0 + cx * nw
            abs_cy = y0 + cy * nh
            abs_w = w * nw
            abs_h = h * nh

            nx = abs_cx / out_w
            ny = abs_cy / out_h
            nw_n = abs_w / out_w
            nh_n = abs_h / out_h

            if nw_n <= 0 or nh_n <= 0:
                continue
            if not (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
                continue
            out_labels.append((cls_id, nx, ny, nw_n, nh_n))

    if not out_labels:
        return None

    return canvas, out_labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Build multi-target YOLO dataset by synthetic composition")
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--extra-ratio", type=float, default=0.7, help="synthetic_count = base_count * extra_ratio")
    parser.add_argument("--min-objs", type=int, default=2)
    parser.add_argument("--max-objs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260412)
    args = parser.parse_args()

    src = Path(args.src_dir).resolve()
    out = Path(args.out_dir).resolve()
    rng = random.Random(args.seed)

    if not src.exists():
        raise FileNotFoundError(f"Source dataset not found: {src}")

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)

    for split in ["train", "val"]:
        img_dir = out / "images" / split
        lbl_dir = out / "labels" / split
        samples = list_samples(img_dir, lbl_dir)
        if not samples:
            continue

        probe = read_image_unicode(samples[0].image_path)
        if probe is None:
            continue
        h, w = probe.shape[:2]

        target_new = int(len(samples) * float(args.extra_ratio))
        made = 0
        tries = 0
        while made < target_new and tries < target_new * 4:
            tries += 1
            built = create_multi_image(
                samples=samples,
                out_w=w,
                out_h=h,
                rng=rng,
                min_objs=args.min_objs,
                max_objs=args.max_objs,
            )
            if built is None:
                continue

            img, labels = built
            stem = f"mt_{split}_{made:05d}"
            out_img = img_dir / f"{stem}.jpg"
            out_lbl = lbl_dir / f"{stem}.txt"
            if not write_image_unicode(out_img, img):
                continue

            out_lbl.write_text(
                "\n".join([f"{c} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}" for c, x, y, bw, bh in labels]) + "\n",
                encoding="utf-8",
            )
            made += 1

        print(f"split={split} base={len(samples)} synthetic={made}")

    # Rewrite path in YAML to new dataset root.
    yaml_path = out / "plate_legal_data.yaml"
    if yaml_path.exists():
        txt = yaml_path.read_text(encoding="utf-8")
        txt = txt.replace(str(src).replace("\\", "/"), str(out).replace("\\", "/"))
        yaml_path.write_text(txt, encoding="utf-8")

    print(f"dataset={out}")


if __name__ == "__main__":
    main()
