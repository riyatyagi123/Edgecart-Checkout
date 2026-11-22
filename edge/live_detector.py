"""
Universal open-vocabulary retail detector (P35 live_camera_detector.py).

Uses YOLO-World so you can detect arbitrary product names ("chips packet",
"instant noodles", ...) without training. Weights download on first run.

  python edge/live_detector.py --source 0
  python edge/live_detector.py --source sample_videos/grocery_01.mp4 --no-display --save out.mp4
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vision.torch_compat  # noqa: E402,F401

TARGET_CLASSES = [
    "cell phone", "chips packet", "potato chips", "chocolate bar", "candy", "cold drink bottle",
    "soda can", "biscuit packet", "cookies", "snack packet", "packaged food", "instant noodles",
    "juice box", "apple", "banana", "orange", "bell pepper", "vegetable", "fruit", "cereal box",
    "soap", "cup", "book", "wallet", "grocery item", "human hand", "person",
]


def get_color(name: str):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)  # stable across runs (hash() is salted)
    return (h % 200 + 40, (h >> 8) % 200 + 40, (h >> 16) % 200 + 40)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--model", default="yolov8s-world.pt")
    ap.add_argument("--classes", default=",".join(TARGET_CLASSES))
    ap.add_argument("--conf", type=float, default=0.12)
    ap.add_argument("--no-display", action="store_true")
    ap.add_argument("--save", default=None)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args(argv)

    from ultralytics import YOLOWorld
    model = YOLOWorld(args.model)
    model.set_classes([c.strip() for c in args.classes.split(",") if c.strip()])

    src = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print("Video source not accessible:", args.source)
        return 1
    if isinstance(src, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    display = not args.no_display and (os.name == "nt" or os.environ.get("DISPLAY") or sys.platform == "darwin")
    writer, n, seen = None, 0, {}

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        res = model.predict(frame, conf=args.conf, iou=0.45, verbose=False)[0]
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (25, 25, 25), -1)
        cv2.putText(frame, "UNIVERSAL RETAIL SCANNER (YOLO-World) | 'q' to exit", (15, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        for box in res.boxes or []:
            name = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            seen[name] = max(seen.get(name, 0), conf)
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            color = get_color(name)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{name.upper()} {int(conf * 100)}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, max(0, y1 - 24)), (x1 + tw + 8, y1), color, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        if args.save:
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), cap.get(cv2.CAP_PROP_FPS) or 25, (w, h))
            writer.write(frame)
        if display:
            cv2.imshow("Live Universal Retail Detector", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        if args.max_frames and n >= args.max_frames:
            break

    cap.release()
    if writer:
        writer.release()
    if display:
        cv2.destroyAllWindows()
    print(f"Processed {n} frames. Detected:", ", ".join(f"{k} ({v:.2f})" for k, v in sorted(seen.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
