import os
import base64
import json
import urllib.request
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SHADOW. Wallpaper Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ORDER_EMAIL    = os.environ.get("ORDER_EMAIL", "getcnr@gmail.com")


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


@app.get("/")
def root():
    return {"status": "SHADOW. backend is running"}


@app.post("/order")
def receive_order(order: OrderRequest):
    try:
        send_order_email(order)
        return {"success": True, "orderId": order.orderId}
    except Exception as e:
        print(f"Email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def send_order_email(order: OrderRequest):
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
Processing  : {'Automated (ready in minutes)' if order.mode == 'auto' else 'Manual Craft (within 24 hrs)'}
Fee         : Rs.{order.fee} (collect on delivery)

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
Please process and deliver via WhatsApp to +{order.deliveryPhone}
"""

    attachments = []
    for i, photo in enumerate(order.photos):
        try:
            header, encoded = photo.data.split(",", 1)
            ext = "png" if "png" in header else "jpg"
            attachments.append({
                "filename": f"order_{order.orderId}_photo{i+1}.{ext}",
                "content": encoded
            })
        except Exception as e:
            print(f"Could not prepare photo {i+1}: {e}")

    # Resend free tier: from must be onboarding@resend.dev, to must be your own verified email
    payload = {
        "from": "SHADOW Orders <onboarding@resend.dev>",
        "to": ["cnreddy@gmail.com"],
        "reply_to": ORDER_EMAIL,
        "subject": f"[SHADOW.] New Order #{order.orderId} — {order.occasion} ({order.mode.upper()})",
        "text": body,
        "attachments": attachments
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"Email sent via Resend: {result}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Resend error body: {error_body}")
        raise Exception(f"Resend {e.code}: {error_body}")
