#!/usr/bin/env python3
"""office-hub — hub do devin-office a correr na VM.

Recebe WorldState via POST /api/ingest (vindo do probe local no Windows)
e serve index.html + /api/state. Zero deps (stdlib only).

Uso: python3 hub.py [--port 8790]
Env: OFFICE_TOKEN (opcional) — se definido, exige header X-Office-Token no ingest.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = (ROOT / "index.html").read_bytes()
TOKEN = os.environ.get("OFFICE_TOKEN", "")
STALE_AFTER_S = 15

STATE_LOCK = threading.Lock()
STATE_CACHE = {
    "ts": int(time.time()),
    "agents": [],
    "services": {},
    "events": [],
    "loading": True,
}
LAST_INGEST = {"at": 0.0}


def current_state() -> dict:
    with STATE_LOCK:
        st = dict(STATE_CACHE)
    age = time.time() - LAST_INGEST["at"]
    st["probe"] = {
        "lastIngestAgoS": round(age, 1),
        "live": bool(LAST_INGEST["at"]) and age <= STALE_AFTER_S,
    }
    if LAST_INGEST["at"] and age > STALE_AFTER_S:
        st["stale"] = True
    return st


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            self._send(200, json.dumps(current_state()).encode())
        elif self.path.startswith("/api/health"):
            self._send(200, json.dumps({"ok": True, "uptimeHint": LAST_INGEST["at"]}).encode())
        elif self.path in ("/", "/index.html"):
            self._send(200, INDEX, "text/html; charset=utf-8")
        elif self.path.startswith("/assets/"):
            self._send_static(self.path)
        else:
            self._send(404, b"404", "text/plain")

    def _send_static(self, path: str):
        rel = path.split("?", 1)[0].lstrip("/")
        target = (ROOT / rel).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self._send(404, b"404", "text/plain")
            return
        ctype = {
            ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
            ".css": "text/css", ".js": "text/javascript", ".html": "text/html",
        }.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        if not self.path.startswith("/api/ingest"):
            self._send(404, b"404", "text/plain")
            return
        if TOKEN and self.headers.get("X-Office-Token") != TOKEN:
            self._send(401, b'{"error":"bad token"}')
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode())
            return
        with STATE_LOCK:
            global STATE_CACHE
            STATE_CACHE = payload
        LAST_INGEST["at"] = time.time()
        self._send(200, b'{"ok":true}')


if __name__ == "__main__":
    port = 8790
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"devin-office hub -> http://0.0.0.0:{port} (token={'set' if TOKEN else 'open'})")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
