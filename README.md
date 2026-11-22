# Grab & Go — Decentralized Edge-Based Autonomous Retail Checkout

An AI-powered, cashier-less checkout system for small and independent stores. Shoppers hold a product up to a camera
(or simply take it off a shelf), the item is recognised and added to a digital cart automatically, and they pay by
UPI, card or wallet, with no billing queue.

Unlike cloud-heavy systems (ceiling camera arrays, weight-sensing shelves, RFID), every camera device runs its own AI
**on the edge** and sends only small events to the server. Video never leaves the device.

> Final-year project, Sharda University · Riya Tyagi & Ashutosh Bhardwaj · Guide: Prof. (Dr.) Ambuj Kumar Agarwal

---

## Features

- **Live camera scanning kiosk.** Click *Initialize camera*, hold an item in the frame, and it is added automatically with an *Undo* option.
- **Hybrid AI recognition.** YOLOv8 finds the item, CLIP names the exact brand (zero-shot, no training), and a barcode confirms it with certainty.
- **Shelf edge nodes.** YOLOv8 + ByteTrack follow hands and products; a **Touch → Take → Return** state machine adds or removes items from the cart.
- **Real-time sync.** Every cart change is pushed instantly to all screens over WebSockets.
- **Checkout.** UPI QR for the exact amount, card or wallet, with 18 % GST (CGST 9 % + SGST 9 %).
- **Receipt.** Order number (GG-1001…), itemised bill, SMS request, auto-reset for the next shopper.
- **Staff dashboard.** Orders and revenue today, live event feed, connected devices, AI engine status, help requests.
- **English / हिंदी** toggle, *Call staff* button, light sky-blue retail theme, works on desktop, tablet and phone.
- **Robust.** Runs in reduced mode if a model can't load, edge nodes queue events while offline, and false detections are filtered.

---

## How it works

```text
 Shopper kiosk (browser)                    Central server (app.py)                Edge shelf node (edge_node.py)
 ───────────────────────                    ────────────────────────               ──────────────────────────────
 camera ──JPEG every 250 ms──►  /ws/detect → VisionEngine                         shelf camera
                                            1. barcode (pyzbar / OpenCV)          → YOLOv8 + ByteTrack
        ◄── boxes, names, % ──              2. YOLOv8 finds the item              → Touch / Take / Return
                                            3. CLIP names the brand               → POST /api/edge/event
 seen 3 frames in a row? ──► POST /api/cart/add                                     (queued if server is down)
                                            cart · orders · events (memory)  ◄──────┘
 live cart  ◄────────────── /ws/cart pushes every change to every screen ──────►  Staff dashboard (browser)
```

**Kiosk pipeline:** barcode first; YOLOv8 localises products; the largest box is cropped and classified by CLIP
against text prompts; if CLIP is unsure, the YOLO class is mapped to a generic product (e.g. `bottle` → Cold Drink).

**Shelf pick-up logic:** a product is *Touched* when a hand covers ≥ 30 % of its box, *Taken* when it moves more than
its own size from its home position for 6 consecutive frames, and *Returned* when it comes back. While idle, the home
position is re-anchored so the shelf map corrects itself (Dynamic Resting State).

---

## AI models

| Model | Role | Notes |
|---|---|---|
| **YOLOv8s** | Object detection (where is it?) | Default, `models/yolov8s.pt` (22 MB), pre-trained on COCO (80 classes) |
| **YOLOv8n** | Lightweight detection | `models/yolov8n.pt` (6 MB), for Raspberry Pi / low-power devices |
| **CLIP ViT-B/32** (OpenAI) | Brand recognition (what is it?) | Zero-shot; ~340 MB, downloaded once into `models/clip/` on first start |
| **ByteTrack** | Multi-object tracking | Stable ID per product across frames (built into Ultralytics) |
| **pyzbar / OpenCV** | EAN-13 barcode decoding | Ground truth; OpenCV is the fallback if pyzbar's library is missing |
| **YOLO-World** | Open-vocabulary detection (optional) | Used by `edge/live_detector.py` and for auto-labelling in training |

**Engine modes** (shown in the kiosk and at `/api/status`): *hybrid* (YOLOv8 + CLIP), *YOLOv8 only*,
*CLIP only* or *barcode only*. The server never fails to start because a model is missing.

---

## Requirements

