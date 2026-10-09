# -*- coding: utf-8 -*-
"""POST /api/booking — send a booking request. Never confirms the appointment."""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from booking.request import accept  # noqa: E402

_MAX_BODY = 8000


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length < 0 or length > _MAX_BODY:
            self._send(413, {"ok": False, "status": "PAYLOAD_TOO_LARGE"})
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, {"ok": False, "status": "INVALID_JSON"})
            return
        code, payload = accept(body)
        self._send(code, payload)

    def do_GET(self):
        self._send(405, {"ok": False, "status": "POST_ONLY"})

    def _send(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
