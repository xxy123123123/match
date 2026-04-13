from __future__ import annotations

import argparse
import random
import shutil
from collections import defaultdict
from pathlib import Path


def read_class_id(label_path: Path) -> int | None:
    if not label_path.exists():
        return None
    lines = [ln.strip() for ln in label_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0].split()
    if not first:
        return None
    try:
        return int(first[0])
    except ValueError:
        return None


def copy_pair(src_img: Path, src_lbl: Path, dst_img: Path, dst_lbl: Path) -> None:
    dst_img.parent.mkdir(parents=True, exist_ok=True)
    dst_lbl.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_img, dst_img)
    shutil.copy2(src_lbl, dst_lbl)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance YOLO legal dataset by oversampling minority classes")
    parser.add_argument("--src-dir", required=True, help="Source YOLO dir containing images/labels train/val")
    parser.add_argument("--out-dir", required=True, help="Output balanced YOLO dir")
    parser.add_argument("--seed", type=int, default=20260411)
    args = parser.parse_args()

    random.seed(args.seed)

    src_dir = Path(args.src_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    src_train_img = src_dir / "images" / "train"
    src_train_lbl = src_dir / "labels" / "train"
    src_val_img = src_dir / "images" / "val"
    src_val_lbl = src_dir / "labels" / "val"

    out_train_img = out_dir / "images" / "train"
    out_train_lbl = out_dir / "labels" / "train"
    out_val_img = out_dir / "images" / "val"
    out_val_lbl = out_dir / "labels" / "val"

    # Reset output folder for reproducibility.
    if out_dir.exists():
        shutil.rmtree(out_dir)

    class_samples: dict[int, list[tuple[Path, Path]]] = defaultdict(list)

    train_images = sorted([p for p in src_train_img.iterdir() if p.is_file()])
    for img in train_images:
        lbl = src_train_lbl / (img.stem + ".txt")
        cid = read_class_id(lbl)
        if cid is None:
            continue
        class_samples[cid].append((img, lbl))

    if not class_samples:
        raise RuntimeError("No valid training samples found in source dataset")

    class_counts = {cid: len(v) for cid, v in class_samples.items()}
    target = max(class_counts.values())

    # Copy original train set first.
    for cid, samples in class_samples.items():
        for img, lbl in samples:
            copy_pair(img, lbl, out_train_img / img.name, out_train_lbl / lbl.name)

    # Oversample each class to target count.
    for cid, samples in class_samples.items():
        deficit = target - len(samples)
        for i in range(deficit):
            img, lbl = random.choice(samples)
            new_name = f"{img.stem}__rep{cid}_{i}{img.suffix}"
            new_lbl_name = f"{img.stem}__rep{cid}_{i}.txt"
            copy_pair(img, lbl, out_train_img / new_name, out_train_lbl / new_lbl_name)

    # Keep validation set untouched.
    val_images = sorted([p for p in src_val_img.iterdir() if p.is_file()])
    for img in val_images:
        lbl = src_val_lbl / (img.stem + ".txt")
        if not lbl.exists():
            continue
        copy_pair(img, lbl, out_val_img / img.name, out_val_lbl / lbl.name)

    yaml_path = out_dir / "plate_legal_data.yaml"
    out_dir_unix = str(out_dir).replace("\\", "/")
    yaml_path.write_text(
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

    out_train_count = len(list(out_train_img.glob("*")))
    out_val_count = len(list(out_val_img.glob("*")))

    print(f"source_train_class_counts={class_counts}")
    print(f"target_per_class={target}")
    print(f"balanced_train_images={out_train_count}")
    print(f"balanced_val_images={out_val_count}")
    print(f"yaml={yaml_path}")


if __name__ == "__main__":
    main()
