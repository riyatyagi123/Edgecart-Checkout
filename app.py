"""
Grab & Go - Decentralized Edge-Based Autonomous Retail Checkout (integrated build)

Kiosk      : browser webcam -> /ws/detect -> VisionEngine -> auto-add to cart
Edge nodes : edge/edge_node.py (shelf camera) -> /api/edge/event (Take/Return)
Live sync  : cart changes and store events are pushed to every browser on /ws/cart
Pages      : /  (kiosk)  /checkout  /payment-success  /dashboard (staff)
"""
from __future__ import annotations

import base64
import datetime
import io
import itertools
import json
import logging
import threading
from collections import deque
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote

import cv2
import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import config
from vision.catalog import COCO_RETAIL_MAP, lookup_product, public_catalog

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("grab_and_go")

# --------------------------------------------------------------------- state
cart: dict[str, dict[str, Any]] = {}
cart_lock = threading.Lock()
cart_clients: set[WebSocket] = set()
edge_nodes: dict[str, dict[str, Any]] = {}
kiosk_clients: dict[str, dict[str, Any]] = {}
orders: list[dict[str, Any]] = []
events: deque[dict[str, Any]] = deque(maxlen=300)
_event_ids = itertools.count(1)
_order_numbers = itertools.count(config.FIRST_ORDER_NUMBER)
engine = None  # vision.engine.VisionEngine, created at startup


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load_engine():
    from vision.engine import VisionEngine
    return VisionEngine(
        yolo_model=config.YOLO_MODEL, use_clip=config.USE_CLIP, clip_model_name=config.CLIP_MODEL,
        clip_weights_dir=config.CLIP_WEIGHTS_DIR, yolo_conf=config.YOLO_CONFIDENCE,
        clip_threshold=config.CLIP_THRESHOLD,
    ).load()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global engine
    if config.ENABLE_VISION:
        logger.info("Loading vision engine (first run downloads model weights)...")
        engine = await run_in_threadpool(load_engine)
    else:
        logger.warning("Vision disabled (GRAB_GO_ENABLE_VISION=false) - cart/UI only.")
    yield


