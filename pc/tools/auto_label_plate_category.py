from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


def normalize_row_keys(row: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in row.items():
        nk = (k or "").replace("\ufeff", "").strip().strip('"')
        out[nk] = v
    return out


def parse_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def imread_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def clamp_box(x: int, y: int, w: int, h: int, iw: int, ih: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(iw - 1, x))
    y1 = max(0, min(ih - 1, y))
    x2 = max(0, min(iw, x + w))
    y2 = max(0, min(ih, y + h))
    if x2 <= x1:
        x2 = min(iw, x1 + 1)
    if y2 <= y1:
        y2 = min(ih, y1 + 1)
    return x1, y1, x2, y2


def dominant_color_bgr(roi: np.ndarray) -> str:
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0].astype(np.float32)
    s = hsv[:, :, 1].astype(np.float32)
    v = hsv[:, :, 2].astype(np.float32)

    sat_mask = s > 40
    if sat_mask.any():
        hm = float(np.mean(h[sat_mask]))
        sm = float(np.mean(s[sat_mask]))
        vm = float(np.mean(v[sat_mask]))
    else:
        hm = float(np.mean(h))
        sm = float(np.mean(s))
        vm = float(np.mean(v))

    if vm < 45:
        return "black"
    if sm < 40 and vm > 150:
        return "white"
    if 90 <= hm <= 135:
        return "blue"
    if 35 <= hm <= 89:
        return "green"
    if 12 <= hm <= 34:
        return "yellow"
    return "other"


def parse_conf(notes: str) -> float:
    if not notes:
        return 0.0
    key = "conf="
    i = notes.find(key)
    if i < 0:
        return 0.0
    tail = notes[i + len(key) :]
    tail = tail.split(";")[0]
    return parse_float(tail, 0.0)


def classify_sample(w: float, h: float, conf: float, color: str) -> tuple[str, str, str]:
    # Returns legality, plate_type, reason
    if w <= 1 or h <= 1:
        return "illegal", "illegal", "no_bbox"

    ratio = w / h if h > 0 else 0.0

    # Very low confidence on detected box is treated as likely illegal/no-plate sample.
    if conf < 0.02:
        return "illegal", "illegal", "very_low_conf"

    # Common: mostly blue/green single-row plates.
    if color in {"blue", "green"} and ratio >= 2.0:
        return "legal", "common", f"color={color};ratio={ratio:.2f}"

    # Special: yellow/police/consulate-like colors or double-row-like aspect.
    if color in {"yellow", "white", "black"} or ratio < 2.0:
        return "legal", "special", f"color={color};ratio={ratio:.2f}"

    # Fallback to special for safety; keep review note.
    return "legal", "special", f"fallback;color={color};ratio={ratio:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto label legality/common/special from bbox+appearance rules")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    in_csv = Path(args.input_csv).resolve()
    images_dir = Path(args.images_dir).resolve()
    out_csv = Path(args.output_csv).resolve()

    with in_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_rows = [normalize_row_keys(r) for r in reader]

    out_rows: list[dict[str, str]] = []
    c_legal_common = 0
    c_legal_special = 0
    c_illegal = 0

    for r in raw_rows:
        fn = (r.get("filename") or "").strip()
        x = int(parse_float(r.get("x", "0"), 0.0))
        y = int(parse_float(r.get("y", "0"), 0.0))
        w = parse_float(r.get("w", "0"), 0.0)
        h = parse_float(r.get("h", "0"), 0.0)
        notes = r.get("notes", "") or ""
        conf = parse_conf(notes)

        color = "none"
        if fn and w > 1 and h > 1:
            img_path = images_dir / fn
            img = imread_unicode(img_path) if img_path.exists() else None
            if img is not None:
                ih, iw = img.shape[:2]
                x1, y1, x2, y2 = clamp_box(x, y, int(w), int(h), iw, ih)
                roi = img[y1:y2, x1:x2]
                if roi.size > 0:
                    color = dominant_color_bgr(roi)

        legality, plate_type, reason = classify_sample(w, h, conf, color)

        if legality == "illegal":
            c_illegal += 1
        elif plate_type == "common":
            c_legal_common += 1
        else:
            c_legal_special += 1

        out_rows.append(
            {
                "filename": fn,
                "plate_text": r.get("plate_text", "") or "",
                "x": str(int(x)),
                "y": str(int(y)),
                "w": str(int(w)),
                "h": str(int(h)),
                "legality": legality,
                "plate_type": plate_type,
                "notes": (notes + ";auto_rule=" + reason).strip(";"),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["filename", "plate_text", "x", "y", "w", "h", "legality", "plate_type", "notes"],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"total={len(out_rows)}")
    print(f"legal_common={c_legal_common}")
    print(f"legal_special={c_legal_special}")
    print(f"illegal={c_illegal}")
    print(f"output={out_csv}")


if __name__ == "__main__":
    main()
