from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


Bbox = Tuple[int, int, int, int]


def _valid_bbox(b: Bbox) -> bool:
    return len(b) == 4 and b[2] > 0 and b[3] > 0


def _iou(a: Bbox, b: Bbox) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    area_a = aw * ah
    area_b = bw * bh
    denom = area_a + area_b - inter
    if denom <= 0:
        return 0.0
    return inter / float(denom)


def _center_distance_norm(a: Bbox, b: Bbox) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    acx, acy = ax + aw / 2.0, ay + ah / 2.0
    bcx, bcy = bx + bw / 2.0, by + bh / 2.0
    dist = ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5
    scale = max(((aw * aw + ah * ah) ** 0.5), 1.0)
    return dist / scale


def _smooth(prev: Bbox, curr: Bbox, alpha: float) -> Bbox:
    px, py, pw, ph = prev
    cx, cy, cw, ch = curr
    return (
        int(alpha * cx + (1.0 - alpha) * px),
        int(alpha * cy + (1.0 - alpha) * py),
        int(alpha * cw + (1.0 - alpha) * pw),
        int(alpha * ch + (1.0 - alpha) * ph),
    )


@dataclass
class TrackUpdate:
    bbox: Optional[Bbox]
    source: str  # detect | track_only | predict | none
    lost: int = 0
    track_id: int = -1


@dataclass
class _TrackState:
    track_id: int
    bbox: Bbox
    vel: Tuple[float, float, float, float]
    lost: int = 0


class PlateTracker:
    def __init__(self, iou_threshold: float = 0.15, max_lost: int = 12, smooth_alpha: float = 0.65) -> None:
        self.iou_threshold = float(iou_threshold)
        self.max_lost = int(max_lost)
        self.smooth_alpha = float(smooth_alpha)
        self._bbox: Optional[Bbox] = None
        self._lost = 0
        self._vel = (0.0, 0.0, 0.0, 0.0)

    @staticmethod
    def _center(b: Bbox) -> Tuple[float, float]:
        x, y, w, h = b
        return x + w / 2.0, y + h / 2.0

    def _predict_bbox(self) -> Optional[Bbox]:
        if self._bbox is None:
            return None

        x, y, w, h = self._bbox
        vx, vy, vw, vh = self._vel

        # Light decay keeps the box moving, but prevents drift from exploding.
        decay = 0.92 ** max(self._lost, 1)
        px = int(round(x + vx * decay))
        py = int(round(y + vy * decay))
        pw = max(1, int(round(w + vw * decay)))
        ph = max(1, int(round(h + vh * decay)))
        return (px, py, pw, ph)

    def _update_velocity(self, prev: Bbox, curr: Bbox) -> None:
        px, py = self._center(prev)
        cx, cy = self._center(curr)
        prev_w, prev_h = prev[2], prev[3]
        curr_w, curr_h = curr[2], curr[3]

        # Smooth the estimated motion so the track can follow moving vehicles.
        self._vel = (
            0.7 * self._vel[0] + 0.3 * (cx - px),
            0.7 * self._vel[1] + 0.3 * (cy - py),
            0.7 * self._vel[2] + 0.3 * (curr_w - prev_w),
            0.7 * self._vel[3] + 0.3 * (curr_h - prev_h),
        )

    def update(self, detections: List[Bbox]) -> TrackUpdate:
        valid = [d for d in detections if _valid_bbox(d)]

        # No active track yet: initialize from the largest detection.
        if self._bbox is None:
            if not valid:
                return TrackUpdate(bbox=None, source="none", lost=0)
            best = max(valid, key=lambda b: b[2] * b[3])
            self._bbox = best
            self._lost = 0
            self._vel = (0.0, 0.0, 0.0, 0.0)
            return TrackUpdate(bbox=self._bbox, source="detect", lost=0)

        best_det: Optional[Bbox] = None
        best_iou = 0.0
        for det in valid:
            v = _iou(self._bbox, det)
            if v > best_iou:
                best_iou = v
                best_det = det

        if best_det is not None and best_iou >= self.iou_threshold:
            prev = self._bbox
            self._bbox = _smooth(self._bbox, best_det, self.smooth_alpha)
            self._update_velocity(prev, self._bbox)
            self._lost = 0
            return TrackUpdate(bbox=self._bbox, source="detect", lost=0)

        # Fallback: keep last track for short occlusions/missed detections.
        self._lost += 1
        if self._lost <= self.max_lost:
            predicted = self._predict_bbox()
            if predicted is not None:
                self._bbox = predicted
                return TrackUpdate(bbox=self._bbox, source="predict", lost=self._lost, track_id=0)
            return TrackUpdate(bbox=self._bbox, source="track_only", lost=self._lost, track_id=0)

        self._bbox = None
        self._lost = 0
        self._vel = (0.0, 0.0, 0.0, 0.0)
        return TrackUpdate(bbox=None, source="none", lost=0, track_id=0)


