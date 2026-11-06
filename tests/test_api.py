"""HTTP API smoke test on an ephemeral port (stdlib only)."""

import json
import threading
import urllib.request

import pytest

from swarm_desk.api import make_server
from swarm_desk.ledger import read_entries


@pytest.fixture()
def server(tmp_path):
    ledger = tmp_path / "api-ledger.jsonl"
    httpd = make_server(port=0, ledger_path=ledger)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield base, ledger
    httpd.shutdown()
    httpd.server_close()


def _post(base, route, payload):
    req = urllib.request.Request(
        base + route,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get(base, route):
    with urllib.request.urlopen(base + route, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_http_verdict_personas_outcome_flow(server):
    base, ledger = server

    status, body = _post(base, "/verdict", {
        "asset": "NVDA", "momentum": 0.8, "volatility": 0.3,
        "headlines": ["Chipmaker beats estimates as growth surges"],
    })
    assert status == 200
    assert body["asset"] == "NVDA"
    assert body["gate"] in ("KEEP", "PRUNE-CANDIDATE")
    ledger_id = body["ledger_id"]
    assert ledger_id
    assert len(read_entries(ledger)) == 1

    status, body = _get(base, "/personas")
    assert status == 200
    assert len(body["personas"]) >= 8

    status, body = _post(base, "/outcome", {
        "ledger_id": ledger_id, "outcome": 0.07,
    })
    assert status == 200
    assert body["scored"] is True
    assert read_entries(ledger)[0]["outcome"] == 0.07


def test_http_health(server):
    base, _ = server
    status, body = _get(base, "/health")
    assert status == 200
    assert body["status"] == "ok"
