#!/usr/bin/env python3
"""Generic agent example - the HTTP door (standard library only).

Asks a running Swarm Desk HTTP server for one asset's verdict, using
the NVDA sample signals, and prints the verdict JSON it gets back -
including the ledger_id of the run the server just logged.

Start the server first, in another terminal:

    swarm-desk serve --port 8799

Then:

    python examples/http_agent.py

Point it elsewhere with the SWARM_DESK_URL environment variable, e.g.
SWARM_DESK_URL=http://127.0.0.1:8800 python examples/http_agent.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("SWARM_DESK_URL", "http://127.0.0.1:8799")
ASSET = "NVDA"

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_PATH = REPO_ROOT / "examples" / "sample_signals.json"


def main() -> int:
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    spec = samples[ASSET]
    # POST /verdict accepts the signals flat, next to the asset, or
    # nested under a "signals" object - this example sends them flat.
    payload = {"asset": ASSET, "headlines": spec.get("headlines") or []}
    payload.update(spec.get("signals") or {})

    request = urllib.request.Request(
        BASE_URL + "/verdict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            verdict = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        print(f"Could not reach the Swarm Desk server at {BASE_URL} ({exc}).")
        print("Start it first, in another terminal:")
        print("    swarm-desk serve --port 8799")
        return 1

    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
