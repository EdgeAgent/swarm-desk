# Swarm Desk — Quickstart

Swarm Desk is a swarm-sentiment engine for the H-QRD Trading Desk:
nine persona agents debate one asset over two rounds, and the engine
hands back a single confidence number (0..1) plus a gate call for the
desk's Agent 02 prune gate. It runs fully offline — no API keys, no
accounts, nothing beyond the Python standard library (the MCP door
adds one optional package). **Paper/research only — it places no
trades and moves no money.**

## Prerequisites

- **Python 3.12 or newer** (the package declares `requires-python >= 3.12`;
  3.12 is the tested version). Check yours: `python3 --version`
- That's it. No API keys, no network access needed after install.

## One-command setup

From the repo root:

```bash
./setup.sh            # Linux / macOS
.\setup.ps1           # Windows PowerShell
```

The script creates a `.venv`, installs Swarm Desk **with its MCP
door** from this checkout, verifies the install
(`swarm-desk --version` → `swarm-desk 0.1.1`), runs the test suite
when pytest is available, and finishes by running the demo below.
It's safe to re-run.

### The manual path (same result, by hand)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[mcp]"
swarm-desk --version
```

## Your first run: the demo

```bash
swarm-desk demo
```

This runs the swarm over the built-in 12-asset sample universe
(`examples/sample_signals.json`, seed 42) and prints a table like:

```
Asset     Stance  Bull%  Bear%   Conf  Verdict        Gate
NVDA       +0.52    89%    11%   0.73  BULLISH        KEEP
...
2 KEEP / 10 PRUNE-CANDIDATE at the 0.70 gate.
```

How to read it:

- **Conf** is the aggregated confidence, 0..1.
- **KEEP** means confidence ≥ **0.70** — the asset survives the
  Agent 02 prune gate and stays on the desk's shortlist.
- **PRUNE-CANDIDATE** means confidence < 0.70 — the gate drops it.
  With the sample data only NVDA (0.73) and PG (0.72) clear the bar;
  a swarm that keeps everything isn't a filter.
- Every run is appended to the experiment ledger
  (`data/ledger.jsonl`), so predictions can be scored against reality
  later. That ledger is the point: a signal earns trust from its
  scored track record, failures included.

## The doors

### CLI — one asset, your signals

```bash
swarm-desk run --asset NVDA --momentum 0.8 --volatility 0.3 \
    --headlines "Chipmaker beats estimates as AI demand surges"
```

Signals: `--momentum`, `--value`, `--sentiment` range −1..+1;
`--volatility` ranges 0..1. Add `--seed` / `--rounds` to taste
(defaults 42 and 2; same inputs + same seed = same verdict, always).

### HTTP — a server any agent can call

```bash
swarm-desk serve --port 8799
```

```bash
curl -s -X POST http://127.0.0.1:8799/verdict \
  -H "Content-Type: application/json" \
  -d '{"asset": "NVDA", "momentum": 0.8, "volatility": 0.3,
       "headlines": ["Chipmaker beats estimates as AI demand surges"]}'
```

Returns the verdict JSON plus a `ledger_id`. The other routes:
`GET /personas`, `POST /outcome` (score a past prediction),
`GET /health`. Signals may also be nested under a `"signals"` object.
A worked client is in `examples/http_agent.py`.

### Python — in-process

```python
from swarm_desk import run_swarm

verdict = run_swarm("NVDA",
                    signals={"momentum": 0.8, "volatility": 0.3},
                    headlines=["Chipmaker beats estimates as AI demand surges"])
print(round(verdict.confidence, 2), verdict.gate)   # 0.61 PRUNE-CANDIDATE
```

`examples/python_agent.py` runs the whole sample universe this way.
(Library calls don't write to the ledger on their own — pass a verdict
to `swarm_desk.ledger.log_run()` to record it.)

### MCP — tools for an agent host

```bash
swarm-desk mcp        # stdio server; your MCP host runs this for you
```

Wire it into Hermes or any MCP host with the ready-made block in
`examples/hermes_mcp_config.json` — see `examples/README.md` for where
it goes and the four tools the agent gains (`run_swarm`, `check_gate`,
`list_personas`, `score_outcome`).

## Troubleshooting

**`AttributeError: 'Server' object has no attribute 'list_tools'` when
starting the MCP server**
You have mcp 2.x installed; the server uses the mcp 1.x API. Swarm
Desk v0.1.1 pins the extra to `mcp>=1.0,<2.0` — reinstall from the
checkout so the pin applies:

```bash
pip install --force-reinstall -e ".[mcp]"
swarm-desk --version    # should say 0.1.1
```

**The installed version looks old / behaves like an older release**
pip may be reusing a previous install. Force it:

```bash
pip install --force-reinstall -e ".[mcp]"
swarm-desk --version    # expect: swarm-desk 0.1.1
```

**No pytest in a fresh venv**
The test suite is optional for using Swarm Desk. Either install it:

```bash
pip install pytest
python -m pytest tests -q
```

…or skip the suite and smoke-test with the demo instead —
`swarm-desk demo` exercises the full engine end to end.

**`Address already in use` when starting the HTTP server**
Something (often an earlier `swarm-desk serve`) already holds the
port. Pick another and point clients at it:

```bash
swarm-desk serve --port 8800
SWARM_DESK_URL=http://127.0.0.1:8800 python examples/http_agent.py
```

**`swarm-desk mcp` prints an install hint and exits**
The optional `mcp` package isn't installed in that environment.
`pip install -e ".[mcp]"` fixes it; the CLI, HTTP and Python doors
work without it.
