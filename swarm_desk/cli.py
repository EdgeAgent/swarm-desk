"""Swarm Desk command line.

    swarm-desk demo                          full 12-asset universe demo
    swarm-desk run --asset NVDA ...          one asset, your signals
    swarm-desk serve --port 8799             HTTP API (stdlib only)
    swarm-desk mcp                           MCP server (needs the
                                             optional mcp package)

Also runnable as `python -m swarm_desk ...`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .engine import run_swarm
from .ledger import default_ledger_path, log_run

UNIVERSE = ("NVDA", "AMZN", "TSLA", "MSFT", "META", "GOOGL",
            "AAPL", "JPM", "V", "XOM", "JNJ", "PG")


def _samples_path() -> Path:
    return (Path(__file__).resolve().parent.parent
            / "examples" / "sample_signals.json")


def load_samples() -> dict:
    return json.loads(_samples_path().read_text(encoding="utf-8"))


def _print_table(rows: list[dict]) -> None:
    header = (f"{'Asset':<7}{'Stance':>8}{'Bull%':>7}{'Bear%':>7}"
              f"{'Conf':>7}  {'Verdict':<13}Gate")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['asset']:<7}{r['mean_stance']:>+8.2f}"
              f"{r['bullish_share']:>7.0%}{r['bearish_share']:>7.0%}"
              f"{r['confidence']:>7.2f}  {r['label']:<13}{r['gate']}")


def cmd_demo(args) -> int:
    samples = load_samples()
    ledger = args.ledger or default_ledger_path()
    rows = []
    for asset in UNIVERSE:
        spec = samples[asset]
        verdict = run_swarm(asset, signals=spec.get("signals"),
                            headlines=spec.get("headlines"),
                            rounds=args.rounds, seed=args.seed,
                            use_llm=args.llm)
        log_run(verdict, inputs_summary={
            "signals": spec.get("signals") or {},
            "headlines": spec.get("headlines") or [],
            "source": "demo",
        }, path=ledger)
        rows.append(verdict.to_dict())
    _print_table(rows)
    keeps = sum(1 for r in rows if r["gate"] == "KEEP")
    print(f"\n{keeps} KEEP / {len(rows) - keeps} PRUNE-CANDIDATE "
          f"at the 0.70 gate.")
    print(f"Ledger: {ledger} ({len(rows)} entries appended)")
    return 0


def cmd_run(args) -> int:
    signals = {
        "momentum": args.momentum,
        "volatility": args.volatility,
        "value": args.value,
        "sentiment": args.sentiment,
    }
    headlines = list(args.headlines or [])
    verdict = run_swarm(args.asset, signals=signals, headlines=headlines,
                        rounds=args.rounds, seed=args.seed, use_llm=args.llm)
    ledger = args.ledger or default_ledger_path()
    entry = log_run(verdict, inputs_summary={
        "signals": signals, "headlines": headlines, "source": "cli",
    }, path=ledger)
    d = verdict.to_dict()
    print(f"{d['asset']}: {d['label']}  stance {d['mean_stance']:+.2f}  "
          f"bull {d['bullish_share']:.0%} / bear {d['bearish_share']:.0%}  "
          f"confidence {d['confidence']:.2f}  ->  {d['gate']}")
    print(f"Headline score: {d['headline_score']:+.2f}")
    for s in d["stances"]:
        print(f"  {s['display']:<26} r1 {s['round1_stance']:+.2f} -> "
              f"final {s['final_stance']:+.2f}   {s['rationale']}")
    print(f"Ledger entry: {entry['id']} -> {ledger}")
    return 0


def cmd_serve(args) -> int:
    from .api import serve

    return serve(port=args.port, host=args.host, ledger_path=args.ledger)


def cmd_mcp(args) -> int:
    from .mcp_server import main as mcp_main

    return mcp_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm-desk",
        description="Swarm Desk - swarm-sentiment engine for the "
                    "H-QRD Trading Desk (paper/research only).")
    parser.add_argument("--version", action="version",
                        version=f"swarm-desk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="run the 12-asset universe demo")
    p_demo.add_argument("--seed", type=int, default=42)
    p_demo.add_argument("--rounds", type=int, default=2)
    p_demo.add_argument("--ledger", default=None,
                        help="ledger path (default: data/ledger.jsonl)")
    p_demo.add_argument("--llm", action="store_true",
                        help="blend in the optional LLM headline read "
                             "(needs SWARM_LLM_* env vars)")
    p_demo.set_defaults(func=cmd_demo)

    p_run = sub.add_parser("run", help="run the swarm on one asset")
    p_run.add_argument("--asset", required=True)
    p_run.add_argument("--momentum", type=float, default=0.0)
    p_run.add_argument("--volatility", type=float, default=0.5)
    p_run.add_argument("--value", type=float, default=0.0)
    p_run.add_argument("--sentiment", type=float, default=0.0)
    p_run.add_argument("--headlines", nargs="*", default=[])
    p_run.add_argument("--seed", type=int, default=42)
    p_run.add_argument("--rounds", type=int, default=2)
    p_run.add_argument("--ledger", default=None)
    p_run.add_argument("--llm", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_serve = sub.add_parser("serve", help="run the HTTP API server")
    p_serve.add_argument("--port", type=int, default=8799)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--ledger", default=None)
    p_serve.set_defaults(func=cmd_serve)

    p_mcp = sub.add_parser("mcp", help="run the MCP server (stdio)")
    p_mcp.set_defaults(func=cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
