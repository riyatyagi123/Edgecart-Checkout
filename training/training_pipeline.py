"""Full train -> validate -> test pipeline with evaluation plots (confusion matrix, PR, F1).

  python training/training_pipeline.py --data training/custom_dataset.yaml --model yolov8s.pt
Reports are written to training/runs/retail_model*/.
"""
import argparse
import yaml
from ultralytics import YOLO
from _common import DEVICE, RUNS_DIR, TRAIN_DIR, resolve_data

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(TRAIN_DIR / "custom_dataset.yaml"))
    ap.add_argument("--model", default="yolov8s.pt")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=16)
    a = ap.parse_args()
    a.data = resolve_data(a.data)

    model = YOLO(a.model)
    model.train(data=a.data, epochs=a.epochs, imgsz=640, batch=a.batch, project=str(RUNS_DIR),
                name="retail_model", exist_ok=True, device=DEVICE)
    best = YOLO(str(RUNS_DIR / "retail_model" / "weights" / "best.pt"))
    val = best.val(data=a.data, split="val", plots=True, conf=0.25, iou=0.60, save_json=True,
                   project=str(RUNS_DIR), name="retail_model_val", exist_ok=True)
    print(f"VAL  mAP50={val.box.map50:.3f}  mAP50-95={val.box.map:.3f}")
    if "test" in (yaml.safe_load(open(a.data)) or {}):
        test = best.val(data=a.data, split="test", plots=True, conf=0.25,
                        project=str(RUNS_DIR), name="retail_model_test", exist_ok=True)
        print(f"TEST mAP50={test.box.map50:.3f}  mAP50-95={test.box.map:.3f}")
