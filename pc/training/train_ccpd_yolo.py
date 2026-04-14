from __future__ import annotations

import argparse
from pathlib import Path
from ultralytics import YOLO

from tools.ccpd_to_yolo import main as convert_main


def build_convert_args(args: argparse.Namespace) -> list[str]:
    return [
        "--ccpd-root",
        str(args.ccpd_root),
        "--out-dir",
        str(args.dataset_out_dir),
        "--class-id",
        str(args.class_id),
        "--val-ratio",
        str(args.val_ratio),
        "--seed",
        str(args.seed),
        "--limit",
        str(args.limit),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert CCPD and train YOLO in one command")
    parser.add_argument("--ccpd-root", required=True, help="Root folder of extracted CCPD dataset")
    parser.add_argument(
        "--dataset-out-dir",
        required=True,
        help="Output directory for converted YOLO dataset",
    )
    parser.add_argument("--class-id", type=int, default=0, help="YOLO class id for plate detection")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation ratio in CCPD-Base")
    parser.add_argument("--seed", type=int, default=20260414)
    parser.add_argument("--limit", type=int, default=0, help="Optional max images for debug")
    parser.add_argument("--model", default="yolov8n.pt", help="Initial YOLO weights")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--project", default="../results/training")
    parser.add_argument("--name", default="ccpd_yolo")
    parser.add_argument(
        "--profile",
        default="standard",
        choices=["standard", "mobile"],
        help="Training profile. 'mobile' applies stronger motion-friendly augmentations.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    ccpd_root = Path(args.ccpd_root).resolve()
    dataset_out_dir = Path(args.dataset_out_dir).resolve()
    if not ccpd_root.exists():
        raise FileNotFoundError(f"CCPD root not found: {ccpd_root}")

    # Reuse the standalone converter by invoking its CLI logic.
    import sys

    old_argv = sys.argv[:]
    try:
        sys.argv = ["ccpd_to_yolo.py"] + build_convert_args(args)
        convert_main()
    finally:
        sys.argv = old_argv

    data_yaml = dataset_out_dir / "ccpd_plate_data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError(f"Converted data yaml not found: {data_yaml}")

    model = YOLO(args.model)
    train_kwargs = {
        "data": str(data_yaml),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": args.project,
        "name": args.name,
        "device": "cpu",
        "verbose": True,
    }

    if args.profile == "mobile":
        train_kwargs.update(
            {
                "degrees": 4.0,
                "translate": 0.18,
                "scale": 0.35,
                "shear": 1.5,
                "perspective": 0.0007,
                "hsv_h": 0.02,
                "hsv_s": 0.75,
                "hsv_v": 0.45,
                "erasing": 0.3,
            }
        )

    if args.resume:
        train_kwargs["resume"] = True

    model.train(**train_kwargs)


if __name__ == "__main__":
    main()
