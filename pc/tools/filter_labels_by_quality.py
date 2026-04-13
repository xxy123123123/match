from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_conf(notes: str) -> float:
    if not notes:
        return 0.0
    marker = "conf="
    idx = notes.find(marker)
    if idx < 0:
        return 0.0
    try:
        return float(notes[idx + len(marker) :].split(";")[0])
    except ValueError:
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter auto-labeled bboxes by quality rules")
    parser.add_argument("--in-csv", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--min-conf", type=float, default=0.20)
    parser.add_argument("--min-w", type=float, default=20.0)
    parser.add_argument("--min-h", type=float, default=10.0)
    parser.add_argument("--min-ratio", type=float, default=1.6, help="w/h lower bound")
    parser.add_argument("--max-ratio", type=float, default=6.5, help="w/h upper bound")
    args = parser.parse_args()

    in_csv = Path(args.in_csv).resolve()
    out_csv = Path(args.out_csv).resolve()

    with in_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    kept = []
    drop_no_box = 0
    drop_conf = 0
    drop_shape = 0

    for r in rows:
        try:
            w = float(r.get("w", "0") or 0)
            h = float(r.get("h", "0") or 0)
            x = float(r.get("x", "0") or 0)
            y = float(r.get("y", "0") or 0)
        except ValueError:
            continue

        if w <= 1 or h <= 1:
            drop_no_box += 1
            continue

        conf = parse_conf(r.get("notes", ""))
        if conf < args.min_conf:
            drop_conf += 1
            continue

        ratio = w / h if h > 0 else 0
        if w < args.min_w or h < args.min_h or ratio < args.min_ratio or ratio > args.max_ratio:
            drop_shape += 1
            continue

        kept.append(
            {
                "filename": r.get("filename", ""),
                "plate_text": r.get("plate_text", ""),
                "x": f"{x:.0f}",
                "y": f"{y:.0f}",
                "w": f"{w:.0f}",
                "h": f"{h:.0f}",
                "notes": (r.get("notes", "") + ";clean=1").strip(";"),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "plate_text", "x", "y", "w", "h", "notes"])
        writer.writeheader()
        writer.writerows(kept)

    print(f"total={len(rows)} kept={len(kept)}")
    print(f"drop_no_box={drop_no_box} drop_conf={drop_conf} drop_shape={drop_shape}")
    print(f"output={out_csv}")


if __name__ == "__main__":
    main()
