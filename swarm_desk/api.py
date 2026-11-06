"""Swarm Desk HTTP API - zero new dependencies (stdlib http.server).

    swarm-desk serve --port 8799

Endpoints (JSON in, JSON out):

    POST /verdict   {asset, momentum, volatility, value, sentiment,
                     headlines[], rounds, seed}
                    -> the verdict, plus the ledger_id of the run it
                       just logged. Signals may also be nested under a
                       "signals" object.
    GET  /personas  -> the persona roster and reasoning styles.
    POST /outcome   {ledger_id, outcome}  (or {timestamp, asset, outcome})
                    -> scores a past prediction in the ledger.
    GET  /health    -> {"status": "ok"}
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import run_swarm
from .ledger import default_ledger_path, log_run, score_outcome
from .mcp_server import personas_payload

_SIGNAL_KEYS = ("momentum", "volatility", "value", "sentiment")


def verdict_for_payload(payload: dict, ledger_path=None) -> tuple[int, dict]:
    """Shared logic for POST /verdict. Returns (status, body)."""
    asset = payload.get("asset")
    if not asset:
        return 400, {"error": "missing required field: asset"}
    signals = dict(payload.get("signals") or {})
    for key in _SIGNAL_KEYS:
        if key in payload:
            signals[key] = payload[key]
    headlines = payload.get("headlines") or []
    verdict = run_swarm(
        asset=asset,
        signals=signals,
        headlines=headlines,
        rounds=int(payload.get("rounds", 2)),
        seed=int(payload.get("seed", 42)),
    )
    entry = log_run(verdict, inputs_summary={
        "signals": signals,
        "headlines": headlines,
        "source": "http",
    }, path=ledger_path)
    body = verdict.to_dict()
    body["ledger_id"] = entry["id"]
    return 200, body


def outcome_for_payload(payload: dict, ledger_path=None) -> tuple[int, dict]:
    """Shared logic for POST /outcome. Returns (status, body)."""
    if "outcome" not in payload:
        return 400, {"error": "missing required field: outcome"}
    entry = score_outcome(
        payload["outcome"],
        path=ledger_path,
        entry_id=payload.get("ledger_id") or payload.get("id"),
        timestamp=payload.get("timestamp"),
        asset=payload.get("asset"),
    )
    if entry is None:
        return 404, {"scored": False, "error": "no matching ledger entry"}
    return 200, {"scored": True, "entry": entry}


def make_handler(ledger_path=None):
    class SwarmDeskHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "SwarmDesk/0.1"

        def log_message(self, *args):  # keep the console quiet
            pass

        def _send_json(self, status: int, body: dict) -> None:
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict | None:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None

        def do_GET(self):
            if self.path == "/personas":
                self._send_json(200, {"personas": personas_payload()})
            elif self.path == "/health":
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": f"no route: GET {self.path}"})

        def do_POST(self):
            payload = self._read_json()
            if payload is None:
                self._send_json(400, {"error": "request body is not JSON"})
                return
            if self.path == "/verdict":
                status, body = verdict_for_payload(payload, ledger_path)
                self._send_json(status, body)
            elif self.path == "/outcome":
                status, body = outcome_for_payload(payload, ledger_path)
                self._send_json(status, body)
            else:
                self._send_json(404, {"error": f"no route: POST {self.path}"})

    return SwarmDeskHandler


def make_server(port: int = 8799, host: str = "127.0.0.1",
                ledger_path=None) -> ThreadingHTTPServer:
    """Build (but do not start) the HTTP server - tests use port 0."""
    return ThreadingHTTPServer((host, port), make_handler(ledger_path))


def serve(port: int = 8799, host: str = "127.0.0.1",
          ledger_path=None) -> int:
    httpd = make_server(port, host, ledger_path)
    ledger = ledger_path or default_ledger_path()
    print(f"Swarm Desk API on http://{host}:{port}  (ledger: {ledger})")
    print("  POST /verdict   GET /personas   POST /outcome   GET /health")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
