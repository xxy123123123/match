from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from ultralytics import YOLO

from tools.ccpd_autolabel import parse_bbox

VALID_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Sample:
    path: Path
    subset: str
    gt_bbox: Tuple[int, int, int, int]


def iou_xywh(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh

    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    union = aw * ah + bw * bh - inter
    if union <= 0:
        return 0.0
    return inter / float(union)


def parse_gt_bbox_from_name(name: str) -> Tuple[int, int, int, int]:
    stem = Path(name).stem
    parts = stem.split("-")
    if len(parts) < 3:
        raise ValueError(f"Unexpected CCPD filename: {name}")
    return parse_bbox(parts[2])


def collect_samples(ccpd_root: Path, max_images: int = 0) -> List[Sample]:
    items: List[Sample] = []
    for p in ccpd_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in VALID_SUFFIX:
            continue
        subset = "ccpd-unknown"
        for seg in p.parts:
            s = str(seg).lower()
            if s.startswith("ccpd"):
                subset = s
                break
        try:
            gt = parse_gt_bbox_from_name(p.name)
        except Exception:
            continue
        items.append(Sample(path=p, subset=subset, gt_bbox=gt))
        if max_images > 0 and len(items) >= max_images:
            break
    return items


def eval_subsets(
    samples: List[Sample],
    model_path: Path,
    conf: float,
    iou_ok: float,
    device: str,
) -> Dict[str, Dict[str, float]]:
    model = YOLO(str(model_path.resolve()))

    agg: Dict[str, Dict[str, float]] = {}
    for s in samples:
        res = model.predict(source=str(s.path), conf=conf, max_det=1, verbose=False, device=device)[0]

        pred_iou = 0.0
        if res.boxes is not None and len(res.boxes) > 0:
            xyxy = res.boxes.xyxy.cpu().numpy()[0]
            x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
            pred = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
            pred_iou = iou_xywh(pred, s.gt_bbox)

        if s.subset not in agg:
            agg[s.subset] = {"n": 0.0, "ok": 0.0, "iou_sum": 0.0}
        agg[s.subset]["n"] += 1.0
        agg[s.subset]["iou_sum"] += pred_iou
        if pred_iou >= iou_ok:
            agg[s.subset]["ok"] += 1.0

    for subset, m in agg.items():
        n = max(1.0, m["n"])
        m["precision_iou"] = m["ok"] / n
        m["mean_iou"] = m["iou_sum"] / n

    return agg


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate detector performance by CCPD subset")
    parser.add_argument("--ccpd-root", required=True)
    parser.add_argument("--model", required=True, help="YOLO model path")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou-ok", type=float, default=0.7, help="IoU threshold for correct detection")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-images", type=int, default=0)
    args = parser.parse_args()

    ccpd_root = Path(args.ccpd_root).resolve()
    model_path = Path(args.model).resolve()

    if not ccpd_root.exists():
        raise FileNotFoundError(f"CCPD root not found: {ccpd_root}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    samples = collect_samples(ccpd_root, max_images=int(args.max_images))
    if not samples:
        print("No valid CCPD samples found.")
        return

    agg = eval_subsets(samples, model_path=model_path, conf=float(args.conf), iou_ok=float(args.iou_ok), device=str(args.device))

    print(f"Total samples: {len(samples)}")
    print(f"IoU success threshold: {args.iou_ok}")
    print("subset\tn\tprecision_iou\tmean_iou")
    for subset in sorted(agg.keys()):
        m = agg[subset]
        print(f"{subset}\t{int(m['n'])}\t{m['precision_iou']:.4f}\t{m['mean_iou']:.4f}")


if __name__ == "__main__":
    main()
