from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, Tuple

import cv2

from inference.recognizer import PlateRecognizer
from config_loader import load_config
from transport.fpga_stream import FpgaReplaySource, FpgaTcpSource
from vision.plate_detector import detect_plate_candidates
from vision.plate_tracker import MultiPlateTracker
from vision.virtual_source import VirtualPlateSource
from vision.yolo_plate_detector import build_yolo_detector


def draw_result(frame, bbox: Tuple[int, int, int, int], text: str, tracked_only: bool = False) -> None:
    x, y, w, h = bbox
    color = (0, 220, 255) if not tracked_only else (0, 255, 120)
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    cv2.putText(
        frame,
        text,
        (x, y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )


def build_source(cfg: Dict, source_name: str):
    if source_name == "virtual":
        vcfg = cfg.get("virtual_source", {})
        return VirtualPlateSource(
            width=int(vcfg.get("width", 1280)),
            height=int(vcfg.get("height", 720)),
            fps=int(vcfg.get("fps", 25)),
            plate_pool=list(vcfg.get("plate_pool", ["TEST123"])),
        )

    if source_name == "fpga_tcp":
        scfg = cfg.get("fpga_source", {})
        return FpgaTcpSource(
            host=str(scfg.get("host", "127.0.0.1")),
            port=int(scfg.get("port", 5600)),
            timeout_s=float(scfg.get("timeout_s", 5.0)),
        )

    if source_name == "fpga_replay":
        scfg = cfg.get("fpga_source", {})
        return FpgaReplaySource(stream_file=str(scfg.get("replay_file", "../dataset/samples/fpga_stream.bin")))

    raise ValueError(
        f"Unsupported source: {source_name}. Use one of ['virtual', 'fpga_tcp', 'fpga_replay']."
    )


def ensure_result_path(cfg: Dict) -> Path:
    out_cfg = cfg.get("output", {})
    result_dir = Path(out_cfg.get("result_dir", "../results")).resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Plate recognition demo with virtual/fpga sources")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--source", default="virtual", help="Frame source name")
    parser.add_argument("--show", action="store_true", help="Show live window")
    args = parser.parse_args()

    cfg = load_config(args.config)
    app_cfg = cfg.get("app", {})
    detector_cfg = cfg.get("detector", {})
    tracking_cfg = cfg.get("tracking", {})
    recognizer_cfg = cfg.get("recognizer", {})

    max_frames = int(app_cfg.get("max_frames", 300))
    window_name = str(app_cfg.get("window_name", "Plate Recognition Demo"))
    detector_mode = str(detector_cfg.get("mode", "contour")).lower()

    source = build_source(cfg, args.source)
    recognizer = PlateRecognizer(mode=str(recognizer_cfg.get("mode", "mock")))
    tracker = MultiPlateTracker(
        iou_threshold=float(tracking_cfg.get("iou_threshold", 0.15)),
        max_lost=int(tracking_cfg.get("max_lost", 8)),
        smooth_alpha=float(tracking_cfg.get("smooth_alpha", 0.65)),
        max_tracks=int(tracking_cfg.get("max_tracks", 6)),
        spawn_iou_threshold=float(tracking_cfg.get("spawn_iou_threshold", 0.35)),
        center_dist_threshold=float(tracking_cfg.get("center_dist_threshold", 1.2)),
        center_dist_weight=float(tracking_cfg.get("center_dist_weight", 0.25)),
    )
    min_persist_frames = int(tracking_cfg.get("min_persist_frames", 2))
    track_seen_counts: Dict[int, int] = {}
    result_dir = ensure_result_path(cfg)
    csv_path = result_dir / "run_result.csv"

    yolo_detector = None
    if detector_mode == "yolo":
        yolo_detector = build_yolo_detector(detector_cfg)

    t0 = time.time()
    hits = 0
    total = 0

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "track_id", "prediction", "gt", "matched", "track_source", "bbox"])

        for packet in source.frames(max_frames=max_frames):
            frame = packet.frame
            meta = packet.meta
            if yolo_detector is not None:
                candidates = yolo_detector.detect(frame)
            else:
                candidates = detect_plate_candidates(frame, detector_cfg)
            updates = tracker.update(candidates)
            frame_idx = int(meta.get("index", total))

            for u in updates:
                track_seen_counts[u.track_id] = track_seen_counts.get(u.track_id, 0) + 1
                if track_seen_counts[u.track_id] < min_persist_frames:
                    continue

                bbox = u.bbox
                pred = recognizer.recognize(frame, bbox, meta) if bbox is not None else "UNKNOWN"
                gt = str(meta.get("gt_plate", "")) if len(updates) == 1 else ""
                matched = int(bool(gt) and pred == gt)

                if bbox and len(bbox) == 4:
                    draw_result(
                        frame,
                        bbox,
                        f"id={u.track_id} pred={pred}",
                        tracked_only=(u.source in {"track_only", "predict"}),
                    )

                bbox_text = ""
                if bbox is not None and len(bbox) == 4:
                    bbox_text = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

                writer.writerow([
                    frame_idx,
                    u.track_id,
                    pred,
                    gt,
                    matched,
                    u.source,
                    bbox_text,
                ])

                total += 1
                hits += matched

            if args.show:
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    elapsed = max(time.time() - t0, 1e-6)
    fps = total / elapsed
    acc = hits / max(total, 1)

    print(f"Processed frames: {total}")
    print(f"Average FPS: {fps:.2f}")
    print(f"Match ratio: {acc:.2%}")
    print(f"Result CSV: {csv_path}")

    if args.show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
