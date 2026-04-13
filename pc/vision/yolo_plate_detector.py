from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from ultralytics import YOLO


Bbox = Tuple[int, int, int, int]


class YoloPlateDetector:
    def __init__(
        self,
        model_path: str,
        conf: float = 0.25,
        iou: float = 0.5,
        max_det: int = 3,
        min_area: float = 0.0,
        max_area: float = 1e12,
        aspect_ratio_min: float = 0.0,
        aspect_ratio_max: float = 1e12,
    ) -> None:
        resolved = Path(model_path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"YOLO model not found: {resolved}")

        self.model = YOLO(str(resolved))
        self.conf = float(conf)
        self.iou = float(iou)
        self.max_det = int(max_det)
        self.min_area = float(min_area)
        self.max_area = float(max_area)
        self.aspect_ratio_min = float(aspect_ratio_min)
        self.aspect_ratio_max = float(aspect_ratio_max)

    def _is_valid_plate_shape(self, w: int, h: int) -> bool:
        if w <= 0 or h <= 0:
            return False
        area = float(w * h)
        if area < self.min_area or area > self.max_area:
            return False
        ar = w / float(h)
        return self.aspect_ratio_min <= ar <= self.aspect_ratio_max

    def detect(self, frame: np.ndarray) -> List[Bbox]:
        result = self.model.predict(
            source=frame,
            conf=self.conf,
            iou=self.iou,
            max_det=self.max_det,
            verbose=False,
            device="cpu",
        )[0]

        boxes: List[Tuple[float, Bbox]] = []
        if result.boxes is None or len(result.boxes) == 0:
            return []

        xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            w = max(1, int(round(x2 - x1)))
            h = max(1, int(round(y2 - y1)))
            if not self._is_valid_plate_shape(w, h):
                continue
            x = int(round(x1))
            y = int(round(y1))
            boxes.append((float(confs[i]), (x, y, w, h)))

        boxes.sort(key=lambda item: item[0], reverse=True)
        return [b for _, b in boxes[: self.max_det]]


def build_yolo_detector(cfg: Dict[str, object]) -> YoloPlateDetector:
    model_path = str(cfg.get("model", ""))
    if not model_path:
        raise ValueError("detector.model must be configured when detector.mode is 'yolo'")
    return YoloPlateDetector(
        model_path=model_path,
        conf=float(cfg.get("conf", 0.25)),
        iou=float(cfg.get("iou", 0.5)),
        max_det=int(cfg.get("max_det", 3)),
        min_area=float(cfg.get("min_area", 1200)),
        max_area=float(cfg.get("max_area", 25000)),
        aspect_ratio_min=float(cfg.get("aspect_ratio_min", 2.0)),
        aspect_ratio_max=float(cfg.get("aspect_ratio_max", 6.5)),
    )
