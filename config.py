"""Central configuration. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


HOST: str = os.getenv("GRAB_GO_HOST", "127.0.0.1")
PORT: int = int(os.getenv("GRAB_GO_PORT", "8000"))
DEBUG: bool = _bool("GRAB_GO_DEBUG", "false")

# YOLOv8 detector. A bare name such as "yolov8s.pt" is auto-downloaded by ultralytics.
# yolov8s = best accuracy/speed balance on a laptop CPU; use yolov8n.pt on a Raspberry Pi.
_default_yolo = MODELS_DIR / "yolov8s.pt"
YOLO_MODEL: str = os.getenv("GRAB_GO_YOLO_MODEL", str(_default_yolo) if _default_yolo.exists() else "yolov8s.pt")
YOLO_CONFIDENCE: float = float(os.getenv("GRAB_GO_CONFIDENCE", "0.30"))

# CLIP vision-language model. Weights (~340 MB) download once into models/clip/.
USE_CLIP: bool = _bool("GRAB_GO_USE_CLIP", "true")
CLIP_MODEL: str = os.getenv("GRAB_GO_CLIP_MODEL", "ViT-B/32")
CLIP_WEIGHTS_DIR: str = os.getenv("GRAB_GO_CLIP_DIR", str(MODELS_DIR / "clip"))
CLIP_THRESHOLD: float = float(os.getenv("GRAB_GO_CLIP_THRESHOLD", "0.38"))

# Set to false to start the web app without loading any AI models (UI/cart testing).
ENABLE_VISION: bool = _bool("GRAB_GO_ENABLE_VISION", "true")

GST_RATE: float = float(os.getenv("GRAB_GO_GST_RATE", "0.18"))

CORS_ORIGINS: list[str] = os.getenv("GRAB_GO_CORS_ORIGINS", "*").split(",")
LOG_LEVEL: str = os.getenv("GRAB_GO_LOG_LEVEL", "INFO")

# Shown in the kiosk header and on receipts.
STORE_NAME: str = os.getenv("GRAB_GO_STORE_NAME", "Grab & Go")
KIOSK_NAME: str = os.getenv("GRAB_GO_KIOSK_NAME", "Kiosk 1 · Main entrance")
# UPI ID encoded in the checkout QR code (demo value - set your own merchant VPA).
UPI_ID: str = os.getenv("GRAB_GO_UPI_ID", "grabandgo@upi")
UPI_PAYEE: str = os.getenv("GRAB_GO_UPI_PAYEE", "Grab and Go Store")
FIRST_ORDER_NUMBER: int = int(os.getenv("GRAB_GO_FIRST_ORDER", "1001"))
