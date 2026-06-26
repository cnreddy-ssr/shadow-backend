import os
import base64
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from wallpaper import generate_wallpapers

app = FastAPI(title="SHADOW. Wallpaper Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
ORDER_EMAIL   = os.environ.get("ORDER_EMAIL", "cnreddy@gmail.com")
ADMIN_PASS    = os.environ.get("ADMIN_PASSWORD", "shadow")

# ── IN-MEMORY ORDER STORE ──
orders = []


# ── MODELS ──
class Photo(BaseModel):
    name: str
    data: str

class OrderRequest(BaseModel):
    orderId: str
    phone: str
    occasion: str
    mode: str
    fee: int
    photos: List[Photo]
    formats: List[str]
    template: str
    customText: Optional[str] = ""
    bgColor: str
    accentColor: str
    font: str
    deliveryPhone: str
    deliveryEmail: Optional[str] = ""


# ── HEALTH ──
@app.get("/")
def root():
    return {"status": "SHADOW. backend is running"}


@app.get("/test-email")
def test_email():
    payload = {
        "sender":      {"name": "SHADOW Orders", "email": "cnreddy@gmail.com"},
        "to":          [{"email": "cnreddy@gmail.com"}],
        "subject":     "SHADOW. Test Email",
        "textContent": "This is a test from SHADOW. backend via Brevo."
    }
    result = call_brevo(payload)
    return result


# ── ORDER ──
@app.post("/order")
def receive_order(order: OrderRequest):
    try:
        # Store order
        order_dict = order.dict()
        order_dict["status"]     = "Pending"
        order_dict["receivedAt"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
        order_dict["wallpapers"] = {}
        orders.append(order_dict)

        # Generate wallpapers for automated orders
        wallpaper_attachments = []
        if order.mode == "auto" and order.photos:
            try:
                for i, photo in enumerate(order.photos):
                    results = generate_wallpapers(
                        photo_data_url = photo.data,
                        template       = order.template,
                        custom_text    = order.customText or "",
                        bg_color       = order.bgColor,
                        accent_color   = order.accentColor,
                        formats        = order.formats
                    )
                    for fmt, img_bytes in results.items():
                        encoded = base64.b64encode(img_bytes).decode()
                        fname   = f"{order.orderId}_photo{i+1}_{fmt}.jpg"
                        wallpaper_attachments.append({
                            "content":  encoded,
                            "name":     fname
                        })
                        order_dict["wallpapers"][fname] = encoded
            except Exception as e:
                print(f"Wallpaper generation error: {e}")

        # Send order email
        send_order_email(order, wallpaper_attachments)
        return {"success": True, "orderId": order.orderId}

    except Exception as e:
        print(f"Order error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── ADMIN API ──
@app.get("/admin/orders")
def get_orders(password: str = ""):
    if password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Return orders without photo data (too large)
    safe_orders = []
    for o in orders:
        safe = {k: v for k, v in o.items() if k not in ("photos", "wallpapers")}
        safe["photoCount"]     = len(o.get("photos", []))
        safe["wallpaperCount"] = len(o.get("wallpapers", {}))
        safe_orders.append(safe)
    return safe_orders


@app.post("/admin/status")
def update_status(orderId: str, status: str, password: str = ""):
    if password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    for o in orders:
        if o["orderId"] == orderId:
            o["status"] = status
            return {"success": True}
    raise HTTPException(status_code=404, detail="Order not found")


@app.get("/admin/wallpapers/{orderId}")
def get_wallpapers(orderId: str, password: str = ""):
    if password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    for o in orders:
        if o["orderId"] == orderId:
            return {"wallpapers": list(o.get("wallpapers", {}).keys())}
    raise HTTPException(status_code=404, detail="Order not found")


# ── EMAIL ──
def send_order_email(order: OrderRequest, wallpaper_attachments: list):
    mode_text = "Automated (ready in minutes)" if order.mode == "auto" else "Manual Craft (within 24 hrs)"
    auto_note = f"\n{len(wallpaper_attachments)} wallpaper(s) auto-generated and attached." if wallpaper_attachments else ""

    body = f"""
NEW WALLPAPER ORDER RECEIVED
═══════════════════════════════════════
Order ID    : {order.orderId}
Time        : {datetime.now().strftime('%d %b %Y, %I:%M %p')}

CUSTOMER
────────────────────────────────────
Phone       : +{order.phone}
WhatsApp    : +{order.deliveryPhone}
Email       : {order.deliveryEmail or '—'}

ORDER DETAILS
────────────────────────────────────
Occasion    : {order.occasion}
Processing  : {mode_text}
Fee         : Rs.{order.fee} (collect on delivery){auto_note}

STYLE OPTIONS
────────────────────────────────────
Formats     : {', '.join(order.formats)}
Template    : {order.template}
Custom Text : {order.customText or '—'}
Background  : {order.bgColor}
Accent      : {order.accentColor}
Font        : {order.font}
Photos      : {len(order.photos)} photo(s) attached

═══════════════════════════════════════
Please deliver via WhatsApp to +{order.deliveryPhone}
"""

    # Original photo attachments
    photo_attachments = []
    for i, photo in enumerate(order.photos):
        try:
            header, encoded = photo.data.split(",", 1)
            ext = "png" if "png" in header else "jpg"
            photo_attachments.append({
                "content": encoded,
                "name":    f"original_{order.orderId}_photo{i+1}.{ext}"
            })
        except Exception as e:
            print(f"Could not prepare photo {i+1}: {e}")

    all_attachments = photo_attachments + wallpaper_attachments

    payload = {
        "sender":      {"name": "SHADOW Orders", "email": "cnreddy@gmail.com"},
        "to":          [{"email": ORDER_EMAIL}],
        "subject":     f"[SHADOW.] #{order.orderId} — {order.occasion} ({order.mode.upper()})",
        "textContent": body,
        "attachment":  all_attachments
    }

    call_brevo(payload)


def call_brevo(payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "api-key":      BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"Brevo response: {result}")
            return {"success": True, "response": result}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Brevo error {e.code}: {error_body}")
        raise Exception(f"Brevo {e.code}: {error_body}")
