"""Engine tests: determinism, aggregation math, gate mapping, debate."""

from swarm_desk.engine import (
    aggregate,
    debate_shift,
    gate_for,
    headline_score,
    headlines_score,
    run_swarm,
)
from swarm_desk.personas import PERSONAS

BULLISH = {"momentum": 0.9, "volatility": 0.2, "value": 0.3, "sentiment": 0.8}
BULLISH_HEADLINES = ["Company beats estimates as growth surges"]


def test_persona_determinism_same_seed_same_verdict():
    v1 = run_swarm("NVDA", BULLISH, BULLISH_HEADLINES, seed=7)
    v2 = run_swarm("NVDA", BULLISH, BULLISH_HEADLINES, seed=7)
    assert v1.to_dict() == v2.to_dict()


def test_personas_roster():
    assert len(PERSONAS) >= 8
    names = [p.name for p in PERSONAS]
    assert len(names) == len(set(names))
    for p in PERSONAS:
        assert p.style  # every persona documents its reasoning style
        assert p.weights


def test_aggregation_unanimous_strong():
    agg = aggregate([1.0, 1.0, 1.0, 1.0])
    assert agg.mean_stance == 1.0
    assert agg.bullish_share == 1.0
    assert agg.confidence == 1.0


def test_aggregation_perfectly_split_is_zero_confidence():
    agg = aggregate([1.0, -1.0, 1.0, -1.0])
    assert agg.mean_stance == 0.0
    assert agg.majority_conviction == 0.0
    assert agg.consensus == 0.0
    assert agg.confidence == 0.0


def test_aggregation_known_values():
    agg = aggregate([0.5, 0.5])
    # M = 0.5, A = 1.0 -> 0.65*0.5 + 0.35*1.0 = 0.675
    assert agg.confidence == 0.675


def test_gate_boundary():
    assert gate_for(0.69) == "PRUNE-CANDIDATE"
    assert gate_for(0.70) == "KEEP"
    assert gate_for(0.71) == "KEEP"
    assert gate_for(0.0) == "PRUNE-CANDIDATE"
    assert gate_for(1.0) == "KEEP"


def test_headline_scoring():
    assert headline_score("Company beats estimates as shares surge") > 0.3
    assert headline_score("Shares plunge after downgrade and lawsuit") < -0.3
    assert headline_score("Company holds its annual meeting") == 0.0
    assert headlines_score([]) == 0.0


def test_contrarian_shifts_against_consensus():
    # Consensus is bullish (+0.8); the contrarian's herd coefficient is
    # negative, so the debate shift must push his stance DOWN, away.
    contrarian = next(p for p in PERSONAS if p.name == "contrarian")
    assert contrarian.herd < 0
    moved = debate_shift(0.2, 0.8, contrarian.herd)
    assert moved < 0.2


def test_herder_shifts_toward_consensus():
    herder = next(p for p in PERSONAS
                  if p.name == "retail_sentiment_watcher")
    assert herder.herd > 0
    moved = debate_shift(0.2, 0.8, herder.herd)
    assert 0.2 < moved < 0.8


def test_contrarian_moves_against_in_full_run():
    verdict = run_swarm("NVDA", BULLISH, BULLISH_HEADLINES, seed=42)
    contrarian = next(s for s in verdict.stances
                      if s.persona == "contrarian")
    # Bullish swarm: the contrarian's final stance is at or below his
    # Round-1 stance - the debate pushed him against the crowd.
    assert contrarian.final_stance <= contrarian.round1_stance


def test_verdict_bounds_and_gate_consistency():
    verdict = run_swarm("TSLA", {"momentum": 0.7, "volatility": 0.8,
                                 "value": -0.5, "sentiment": 0.3},
                        ["Deliveries beat estimates",
                         "Shares plunge on margin warning"], seed=3)
    assert -1.0 <= verdict.mean_stance <= 1.0
    assert 0.0 <= verdict.confidence <= 1.0
    for s in verdict.stances:
        assert -1.0 <= s.final_stance <= 1.0
        assert 0.0 <= s.confidence <= 1.0
    assert verdict.gate == gate_for(verdict.confidence)
