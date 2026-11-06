# Examples

Three worked ways for an agent to use Swarm Desk — one per door.
Everything below uses only the interfaces the package actually ships.

| File | Door | What it does |
|---|---|---|
| `hermes_mcp_config.json` | MCP | Server config block that gives an MCP host (Hermes-style) the swarm as tools |
| `http_agent.py` | HTTP | Asks a running server for one asset's verdict, standard library only |
| `python_agent.py` | Python | Runs the swarm in-process over all 12 sample assets |

Run them from the repo root, after `./setup.sh` (Windows: `.\setup.ps1`)
or a manual `pip install -e ".[mcp]"`.

## Python door

```bash
python examples/python_agent.py
```

Prints every sample asset's confidence and gate call
(`KEEP` at confidence ≥ 0.70, otherwise `PRUNE-CANDIDATE`).
Library calls don't write to the experiment ledger by themselves —
pass a verdict to `swarm_desk.ledger.log_run()` if you want it recorded.

## HTTP door

Terminal 1:

```bash
swarm-desk serve --port 8799
```

Terminal 2:

```bash
python examples/http_agent.py
```

Sends the NVDA sample signals to `POST /verdict` and prints the full
verdict JSON, including the `ledger_id` of the run the server logged.
Set `SWARM_DESK_URL` to aim it at another host/port. The other routes
are `GET /personas`, `POST /outcome` and `GET /health`.

## MCP door — wiring Swarm Desk into Hermes (or any MCP host)

`hermes_mcp_config.json` is the whole wiring:

```json
{
  "mcpServers": {
    "swarm-desk": {
      "command": "swarm-desk",
      "args": ["mcp"]
    }
  }
}
```

Add that `swarm-desk` entry to your MCP host's server configuration
(for Hermes, wherever it keeps its MCP server list). Two things to know:

- The host starts the server itself over stdio — you don't run
  `swarm-desk mcp` by hand. The `swarm-desk` command must resolve on
  the host's PATH: activate the project virtualenv first, or replace
  `"swarm-desk"` with the full path, e.g.
  `/path/to/swarm-desk/.venv/bin/swarm-desk`.
- It needs the MCP extra installed (`pip install -e ".[mcp]"`, already
  done by the setup scripts). Without it, `swarm-desk mcp` prints an
  install hint and exits.

Once connected, the agent gains exactly the four tools the server
exposes:

| Tool | What it does |
|---|---|
| `run_swarm` | Run the persona swarm on one asset (`asset` required; `signals`, `headlines`, `rounds`, `seed` optional) and return the verdict; the run is appended to the ledger |
| `check_gate` | Map a confidence to the gate call: `KEEP` at ≥ 0.70, otherwise `PRUNE-CANDIDATE` |
| `list_personas` | List the nine personas with their reasoning styles and signal weights |
| `score_outcome` | Attach a realized outcome to a past ledger entry (`outcome` required; identify the entry by `ledger_id`, or by `timestamp` + `asset`) |
