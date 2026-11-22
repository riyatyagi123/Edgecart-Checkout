"""Train the hand + product detector described in the patent (dataset.yaml).

Label your images with two classes (0 = hand, 1 = product), place them under
training/datasets/retail_interaction/{images,labels}/{train,val}, then:
  python training/train_yolo.py --epochs 300
The edge node automatically uses the 'hand' class of such a model.
"""
import argparse
from ultralytics import YOLO
from _common import DEVICE, RUNS_DIR, TRAIN_DIR, resolve_data

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(TRAIN_DIR / "dataset.yaml"))
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--export-onnx", action="store_true", help="export for edge devices")
    a = ap.parse_args()
    model = YOLO(a.model)
    model.train(data=resolve_data(a.data), epochs=a.epochs, patience=50, imgsz=640, batch=a.batch, device=DEVICE,
                optimizer="auto", lr0=0.001, mosaic=1.0, project=str(RUNS_DIR), name="yolov8n_hand_product",
                exist_ok=True)
    if a.export_onnx:
        print("ONNX model:", model.export(format="onnx"))
