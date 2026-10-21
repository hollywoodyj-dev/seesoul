# -*- coding: utf-8 -*-
"""POST /api/compass — retired. Compass v2 builds its note in the page and sends nothing here."""

import json
from http.server import BaseHTTPRequestHandler

_BODY = json.dumps({"ok": False, "status": "RETIRED"}).encode("utf-8")


class handler(BaseHTTPRequestHandler):
    def _gone(self):
        self.send_response(410)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(_BODY)))
        self.end_headers()
        self.wfile.write(_BODY)

    do_GET = _gone
    do_POST = _gone
    do_PUT = _gone
    do_DELETE = _gone
