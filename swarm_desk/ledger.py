"""Experiment ledger: every swarm run is written down, REA-style.

One JSON object per line (JSONL). Each entry records the timestamp, the
asset, a summary of the inputs, the full verdict, and the gate result.
Outcome fields start as null and are filled in later by score_outcome()
once reality has had its say - that is the whole point of the ledger:
a signal earns trust only from its scored track record, failures
included. Nothing is ever deleted; scoring rewrites the entry in place
with the outcome attached.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def default_ledger_path() -> Path:
    """$SWARM_DESK_LEDGER, or data/ledger.jsonl under the current dir."""
    env = os.environ.get("SWARM_DESK_LEDGER")
    if env:
        return Path(env)
    return Path("data") / "ledger.jsonl"


def _resolve(path: str | Path | None) -> Path:
    return Path(path) if path is not None else default_ledger_path()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_entry(entry: dict, path: str | Path | None = None) -> Path:
    """Append one entry (a dict) to the ledger; returns the ledger path."""
    ledger = _resolve(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return ledger


def read_entries(path: str | Path | None = None) -> list[dict]:
    """Read all entries; a missing ledger reads as an empty list."""
    ledger = _resolve(path)
    if not ledger.exists():
        return []
    entries = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def log_run(verdict, inputs_summary: dict | None = None,
            path: str | Path | None = None) -> dict:
    """Build a ledger entry from a SwarmVerdict and append it.

    Returns the entry (which includes its unique "id", used later by
    score_outcome).
    """
    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": utc_now_iso(),
        "asset": verdict.asset,
        "inputs": inputs_summary or {},
        "verdict": verdict.to_dict(),
        "gate": verdict.gate,
        "outcome": None,
        "outcome_scored_at": None,
    }
    append_entry(entry, path)
    return entry


def score_outcome(outcome, path: str | Path | None = None,
                  entry_id: str | None = None, timestamp: str | None = None,
                  asset: str | None = None) -> dict | None:
    """Attach a realized outcome to a past entry and return the entry.

    The entry is found by entry_id, or by the (timestamp, asset) pair.
    Returns None when nothing matches. The ledger file is rewritten with
    the outcome filled in; every other entry is preserved verbatim.
    """
    ledger = _resolve(path)
    entries = read_entries(ledger)
    match = None
    for entry in entries:
        if entry_id is not None and entry.get("id") == entry_id:
            match = entry
            break
        if (timestamp is not None and asset is not None
                and entry.get("timestamp") == timestamp
                and entry.get("asset") == asset.upper()):
            match = entry
            break
    if match is None:
        return None
    match["outcome"] = outcome
    match["outcome_scored_at"] = utc_now_iso()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")
    return match
