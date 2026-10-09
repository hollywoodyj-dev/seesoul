# -*- coding: utf-8 -*-
"""Accept a booking request. A received request is not a confirmed appointment."""

import json
import os
import re
import smtplib
import ssl
import uuid
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

SLOTS = ("09:00", "10:30", "13:00", "14:30", "16:00", "19:30")
SERVICES = {
    "counselling": "一对一咨询 · 60 分钟 · AUD $150",
    "life-theme": "生命课题解读 · 50 分钟 · AUD $100",
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clip(value, limit):
    text = value.strip() if isinstance(value, str) else ""
    return text[:limit]


def validate(body):
    if not isinstance(body, dict):
        return None, ["body"]
    service = body.get("service")
    mode = body.get("mode")
    day = body.get("date")
    slot = body.get("time")
    name = _clip(body.get("name"), 80)
    email = _clip(body.get("email"), 120)
    contact = _clip(body.get("contact"), 120)
    note = _clip(body.get("note"), 1000)
    missing = []
    if service not in SERVICES:
        missing.append("service")
    if mode not in ("online", "offline"):
        missing.append("mode")
    parsed = None
    if not isinstance(day, str):
        missing.append("date")
    else:
        try:
            parsed = date.fromisoformat(day)
        except ValueError:
            missing.append("date")
        else:
            earliest = date.today() - timedelta(days=1)
            latest = date.today() + timedelta(days=120)
            if parsed < earliest or parsed > latest:
                missing.append("date")
    if slot not in SLOTS:
        missing.append("time")
    if not name:
        missing.append("name")
    if not _EMAIL.match(email):
        missing.append("email")
    if missing:
        return None, missing
    return {
        "request_id": uuid.uuid4().hex[:12],
        "service": service,
        "service_label": SERVICES[service],
        "mode": "线上一对一" if mode == "online" else "线下一对一",
        "date": parsed.isoformat(),
        "time": slot,
        "name": name,
        "email": email,
        "contact": contact,
        "note": note,
    }, []


def render_text(record):
    return "\n".join([
        "这是一次预约请求，不是已经确认的预约，也还没有付款。",
        "",
        "服务：" + record["service_label"],
        "方式：" + record["mode"],
        "日期：" + record["date"],
        "时间：" + record["time"],
        "姓名：" + record["name"],
        "邮箱：" + record["email"],
        "联系方式：" + (record["contact"] or "（未留）"),
        "备注：" + (record["note"] or "（未留）"),
        "请求编号：" + record["request_id"],
    ])


def mailto_url(record, inbox):
    subject = "SeeSoul 预约请求 · " + record["date"] + " " + record["time"]
    note = record["note"]
    mailed = dict(record)
    if len(note) > 300:
        mailed["note"] = note[:300] + "（备注已截短）"
    body = render_text(mailed)
    return "mailto:" + quote(inbox) + "?subject=" + quote(subject) + "&body=" + quote(body)


def _store_path():
    override = os.environ.get("BOOKING_STORE_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "booking-requests.jsonl"


def _file_store(record):
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def _smtp(record, inbox):
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    sender = os.environ.get("BOOKING_FROM", "").strip() or user
    if not host or not sender:
        return False
    port = int(os.environ.get("SMTP_PORT") or "587")
    message = EmailMessage()
    message["Subject"] = "SeeSoul 预约请求 · " + record["date"] + " " + record["time"]
    message["From"] = sender
    message["To"] = inbox
    message["Reply-To"] = record["email"]
    message.set_content(render_text(record))
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if user:
                smtp.login(user, os.environ.get("SMTP_PASS", ""))
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        return False
    return True


def _resend(record, inbox):
    sender = os.environ.get("BOOKING_FROM", "").strip()
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not sender or not key:
        return False
    payload = json.dumps({
        "from": sender,
        "to": [inbox],
        "reply_to": record["email"],
        "subject": "SeeSoul 预约请求 · " + record["date"] + " " + record["time"],
        "text": render_text(record),
    }).encode("utf-8")
    req = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return 200 <= getattr(resp, "status", 0) < 300
    except OSError:
        return False


def _inbox():
    inbox = os.environ.get("BOOKING_TO", "").strip()
    if inbox and _EMAIL.match(inbox):
        return inbox
    return ""


def accept(body):
    record, missing = validate(body)
    if missing:
        return 400, {"ok": False, "status": "INVALID", "fields": missing}
    if os.environ.get("BOOKING_DELIVERY", "").strip() == "file":
        _file_store(record)
        return 200, {"ok": True, "status": "REQUEST_RECEIVED", "request_id": record["request_id"]}
    inbox = _inbox()
    if inbox and os.environ.get("RESEND_API_KEY", "").strip() and os.environ.get("BOOKING_FROM", "").strip():
        if _resend(record, inbox):
            return 200, {"ok": True, "status": "REQUEST_RECEIVED", "request_id": record["request_id"]}
        return 502, {"ok": False, "status": "DELIVERY_FAILED"}
    if inbox and os.environ.get("SMTP_HOST", "").strip():
        if _smtp(record, inbox):
            return 200, {"ok": True, "status": "REQUEST_RECEIVED", "request_id": record["request_id"]}
        return 502, {"ok": False, "status": "DELIVERY_FAILED"}
    if inbox:
        return 200, {"ok": True, "status": "OPEN_MAIL", "mailto": mailto_url(record, inbox)}
    return 503, {"ok": False, "status": "DELIVERY_NOT_CONFIGURED"}
