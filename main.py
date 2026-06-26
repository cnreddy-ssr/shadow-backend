import os
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.environ.get("SMTP_USER", "getcnr@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ORDER_EMAIL   = os.environ.get("ORDER_EMAIL", "getcnr@gmail.com")


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
    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = ORDER_EMAIL
    msg["Subject"] = f"[SHADOW.] New Order #{order.orderId} — {order.occasion} ({order.mode.upper()})"

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
    msg.attach(MIMEText(body, "plain"))

    for i, photo in enumerate(order.photos):
        try:
            header, encoded = photo.data.split(",", 1)
            ext = "png" if "png" in header else "jpg"
            image_data = base64.b64decode(encoded)
            part = MIMEBase("application", "octet-stream")
            part.set_payload(image_data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="order_{order.orderId}_photo{i+1}.{ext}"')
            msg.attach(part)
        except Exception as e:
            print(f"Could not attach photo {i+1}: {e}")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, ORDER_EMAIL, msg.as_string())
        print(f"Order email sent: {order.orderId}")
