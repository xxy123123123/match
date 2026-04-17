from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple


def _read_last_metric(results_csv: Path) -> Optional[float]:
    if not results_csv.exists():
        return None

    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return None

    last = rows[-1]
    for key in ("metrics/mAP50-95(B)", "metrics/mAP50(B)"):
        if key in last:
            try:
                return float(last[key])
            except (TypeError, ValueError):
                return None
    return None


def _iter_candidate_runs(training_roots: Iterable[Path]) -> Iterable[Tuple[Path, float]]:
    for root in training_roots:
        if not root.exists() or not root.is_dir():
            continue

        for run_dir in root.iterdir():
            if not run_dir.is_dir():
                continue
            best_pt = run_dir / "weights" / "best.pt"
            results_csv = run_dir / "results.csv"
            if not best_pt.exists() or not results_csv.exists():
                continue

            metric = _read_last_metric(results_csv)
            if metric is None:
                continue
            yield best_pt, metric


def find_best_model(training_roots: Iterable[Path]) -> Optional[Tuple[Path, float]]:
    best: Optional[Tuple[Path, float]] = None
    for best_pt, metric in _iter_candidate_runs(training_roots):
        if best is None or metric > best[1]:
            best = (best_pt, metric)
    return best


def update_default_model_path(default_yaml: Path, best_model: Path) -> bool:
    if not default_yaml.exists():
        raise FileNotFoundError(f"Default config not found: {default_yaml}")

    config_dir = default_yaml.parent.resolve()
    model_abs = Path(best_model).resolve()

    # Use path relative to pc/config when possible; fallback to absolute on cross-drive setups.
    try:
        rel_model_str = os.path.relpath(str(model_abs), str(config_dir)).replace("\\", "/")
    except ValueError:
        rel_model_str = model_abs.as_posix()

    text = default_yaml.read_text(encoding="utf-8")
    pattern = r'(^\s*model:\s*").*("\s*$)'
    new_text, count = re.subn(pattern, rf'\1{rel_model_str}\2', text, count=1, flags=re.MULTILINE)
    if count == 0:
        return False

    default_yaml.write_text(new_text, encoding="utf-8")
    return True


def auto_switch_best_model(pc_root: Path) -> Optional[Tuple[Path, float]]:
    training_roots = [
        (pc_root / "runs" / "results" / "training").resolve(),
        (pc_root.parent / "results" / "training").resolve(),
    ]
    best = find_best_model(training_roots)
    if best is None:
        return None

    default_yaml = (pc_root / "config" / "default.yaml").resolve()
    updated = update_default_model_path(default_yaml, best[0])
    if not updated:
        return None
    return best
