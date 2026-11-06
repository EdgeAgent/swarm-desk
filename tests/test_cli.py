"""CLI tests: demo smoke (12 rows out) and argument parsing."""

from swarm_desk.cli import UNIVERSE, build_parser, main


def test_demo_smoke_twelve_rows(tmp_path, capsys):
    ledger = tmp_path / "demo-ledger.jsonl"
    rc = main(["demo", "--ledger", str(ledger)])
    assert rc == 0
    out = capsys.readouterr().out
    for asset in UNIVERSE:
        assert asset in out
    assert len(UNIVERSE) == 12
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 12


def test_run_command(tmp_path, capsys):
    ledger = tmp_path / "run-ledger.jsonl"
    rc = main(["run", "--asset", "NVDA", "--momentum", "0.8",
               "--volatility", "0.3", "--ledger", str(ledger),
               "--headlines", "Chipmaker beats estimates"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "NVDA" in out
    assert ledger.exists()


def test_serve_and_mcp_argument_parsing():
    parser = build_parser()
    args = parser.parse_args(["serve", "--port", "8799"])
    assert args.command == "serve"
    assert args.port == 8799
    args = parser.parse_args(["serve"])
    assert args.port == 8799  # documented default
    args = parser.parse_args(["mcp"])
    assert args.command == "mcp"
    args = parser.parse_args(["demo"])
    assert args.command == "demo"
