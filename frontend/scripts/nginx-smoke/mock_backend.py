"""Backend giả cho smoke test nginx production (FE-14), chỉ dùng stdlib.

Chạy trong container có alias mạng `backend`, cổng 8000. Thời gian chờ đổi được
qua query string để `run.sh --quick` chạy nhanh:

- GET  /api/health                  -> 200 JSON
- GET  /api/json                    -> 200 JSON ~4KB (kiểm gzip cho response proxy)
- POST /api/documents               -> đọc hết body, 202 {"received": <số byte>}
- PUT  /api/documents/<id>/markdown -> đọc hết body, 200 {"received": <số byte>}
- POST /api/chat                    -> đọc hết body, 200
- POST /api/chat/stream?gap=120     -> một dòng NDJSON, ngủ `gap` giây, một dòng nữa
- POST /api/ingest/chunk?sleep=200  -> ngủ `sleep` giây rồi 200
- GET  /api/slow?sleep=130          -> ngủ `sleep` giây rồi 200 (nginx phải cắt 504 ở 120s)
"""

from __future__ import annotations

import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class Handler(BaseHTTPRequestHandler):
    def _query_number(self, name: str, default: float) -> float:
        values = parse_qs(urlsplit(self.path).query).get(name)
        return float(values[0]) if values else default

    def _read_body(self) -> int:
        remaining = int(self.headers.get("Content-Length") or 0)
        received = 0
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 1 << 20))
            if not chunk:
                break
            received += len(chunk)
            remaining -= len(chunk)
        return received

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route == "/api/health":
            self._json(200, {"status": "ok"})
        elif route == "/api/json":
            self._json(200, {"items": [{"id": i, "text": "lorem ipsum dolor"} for i in range(120)]})
        elif route == "/api/slow":
            time.sleep(self._query_number("sleep", 130))
            self._json(200, {"slept": True})
        else:
            self._json(404, {"detail": "Not Found"})

    def do_POST(self) -> None:
        route = urlsplit(self.path).path
        received = self._read_body()
        if route == "/api/documents":
            self._json(202, {"received": received})
        elif route == "/api/chat":
            self._json(200, {"received": received})
        elif route == "/api/chat/stream":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.end_headers()
            self.wfile.write(b'{"type":"start"}\n')
            self.wfile.flush()
            time.sleep(self._query_number("gap", 120))
            self.wfile.write(b'{"type":"done"}\n')
            self.wfile.flush()
            self.close_connection = True
        elif route in {"/api/ingest/chunk", "/api/ingest"}:
            time.sleep(self._query_number("sleep", 200))
            self._json(200, {"chunked": True})
        else:
            self._json(404, {"detail": "Not Found"})

    def do_PUT(self) -> None:
        route = urlsplit(self.path).path
        received = self._read_body()
        if re.fullmatch(r"/api/documents/[^/]+/markdown", route):
            self._json(200, {"received": received})
        else:
            self._json(404, {"detail": "Not Found"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - chữ ký của stdlib
        print(f"[mock] {self.command} {self.path} -> {format % args}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
