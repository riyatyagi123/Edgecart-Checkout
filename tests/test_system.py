"""End-to-end tests:  python -m pytest -q tests

Set GRAB_GO_TEST_VISION=1 to also load the real YOLO model for the detection test.
"""
import base64
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("GRAB_GO_ENABLE_VISION", os.getenv("GRAB_GO_TEST_VISION", "false"))
os.environ.setdefault("GRAB_GO_USE_CLIP", "false")

from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402
from vision.interaction import SpatialInteractionEngine, calculate_iou  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(server.app) as c:
        c.post("/api/cart/clear")
        yield c


def test_pages_render(client):
    for path in ("/", "/checkout", "/payment-success", "/dashboard"):
        r = client.get(path)
        assert r.status_code == 200 and "<html" in r.text.lower()
    assert client.get("/static/img/chips.svg").status_code == 200
    for asset in ("css/app.css", "js/common.js", "js/kiosk.js", "js/checkout.js", "js/receipt.js", "js/dashboard.js"):
        assert client.get(f"/static/{asset}").status_code == 200, asset
    home = client.get("/").text
    assert 'id="startBtn"' in home and 'id="view"' in home and "/static/js/kiosk.js" in home


def test_products_and_status(client):
    prods = client.get("/api/products").json()
    assert len(prods) >= 9 and all("prompts" not in p for p in prods)
    assert "vision" in client.get("/api/status").json()


def test_cart_flow_and_checkout(client):
    r = client.post("/api/cart/add", json={"product_id": "prod_coke", "quantity": 2})
    assert r.status_code == 200 and r.json()["cart"]["total"] == 80
    client.post("/api/cart/add", json={"product_id": "prod_thumsup"})          # barcode-only product
    client.post("/api/cart/add", json={"product_id": "bc_1234567890123"})      # unknown barcode
    r = client.post("/api/cart/update", json={"product_id": "prod_coke", "quantity_delta": -1})
    assert {i["product_id"] for i in r.json()["items"]} == {"prod_coke", "prod_thumsup", "bc_1234567890123"}
    assert client.post("/api/cart/remove", json={"product_id": "prod_thumsup"}).status_code == 200
    assert client.delete("/api/cart/remove/bc_1234567890123").status_code == 200
    assert client.post("/api/cart/add", json={"product_id": "nope"}).status_code == 404
    order = client.post("/api/checkout").json()
    assert order["order_id"].startswith("GG-") and order["total"] == 40 and order["method"] == "upi"
    assert order["grand_total"] == pytest.approx(47.2)
    assert client.get("/api/cart").json()["items"] == []
    assert client.post("/api/checkout").status_code == 400


def test_edge_events_push_to_live_cart(client):
    with client.websocket_connect("/ws/cart") as ws:
        assert ws.receive_json()["type"] == "cart"
        r = client.post("/api/edge/event", json={"node_id": "shelf-A", "event": "Take", "label": "banana"})
        assert r.status_code == 200
        msg = ws.receive_json()
        assert msg["type"] == "cart" and msg["cart"]["items"][0]["product_id"] == "coco_banana"
        assert ws.receive_json()["type"] == "edge_event"
        assert ws.receive_json()["type"] == "event"
        client.post("/api/edge/event", json={"node_id": "shelf-A", "event": "Return", "label": "banana"})
        assert ws.receive_json()["cart"]["items"] == []
    assert "shelf-A" in client.get("/api/status").json()["edge_nodes"]
    assert client.post("/api/edge/event", json={"event": "Take", "label": "unicorn"}).status_code == 404


def _frame_b64(img):
    ok, buf = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def test_detect_websocket(client):
    with client.websocket_connect("/ws/detect") as ws:
        ws.send_text("not-an-image")
        assert "error" in ws.receive_json()
        ws.send_text(_frame_b64(np.zeros((480, 640, 3), np.uint8)))
        res = ws.receive_json()
        assert res["detections"] == [] and "barcode" in res


def test_barcode_decoding():
    barcode = pytest.importorskip("barcode")
    from barcode.writer import ImageWriter
    from vision.engine import VisionEngine
    import io
    buf = io.BytesIO()
    barcode.get("ean13", "890149110183", writer=ImageWriter()).write(buf)
    img = cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_COLOR)
    eng = VisionEngine(yolo_model="none.pt", use_clip=False).load()
    res = eng.decode_barcode(img)
    assert res is not None and res["product_id"] == "prod_lays_blue"


def test_interaction_take_and_return():
    eng = SpatialInteractionEngine(min_seen_frames=2, displaced_frames=2)
    shelf, hand = [100, 100, 140, 140], [90, 90, 200, 200]
    moved = [300, 300, 340, 340]
    events = []
    for _ in range(3):
        events += eng.update([{"track_id": 1, "label": "apple", "bbox": shelf}], [])
    events += eng.update([{"track_id": 1, "label": "apple", "bbox": shelf}], [hand])
    for _ in range(3):
        events += eng.update([{"track_id": 1, "label": "apple", "bbox": moved}], [[290, 290, 400, 400]])
    for _ in range(2):
        events += eng.update([{"track_id": 1, "label": "apple", "bbox": shelf}], [])
    assert [e["event"] for e in events] == ["Touch", "Take", "Return"]
    assert calculate_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert calculate_iou([0, 0, 0, 0], [0, 0, 0, 0]) == 0.0  # no ZeroDivisionError (P35 bug)


def test_orders_receipt_qr_and_sms(client):
    client.post("/api/cart/add", json={"product_id": "prod_maggi", "quantity": 3})
    order = client.post("/api/checkout", json={"method": "card"}).json()
    assert order["method"] == "card" and order["grand_total"] == pytest.approx(49.56)
    assert client.get(f"/api/orders/{order['order_id']}").json()["order_id"] == order["order_id"]
    assert client.get("/api/orders/latest").json()["order_id"] == order["order_id"]
    assert client.get("/api/orders/GG-0").status_code == 404
    assert client.post("/api/checkout", json={"method": "cash"}).status_code == 400
    qr = client.get("/api/upi-qr?amount=49.56")
    assert qr.status_code == 200 and qr.headers["content-type"].startswith("image/svg")
    assert client.post("/api/receipt/sms", json={"order_id": order["order_id"], "phone": "12345"}).status_code == 400
    ok = client.post("/api/receipt/sms", json={"order_id": order["order_id"], "phone": "9876543210"})
    assert ok.status_code == 200 and ok.json()["sent"] is False


def test_events_staff_call_and_dashboard(client):
    with client.websocket_connect("/ws/cart") as ws:
        ws.receive_json()
        client.post("/api/staff-call", json={"reason": "Need help"})
        msg = ws.receive_json()
        assert msg["type"] == "event" and msg["event"]["kind"] == "Help" and msg["event"]["needs_action"]
    client.post("/api/cart/add", json={"product_id": "prod_coke", "source": "vision", "confidence": 0.91})
    client.post("/api/edge/event", json={"node_id": "shelf-1", "event": "Take", "label": "apple", "confidence": 0.3})
    evs = client.get("/api/events").json()
    kinds = [e["kind"] for e in evs[:3]]
    assert kinds == ["Take", "Vision", "Help"]
    assert evs[0]["needs_action"] is True                        # low-confidence pick-up flagged
    d = client.get("/api/dashboard").json()
    assert d["open_actions"] >= 2 and any(n["node_id"] == "shelf-1" for n in d["edge_nodes"])
    help_id = evs[2]["id"]
    assert client.post(f"/api/events/{help_id}/resolve").json()["resolved"] is True
    assert client.post("/api/events/999999/resolve").status_code == 404
