"""
Product catalogs shared by the web server and the edge nodes.

Merged from:
  * grab_and_go/app.py              -> RETAIL_CATALOG (CLIP prompts), BARCODE_CATALOG
  * P35/smart_retail_scanner.py     -> COCO_RETAIL_MAP (YOLO class -> product)
  * P35/run_inference.py            -> extra produce classes for the shelf demo
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 1. Branded products recognised by the CLIP vision-language model.
# ---------------------------------------------------------------------------
RETAIL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "prod_lays_blue", "name": "Lays India's Magic Masala", "brand": "PepsiCo",
        "price": 20, "category": "Chips & Snacks", "emoji": "🥔", "image": "/static/img/chips.svg",
        "prompts": [
            "a photo of a blue packet of Lays India's Magic Masala potato chips",
            "a blue bag of Lays potato chips snack being held",
            "holding a blue Lays chips packet in front of webcam",
        ],
    },
    {
        "id": "prod_lays_yellow", "name": "Lays Classic Salted", "brand": "PepsiCo",
        "price": 20, "category": "Chips & Snacks", "emoji": "🥔", "image": "/static/img/chips.svg",
        "prompts": [
            "a photo of a yellow packet of Lays classic salted potato chips",
            "a yellow bag of Lays potato chips",
            "holding a yellow Lays chips packet in front of camera",
        ],
    },
    {
        "id": "prod_kurkure", "name": "Kurkure Masala Munch", "brand": "PepsiCo",
        "price": 20, "category": "Chips & Snacks", "emoji": "🌽", "image": "/static/img/snack.svg",
        "prompts": [
            "a photo of an orange packet of Kurkure Masala Munch",
            "an orange packet of Kurkure snack",
            "holding a Kurkure spicy snack packet",
        ],
    },
    {
        "id": "prod_hide_seek", "name": "Hide & Seek Chocolate Chip", "brand": "Parle",
        "price": 30, "category": "Biscuits & Cookies", "emoji": "🍪", "image": "/static/img/biscuit.svg",
        "prompts": [
            "a photo of a brown packet of Parle Hide and Seek biscuits",
            "Hide and Seek chocolate chip cookies packet",
            "holding a packet of Hide & Seek biscuits",
        ],
    },
    {
        "id": "prod_oreo", "name": "Oreo Vanilla Creme", "brand": "Cadbury",
        "price": 35, "category": "Biscuits & Cookies", "emoji": "🍪", "image": "/static/img/biscuit.svg",
        "prompts": [
            "a photo of a blue packet of Oreo biscuits",
            "Oreo chocolate cookies pack",
            "holding an Oreo biscuit pack",
        ],
    },
    {
        "id": "prod_silk", "name": "Dairy Milk Silk", "brand": "Cadbury",
        "price": 80, "category": "Chocolates", "emoji": "🍫", "image": "/static/img/chocolate.svg",
        "prompts": [
            "a photo of a purple packet of Cadbury Dairy Milk Silk chocolate",
            "a Cadbury Dairy Milk chocolate bar",
            "holding a chocolate bar packet",
        ],
    },
    {
        "id": "prod_coke", "name": "Coca-Cola 500ml", "brand": "Coca-Cola",
        "price": 40, "category": "Beverages", "emoji": "🥤", "image": "/static/img/bottle.svg",
        "prompts": [
            "a photo of a bottle or can of Coca-Cola cold drink",
            "a plastic bottle of cold drink soda",
            "holding a bottle of cold drink or Coke",
        ],
    },
    {
        "id": "prod_maggi", "name": "Maggi 2-Minute Noodles", "brand": "Nestle",
        "price": 14, "category": "Instant Food", "emoji": "🍜", "image": "/static/img/cup.svg",
        "prompts": [
            "a photo of a yellow packet of Nestle Maggi 2-Minute noodles",
            "a pack of Maggi instant noodles",
            "holding a yellow Maggi noodles packet",
        ],
    },
    {
        "id": "prod_phone", "name": "Smartphone Device", "brand": "Electronics",
        "price": 14999, "category": "Electronics", "emoji": "📱", "image": "/static/img/phone.svg",
        "prompts": [
            "a close-up photo of a smartphone mobile phone screen held up to camera",
            "showing a mobile phone screen directly into the camera",
        ],
    },
]

BACKGROUND_PROMPTS: list[str] = [
    "a webcam photo of a person sitting in their room with no grocery items",
    "a person looking at their laptop screen or webcam, empty hands",
    "an empty room background with wall, chair, desk, clothes, no retail products",
    "human face, hair, clothing, room background without products",
    "a laptop computer keyboard and monitor screen, desk environment",
]

# ---------------------------------------------------------------------------
# 2. Barcode (EAN-13) ground truth.
# ---------------------------------------------------------------------------
BARCODE_CATALOG: dict[str, dict[str, Any]] = {
    "8901491101837": {"id": "prod_lays_blue", "name": "Lays India's Magic Masala", "brand": "PepsiCo", "price": 20, "category": "Chips & Snacks", "emoji": "🥔"},
    "8901491001007": {"id": "prod_kurkure", "name": "Kurkure Masala Munch", "brand": "PepsiCo", "price": 20, "category": "Chips & Snacks", "emoji": "🌽"},
    "8901719101038": {"id": "prod_hide_seek", "name": "Hide & Seek Chocolate Chip", "brand": "Parle", "price": 30, "category": "Biscuits & Cookies", "emoji": "🍪"},
    "8901719114137": {"id": "prod_hide_seek_fab", "name": "Hide & Seek Fab Vanilla", "brand": "Parle", "price": 30, "category": "Biscuits & Cookies", "emoji": "🍪"},
    "8901764012228": {"id": "prod_coke", "name": "Coca-Cola 500ml", "brand": "Coca-Cola", "price": 40, "category": "Beverages", "emoji": "🥤"},
    "8901764022227": {"id": "prod_thumsup", "name": "Thums Up 500ml", "brand": "Coca-Cola", "price": 40, "category": "Beverages", "emoji": "🥤"},
    "7622201755104": {"id": "prod_oreo", "name": "Oreo Vanilla Creme", "brand": "Cadbury", "price": 35, "category": "Biscuits & Cookies", "emoji": "🍪"},
    "7622201140023": {"id": "prod_silk", "name": "Dairy Milk Silk", "brand": "Cadbury", "price": 80, "category": "Chocolates", "emoji": "🍫"},
    "8901058852370": {"id": "prod_maggi", "name": "Maggi 2-Minute Noodles", "brand": "Nestle", "price": 14, "category": "Instant Food", "emoji": "🍜"},
}

UNKNOWN_BARCODE_PRICE = 25

# ---------------------------------------------------------------------------
# 3. Generic YOLO (COCO) classes -> sellable products (fallback when CLIP is
#    unavailable, and the class list used by the edge shelf node).
# ---------------------------------------------------------------------------
COCO_RETAIL_MAP: dict[str, dict[str, Any]] = {
    "cell phone": {"id": "prod_phone", "name": "Smartphone Device", "brand": "Electronics", "price": 14999, "category": "Electronics", "emoji": "📱", "image": "/static/img/phone.svg"},
    "bottle":     {"id": "coco_bottle", "name": "Cold Drink / Water Bottle", "brand": "Beverage", "price": 40, "category": "Beverages", "emoji": "🥤", "image": "/static/img/bottle.svg"},
    "cup":        {"id": "coco_cup", "name": "Cup Noodles / Hot Beverage", "brand": "Instant Food", "price": 50, "category": "Instant Food", "emoji": "🍜", "image": "/static/img/cup.svg"},
    "banana":     {"id": "coco_banana", "name": "Fresh Banana Bunch", "brand": "Fresh Farm", "price": 30, "category": "Fruits", "emoji": "🍌", "image": "/static/img/banana.svg"},
    "apple":      {"id": "coco_apple", "name": "Fresh Washington Apple", "brand": "Fresh Farm", "price": 25, "category": "Fruits", "emoji": "🍎", "image": "/static/img/apple.svg"},
    "orange":     {"id": "coco_orange", "name": "Fresh Orange", "brand": "Fresh Farm", "price": 20, "category": "Fruits", "emoji": "🍊", "image": "/static/img/orange.svg"},
    "broccoli":   {"id": "coco_broccoli", "name": "Fresh Broccoli", "brand": "Fresh Farm", "price": 40, "category": "Vegetables", "emoji": "🥦", "image": "/static/img/broccoli.svg"},
    "carrot":     {"id": "coco_carrot", "name": "Carrots", "brand": "Fresh Farm", "price": 20, "category": "Vegetables", "emoji": "🥕", "image": "/static/img/carrot.svg"},
    "sandwich":   {"id": "coco_sandwich", "name": "Fresh Deli Sandwich", "brand": "Bakery", "price": 60, "category": "Bakery", "emoji": "🥪", "image": "/static/img/sandwich.svg"},
    "hot dog":    {"id": "coco_hotdog", "name": "Packaged Hot Dog", "brand": "Deli", "price": 80, "category": "Bakery", "emoji": "🌭", "image": "/static/img/hotdog.svg"},
    "donut":      {"id": "coco_donut", "name": "Glazed Donut", "brand": "Bakery", "price": 45, "category": "Bakery", "emoji": "🍩", "image": "/static/img/donut.svg"},
    "cake":       {"id": "coco_cake", "name": "Pastry Slice", "brand": "Bakery", "price": 70, "category": "Bakery", "emoji": "🍰", "image": "/static/img/cake.svg"},
    "sports ball": {"id": "coco_produce", "name": "Round Fruit / Produce", "brand": "Fresh Farm", "price": 20, "category": "Fruits", "emoji": "🍅", "image": "/static/img/orange.svg"},
    "book":       {"id": "coco_packet", "name": "Biscuit / Snack Pack", "brand": "Packaged", "price": 30, "category": "Biscuits & Cookies", "emoji": "🍪", "image": "/static/img/biscuit.svg"},
}

# COCO classes that YOLO should localise as "product-like" objects.
PRODUCT_CLASSES: set[str] = set(COCO_RETAIL_MAP)
PERSON_CLASS = "person"


def all_products() -> list[dict[str, Any]]:
    """Every product the cart can accept, de-duplicated by id."""
    seen: dict[str, dict[str, Any]] = {}
    for p in RETAIL_CATALOG:
        seen[p["id"]] = p
    for p in BARCODE_CATALOG.values():
        seen.setdefault(p["id"], p)
    for p in COCO_RETAIL_MAP.values():
        seen.setdefault(p["id"], p)
    return list(seen.values())


def lookup_product(product_id: str) -> dict[str, Any] | None:
    for p in all_products():
        if p["id"] == product_id:
            return p
    if product_id.startswith("bc_") and product_id[3:].isdigit():
        code = product_id[3:]
        return {
            "id": product_id, "name": f"Verified Product ({code})", "brand": "Barcode Scan",
            "price": UNKNOWN_BARCODE_PRICE, "category": "Packaged", "emoji": "🏷️",
        }
    return None


def public_catalog() -> list[dict[str, Any]]:
    """Catalog shown in the UI (no CLIP prompts)."""
    return [{k: v for k, v in p.items() if k != "prompts"} for p in RETAIL_CATALOG]
