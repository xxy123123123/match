from __future__ import annotations

from typing import Dict, List, Tuple

import cv2
import numpy as np


Bbox = Tuple[int, int, int, int]


def detect_plate_candidates(frame: np.ndarray, cfg: Dict[str, float]) -> List[Bbox]:
    min_area = float(cfg.get("min_area", 1200))
    max_area = float(cfg.get("max_area", 25000))
    ar_min = float(cfg.get("aspect_ratio_min", 2.0))
    ar_max = float(cfg.get("aspect_ratio_max", 6.5))

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 80, 180)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes: List[Bbox] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < min_area or area > max_area:
            continue
        if h <= 0:
            continue
        ar = w / float(h)
        if ar_min <= ar <= ar_max:
            boxes.append((x, y, w, h))

    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    return boxes[:3]
