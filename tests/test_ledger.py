"""Ledger tests: append/read round-trip and outcome scoring."""

from swarm_desk.engine import run_swarm
from swarm_desk.ledger import (
    append_entry,
    log_run,
    read_entries,
    score_outcome,
)


def test_append_read_round_trip(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_entry({"id": "a", "asset": "NVDA", "outcome": None}, ledger)
    append_entry({"id": "b", "asset": "PG", "outcome": None}, ledger)
    entries = read_entries(ledger)
    assert [e["id"] for e in entries] == ["a", "b"]
    assert entries[0]["asset"] == "NVDA"


def test_missing_ledger_reads_empty(tmp_path):
    assert read_entries(tmp_path / "nope.jsonl") == []


def test_log_run_writes_null_outcome(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    verdict = run_swarm("NVDA", {"momentum": 0.5}, [], seed=1)
    entry = log_run(verdict, {"source": "test"}, path=ledger)
    assert entry["asset"] == "NVDA"
    assert entry["outcome"] is None
    assert entry["outcome_scored_at"] is None
    assert entry["gate"] == verdict.gate
    stored = read_entries(ledger)
    assert len(stored) == 1
    assert stored[0]["id"] == entry["id"]


def test_score_outcome_by_id(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    verdict = run_swarm("PG", {"momentum": 0.4}, [], seed=1)
    entry = log_run(verdict, {}, path=ledger)
    scored = score_outcome(0.05, path=ledger, entry_id=entry["id"])
    assert scored is not None
    assert scored["outcome"] == 0.05
    assert scored["outcome_scored_at"] is not None
    # And it persists on disk.
    assert read_entries(ledger)[0]["outcome"] == 0.05


def test_score_outcome_by_timestamp_and_asset(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    verdict = run_swarm("V", {"momentum": 0.1}, [], seed=1)
    entry = log_run(verdict, {}, path=ledger)
    scored = score_outcome(-0.02, path=ledger,
                           timestamp=entry["timestamp"], asset="V")
    assert scored is not None
    assert scored["outcome"] == -0.02


def test_score_outcome_no_match_returns_none(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_entry({"id": "x", "asset": "NVDA"}, ledger)
    assert score_outcome(0.1, path=ledger, entry_id="missing") is None
