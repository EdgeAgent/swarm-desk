"""Swarm Desk MCP server (stdio). An OPTIONAL door into the engine.

The official `mcp` Python package is an optional extra:

    pip install "swarm-desk[mcp]"        # or: pip install mcp

Without it, `swarm-desk mcp` prints an install hint and exits - the core
package, the HTTP API and the Python API never need it.

The tool schemas come from swarm_desk.tools (one shared source), and the
dispatch logic lives in handle_tool(), which is plain Python and fully
testable without the mcp package installed.
"""

from __future__ import annotations

import json
import sys

from .engine import gate_for, run_swarm
from .ledger import log_run, score_outcome
from .personas import PERSONAS
from .tools import mcp_tools

INSTALL_HINT = (
    "The MCP server needs the optional 'mcp' package.\n"
    "Install it with:  pip install \"swarm-desk[mcp]\"   (or: pip install mcp)\n"
    "Everything else in Swarm Desk works without it."
)

try:
    import mcp  # noqa: F401

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def build_tool_schemas() -> list[dict]:
    """The MCP tool list as plain dicts - no mcp package required."""
    return mcp_tools()


def personas_payload() -> list[dict]:
    return [
        {
            "name": p.name,
            "display": p.display,
            "style": p.style,
            "weights": p.weights,
            "bias": p.bias,
            "noise_scale": p.noise_scale,
            "herd": p.herd,
        }
        for p in PERSONAS
    ]


def handle_tool(name: str, arguments: dict | None = None,
                ledger_path=None) -> dict:
    """Dispatch one tool call. Pure Python; used by the MCP server and
    directly testable without the mcp package."""
    args = arguments or {}
    if name == "run_swarm":
        verdict = run_swarm(
            asset=args["asset"],
            signals=args.get("signals"),
            headlines=args.get("headlines"),
            rounds=int(args.get("rounds", 2)),
            seed=int(args.get("seed", 42)),
        )
        entry = log_run(verdict, inputs_summary={
            "signals": args.get("signals") or {},
            "headlines": args.get("headlines") or [],
            "source": "mcp",
        }, path=ledger_path)
        return {"verdict": verdict.to_dict(), "ledger_id": entry["id"]}
    if name == "check_gate":
        confidence = float(args["confidence"])
        return {"confidence": confidence, "gate": gate_for(confidence),
                "gate_threshold": 0.70}
    if name == "list_personas":
        return {"personas": personas_payload()}
    if name == "score_outcome":
        entry = score_outcome(
            args["outcome"],
            path=ledger_path,
            entry_id=args.get("ledger_id"),
            timestamp=args.get("timestamp"),
            asset=args.get("asset"),
        )
        if entry is None:
            return {"scored": False, "error": "no matching ledger entry"}
        return {"scored": True, "entry": entry}
    return {"error": f"unknown tool: {name}"}


def create_server():
    """Build the stdio MCP server (requires the mcp package)."""
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    server = Server("swarm-desk")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"],
                 inputSchema=t["inputSchema"])
            for t in build_tool_schemas()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None = None):
        result = handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def _serve() -> None:
    from mcp.server.stdio import stdio_server

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         server.create_initialization_options())


def main() -> int:
    if not MCP_AVAILABLE:
        print(INSTALL_HINT, file=sys.stderr)
        return 1
    import asyncio

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
