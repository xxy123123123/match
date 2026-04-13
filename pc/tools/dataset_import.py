from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

VALID_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _next_index(dst_dir: Path) -> int:
    max_idx = 0
    for p in dst_dir.glob("*.*"):
        stem = p.stem
        if stem.isdigit():
            max_idx = max(max_idx, int(stem))
    return max_idx + 1


def _collect_images(src_dir: Path) -> list[Path]:
    files = []
    for p in sorted(src_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in VALID_SUFFIX:
            files.append(p)
    return files


def import_images(src_dir: Path, dst_dir: Path, start_idx: int | None) -> list[tuple[str, str]]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    images = _collect_images(src_dir)
    if not images:
        return []

    idx = _next_index(dst_dir) if start_idx is None else start_idx
    mapping: list[tuple[str, str]] = []

    for img in images:
        new_name = f"{idx:04d}.jpg"
        out_path = dst_dir / new_name
        while out_path.exists():
            idx += 1
            new_name = f"{idx:04d}.jpg"
            out_path = dst_dir / new_name

        shutil.copy2(img, out_path)
        mapping.append((img.name, new_name))
        idx += 1

    return mapping


def append_pending_labels(csv_file: Path, names: list[str]) -> None:
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    existed = csv_file.exists()
    with csv_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not existed:
            writer.writerow(["filename", "plate_text", "x", "y", "w", "h", "notes"])
        for name in names:
            writer.writerow([name, "", "", "", "", "", "pending"])


def write_mapping(csv_file: Path, mapping: list[tuple[str, str]]) -> None:
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["original_name", "renamed_name"])
        writer.writerows(mapping)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and rename training images")
    parser.add_argument("--src", required=True, help="Source folder containing images")
    parser.add_argument(
        "--dst",
        default="../dataset/plate_train/labeled/images",
        help="Destination images folder",
    )
    parser.add_argument(
        "--pending-csv",
        default="../dataset/plate_train/labeled/annotations/pending_labels.csv",
        help="CSV file to append pending labels",
    )
    parser.add_argument(
        "--mapping-csv",
        default="../dataset/plate_train/labeled/annotations/import_mapping.csv",
        help="CSV file to write rename mapping",
    )
    parser.add_argument("--start-idx", type=int, default=None, help="Optional start index")
    args = parser.parse_args()

    src_dir = Path(args.src).resolve()
    dst_dir = Path(args.dst).resolve()
    pending_csv = Path(args.pending_csv).resolve()
    mapping_csv = Path(args.mapping_csv).resolve()

    if not src_dir.exists():
        raise FileNotFoundError(f"Source folder not found: {src_dir}")

    mapping = import_images(src_dir, dst_dir, args.start_idx)
    if not mapping:
        print("No image files found in source folder.")
        return

    renamed = [new for _, new in mapping]
    append_pending_labels(pending_csv, renamed)
    write_mapping(mapping_csv, mapping)

    print(f"Imported images: {len(mapping)}")
    print(f"Destination: {dst_dir}")
    print(f"Pending labels CSV: {pending_csv}")
    print(f"Mapping CSV: {mapping_csv}")


if __name__ == "__main__":
    main()
