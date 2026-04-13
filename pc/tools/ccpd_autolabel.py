from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable, List, Tuple

PROVINCES = [
    "皖",
    "沪",
    "津",
    "渝",
    "冀",
    "晋",
    "蒙",
    "辽",
    "吉",
    "黑",
    "苏",
    "浙",
    "京",
    "闽",
    "赣",
    "鲁",
    "豫",
    "鄂",
    "湘",
    "粤",
    "桂",
    "琼",
    "川",
    "贵",
    "云",
    "藏",
    "陕",
    "甘",
    "青",
    "宁",
    "新",
    "警",
    "学",
    "O",
]

ALPHABETS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "O",
]

ADS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "O",
]


def _safe_idx(table: List[str], idx: int) -> str:
    if 0 <= idx < len(table):
        return table[idx]
    return "?"


def parse_bbox(field: str) -> Tuple[int, int, int, int]:
    # CCPD bbox field: x1&y1_x2&y2
    p1, p2 = field.split("_")
    x1, y1 = [int(v) for v in p1.split("&")]
    x2, y2 = [int(v) for v in p2.split("&")]
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return x, y, w, h


def parse_plate(field: str) -> str:
    nums = [int(v) for v in field.split("_") if v != ""]
    if len(nums) < 2:
        return ""

    province = _safe_idx(PROVINCES, nums[0])
    alpha = _safe_idx(ALPHABETS, nums[1])
    tail = "".join(_safe_idx(ADS, n) for n in nums[2:])
    return f"{province}{alpha}·{tail}" if tail else f"{province}{alpha}"


def parse_ccpd_filename(name: str) -> Tuple[str, int, int, int, int, str]:
    stem = Path(name).stem
    parts = stem.split("-")
    if len(parts) < 6:
        raise ValueError(f"Unexpected CCPD filename: {name}")

    tilt_field = parts[1]
    bbox_field = parts[2]
    plate_field = parts[4]

    x, y, w, h = parse_bbox(bbox_field)
    plate = parse_plate(plate_field)
    notes = f"ccpd_tilt={tilt_field}"
    return plate, x, y, w, h, notes


def load_mapping(path: Path) -> Iterable[Tuple[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield str(row["original_name"]), str(row["renamed_name"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-generate labels from CCPD filenames")
    parser.add_argument(
        "--mapping-csv",
        default="../dataset/plate_train/labeled/annotations/import_mapping.csv",
        help="CSV containing original_name and renamed_name",
    )
    parser.add_argument(
        "--output-csv",
        default="../dataset/plate_train/labeled/annotations/ccpd_labels.csv",
        help="Output labels CSV",
    )
    args = parser.parse_args()

    mapping_csv = Path(args.mapping_csv).resolve()
    output_csv = Path(args.output_csv).resolve()

    if not mapping_csv.exists():
        raise FileNotFoundError(f"Mapping CSV not found: {mapping_csv}")

    rows = []
    for original_name, renamed_name in load_mapping(mapping_csv):
        try:
            plate, x, y, w, h, notes = parse_ccpd_filename(original_name)
        except Exception:
            plate, x, y, w, h, notes = "", 0, 0, 0, 0, "parse_error"
        rows.append([renamed_name, plate, x, y, w, h, notes])

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "plate_text", "x", "y", "w", "h", "notes"])
        writer.writerows(rows)

    ok = sum(1 for r in rows if r[6] != "parse_error")
    print(f"Total rows: {len(rows)}")
    print(f"Parsed rows: {ok}")
    print(f"Output CSV: {output_csv}")


if __name__ == "__main__":
    main()
