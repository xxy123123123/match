from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Row:
    frame: int
    track_id: int
    matched: int
    source: str
    gt: str


def _safe_int(v: str, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def load_rows(csv_path: Path) -> List[Row]:
    rows: List[Row] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                Row(
                    frame=_safe_int(str(r.get("frame", "0")), 0),
                    track_id=_safe_int(str(r.get("track_id", "-1")), -1),
                    matched=_safe_int(str(r.get("matched", "0")), 0),
                    source=str(r.get("track_source", "")).strip(),
                    gt=str(r.get("gt", "")).strip(),
                )
            )
    rows.sort(key=lambda x: (x.track_id, x.frame))
    return rows


def evaluate(rows: List[Row], short_track_len: int = 2) -> Dict[str, float | int]:
    by_track: Dict[int, List[Row]] = defaultdict(list)
    for r in rows:
        if r.track_id >= 0:
            by_track[r.track_id].append(r)

    continuity_num = 0
    continuity_den = 0
    recovery_segments = 0
    recovered_segments = 0
    short_tracks = 0

    for tid, tr in by_track.items():
        tr.sort(key=lambda x: x.frame)
        if len(tr) <= short_track_len:
            short_tracks += 1

        for i in range(1, len(tr)):
            continuity_den += 1
            if tr[i].frame == tr[i - 1].frame + 1:
                continuity_num += 1

        # Count predict segments; if a segment ends at detect, treat it as recovered.
        in_predict = False
        for i, row in enumerate(tr):
            if row.source == "predict" and not in_predict:
                in_predict = True
                recovery_segments += 1
            if in_predict and row.source != "predict":
                if row.source == "detect":
                    recovered_segments += 1
                in_predict = False
            if in_predict and i == len(tr) - 1:
                in_predict = False

    total_rows = len(rows)
    tracks = len(by_track)
    continuity = (continuity_num / continuity_den) if continuity_den > 0 else 0.0
    recovery_rate = (recovered_segments / recovery_segments) if recovery_segments > 0 else 0.0
    short_track_ratio = (short_tracks / tracks) if tracks > 0 else 0.0

    gt_rows = [r for r in rows if r.gt]
    gt_count = len(gt_rows)
    matched_count = sum(r.matched for r in gt_rows)
    match_ratio = (matched_count / gt_count) if gt_count > 0 else 0.0

    return {
        "rows": total_rows,
        "tracks": tracks,
        "continuity": round(continuity, 4),
        "predict_recovery_rate": round(recovery_rate, 4),
        "short_track_ratio": round(short_track_ratio, 4),
        "gt_rows": gt_count,
        "match_ratio": round(match_ratio, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate run_result.csv for tracking stability")
    parser.add_argument("--csv", default="../results/run_result.csv", help="Path to run_result.csv")
    parser.add_argument("--short-track-len", type=int, default=2, help="Threshold for short-track ratio")
    parser.add_argument("--out-json", default="", help="Optional output json path")
    args = parser.parse_args()

    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = load_rows(csv_path)
    metrics = evaluate(rows, short_track_len=int(args.short_track_len))

    print(f"CSV: {csv_path}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.out_json:
        out_path = Path(args.out_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
