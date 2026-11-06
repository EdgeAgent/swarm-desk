"""Tool-schema tests: the shared definitions, both renderings, the
shipped tools.json, and the MCP dispatch layer - all without the mcp
package installed."""

import json
from pathlib import Path

import swarm_desk
from swarm_desk.mcp_server import build_tool_schemas, handle_tool
from swarm_desk.tools import mcp_tools, openai_tools

EXPECTED_TOOLS = ["check_gate", "list_personas", "run_swarm", "score_outcome"]


def _check_schema(params):
    assert params["type"] == "object"
    assert "properties" in params
    for required in params.get("required", []):
        assert required in params["properties"]


def test_openai_tools_well_formed():
    tools = openai_tools()
    assert sorted(t["function"]["name"] for t in tools) == EXPECTED_TOOLS
    for t in tools:
        assert t["type"] == "function"
        assert t["function"]["description"]
        _check_schema(t["function"]["parameters"])


def test_mcp_tools_well_formed():
    tools = mcp_tools()
    assert sorted(t["name"] for t in tools) == EXPECTED_TOOLS
    for t in tools:
        assert t["description"]
        _check_schema(t["inputSchema"])


def test_mcp_server_schemas_come_from_shared_source():
    schemas = build_tool_schemas()
    assert schemas == mcp_tools()


def test_shipped_tools_json_matches_source():
    path = Path(swarm_desk.__file__).parent / "tools.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["openai"] == openai_tools()
    assert payload["mcp"] == mcp_tools()


def test_handle_tool_check_gate_boundary():
    assert handle_tool("check_gate", {"confidence": 0.69})["gate"] == \
        "PRUNE-CANDIDATE"
    assert handle_tool("check_gate", {"confidence": 0.70})["gate"] == "KEEP"


def test_handle_tool_list_personas():
    result = handle_tool("list_personas", {})
    assert len(result["personas"]) >= 8


def test_handle_tool_run_and_score(tmp_path):
    ledger = tmp_path / "mcp-ledger.jsonl"
    result = handle_tool(
        "run_swarm",
        {"asset": "NVDA", "signals": {"momentum": 0.8},
         "headlines": ["Company beats estimates"]},
        ledger_path=ledger,
    )
    assert result["verdict"]["asset"] == "NVDA"
    assert result["ledger_id"]
    scored = handle_tool(
        "score_outcome",
        {"ledger_id": result["ledger_id"], "outcome": 0.03},
        ledger_path=ledger,
    )
    assert scored["scored"] is True
    assert scored["entry"]["outcome"] == 0.03


def test_handle_tool_unknown():
    assert "error" in handle_tool("nope", {})