- **Python 3.10 – 3.12** (tested on 3.12) and **Git** (needed to install the CLIP package)
- Windows, Linux or macOS; a webcam for the kiosk
- About **4 GB** of disk space (PyTorch + models). A GPU is optional; everything runs on CPU.
- Chrome or Edge (the camera does not work inside VS Code's built-in browser)

---

## Installation (first time only)

**Windows: VS Code terminal / PowerShell**, inside the project folder:
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

**Linux / macOS:**
```bash
sudo apt install libzbar0        # Linux only, for barcodes (macOS: brew install zbar)
./setup.sh
```

> **Windows tips**
> - Always use `python -m pip` and `python -m uvicorn` (not `pip.exe` / `uvicorn.exe`), which works even when Windows blocks small `.exe` files.
> - *"running scripts is disabled"* → `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> - *"DLL load failed … Application Control policy"* → turn **Smart App Control** off in Windows Security → App & browser control.

---

## Running

**Start the server**, with the line starting with `(.venv)`:
```powershell
.venv\Scripts\activate
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 2
```
Wait for `Uvicorn running on http://127.0.0.1:8000`, then open it in **Chrome** and click **Initialize camera**.
The first start downloads CLIP (~340 MB); later starts reuse it.

**Stop:** press **Ctrl + C** in the terminal (press it twice if a browser tab is still connected).

| Page | URL | For |
|---|---|---|
| Kiosk | http://127.0.0.1:8000 | Shopper: camera scanning and cart |
| Checkout | http://127.0.0.1:8000/checkout | Shopper: UPI / card / wallet |
| Receipt | http://127.0.0.1:8000/payment-success | Shopper: bill and SMS |
| Dashboard | http://127.0.0.1:8000/dashboard | Staff: orders, live events, devices |
| API docs | http://127.0.0.1:8000/docs | Developers: interactive API reference |

**Shelf edge node** (second terminal, while the server runs):
```powershell
.venv\Scripts\activate
python edge\edge_node.py --source sample_videos\shop_shelf.mp4 --server http://127.0.0.1:8000 --node-id shelf-01
python edge\edge_node.py --source 0 --server http://127.0.0.1:8000 --node-id shelf-01     # webcam
```
Useful options: `--model models\yolov8n.pt` (faster), `--no-display`, `--save out.mp4`, `--cooldown 3`, `--ignore "cell phone"`.

**Tests:**
```powershell
python -m pytest -q tests
```

---

## Using the kiosk

1. Click **Initialize camera** and allow camera access in Chrome.
2. Hold **one item at a time**, close to the camera and inside the frame. Showing the **barcode** is the most reliable.
3. The item is added after it is recognised in **3 frames in a row**. To add another unit, take the item out of view and show it again.
4. Use **Undo**, **+ / −** or **Clear cart** to correct the cart.
5. Press **Pay**, choose a method, then **I've paid** to see the receipt.

**False-detection protection:** a CLIP match on a YOLO product box needs ≥ 38 % confidence; a guess on the centre of
the frame with no product box needs ≥ 70 %; and the product must score at least 2× the "background / nothing here"
class. These can be tuned with the settings below.

---

## Project structure

```text
grab_and_go_final/
├── app.py                  FastAPI server: pages, REST API, WebSockets, cart, orders, events
├── config.py               All settings (overridable with GRAB_GO_* environment variables)
├── requirements.txt        Python packages
├── setup.bat / setup.sh    First-time setup          run_app.bat / .sh        Start the server
├── run_edge_node.bat / .sh Start a shelf edge node
├── vision/                 Shared AI package (server + edge nodes)
│   ├── engine.py           VisionEngine: YOLOv8 + CLIP + barcode with fallbacks
│   ├── catalog.py          Products, CLIP prompts, barcodes, YOLO class → product map
│   ├── interaction.py      IoU / overlap + Touch-Take-Return state machine
│   └── torch_compat.py     PyTorch 2.6+ checkpoint-loading fix
├── edge/
│   ├── edge_node.py        Decentralized shelf node (tracking, events, offline queue)
│   └── live_detector.py    YOLO-World open-vocabulary detector demo
├── templates/              _base, index (kiosk), checkout, payment_success, dashboard
├── static/
│   ├── css/app.css         Design system (colours, layout, responsive)
│   ├── js/                 common, kiosk, checkout, receipt, dashboard
│   └── img/                Product icons
├── models/                 yolov8s.pt, yolov8n.pt, clip/ (downloaded)
├── training/               extract_frames → auto_train → train_yolo / training_pipeline
├── tests/test_system.py    9 end-to-end tests
├── sample_videos/          Shelf and grocery test clips
├── tools/generate_svgs.py  Regenerates product icons
└── docs/                   Patent flowchart and chart generator scripts
```

---

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Vision engine mode, loaded models, edge nodes |
| GET | `/api/products` | Product catalog |
| GET | `/api/cart` | Current cart with subtotal, GST and total |
| POST | `/api/cart/add` · `/update` · `/remove` · `/clear` | Change the cart |
| POST | `/api/checkout` | Create an order (`method`: upi / card / wallet) |
| GET | `/api/orders`, `/api/orders/{id or latest}` | Orders |
| GET | `/api/upi-qr?amount=` | UPI payment QR (SVG) |
| POST | `/api/edge/event` | Take / Return from a shelf node |
| POST | `/api/staff-call`, `/api/receipt/sms` | Help request, SMS receipt request |
| GET | `/api/events`, `/api/dashboard` | Dashboard data |
| WS | `/ws/detect` | Kiosk camera frames → detections |
| WS | `/ws/cart` | Live cart and event push to every page |

---

## Settings

Set before starting the server, e.g. `set GRAB_GO_CLIP_CENTER_THRESHOLD=0.8` (Windows) or `export …` (Linux/macOS).

| Variable | Default | Meaning |
|---|---|---|
| `GRAB_GO_YOLO_MODEL` | `models/yolov8s.pt` | Detector weights (e.g. a custom `best.pt`) |
| `GRAB_GO_CONFIDENCE` | `0.30` | Minimum YOLO box confidence |
| `GRAB_GO_USE_CLIP` | `true` | Turn CLIP brand recognition on/off |
| `GRAB_GO_CLIP_THRESHOLD` | `0.38` | CLIP confidence on a YOLO product box |
| `GRAB_GO_CLIP_CENTER_THRESHOLD` | `0.70` | CLIP confidence when there is no product box |
| `GRAB_GO_CLIP_BG_MARGIN` | `2.0` | Product must beat "background" by this factor |
| `GRAB_GO_ENABLE_VISION` | `true` | `false` = UI and cart only, no AI models |
| `GRAB_GO_GST_RATE` | `0.18` | Tax rate |
| `GRAB_GO_STORE_NAME` / `GRAB_GO_KIOSK_NAME` | `Grab & Go` / `Kiosk 1 · Main entrance` | Names shown in the UI |
| `GRAB_GO_UPI_ID` / `GRAB_GO_UPI_PAYEE` | `grabandgo@upi` / `Grab and Go Store` | Merchant in the checkout QR (set your own) |
| `GRAB_GO_HOST` / `GRAB_GO_PORT` | `127.0.0.1` / `8000` | Use `0.0.0.0` so edge devices on the LAN can connect |

**Adding a product:** add an entry with 2–3 descriptive text prompts to `RETAIL_CATALOG` in `vision/catalog.py`
(and its EAN-13 code to `BARCODE_CATALOG`), then restart. No retraining is needed.

---

## Training a custom model

The stock COCO model has no class for "chips packet" or "bell pepper", so shelf items are mapped to the nearest
COCO class. For better accuracy, train on your own store footage:
```powershell
python training\extract_frames.py --video my_shelf.mp4 --every 5     # video → images
python training\auto_train.py --epochs 60                              # auto-label + train
python edge\edge_node.py --model training\runs\auto_trained_model\weights\best.pt --source 0
```
- `training\train_yolo.py` trains the two-class **hand + product** detector defined in `training\dataset.yaml`
  (the edge node automatically uses a real `hand` class when the model has one).
- `training\training_pipeline.py` runs train → validate → test and saves **real** loss, mAP, PR, F1 and confusion-matrix plots in `training\runs\`.
- Training on a laptop CPU is slow; a GPU (e.g. Google Colab) is recommended.

---

## Verified results

Measured on a 2-core laptop CPU without a GPU:

- Kiosk inference about **150–290 ms per frame**; edge node about **6 FPS (YOLOv8s)** / **14 FPS (YOLOv8n)**.
- Bottle detected at **91 %** and auto-added once; EAN-13 barcode decoded exactly and added once.
- Full flow verified in Chrome with a simulated camera: scan → shelf event → checkout → UPI QR → receipt → dashboard.
- Hardened shelf logic reduced false Take events on the sample video from **23 to 2**.
- **9 / 9** automated tests pass.

> The charts in `docs/` (`generate_evaluation_graphs.py`, `generate_patent_graphs.py`) are **illustrative curves
> generated from formulas**, not training results. Use `training\training_pipeline.py` for real metrics.

---

## Limitations and future work

| Limitation | Next step |
|---|---|
| Generic COCO classes on the shelf; person box used as the hand | Train the custom hand + product model |
| Kiosk adds one item at a time | Multi-item recognition per frame |
| Payment confirmation is simulated; SMS is not sent | Payment gateway (Razorpay / PhonePe PG) and SMS gateway (MSG91 / Twilio) |
| Cart, orders and events are kept in memory | SQLite / PostgreSQL storage, one session per shopper |
| Dashboard has no login | Staff authentication |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named uvicorn` | Run `.venv\Scripts\activate` first. The prompt must start with `(.venv)` |
| `.venv\Scripts\activate` not found | Run the installation steps again |
| Camera doesn't start | Use Chrome/Edge (not the VS Code browser), allow the camera, and close Zoom/Teams |
| Ctrl + C doesn't stop the server | Press it again, close the browser tab, or `taskkill /F /IM python.exe` |
| Port 8000 already in use | Stop the old server, or use `--port 8001` |
| Wrong items added by themselves | Raise `GRAB_GO_CLIP_CENTER_THRESHOLD` (e.g. 0.8) and keep faces out of the centre of the frame |
| `Barcode decoder: OpenCV (pyzbar not available)` | Install the Microsoft Visual C++ 2013 Redistributable (x64), or ignore it, since OpenCV still works |

---

## Credits

Built by integrating two repositories:
[197Ashutosh/grab_and_go](https://github.com/197Ashutosh/grab_and_go) (web kiosk, CLIP, barcode) and
[197Ashutosh/P35-Decentralized_Edge_Based_Grab_and_Go](https://github.com/197Ashutosh/P35-Decentralized_Edge_Based_Grab_and_Go)
(YOLOv8 edge detection, interaction logic, training pipeline, sample videos).

Models: [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) · [OpenAI CLIP](https://github.com/openai/CLIP) ·
ByteTrack · ZBar.
