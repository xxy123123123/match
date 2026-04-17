from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from training.auto_switch_best_model import auto_switch_best_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLO plate detector")
    parser.add_argument("--data", required=True, help="Path to yolo data yaml")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--project", default="../results/training")
    parser.add_argument("--name", default="plate_det")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument(
        "--profile",
        default="standard",
        choices=["standard", "mobile"],
        help="Training profile. 'mobile' applies stronger motion-friendly augmentations.",
    )
    parser.add_argument(
        "--auto-switch-best",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="After training, auto-update config/default.yaml to the best model by mAP50-95.",
    )
    args = parser.parse_args()

    data_yaml = Path(args.data).resolve()
    if not data_yaml.exists():
        raise FileNotFoundError(f"Data yaml not found: {data_yaml}")

    model = YOLO(args.model)
    train_kwargs = {
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": args.project,
        "name": args.name,
        "device": "cpu",
        "verbose": True,
    }

    if args.profile == "mobile":
        # Mobile profile: improve robustness for moving vehicles and slight motion blur.
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
    else:
        train_kwargs["data"] = str(data_yaml)

    model.train(**train_kwargs)

    if args.auto_switch_best:
        pc_root = Path(__file__).resolve().parents[1]
        best = auto_switch_best_model(pc_root)
        if best is None:
            print("[WARN] Auto-switch best model skipped: no valid best run found.")
        else:
            print(f"[INFO] Auto-switched default model to: {best[0]} (mAP50-95={best[1]:.4f})")


if __name__ == "__main__":
    main()
