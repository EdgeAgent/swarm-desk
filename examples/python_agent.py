#!/usr/bin/env python3
"""Generic agent example - the Python door.

Runs the swarm directly, in-process, on every asset in the bundled
sample data and prints each asset's confidence and gate call.

    python examples/python_agent.py

Needs the package installed (./setup.sh, or: pip install -e ".[mcp]").
Note: library calls do not write to the experiment ledger on their own -
if you want a run recorded, pass it to swarm_desk.ledger.log_run().
"""

import json
from pathlib import Path

from swarm_desk import run_swarm

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_PATH = REPO_ROOT / "examples" / "sample_signals.json"


def main() -> int:
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    keeps = 0
    for asset, spec in samples.items():
        verdict = run_swarm(asset,
                            signals=spec.get("signals"),
                            headlines=spec.get("headlines"))
        keeps += verdict.gate == "KEEP"
        print(f"{asset:<6} confidence {verdict.confidence:.2f}  "
              f"{verdict.label:<13} ->  {verdict.gate}")
    print(f"\n{keeps} KEEP / {len(samples) - keeps} PRUNE-CANDIDATE "
          f"at the 0.70 gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
