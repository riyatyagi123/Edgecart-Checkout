"""Step 1 - extract frames from a shelf video into custom_dataset/raw_images.

  python training/extract_frames.py --video sample_videos/shop_shelf.mp4 --every 5
"""
import argparse
import cv2
from _common import CUSTOM_DATASET, ROOT


def extract_frames(video_path, output_dir, frame_skip=15):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Video '{video_path}' not found or unreadable.")
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    count = saved = 0
    stem = video_path.stem if hasattr(video_path, "stem") else "frame"
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if count % frame_skip == 0:
            cv2.imwrite(str(output_dir / f"{stem}_{saved:05d}.jpg"), frame)
            saved += 1
        count += 1
    cap.release()
    print(f"Saved {saved} frames to {output_dir}")
    print("Next: python training/auto_train.py  (auto-label + train)  or label them in Roboflow/CVAT.")
    return saved


if __name__ == "__main__":
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(ROOT / "sample_videos" / "shop_shelf.mp4"))
    ap.add_argument("--out", default=str(CUSTOM_DATASET / "raw_images"))
    ap.add_argument("--every", type=int, default=5)
    a = ap.parse_args()
    extract_frames(Path(a.video), Path(a.out), a.every)
