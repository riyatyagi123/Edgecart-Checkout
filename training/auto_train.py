"""Step 2 - auto-label raw frames with a zero-shot teacher (YOLO-World) and
self-train a compact YOLOv8 student for the edge node.

  python training/auto_train.py --epochs 60
Result: training/runs/auto_trained_model/weights/best.pt
Use it:  python edge/edge_node.py --model training/runs/auto_trained_model/weights/best.pt
"""
import argparse
import random
import shutil

import cv2
import yaml
from ultralytics import YOLO

from _common import CUSTOM_DATASET, DEVICE, RUNS_DIR, resolve_data

TEACHER_CLASSES = ["maggi noodles packet", "lays chips packet", "chocolate", "bottle", "grocery item",
                   "bell pepper", "fruit", "vegetable"]


def load_teacher():
    try:
        from ultralytics import YOLOWorld
        t = YOLOWorld("yolov8s-world.pt")
        t.set_classes(TEACHER_CLASSES)
        return t
    except Exception as e:
        print("YOLO-World unavailable, falling back to YOLOv8x:", e)
        return YOLO("yolov8x.pt")


def auto_label(val_split=0.2, conf=0.10):
    raw = CUSTOM_DATASET / "raw_images"
    images = sorted(p for p in raw.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not images:
        print(f"No images in {raw}. Run training/extract_frames.py first.")
        return None
    teacher = load_teacher()
    random.seed(0)
    random.shuffle(images)
    n_val = max(1, int(len(images) * val_split))
    labelled = 0
    for i, img_path in enumerate(images):
        split = "val" if i < n_val else "train"
        (CUSTOM_DATASET / "images" / split).mkdir(parents=True, exist_ok=True)
        (CUSTOM_DATASET / "labels" / split).mkdir(parents=True, exist_ok=True)
        frame = cv2.imread(str(img_path))
        shutil.copy(img_path, CUSTOM_DATASET / "images" / split / img_path.name)
        res = teacher.predict(frame, conf=conf, verbose=False)[0]
        lines = []
        if res.boxes is not None:
            for box, cls in zip(res.boxes.xywhn.cpu().numpy(), res.boxes.cls.cpu().numpy()):
                if teacher.names[int(cls)] != "person":
                    lines.append("0 " + " ".join(f"{v:.6f}" for v in box))
        (CUSTOM_DATASET / "labels" / split / (img_path.stem + ".txt")).write_text("\n".join(lines))
        labelled += bool(lines)
    print(f"Auto-labelled {len(images)} images ({labelled} with products).")
    cfg = {"path": CUSTOM_DATASET.name, "train": "images/train", "val": "images/val",
           "names": {0: "Grocery Product"}}
    out = CUSTOM_DATASET.parent / "custom_dataset.yaml"
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--student", default="yolov8s.pt")
    a = ap.parse_args()
    data = auto_label()
    if data:
        YOLO(a.student).train(data=resolve_data(data), epochs=a.epochs, imgsz=640, batch=a.batch,
                              project=str(RUNS_DIR), name="auto_trained_model", exist_ok=True, device=DEVICE)
        print("Done ->", RUNS_DIR / "auto_trained_model" / "weights" / "best.pt")
