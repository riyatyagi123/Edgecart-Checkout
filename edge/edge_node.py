"""
Decentralized edge shelf node (P35 smart_retail_scanner.py + run_inference.py).

Runs on the device attached to a shelf camera (laptop, Raspberry Pi, Jetson):
  1. YOLOv8 + ByteTrack follow people (hands) and products on the shelf.
  2. SpatialInteractionEngine turns overlaps / displacement into Take, Return, Touch.
  3. Barcodes shown to the camera are added directly (ground truth).
  4. Each Take / Return is applied to the local ledger and, if --server is given,
     POSTed to the central Grab & Go server, which pushes it to the kiosk UI live.

The node keeps working if the server is unreachable (decentralized operation);
events are queued and re-sent when the server comes back.

Examples
  python edge/edge_node.py --source 0 --server http://127.0.0.1:8000
  python edge/edge_node.py --source sample_videos/shop_shelf.mp4 --no-display --save out.mp4
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import deque
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from vision.catalog import COCO_RETAIL_MAP, PERSON_CLASS, lookup_product  # noqa: E402
from vision.engine import VisionEngine  # noqa: E402
from vision.interaction import SpatialInteractionEngine  # noqa: E402


class ServerLink:
    """Best-effort REST link to the central server with an offline queue."""

    def __init__(self, url: str | None, node_id: str):
        self.url = url.rstrip("/") if url else None
        self.node_id = node_id
        self.queue: deque[dict] = deque(maxlen=500)
        self.online = None
        if self.url:
            import requests
            self.session = requests.Session()

    def send(self, payload: dict) -> None:
        if not self.url:
            return
        self.queue.append({"node_id": self.node_id, **payload})
        self.flush()

    def flush(self) -> None:
        while self.url and self.queue:
            try:
                r = self.session.post(f"{self.url}/api/edge/event", json=self.queue[0], timeout=2)
                self.queue.popleft()
                self.online = True
                if r.status_code >= 400:
                    print(f"[server] rejected event: {r.text[:120]}")
            except Exception:
                if self.online is not False:
                    print(f"[server] unreachable - queueing events ({len(self.queue)})")
                self.online = False
                return


def draw_overlay(frame, products, hands, ledger, status, barcode, engine_mode):
    h, w = frame.shape[:2]
    for b in hands:
        cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (255, 100, 100), 2)
    for d in products:
        x1, y1, x2, y2 = d["bbox"]
        item = COCO_RETAIL_MAP.get(d["label"], {})
        color = (0, 200, 255) if d["label"] == "cell phone" else (100, 255, 100)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        tag = f"#{d.get('track_id')} {item.get('name', d['label'])} Rs.{item.get('price', '?')}"
        cv2.putText(frame, tag, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    if barcode and barcode.get("points"):
        import numpy as np
        cv2.polylines(frame, [np.array(barcode["points"], dtype=int)], True, (0, 255, 0), 3)

    # cart panel
    lines = list(ledger.items())[-6:]
    ph = 110 + 24 * len(lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (370, ph), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.putText(frame, "EDGE NODE - SMART CART", (22, 38), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, engine_mode[:48], (22, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 255), 1)
    y, total = 84, 0
    for pid, e in lines:
        cv2.putText(frame, f"{e['name'][:26]}", (22, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1)
        cv2.putText(frame, f"x{e['qty']}", (320, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)
        y += 24
    total = sum(e["price"] * e["qty"] for e in ledger.values())
    cv2.putText(frame, f"TOTAL: Rs. {total}", (22, ph - 14), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
    color = (0, 165, 255) if "TOUCH" in status else (0, 255, 0) if ("TAKE" in status or "BARCODE" in status) else (200, 200, 200)
    cv2.putText(frame, status, (390, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
    cv2.putText(frame, "[q] quit  [c] clear", (w - 190, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grab & Go decentralized edge shelf node")
    ap.add_argument("--source", default="0", help="camera index or video file")
    ap.add_argument("--server", default=None, help="central server URL, e.g. http://127.0.0.1:8000")
    ap.add_argument("--node-id", default="edge-01")
    ap.add_argument("--model", default=config.YOLO_MODEL, help="YOLOv8 weights (yolov8s.pt / yolov8x.pt = more accurate)")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--clip", action="store_true", help="also load CLIP (slower on edge devices)")
    ap.add_argument("--no-display", action="store_true", help="headless mode (no OpenCV window)")
    ap.add_argument("--save", default=None, help="write annotated video to this path")
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--barcode-every", type=int, default=3, help="decode barcodes every N frames")
    ap.add_argument("--product-conf", type=float, default=0.35, help="min confidence for shelf products")
    ap.add_argument("--ignore", default="cell phone",
                    help="comma-separated classes never billed at the shelf (shopper's own items)")
    ap.add_argument("--cooldown", type=float, default=3.0, help="seconds before the same product can be taken again")
    args = ap.parse_args(argv)

    engine = VisionEngine(yolo_model=args.model, use_clip=args.clip, yolo_conf=args.conf,
                          clip_weights_dir=config.CLIP_WEIGHTS_DIR).load()
    if not engine.has_yolo:
        print("YOLO model could not be loaded:", engine.errors.get("yolo"))
        return 1

    src = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"Cannot open video source: {args.source}")
        return 1

    display = not args.no_display and (os.name == "nt" or os.environ.get("DISPLAY") or sys.platform == "darwin")
    writer = None
    interaction = SpatialInteractionEngine()
    link = ServerLink(args.server, args.node_id)
    ledger: dict[str, dict] = {}
    scanned_codes: set[str] = set()
    status, status_until = "STATUS: SCANNING...", 0.0
    barcode = None
    frame_no = 0
    events_log: list[dict] = []
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 25
    is_file = not isinstance(src, int)
    last_take: dict[str, float] = {}
    last_conf: dict[int, float] = {}
    ignored = {c.strip() for c in args.ignore.split(",") if c.strip()}
    # A custom model trained with training/dataset.yaml has a real "hand" class;
    # the stock COCO model only has "person", which is used as the hand proxy.
    hand_label = "hand" if "hand" in set(engine.yolo.names.values()) else PERSON_CLASS
    print(f"Edge node {args.node_id}: source={args.source} hand-class='{hand_label}' server={args.server or 'offline'}")

    def apply(event: str, product: dict, extra: dict):
        pid = product["id"]
        if event == "Take":
            e = ledger.setdefault(pid, {"name": product["name"], "price": product["price"], "qty": 0})
            e["qty"] += 1
        elif event == "Return" and pid in ledger:
            ledger[pid]["qty"] -= 1
            if ledger[pid]["qty"] <= 0:
                ledger.pop(pid)
        link.send({"event": event, "product_id": pid, **extra})
        events_log.append({"frame": frame_no, "event": event, "product": product["name"]})
        print(f"[frame {frame_no:5d}] {event:6s} -> {product['name']}")

    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_no += 1
        fh, fw = frame.shape[:2]
        dets = engine.yolo_boxes(frame, track=True)
        now = frame_no / fps_src if is_file else time.time()
        hands = [d["bbox"] for d in dets if d["label"] == hand_label and d["confidence"] > 0.4]
        products = [d for d in dets if d["label"] in COCO_RETAIL_MAP and d["label"] not in ignored
                    and d["confidence"] >= args.product_conf
                    and (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]) < 0.25 * fw * fh]

        for d in products:
            if d.get("track_id") is not None:
                last_conf[d["track_id"]] = d["confidence"]
        for ev in interaction.update(products, hands):
            if ev["event"] == "Touch":
                status, status_until = f"TOUCH: {ev['label'].upper()}", time.time() + 1.0
                continue
            product = COCO_RETAIL_MAP[ev["label"]]
            if ev["event"] == "Take":
                if now - last_take.get(product["id"], -1e9) < args.cooldown:
                    continue
                last_take[product["id"]] = now
            status, status_until = f"{ev['event'].upper()}: {product['name']}", time.time() + 2.0
            apply(ev["event"], product, {"label": ev["label"], "track_id": ev["track_id"],
                                         "confidence": round(last_conf.get(ev["track_id"], 0.0), 3) or None})

        if frame_no % max(1, args.barcode_every) == 0:
            barcode = engine.decode_barcode(frame)
            if barcode and barcode["code"] not in scanned_codes:
                scanned_codes.add(barcode["code"])
                product = lookup_product(barcode["product_id"])
                status, status_until = f"BARCODE: {product['name']}", time.time() + 2.0
                apply("Take", product, {"label": "barcode", "confidence": 1.0})

        if time.time() > status_until:
            status = "STATUS: SCANNING..."
        if frame_no % 30 == 0:
            link.flush()

        draw_overlay(frame, products, hands, ledger, status, barcode, engine.mode)

        if args.save:
            if writer is None:
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), fps, (fw, fh))
            writer.write(frame)
        if display:
            cv2.imshow(f"Grab & Go Edge Node [{args.node_id}]", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                ledger.clear()
                scanned_codes.clear()
        if args.max_frames and frame_no >= args.max_frames:
            break

    cap.release()
    if writer:
        writer.release()
    if display:
        cv2.destroyAllWindows()
    link.flush()
    dt = time.time() - t0
    total = sum(e["price"] * e["qty"] for e in ledger.values())
    print(f"\nProcessed {frame_no} frames in {dt:.1f}s ({frame_no / max(dt, 1e-6):.1f} FPS)")
    print(f"Events: {len(events_log)} | Final cart: " +
          (", ".join(f"{e['name']} x{e['qty']}" for e in ledger.values()) or "empty") + f" | Total Rs.{total}")
    if link.queue:
        print(f"WARNING: {len(link.queue)} events could not be delivered to {args.server}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