app = FastAPI(title="Grab & Go — Decentralized Edge Retail System", version="3.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


# -------------------------------------------------------------------- models
class CartAddRequest(BaseModel):
    product_id: str
    quantity: int = 1
    source: str = "manual"           # manual | vision | barcode
    confidence: float | None = None


class CartRemoveRequest(BaseModel):
    product_id: str


class CartUpdateRequest(BaseModel):
    product_id: str
    quantity_delta: int = 0


class CheckoutRequest(BaseModel):
    method: str = "upi"


class EdgeEvent(BaseModel):
    node_id: str = "edge-01"
    event: str                       # "Take" | "Return"
    product_id: str | None = None
    label: str | None = None         # YOLO class name, mapped via COCO_RETAIL_MAP
    confidence: float | None = None
    track_id: int | None = None


class StaffCall(BaseModel):
    kiosk: str = config.KIOSK_NAME
    reason: str = "Shopper needs help"


class SmsRequest(BaseModel):
    order_id: str
    phone: str


# ------------------------------------------------------------------- helpers
def _cart_snapshot() -> dict[str, Any]:
    items, total = [], 0.0
    with cart_lock:
        for pid, e in cart.items():
            sub = e["price"] * e["quantity"]
            total += sub
            items.append({"product_id": pid, "name": e["name"], "brand": e["brand"], "price": e["price"],
                          "category": e.get("category", ""), "quantity": e["quantity"], "subtotal": sub,
                          "emoji": e.get("emoji", ""), "image": e.get("image", ""), "source": e.get("source", "")})
    tax = round(total * config.GST_RATE, 2)
    return {"items": items, "total": round(total, 2), "tax": tax, "grand_total": round(total + tax, 2),
            "item_count": sum(i["quantity"] for i in items), "line_count": len(items)}


async def _push(message: dict[str, Any]) -> None:
    for ws in list(cart_clients):
        try:
            await ws.send_json(message)
        except Exception:
            cart_clients.discard(ws)


async def _broadcast_cart() -> dict[str, Any]:
    data = _cart_snapshot()
    await _push({"type": "cart", "cart": data})
    return data


async def _log_event(kind: str, product: str, detail: str, node: str,
                     needs_action: bool = False, **extra: Any) -> dict[str, Any]:
    ev = {"id": next(_event_ids), "ts": _now(), "kind": kind, "product": product, "detail": detail,
          "node": node, "needs_action": needs_action, "resolved": False, **extra}
    events.appendleft(ev)
    await _push({"type": "event", "event": ev})
    return ev


def _cart_add(product: dict[str, Any], qty: int, source: str) -> None:
    with cart_lock:
        pid = product["id"]
        if pid in cart:
            cart[pid]["quantity"] += qty
        else:
            cart[pid] = {"name": product["name"], "brand": product["brand"], "price": product["price"],
                         "category": product.get("category", ""), "emoji": product.get("emoji", ""),
                         "image": product.get("image", ""), "quantity": qty, "source": source}


def _cart_response(message: str) -> JSONResponse:
    data = _cart_snapshot()
    return JSONResponse(content={"message": message, "cart": data, "items": data["items"]})


def _decode_base64_frame(data: str) -> np.ndarray:
    data = data.strip()
    if data.startswith("{"):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                data = parsed.get("frame") or parsed.get("image") or parsed.get("data") or ""
        except Exception:
            pass
    if "," in data:
        data = data.split(",", 1)[1]
    frame = cv2.imdecode(np.frombuffer(base64.b64decode(data), dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid image bytes")
    return frame


def _page_context() -> dict[str, Any]:
    return {"store_name": config.STORE_NAME, "kiosk_name": config.KIOSK_NAME,
            "gst_percent": round(config.GST_RATE * 100)}


# --------------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    return templates.TemplateResponse(request, "index.html", _page_context())


@app.get("/checkout", response_class=HTMLResponse)
async def page_checkout(request: Request):
    return templates.TemplateResponse(request, "checkout.html", _page_context())


@app.get("/payment-success", response_class=HTMLResponse)
async def page_payment_success(request: Request):
    return templates.TemplateResponse(request, "payment_success.html", _page_context())


@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", _page_context())


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# ----------------------------------------------------------------------- API
@app.get("/api/status")
async def api_status():
    return {
        "vision": engine.status() if engine else {"mode": "disabled"},
        "edge_nodes": edge_nodes,
        "cart_items": len(cart),
    }


@app.get("/api/products")
async def api_get_products():
    return JSONResponse(content=public_catalog())


@app.get("/api/cart")
async def api_cart_get():
    return JSONResponse(content=_cart_snapshot())


@app.post("/api/cart/add")
async def api_cart_add(body: CartAddRequest):
    product = lookup_product(body.product_id)
    if product is None:
        return JSONResponse(status_code=404, content={"error": f"Product '{body.product_id}' not found."})
    if body.quantity < 1:
        return JSONResponse(status_code=400, content={"error": "Quantity must be at least 1."})
    _cart_add(product, body.quantity, body.source)
    await _broadcast_cart()
    if body.source in ("vision", "barcode"):
        detail = (f"AI match {round((body.confidence or 0) * 100)}%" if body.source == "vision"
                  else f"Barcode verified{' · ' + body.product_id[3:] if body.product_id.startswith('bc_') else ''}")
        await _log_event("Vision" if body.source == "vision" else "Barcode", product["name"], detail, "kiosk",
                         confidence=body.confidence)
    logger.info("Cart add (%s): %s x%d", body.source, product["name"], body.quantity)
    return _cart_response("Item added.")


@app.post("/api/cart/remove")
async def api_cart_remove_body(body: CartRemoveRequest):
    return await _remove(body.product_id)


@app.api_route("/api/cart/remove/{product_id}", methods=["POST", "DELETE"])
async def api_cart_remove_path(product_id: str):
    return await _remove(product_id)


async def _remove(pid: str):
    with cart_lock:
        removed = cart.pop(pid, None)
    if removed is None:
        return JSONResponse(status_code=404, content={"error": f"Product '{pid}' not in cart."})
    await _broadcast_cart()
    logger.info("Cart remove: %s", removed["name"])
    return _cart_response("Item removed.")


@app.post("/api/cart/update")
async def api_cart_update(body: CartUpdateRequest):
    with cart_lock:
        if body.product_id not in cart:
            return JSONResponse(status_code=404, content={"error": f"Product '{body.product_id}' not in cart."})
        new_qty = cart[body.product_id]["quantity"] + body.quantity_delta
        if new_qty <= 0:
            cart.pop(body.product_id)
        else:
            cart[body.product_id]["quantity"] = new_qty
    await _broadcast_cart()
    return _cart_response("Cart updated.")


@app.post("/api/cart/clear")
async def api_cart_clear():
    with cart_lock:
        cart.clear()
    await _broadcast_cart()
    return _cart_response("Cart cleared.")


@app.post("/api/checkout")
async def api_checkout(body: CheckoutRequest | None = None):
    method = (body.method if body else "upi").lower()
    if method not in ("upi", "card", "wallet"):
        return JSONResponse(status_code=400, content={"error": "method must be upi, card or wallet"})
    data = _cart_snapshot()
    if not data["items"]:
        return JSONResponse(status_code=400, content={"error": "Cart is empty."})
    order = {"order_id": f"GG-{next(_order_numbers)}", **data, "method": method, "timestamp": _now(),
             "status": "completed", "kiosk": config.KIOSK_NAME}
    with cart_lock:
        cart.clear()
    orders.append(order)
    await _broadcast_cart()
    await _log_event("Order", f"{order['order_id']} · ₹{order['grand_total']:.2f}",
                     f"{data['item_count']} items · paid by {method.upper()}", "kiosk")
    logger.info("Order %s finalized - Rs.%.2f via %s", order["order_id"], order["grand_total"], method)
    return JSONResponse(content=order)


@app.get("/api/orders")
async def api_orders():
    return list(reversed(orders[-50:]))


@app.get("/api/orders/{order_id}")
async def api_order(order_id: str):
    if order_id == "latest" and orders:
        return orders[-1]
    for o in orders:
        if o["order_id"] == order_id:
            return o
    return JSONResponse(status_code=404, content={"error": f"Order '{order_id}' not found."})


@app.get("/api/upi-qr")
async def api_upi_qr(amount: float):
    """SVG QR code for a UPI payment of `amount` rupees (demo merchant VPA from config)."""
    try:
        import qrcode
        import qrcode.image.svg
    except Exception:
        return JSONResponse(status_code=501, content={"error": "pip install qrcode"})
    uri = (f"upi://pay?pa={quote(config.UPI_ID)}&pn={quote(config.UPI_PAYEE)}"
           f"&am={amount:.2f}&cu=INR&tn={quote('Grab and Go order')}")
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    return Response(content=buf.getvalue(), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.post("/api/staff-call")
async def api_staff_call(body: StaffCall | None = None):
    body = body or StaffCall()
    ev = await _log_event("Help", body.reason, body.kiosk, "kiosk", needs_action=True)
    logger.info("Staff called from %s", body.kiosk)
    return {"message": "Staff notified.", "event": ev}


@app.post("/api/receipt/sms")
async def api_receipt_sms(body: SmsRequest):
    digits = "".join(c for c in body.phone if c.isdigit())[-10:]
    if len(digits) != 10 or digits[0] not in "6789":
        return JSONResponse(status_code=400, content={"error": "Enter a valid 10-digit mobile number."})
    if not any(o["order_id"] == body.order_id for o in orders):
        return JSONResponse(status_code=404, content={"error": "Order not found."})
    # No SMS gateway is configured in this project: the request is logged for staff / integration.
    await _log_event("SMS", body.order_id, f"Receipt requested for +91 {digits[:2]}******{digits[-2:]}", "kiosk")
    return {"message": "Receipt request saved.", "sent": False}


@app.get("/api/events")
async def api_events(limit: int = 50):
    return list(itertools.islice(events, max(1, min(limit, 300))))


@app.post("/api/events/{event_id}/resolve")
async def api_event_resolve(event_id: int):
    for ev in events:
        if ev["id"] == event_id:
            ev["resolved"] = True
            await _push({"type": "event_update", "event": ev})
            return ev
    return JSONResponse(status_code=404, content={"error": "Event not found."})


@app.get("/api/dashboard")
async def api_dashboard():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    todays = [o for o in orders if o["timestamp"][:10] == today]
    return {
        "orders_today": len(todays),
        "revenue_today": round(sum(o["grand_total"] for o in todays), 2),
        "items_sold_today": sum(o["item_count"] for o in todays),
        "open_actions": sum(1 for e in events if e["needs_action"] and not e["resolved"]),
        "edge_nodes": [{"node_id": k, **v} for k, v in edge_nodes.items()],
        "kiosks": [{"client": k, **v} for k, v in kiosk_clients.items()],
        "vision": engine.status() if engine else {"mode": "disabled"},
        "cart": _cart_snapshot(),
        "recent_orders": list(reversed(orders[-8:])),
    }


@app.post("/api/edge/event")
async def api_edge_event(ev: EdgeEvent):
    """Decentralized edge nodes report Take / Return interactions here."""
    product = lookup_product(ev.product_id) if ev.product_id else COCO_RETAIL_MAP.get(ev.label or "")
    node = edge_nodes.setdefault(ev.node_id, {"events": 0})
    node.update({"last_event": ev.event, "label": ev.label, "last_seen": _now()})
    node["events"] = node.get("events", 0) + 1
    if product is None:
        return JSONResponse(status_code=404, content={"error": f"Unknown product for '{ev.product_id or ev.label}'."})

    kind = ev.event.lower()
    if kind == "take":
        _cart_add(product, 1, f"edge:{ev.node_id}")
        msg = "added"
    elif kind == "return":
        with cart_lock:
            entry = cart.get(product["id"])
            if entry:
                entry["quantity"] -= 1
                if entry["quantity"] <= 0:
                    cart.pop(product["id"])
        msg = "returned"
    else:
        return JSONResponse(status_code=400, content={"error": "event must be 'Take' or 'Return'"})

    data = await _broadcast_cart()
    low = ev.confidence is not None and ev.confidence < 0.5
    await _push({"type": "edge_event", "node_id": ev.node_id, "event": ev.event, "name": product["name"],
                 "price": product["price"], "emoji": product.get("emoji", "")})
    await _log_event("Take" if kind == "take" else "Return", product["name"],
                     ("Picked up from shelf" if kind == "take" else "Put back on shelf")
                     + (" · low confidence" if low else ""), ev.node_id, needs_action=low,
                     confidence=ev.confidence)
    logger.info("Edge %s: %s %s", ev.node_id, product["name"], msg)
    return {"message": f"{product['name']} {msg}.", "cart": data}


# ---------------------------------------------------------------- websockets
@app.websocket("/ws/cart")
async def ws_cart(websocket: WebSocket):
    await websocket.accept()
    cart_clients.add(websocket)
    try:
        await websocket.send_json({"type": "cart", "cart": _cart_snapshot()})
        while True:
            await websocket.receive_text()  # keep-alive pings from browser
    except WebSocketDisconnect:
        pass
    finally:
        cart_clients.discard(websocket)


@app.websocket("/ws/detect")
async def ws_detect(websocket: WebSocket):
    await websocket.accept()
    key = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "kiosk"
    kiosk_clients[key] = {"connected": _now(), "frames": 0, "last_ms": None}
    logger.info("Detection client connected: %s", key)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                frame = _decode_base64_frame(data)
            except Exception:
                await websocket.send_json({"error": "Invalid frame", "detections": [], "barcode": None})
                continue
            if engine is None:
                await websocket.send_json({"detections": [], "barcode": None, "engine": "disabled",
                                           "frame_size": [frame.shape[1], frame.shape[0]]})
                continue
            t0 = datetime.datetime.now()
            result = await run_in_threadpool(engine.analyze_checkout_frame, frame)
            ms = (datetime.datetime.now() - t0).total_seconds() * 1000
            kiosk_clients[key].update(frames=kiosk_clients[key]["frames"] + 1, last_ms=round(ms))
            result["frame_size"] = [frame.shape[1], frame.shape[0]]
            result["latency_ms"] = round(ms)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("Detection client disconnected: %s", key)
    except Exception as err:
        logger.error("WebSocket error: %s", err)
        try:
            await websocket.close(code=1011, reason=str(err)[:120])
        except Exception:
            pass
    finally:
        kiosk_clients.pop(key, None)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Grab & Go on http://%s:%s", config.HOST, config.PORT)
    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
