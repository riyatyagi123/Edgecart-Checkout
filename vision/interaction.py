"""
Spatial interaction engine (P35 interaction_logic.py, completed).

Implements the Take / Return / Touch state machine from the patent flowchart:
  * Touch  - hand (person) box overlaps a product box, product has not moved
  * Take   - a touched product is displaced from its resting shelf position
             (or leaves the frame while being touched)
  * Return - a taken product comes back to its resting position
"""
from __future__ import annotations

from dataclasses import dataclass, field


def calculate_iou(a, b) -> float:
    xa, ya = max(a[0], b[0]), max(a[1], b[1])
    xb, yb = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    den = float(area_a + area_b - inter)
    return inter / den if den > 0 else 0.0


def overlap_ratio(product, hand) -> float:
    """Fraction of the product box covered by the hand/person box."""
    xa, ya = max(product[0], hand[0]), max(product[1], hand[1])
    xb, yb = min(product[2], hand[2]), min(product[3], hand[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area = max(1, (product[2] - product[0]) * (product[3] - product[1]))
    return inter / area


def _center(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


@dataclass
class TrackedProduct:
    track_id: int
    label: str
    home_box: list[int]
    last_box: list[int]
    state: str = "Idle"
    touched: bool = False
    missing_frames: int = 0
    seen_frames: int = 1
    displaced_streak: int = 0
    frames_since_touch: int = 10**6


@dataclass
class SpatialInteractionEngine:
    touch_threshold: float = 0.30     # fraction of product box covered by a hand/person
    displacement_ratio: float = 1.0   # move > 1.0 x box diagonal == displaced
    displaced_frames: int = 6         # ...for this many consecutive frames
    lost_frames_for_take: int = 15    # touched product vanishes for N frames == taken
    touch_memory: int = 5             # a "recent touch" is within N frames
    min_seen_frames: int = 8          # ignore short-lived / flickering tracks
    products: dict[int, TrackedProduct] = field(default_factory=dict)

    # kept for API compatibility with the original P35 class
    def calculate_iou(self, a, b) -> float:
        return calculate_iou(a, b)

    def determine_interaction_state(self, hand_box, product_box, product_in_shelf_zone):
        iou = calculate_iou(hand_box, product_box)
        if iou > self.touch_threshold or overlap_ratio(product_box, hand_box) > self.touch_threshold:
            return ("Touch" if product_in_shelf_zone else "Take"), iou
        return "Idle", iou

    def _displaced(self, p: TrackedProduct, box) -> bool:
        hx, hy = _center(p.home_box)
        cx, cy = _center(box)
        diag = ((p.home_box[2] - p.home_box[0]) ** 2 + (p.home_box[3] - p.home_box[1]) ** 2) ** .5
        return ((cx - hx) ** 2 + (cy - hy) ** 2) ** .5 > self.displacement_ratio * max(diag, 1)

    def update(self, products: list[dict], hands: list[list[int]]) -> list[dict]:
        """products: [{track_id, label, bbox}], hands: [bbox]. Returns events."""
        events: list[dict] = []
        seen = set()
        for det in products:
            tid = det.get("track_id")
            if tid is None:
                continue
            seen.add(tid)
            box = det["bbox"]
            p = self.products.get(tid)
            if p is None:
                self.products[tid] = TrackedProduct(tid, det["label"], box, box)
                continue
            p.last_box, p.missing_frames = box, 0
            p.seen_frames += 1
            touching = any(overlap_ratio(box, h) > self.touch_threshold for h in hands)
            p.frames_since_touch = 0 if touching else p.frames_since_touch + 1
            p.displaced_streak = p.displaced_streak + 1 if self._displaced(p, box) else 0
            stable = p.seen_frames >= self.min_seen_frames
            displaced = p.displaced_streak >= self.displaced_frames

            if p.state == "Idle" and touching and stable:
                p.state, p.touched = "Touch", True
                events.append({"event": "Touch", "track_id": tid, "label": p.label})
            elif p.state == "Touch":
                if displaced and p.frames_since_touch <= self.touch_memory:
                    p.state = "Take"
                    events.append({"event": "Take", "track_id": tid, "label": p.label})
                elif not touching and p.displaced_streak == 0 and p.frames_since_touch > self.touch_memory:
                    p.state, p.touched = "Idle", False
            elif p.state == "Take" and p.displaced_streak == 0 and not touching:
                p.state, p.touched = "Return", False
                events.append({"event": "Return", "track_id": tid, "label": p.label})
            elif p.state == "Return" and touching:
                p.state, p.touched = "Touch", True
            if p.state in ("Idle", "Return") and not touching and p.displaced_streak == 0 and stable:
                p.home_box = box  # slow re-anchoring compensates for camera drift

        for tid, p in list(self.products.items()):
            if tid in seen:
                continue
            p.missing_frames += 1
            if p.state == "Touch" and p.missing_frames == self.lost_frames_for_take \
                    and p.frames_since_touch <= self.touch_memory and p.seen_frames >= self.min_seen_frames:
                p.state = "Take"
                events.append({"event": "Take", "track_id": tid, "label": p.label})
            if p.missing_frames > 300:
                del self.products[tid]
        return events
