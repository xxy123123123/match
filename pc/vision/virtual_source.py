from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple

import cv2
import numpy as np


@dataclass
class FramePacket:
    frame: np.ndarray
    meta: Dict[str, object]


class VirtualPlateSource:
    def __init__(self, width: int, height: int, fps: int, plate_pool: List[str]) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.plate_pool = plate_pool or ["TEST123"]
        self.rng = random.Random(20260408)

    def _draw_background(self, frame: np.ndarray, idx: int) -> None:
        # Use gradient and lane-like lines to mimic road scenes.
        for y in range(self.height):
            color = 40 + int(80 * y / max(1, self.height - 1))
            frame[y, :] = (color // 2, color, color // 3)
        for i in range(0, self.width, 120):
            x = (i + idx * 7) % self.width
            cv2.line(frame, (x, self.height - 200), (x + 40, self.height), (180, 180, 180), 2)

    def _draw_vehicle_and_plate(self, frame: np.ndarray, plate_text: str, idx: int) -> Tuple[int, int, int, int]:
        car_w = 420
        car_h = 160
        x = 80 + (idx * 11) % (self.width - car_w - 160)
        y = self.height // 2 + 80 + int(20 * np.sin(idx / 8.0))

        cv2.rectangle(frame, (x, y), (x + car_w, y + car_h), (30, 30, 30), -1)
        cv2.circle(frame, (x + 70, y + car_h), 30, (20, 20, 20), -1)
        cv2.circle(frame, (x + car_w - 70, y + car_h), 30, (20, 20, 20), -1)

        plate_w = 220
        plate_h = 60
        px = x + (car_w - plate_w) // 2
        py = y + car_h // 2

        cv2.rectangle(frame, (px, py), (px + plate_w, py + plate_h), (245, 245, 245), -1)
        cv2.rectangle(frame, (px, py), (px + plate_w, py + plate_h), (0, 0, 0), 2)
        cv2.putText(
            frame,
            plate_text,
            (px + 12, py + 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
        return (px, py, plate_w, plate_h)

    def frames(self, max_frames: int) -> Iterator[FramePacket]:
        for idx in range(max_frames):
            plate_text = self.plate_pool[idx % len(self.plate_pool)]
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            self._draw_background(frame, idx)
            plate_bbox = self._draw_vehicle_and_plate(frame, plate_text, idx)
            yield FramePacket(
                frame=frame,
                meta={
                    "index": idx,
                    "gt_plate": plate_text,
                    "gt_bbox": plate_bbox,
                    "source": "virtual",
                },
            )
