# Swarm Desk — Integrations

Swarm Desk is plug-and-play: the same engine sits behind three doors.
Pick the door your framework already speaks.

## Which door should you use?

| Door | Use it when | Needs |
|---|---|---|
| **MCP** | Your agent framework speaks Model Context Protocol (Hermes, Claude Desktop, Cursor, most agent runtimes) | `pip install "swarm-desk[mcp]"` |
| **HTTP** | Anything that can make a POST — any language, any agent, a shell script | nothing, stdlib only |
| **Python** | Your code is Python and you want the verdict in-process | nothing |

All three return the same verdict shape and write to the same
experiment ledger, so a prediction made through one door can be scored
through another.

---

## (a) Hermes — MCP

Hermes speaks MCP. Register Swarm Desk as a stdio MCP server in the
MCP servers section of your Hermes config:

```json
{
  "mcpServers": {
    "swarm-desk": {
      "command": "swarm-desk",
      "args": ["mcp"],
      "env": { "SWARM_DESK_LEDGER": "data/ledger.jsonl" }
    }
  }
}
```

That gives the Hermes swarm four new tools: `run_swarm`, `check_gate`,
`list_personas`, `score_outcome`. In the H-QRD desk, Agent 02 calls
`run_swarm` per asset and prunes whatever comes back under the 0.70
gate.

Hermes can also skip MCP entirely: the same box speaks plain HTTP
(`swarm-desk serve --port 8799`, see (c)), which any Hermes HTTP tool
step can call.

## (b) Generic MCP client (Claude Desktop / Cursor style)

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

Not installed yet? Point the client at the module instead:

```json
{
  "mcpServers": {
    "swarm-desk": {
      "command": "python",
      "args": ["-m", "swarm_desk", "mcp"],
      "cwd": "/path/to/swarm-desk"
    }
  }
}
```

## (c) Any agent — HTTP

Start the server (zero dependencies):

```bash
swarm-desk serve --port 8799
```

Get a verdict (this also logs the run and returns its `ledger_id`):

```bash
curl -s -X POST localhost:8799/verdict \
  -H 'Content-Type: application/json' \
  -d '{"asset": "NVDA", "momentum": 0.8, "volatility": 0.3,
       "headlines": ["Chipmaker beats estimates as AI demand surges"]}'
```

```json
{ "asset": "NVDA", "mean_stance": 0.38, "confidence": 0.61,
  "label": "BULLISH", "gate": "PRUNE-CANDIDATE", "ledger_id": "..." }
```

Meet the swarm:

```bash
curl -s localhost:8799/personas
```

Score a prediction later, when the outcome is known:

```bash
curl -s -X POST localhost:8799/outcome \
  -H 'Content-Type: application/json' \
  -d '{"ledger_id": "<id from the verdict>", "outcome": 0.07}'
```

## (d) Python API

```python
from swarm_desk import run_swarm

v = run_swarm("NVDA", signals={"momentum": 0.8, "volatility": 0.3},
              headlines=["Chipmaker beats estimates"])
print(v.confidence, v.gate)   # e.g. 0.61 PRUNE-CANDIDATE
```

## (e) OpenAI-style tools

`swarm_desk/tools.json` ships both renderings of the four tools
(OpenAI function-calling and MCP), generated from one source dict so
they can never drift:

```python
import json
from swarm_desk.tools import openai_tools

tools = openai_tools()  # or: json.load(open("swarm_desk/tools.json"))["openai"]

response = client.chat.completions.create(
    model="your-model",
    messages=[{"role": "user",
               "content": "Run the swarm on NVDA, momentum 0.8, vol 0.3."}],
    tools=tools,
)
# Dispatch tool calls to swarm_desk.mcp_server.handle_tool(name, args),
# which runs the engine and logs to the ledger.
```

## Configuration

| Env var | Door | Meaning |
|---|---|---|
| `SWARM_DESK_LEDGER` | all | Ledger path (default `data/ledger.jsonl`) |
| `SWARM_LLM_API_KEY` | engine | Optional LLM headline blend — key |
| `SWARM_LLM_BASE_URL` | engine | Optional LLM headline blend — OpenAI-compatible base URL |
| `SWARM_LLM_MODEL` | engine | Optional LLM headline blend — model id |

Nothing here is required. With zero environment variables set, every
door works fully offline.
