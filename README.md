# Grab & Go — Decentralized Edge-Based Autonomous Retail Checkout

The integrated final build of two repositories:

| Source repo | What it contributed |
|---|---|
| `197Ashutosh/grab_and_go` | FastAPI server, kiosk web UI (scanner, cart, checkout, payment), CLIP brand recognition, barcode verification |
| `197Ashutosh/P35-Decentralized_Edge_Based_Grab_and_Go` | YOLOv8 detection and tracking, hand–product interaction logic (Touch / Take / Return), edge camera scripts, training pipeline, sample videos, evaluation charts and patent flowchart |

```
 ┌───────────── Edge shelf node(s) ─────────────┐        ┌──────── Central server (app.py) ────────┐
 │ camera → YOLOv8 + ByteTrack → hand/product   │  REST  │ /api/edge/event  → digital ledger (cart) │
 │ IoU → Touch / Take / Return state machine    │ ─────► │ /ws/cart  → live push to every browser   │
 │ barcode scan  · offline queue if server down │        │ /ws/detect ← kiosk webcam frames         │
 └──────────────────────────────────────────────┘        │   YOLOv8 box → CLIP brand → barcode      │
                                                         └───────────────┬──────────────────────────┘
                                                                         ▼
                                                  Kiosk UI  /  → /checkout → /payment-success
```

## Quick start

**Windows (VS Code terminal / PowerShell):**
```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Always use `python -m pip` / `python -m uvicorn` (not `pip.exe`), which works even when Windows
Application Control blocks small `.exe` files. If you see *"DLL load failed … Application Control policy"*,
turn **Smart App Control** off in Windows Security → App & browser control.

**Linux/macOS:** `./setup.sh`, then `./run_app.sh` (Linux barcodes also need `sudo apt install libzbar0`).

Open http://127.0.0.1:8000. Requirements: Python 3.10+ and Git (for the CLIP package). A GPU is optional.

## Screens
| URL | Who | What |
|---|---|---|
| `/` | shopper | **Initialize camera** → live scanning; items (or barcodes) held in the frame are added automatically, with Undo; cart with +/−; English/हिंदी; Call staff |
| `/checkout` | shopper | UPI (live QR for the exact amount), card or wallet; order summary with GST |
| `/payment-success` | shopper | itemised receipt, SMS request, auto-reset to a new order after 45 s |
| `/dashboard` | staff | orders and revenue today, live events (scans, shelf pick-ups, orders, help requests), connected devices, AI engine status |

Auto-add rules: an AI match must be seen in 2 frames in a row; barcodes are added on the first frame.
The same item is not added again until it has left the camera view for 1.5 s (hold it up again to add another).

**Demo limitations:** payment confirmation is simulated (the "I've paid" button), and no SMS gateway is
connected (requests are saved and shown on the dashboard). Set your own UPI ID with `GRAB_GO_UPI_ID`.

**Shelf edge node** (second terminal, while the server runs):
```
python edge/edge_node.py --source sample_videos/shop_shelf.mp4 --server http://127.0.0.1:8000 --node-id shelf-01
python edge/edge_node.py --source 0 --server http://127.0.0.1:8000 --node-id shelf-01     # webcam
```
Pick-ups appear in the kiosk cart and on the dashboard instantly; detections under 50% confidence are
flagged there for staff review. If the server is down, the node keeps working and re-sends later.

## Vision engine modes
The server never refuses to start because of a model problem. It picks the best mode available and shows it in the UI and at `/api/status`:

| Mode | When |
|---|---|
| **hybrid**: YOLOv8 locates the item, CLIP names the exact brand | normal (CLIP weights download to `models/clip/` on first start) |
| **YOLOv8 only**: COCO class → product mapping | CLIP not downloadable or `GRAB_GO_USE_CLIP=false` |
| **barcode**: always on, overrides vision with 100% confidence | pyzbar, or OpenCV as a fallback |

## Project layout
```
app.py, config.py         server + settings (all overridable by GRAB_GO_* env vars)
vision/                   shared engine: catalog.py, engine.py, interaction.py, torch_compat.py
edge/edge_node.py         decentralized shelf node (Take/Return → server)
edge/live_detector.py     YOLO-World open-vocabulary detector demo
training/                 extract_frames → auto_train (auto-label + train) → training_pipeline (eval)
templates/                kiosk, checkout, receipt, dashboard (Jinja2, extend _base.html)
static/css/app.css        shared light retail design system
static/js/                common.js (icons, API, toasts, i18n), kiosk.js (camera + AI), checkout.js, receipt.js, dashboard.js
models/                   yolov8s.pt (default), yolov8n.pt (for Raspberry Pi / low power)
sample_videos/            test videos from P35
docs/                     patent flowchart, chart generators, charts
tests/test_system.py      python -m pytest -q tests
```

## Useful settings
| Env var | Default | Purpose |
|---|---|---|
| `GRAB_GO_YOLO_MODEL` | `models/yolov8s.pt` | a custom `best.pt` from `training/` |
| `GRAB_GO_USE_CLIP` | `true` | turn CLIP brand recognition off |
| `GRAB_GO_ENABLE_VISION` | `true` | `false` = UI/cart only, no models loaded |
| `GRAB_GO_HOST` / `GRAB_GO_PORT` | `127.0.0.1` / `8000` | use `0.0.0.0` so edge devices on the LAN can connect |
| `GRAB_GO_STORE_NAME` / `GRAB_GO_KIOSK_NAME` | `Grab & Go` / `Kiosk 1 · Main entrance` | names shown in the UI |
| `GRAB_GO_UPI_ID` / `GRAB_GO_UPI_PAYEE` | `grabandgo@upi` / `Grab and Go Store` | merchant encoded in the checkout QR |
| `GRAB_GO_GST_RATE` | `0.18` | tax rate |

## Training a custom model (better accuracy)
The stock COCO model has no "chips packet" or "bell pepper" class, so shelf items get mapped to the nearest COCO class. To fix that, train on your own shelf:
```
python training/extract_frames.py --video my_shelf.mp4 --every 5
python training/auto_train.py --epochs 60
python edge/edge_node.py --model training/runs/auto_trained_model/weights/best.pt --source 0
```
For the patent's hand + product design, label two classes (`training/dataset.yaml`) and run `training/train_yolo.py`. The edge node automatically uses a real `hand` class when the model has one.

## Note on the charts in docs/
`docs/generate_evaluation_graphs.py` and `generate_patent_graphs.py` draw **illustrative curves from formulas and random noise**, not from a trained model. For real metrics (confusion matrix, PR/F1 curves, mAP), run `training/training_pipeline.py` and use the plots it writes to `training/runs/`.
