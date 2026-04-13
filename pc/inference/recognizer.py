from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np


Bbox = Tuple[int, int, int, int]


class PlateRecognizer:
    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode

    def recognize(
        self,
        frame: np.ndarray,
        bbox: Optional[Bbox],
        meta: Dict[str, object],
    ) -> str:
        if self.mode == "mock":
            return str(meta.get("gt_plate", "UNKNOWN"))

        if self.mode == "baseline":
            # Baseline mode is a placeholder until OCR/model integration.
            return "PLATE_PENDING"

        return "UNKNOWN"
