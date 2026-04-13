from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np


def make_motion_kernel(length: int, angle_deg: float) -> np.ndarray:
    k = np.zeros((length, length), dtype=np.float32)
    k[length // 2, :] = 1.0
    center = (length / 2.0 - 0.5, length / 2.0 - 0.5)
    rot = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    k = cv2.warpAffine(k, rot, (length, length))
    s = float(k.sum())
    if s > 0:
        k /= s
    return k


def apply_motion_blur(img: np.ndarray, rng: random.Random) -> np.ndarray:
    length = rng.choice([5, 7, 9, 11])
    angle = rng.uniform(-35.0, 35.0)
    kernel = make_motion_kernel(length, angle)
    out = cv2.filter2D(img, -1, kernel)
    return out


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


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a YOLO dataset variant with synthetic motion blur")
    parser.add_argument("--src-dir", required=True, help="Source YOLO dataset dir")
    parser.add_argument("--out-dir", required=True, help="Output YOLO dataset dir")
    parser.add_argument("--ratio", type=float, default=0.7, help="Probability of applying blur per train image")
    parser.add_argument("--seed", type=int, default=20260412)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    src = Path(args.src_dir).resolve()
    out = Path(args.out_dir).resolve()

    if not src.exists():
        raise FileNotFoundError(f"Source dataset not found: {src}")

    copy_tree(src, out)

    train_img_dir = out / "images" / "train"
    if not train_img_dir.exists():
        raise FileNotFoundError(f"Train image dir not found: {train_img_dir}")

    total = 0
    blurred = 0
    for p in sorted(train_img_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            continue

        img = read_image_unicode(p)
        if img is None:
            continue

        total += 1
        if rng.random() < args.ratio:
            img = apply_motion_blur(img, rng)
            blurred += 1

        write_image_unicode(p, img)

    yaml_path = out / "plate_legal_data.yaml"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    yaml_text = yaml_text.replace(str(src).replace("\\", "/"), str(out).replace("\\", "/"))
    yaml_path.write_text(yaml_text, encoding="utf-8")

    print(f"dataset={out}")
    print(f"train_images={total}")
    print(f"blurred_images={blurred}")
    print(f"ratio={args.ratio}")


if __name__ == "__main__":
    main()
