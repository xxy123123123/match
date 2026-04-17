from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_SUBSETS = [
    "ccpd_db",
    "ccpd_rotate",
    "ccpd_weather",
    "ccpd_np",
    "ccpd_blur",
    "ccpd_tilt",
    "ccpd_fn",
    "ccpd_challenge",
    "ccpd_base",
]


def choose_limit(subset: str, quick_limit: int) -> int:
    # Keep small subsets complete; cap large subsets for quick-turnaround runs.
    if subset == "ccpd_np":
        return 0
    return quick_limit


def run_one_subset(
    python_exe: Path,
    pc_root: Path,
    subset_root: Path,
    out_root: Path,
    model: str,
    epochs: int,
    batch: int,
    imgsz: int,
    profile: str,
    class_name: str,
    quick_limit: int,
) -> int:
    subset = subset_root.name
    out_dir = out_root / f"{subset}_yolo"
    run_name = f"ccpd2019_{subset}_e{epochs}"
    limit = choose_limit(subset, quick_limit)

    cmd = [
        str(python_exe),
        "-m",
        "training.train_ccpd_yolo",
        "--ccpd-root",
        str(subset_root),
        "--dataset-out-dir",
        str(out_dir),
        "--model",
        model,
        "--epochs",
        str(epochs),
        "--batch",
        str(batch),
        "--imgsz",
        str(imgsz),
        "--name",
        run_name,
        "--profile",
        profile,
        "--class-name",
        class_name,
    ]

    if limit > 0:
        cmd.extend(["--limit", str(limit)])

    print(f"\n=== [{subset}] start ===")
    print(" ".join(cmd))
    env = os.environ.copy()
    env["YOLO_AUTOINSTALL"] = "False"
    result = subprocess.run(cmd, check=False, cwd=str(pc_root), env=env)
    print(f"=== [{subset}] exit={result.returncode} ===")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train CCPD2019 by subsets in batches (quick mode for 3-5h-scale runs)."
    )
    parser.add_argument(
        "--ccpd2019-root",
        default=r"D:\文档\ccpd\CCPD2019_extracted\CCPD2019",
        help="CCPD2019 extracted root path",
    )
    parser.add_argument(
        "--subsets",
        default=",".join(DEFAULT_SUBSETS),
        help="Comma-separated subset names, e.g. ccpd_db,ccpd_weather",
    )
    parser.add_argument("--model", default="../runs/results/training/ccpd_run2/weights/best.pt")
    parser.add_argument("--epochs", type=int, default=6, help="Use 6-8 for quick mode")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--profile", choices=["standard", "mobile"], default="mobile")
    parser.add_argument("--class-name", default="new_energy_plate")
    parser.add_argument(
        "--quick-limit",
        type=int,
        default=12000,
        help="Max images per subset in quick mode (0 means full subset)",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the whole batch when one subset fails",
    )
    args = parser.parse_args()

    pc_root = Path(__file__).resolve().parents[1]
    root = Path(args.ccpd2019_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"CCPD2019 root not found: {root}")

    subset_names = [s.strip() for s in args.subsets.split(",") if s.strip()]
    out_root = (pc_root / "ccpd2019_batches").resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    python_exe = Path(sys.executable).resolve()
    failed: list[str] = []

    for subset in subset_names:
        subset_root = root / subset
        if not subset_root.exists() or not subset_root.is_dir():
            print(f"[WARN] subset not found, skip: {subset_root}")
            failed.append(subset)
            if args.stop_on_error:
                break
            continue

        code = run_one_subset(
            python_exe=python_exe,
            pc_root=pc_root,
            subset_root=subset_root,
            out_root=out_root,
            model=args.model,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            profile=args.profile,
            class_name=args.class_name,
            quick_limit=args.quick_limit,
        )
        if code != 0:
            failed.append(subset)
            if args.stop_on_error:
                break

    if failed:
        print(f"[DONE] finished with failures: {failed}")
        raise SystemExit(1)
    print("[DONE] all subset batches completed successfully")


if __name__ == "__main__":
    main()
