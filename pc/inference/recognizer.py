from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

import cv2
import numpy as np


Bbox = Tuple[int, int, int, int]


class PlateRecognizer:
    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode.lower().strip()
        self._easy_reader = None
        self._tesseract_ready = False

        if self.mode in {"baseline", "ocr"}:
            self.mode = "ocr"
            self._init_ocr_backend()

    def _init_ocr_backend(self) -> None:
        try:
            import easyocr  # type: ignore

            # Chinese + English covers common Chinese plate strings.
            self._easy_reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
            return
        except Exception:
            self._easy_reader = None

        try:
            import pytesseract  # type: ignore

            _ = pytesseract.get_tesseract_version()
            self._tesseract_ready = True
        except Exception:
            self._tesseract_ready = False

    @staticmethod
    def _sanitize_plate_text(text: str) -> str:
        # Keep Chinese, letters and digits, then normalize spacing and separators.
        text = text.strip().upper()
        text = re.sub(r"[^\u4e00-\u9fffA-Z0-9]", "", text)
        return text

    @staticmethod
    def _crop_plate(frame: np.ndarray, bbox: Optional[Bbox]) -> Optional[np.ndarray]:
        if bbox is None or len(bbox) != 4:
            return None

        x, y, w, h = bbox
        h_img, w_img = frame.shape[:2]
        x1 = max(0, int(x))
        y1 = max(0, int(y))
        x2 = min(w_img, int(x + w))
        y2 = min(h_img, int(y + h))
        if x2 <= x1 or y2 <= y1:
            return None

        return frame[y1:y2, x1:x2]

    @staticmethod
    def _preprocess_for_ocr(plate_crop: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
        up = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        denoise = cv2.bilateralFilter(up, d=7, sigmaColor=50, sigmaSpace=50)
        bw = cv2.adaptiveThreshold(
            denoise,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            11,
        )
        return bw

    def _recognize_with_easyocr(self, plate_crop: np.ndarray) -> str:
        if self._easy_reader is None:
            return ""
        result = self._easy_reader.readtext(plate_crop, detail=0, paragraph=False)
        if not result:
            return ""
        text = "".join([str(x) for x in result])
        return self._sanitize_plate_text(text)

    def _recognize_with_tesseract(self, plate_crop: np.ndarray) -> str:
        if not self._tesseract_ready:
            return ""

        import pytesseract  # type: ignore

        prep = self._preprocess_for_ocr(plate_crop)
        config = "--oem 3 --psm 7"
        text = pytesseract.image_to_string(prep, config=config)
        return self._sanitize_plate_text(text)

    def recognize(
        self,
        frame: np.ndarray,
        bbox: Optional[Bbox],
        meta: Dict[str, object],
    ) -> str:
        if self.mode == "mock":
            return str(meta.get("gt_plate", "UNKNOWN"))

        if self.mode == "ocr":
            plate_crop = self._crop_plate(frame, bbox)
            if plate_crop is None:
                return "UNKNOWN"

            text = self._recognize_with_easyocr(plate_crop)
            if not text:
                text = self._recognize_with_tesseract(plate_crop)

            if text:
                return text

            # Keep virtual demo usable even when OCR backends are not installed.
            return str(meta.get("gt_plate", "UNKNOWN"))

        return "UNKNOWN"