class MultiPlateTracker:
    def __init__(
        self,
        iou_threshold: float = 0.15,
        max_lost: int = 12,
        smooth_alpha: float = 0.65,
        max_tracks: int = 6,
        spawn_iou_threshold: float = 0.35,
        center_dist_threshold: float = 1.2,
        center_dist_weight: float = 0.25,
    ) -> None:
        self.iou_threshold = float(iou_threshold)
        self.max_lost = int(max_lost)
        self.smooth_alpha = float(smooth_alpha)
        self.max_tracks = int(max_tracks)
        self.spawn_iou_threshold = float(spawn_iou_threshold)
        self.center_dist_threshold = float(center_dist_threshold)
        self.center_dist_weight = float(center_dist_weight)
        self._tracks: Dict[int, _TrackState] = {}
        self._next_id = 1

    @staticmethod
    def _center(b: Bbox) -> Tuple[float, float]:
        x, y, w, h = b
        return x + w / 2.0, y + h / 2.0

    def _predict_bbox(self, st: _TrackState) -> Bbox:
        x, y, w, h = st.bbox
        vx, vy, vw, vh = st.vel
        decay = 0.92 ** max(st.lost, 1)
        px = int(round(x + vx * decay))
        py = int(round(y + vy * decay))
        pw = max(1, int(round(w + vw * decay)))
        ph = max(1, int(round(h + vh * decay)))
        return (px, py, pw, ph)

    def _update_velocity(self, st: _TrackState, prev: Bbox, curr: Bbox) -> None:
        px, py = self._center(prev)
        cx, cy = self._center(curr)
        st.vel = (
            0.7 * st.vel[0] + 0.3 * (cx - px),
            0.7 * st.vel[1] + 0.3 * (cy - py),
            0.7 * st.vel[2] + 0.3 * (curr[2] - prev[2]),
            0.7 * st.vel[3] + 0.3 * (curr[3] - prev[3]),
        )

    def _new_track(self, bbox: Bbox) -> _TrackState:
        tid = self._next_id
        self._next_id += 1
        return _TrackState(track_id=tid, bbox=bbox, vel=(0.0, 0.0, 0.0, 0.0), lost=0)

    def update(self, detections: List[Bbox]) -> List[TrackUpdate]:
        valid = [d for d in detections if _valid_bbox(d)]
        updates: List[TrackUpdate] = []

        # Bootstrap tracks when no active states exist.
        if not self._tracks:
            for det in valid[: self.max_tracks]:
                st = self._new_track(det)
                self._tracks[st.track_id] = st
                updates.append(TrackUpdate(bbox=st.bbox, source="detect", lost=0, track_id=st.track_id))
            return updates

        track_ids = sorted(self._tracks.keys())
        predicted = {tid: self._predict_bbox(self._tracks[tid]) for tid in track_ids}

        # Greedy IoU assignment.
        pairs: List[Tuple[float, int, int]] = []
        for ti, tid in enumerate(track_ids):
            pb = predicted[tid]
            for di, det in enumerate(valid):
                iou_v = _iou(pb, det)
                cdn = _center_distance_norm(pb, det)
                if iou_v < self.iou_threshold and cdn > self.center_dist_threshold:
                    continue
                # Higher score is better: IoU dominates, distance penalizes far jumps.
                score = iou_v - self.center_dist_weight * cdn
                pairs.append((score, ti, di))
        pairs.sort(key=lambda x: x[0], reverse=True)

        used_t: set[int] = set()
        used_d: set[int] = set()
        matches: List[Tuple[int, int]] = []
        for score_v, ti, di in pairs:
            if score_v < -self.center_dist_weight * self.center_dist_threshold:
                break
            if ti in used_t or di in used_d:
                continue
            used_t.add(ti)
            used_d.add(di)
            matches.append((ti, di))

        # Update matched tracks.
        matched_t_indices = set()
        for ti, di in matches:
            tid = track_ids[ti]
            st = self._tracks[tid]
            prev = st.bbox
            st.bbox = _smooth(predicted[tid], valid[di], self.smooth_alpha)
            self._update_velocity(st, prev, st.bbox)
            st.lost = 0
            matched_t_indices.add(ti)
            updates.append(TrackUpdate(bbox=st.bbox, source="detect", lost=0, track_id=tid))

        # Keep unmatched tracks by prediction for short gaps.
        for ti, tid in enumerate(track_ids):
            if ti in matched_t_indices:
                continue
            st = self._tracks[tid]
            st.lost += 1
            if st.lost <= self.max_lost:
                st.bbox = predicted[tid]
                updates.append(TrackUpdate(bbox=st.bbox, source="predict", lost=st.lost, track_id=tid))
            else:
                del self._tracks[tid]

        # Spawn new tracks from unmatched detections.
        for di, det in enumerate(valid):
            if di in used_d:
                continue
            if len(self._tracks) >= self.max_tracks:
                break

            # Avoid creating a new track for a detection that mostly overlaps existing tracks.
            duplicate = False
            for st in self._tracks.values():
                if _iou(st.bbox, det) >= self.spawn_iou_threshold:
                    duplicate = True
                    break
            if duplicate:
                continue

            st = self._new_track(det)
            self._tracks[st.track_id] = st
            updates.append(TrackUpdate(bbox=st.bbox, source="detect", lost=0, track_id=st.track_id))

        updates.sort(key=lambda u: u.track_id)
        return updates
