"""
Hybrid edge vision engine.

  YOLOv8 (from P35)          -> localises products / people (real bounding boxes)
  CLIP ViT-B/32 (grab_and_go) -> zero-shot brand identification of the crop
  Barcode (pyzbar or OpenCV)  -> 100% ground-truth override

Every component is optional: if CLIP weights cannot be loaded the engine falls
back to YOLO's COCO class -> product mapping; if YOLO is missing it falls back
to CLIP on the central scan reticle; barcodes work with either.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from . import torch_compat  # noqa: F401  (patches torch.load before ultralytics imports)
from .catalog import (
    BACKGROUND_PROMPTS, BARCODE_CATALOG, COCO_RETAIL_MAP, PERSON_CLASS, PRODUCT_CLASSES,
    RETAIL_CATALOG, UNKNOWN_BARCODE_PRICE,
)

logger = logging.getLogger("grab_and_go.vision")

try:  # pyzbar needs the native zbar library (bundled with the Windows wheel)
    import pyzbar.pyzbar as _pyzbar
except Exception:  # pragma: no cover - depends on the host OS
    _pyzbar = None


class VisionEngine:
    def __init__(
        self,
        yolo_model: str = "yolov8n.pt",
        use_clip: bool = True,
        clip_model_name: str = "ViT-B/32",
        clip_weights_dir: str | Path | None = None,
        yolo_conf: float = 0.30,
        clip_threshold: float = 0.38,
        device: str | None = None,
    ) -> None:
        self.yolo_model_path = yolo_model
        self.use_clip = use_clip
        self.clip_model_name = clip_model_name
        self.clip_weights_dir = str(clip_weights_dir) if clip_weights_dir else None
        self.yolo_conf = yolo_conf
        self.clip_threshold = clip_threshold
        self.device = device

        self.yolo = None
        self.clip_model = None
        self.clip_preprocess = None
        self.class_features = None
        self.cv_barcode = None
        self._lock = threading.Lock()
        self.errors: dict[str, str] = {}

    # ------------------------------------------------------------------ load
    def load(self) -> "VisionEngine":
        import torch

        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            from ultralytics import YOLO
            self.yolo = YOLO(self.yolo_model_path)
            logger.info("YOLO detector loaded: %s", self.yolo_model_path)
        except Exception as exc:
            self.errors["yolo"] = str(exc)
            logger.warning("YOLO unavailable (%s) - continuing without it.", exc)

        if self.use_clip:
            self._load_clip()

        if _pyzbar is None:
            try:
                self.cv_barcode = cv2.barcode.BarcodeDetector()
                logger.info("Barcode decoder: OpenCV (pyzbar not available)")
            except Exception as exc:
                self.errors["barcode"] = str(exc)
                logger.warning("No barcode decoder available: %s", exc)
        else:
            logger.info("Barcode decoder: pyzbar")

        logger.info("Vision engine ready - mode: %s", self.mode)
        return self

    def _load_clip(self) -> None:
        import torch
        try:
            import clip
        except Exception as exc:
            self.errors["clip"] = f"clip package not installed: {exc}"
            logger.warning("CLIP unavailable: %s", self.errors["clip"])
            return
        try:
            model, preprocess = clip.load(
                self.clip_model_name, device=self.device, download_root=self.clip_weights_dir
            )
            model.eval()
            feats = []
            with torch.no_grad():
                for prod in RETAIL_CATALOG:
                    feats.append(self._mean_text_feature(clip, model, prod["prompts"]))
                feats.append(self._mean_text_feature(clip, model, BACKGROUND_PROMPTS))
            self.clip_model, self.clip_preprocess = model, preprocess
            self.class_features = torch.cat(feats, dim=0)
            logger.info("CLIP %s loaded with %d products + background class.",
                        self.clip_model_name, len(RETAIL_CATALOG))
        except Exception as exc:
            self.errors["clip"] = str(exc)
            logger.warning("CLIP weights could not be loaded (%s) - using YOLO class mapping.", exc)

    def _mean_text_feature(self, clip, model, prompts):
        toks = clip.tokenize(prompts).to(self.device)
        f = model.encode_text(toks).float()
        f /= f.norm(dim=-1, keepdim=True)
        m = f.mean(dim=0, keepdim=True)
        return m / m.norm(dim=-1, keepdim=True)

    # --------------------------------------------------------------- status
    @property
    def has_yolo(self) -> bool:
        return self.yolo is not None

    @property
    def has_clip(self) -> bool:
        return self.clip_model is not None

    @property
    def mode(self) -> str:
        if self.has_yolo and self.has_clip:
            return "hybrid (YOLOv8 localisation + CLIP brand recognition)"
        if self.has_clip:
            return "CLIP only (scan reticle)"
        if self.has_yolo:
            return "YOLOv8 only (COCO class mapping)"
        return "barcode only"

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.mode, "device": self.device, "yolo": self.has_yolo, "clip": self.has_clip,
            "barcode": "pyzbar" if _pyzbar else ("opencv" if self.cv_barcode else None),
            "errors": self.errors,
        }

    # ---------------------------------------------------------------- YOLO
    def yolo_boxes(self, frame: np.ndarray, track: bool = False) -> list[dict[str, Any]]:
        """Raw YOLO detections: [{label, confidence, bbox, track_id}]"""
        if self.yolo is None:
            return []
        with self._lock:
            if track:
                res = self.yolo.track(frame, persist=True, tracker="bytetrack.yaml",
                                      conf=min(self.yolo_conf, 0.2), verbose=False)[0]
            else:
                res = self.yolo.predict(frame, conf=self.yolo_conf, verbose=False)[0]
        out = []
        if res.boxes is None or len(res.boxes) == 0:
            return out
        xyxy = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy()
        conf = res.boxes.conf.cpu().numpy()
        ids = res.boxes.id.cpu().numpy() if res.boxes.id is not None else [None] * len(cls)
        for b, c, s, t in zip(xyxy, cls, conf, ids):
            out.append({
                "label": self.yolo.names[int(c)], "confidence": float(s),
                "bbox": [int(v) for v in b], "track_id": int(t) if t is not None else None,
            })
        return out

    # ---------------------------------------------------------------- CLIP
    def classify_crop(self, crop_bgr: np.ndarray) -> tuple[dict[str, Any] | None, float]:
        if not self.has_clip or crop_bgr is None or crop_bgr.size < 2000:
            return None, 0.0
        import torch
        from PIL import Image
        try:
            pil = Image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))
            t = self.clip_preprocess(pil).unsqueeze(0).to(self.device)
            with self._lock, torch.no_grad():
                f = self.clip_model.encode_image(t).float()
                f /= f.norm(dim=-1, keepdim=True)
                probs = (100.0 * f @ self.class_features.T).softmax(dim=-1)[0].cpu().numpy()
            idx = int(np.argmax(probs))
            conf = float(probs[idx])
            if idx == len(RETAIL_CATALOG) or conf < self.clip_threshold:
                return None, conf
            return RETAIL_CATALOG[idx], conf
        except Exception as exc:
            logger.warning("CLIP inference error: %s", exc)
            return None, 0.0

    # ------------------------------------------------------------- barcode
    def decode_barcode(self, frame_bgr: np.ndarray) -> dict[str, Any] | None:
        found: list[tuple[str, list[list[int]]]] = []
        try:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            if _pyzbar is not None:
                codes = _pyzbar.decode(gray)
                if not codes:
                    codes = _pyzbar.decode(cv2.createCLAHE(2.5, (8, 8)).apply(gray))
                for b in codes:
                    pts = [[int(p.x), int(p.y)] for p in b.polygon] if b.polygon else []
                    found.append((b.data.decode("utf-8", "ignore").strip(), pts))
            elif self.cv_barcode is not None:
                # OpenCV >= 4.8: (retval, decoded_info, points, straight_code)
                res = self.cv_barcode.detectAndDecodeMulti(frame_bgr)
                infos = res[1] if len(res) > 1 else None
                points = res[2] if len(res) > 2 else None
                for i, code in enumerate(infos or ()):
                    if code:
                        pts = points[i].astype(int).tolist() if points is not None and i < len(points) else []
                        found.append((str(code).strip(), pts))
        except Exception as exc:
            logger.debug("Barcode decode error: %s", exc)

        for code, pts in found:
            if code in BARCODE_CATALOG:
                p = BARCODE_CATALOG[code]
                return {"code": code, "product_id": p["id"], "name": p["name"], "brand": p["brand"],
                        "price": p["price"], "emoji": p.get("emoji", "🏷️"), "points": pts}
            if len(code) >= 8:
                return {"code": code, "product_id": f"bc_{code}", "name": f"Verified Product ({code})",
                        "brand": "Barcode Scan", "price": UNKNOWN_BARCODE_PRICE, "emoji": "🏷️", "points": pts}
        return None

    # -------------------------------------------------- web checkout frame
    def analyze_checkout_frame(self, frame: np.ndarray) -> dict[str, Any]:
        """Process one webcam frame from the browser checkout kiosk."""
        fh, fw = frame.shape[:2]
        barcode = self.decode_barcode(frame)
        detections: list[dict[str, Any]] = []

        product_boxes = [
            d for d in self.yolo_boxes(frame)
            if d["label"] in PRODUCT_CLASSES and d["label"] != PERSON_CLASS
        ]
        product_boxes.sort(key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]),
                           reverse=True)

        if self.has_clip:
            if product_boxes:
                regions = [d["bbox"] for d in product_boxes[:2]]
            else:  # original grab_and_go behaviour: classify the centre reticle
                regions = [[int(fw * .20), int(fh * .15), int(fw * .80), int(fh * .85)]]
            for x1, y1, x2, y2 in regions:
                px, py = int((x2 - x1) * .1), int((y2 - y1) * .1)
                crop = frame[max(0, y1 - py):min(fh, y2 + py), max(0, x1 - px):min(fw, x2 + px)]
                prod, conf = self.classify_crop(crop)
                if prod:
                    detections.append(self._det(prod, conf, [x1, y1, x2, y2], "clip"))
                    break
        if not detections:
            for d in product_boxes:
                prod = COCO_RETAIL_MAP.get(d["label"])
                if prod:
                    detections.append(self._det(prod, d["confidence"], d["bbox"], "yolo"))
                    break

        return {"detections": detections, "barcode": barcode, "engine": self.mode}

    @staticmethod
    def _det(prod: dict[str, Any], conf: float, bbox: list[int], source: str) -> dict[str, Any]:
        return {
            "label": prod["name"].lower(), "product_id": prod["id"], "name": prod["name"],
            "brand": prod["brand"], "price": prod["price"], "emoji": prod.get("emoji", "📦"),
            "category": prod.get("category", ""), "confidence": round(float(conf), 2),
            "bbox": bbox, "source": source,
        }
