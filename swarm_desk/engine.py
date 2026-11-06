"""Swarm Desk engine: two-round persona debate -> one confidence number.

The maths implemented here is documented, formula for formula, in
docs/MATH.md. In short:

  Round 1   every persona forms a stance from a weighted sum of signal
            features, plus its standing bias, plus seeded noise.
  Round 2   every persona sees the Round-1 swarm mean and shifts by its
            herd coefficient (herders toward consensus, contrarians
            against it), plus a smaller dose of seeded noise.
  Aggregate the final stances become a mean stance, a bullish/bearish
            split, and a confidence in 0..1 built from majority-side
            conviction and directional consensus.
  Gate      confidence >= 0.70 -> "KEEP", otherwise "PRUNE-CANDIDATE".
            That is the exact feed H-QRD Agent 02 consumes.

Everything is deterministic for a given (asset, signals, headlines,
rounds, seed) tuple: the noise comes from a random.Random seeded with a
string, never from the global RNG.
"""

from __future__ import annotations

import random
import re
import statistics
from dataclasses import dataclass, field

from .personas import FEATURE_KEYS, PERSONAS, Persona

GATE_THRESHOLD = 0.70
KEEP = "KEEP"
PRUNE = "PRUNE-CANDIDATE"

# ---------------------------------------------------------------------------
# Headline keyword scoring
# ---------------------------------------------------------------------------

POSITIVE_KEYWORDS = frozenset({
    "approval", "beat", "beats", "breakthrough", "bullish", "dividend",
    "exceed", "exceeds", "gain", "gains", "growth", "profit", "profits",
    "raise", "raises", "raised", "rally", "rallies", "record", "soar",
    "soars", "strong", "surge", "surges", "tops", "upgrade", "upgraded",
    "win", "wins",
})

NEGATIVE_KEYWORDS = frozenset({
    "bearish", "cut", "cuts", "downgrade", "downgraded", "drop", "drops",
    "fall", "falls", "fraud", "lawsuit", "layoffs", "loss", "losses",
    "miss", "misses", "plunge", "plunges", "probe", "recall", "slowdown",
    "slows", "slump", "warning", "weak",
})

_TOKEN_RE = re.compile(r"[a-z']+")


def headline_score(text: str) -> float:
    """Score one headline in -1..+1 from keyword hits.

    score = (P - N) / (P + N) where P and N are the counts of positive and
    negative keyword tokens. A headline with no keyword hits scores 0.0.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    pos = sum(1 for t in tokens if t in POSITIVE_KEYWORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_KEYWORDS)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def headlines_score(headlines: list[str]) -> float:
    """Mean headline score over a list; empty list -> 0.0."""
    if not headlines:
        return 0.0
    return sum(headline_score(h) for h in headlines) / len(headlines)


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

def build_features(signals: dict | None, headlines: list[str],
                   use_llm: bool = False) -> dict:
    """Turn raw inputs into the five model features, each in -1..+1.

    signals keys (all optional): momentum (-1..+1), volatility (0..1),
    value (-1..+1), sentiment (-1..+1). The volatility input is converted
    to the "calm" feature: calm = 1 - 2 * volatility.
    """
    signals = signals or {}
    momentum = _clip(float(signals.get("momentum", 0.0)))
    volatility = min(max(float(signals.get("volatility", 0.5)), 0.0), 1.0)
    value = _clip(float(signals.get("value", 0.0)))
    sentiment = _clip(float(signals.get("sentiment", 0.0)))
    head = headlines_score(headlines)
    if use_llm:
        # Optional mode: blend the keyword score with an LLM headline
        # read when (and only when) an endpoint is configured. Offline
        # or unconfigured, this silently stays the pure keyword score.
        from .llm import llm_headline_score

        llm_score = llm_headline_score(headlines)
        if llm_score is not None:
            head = 0.5 * head + 0.5 * llm_score
    return {
        "momentum": momentum,
        "calm": 1.0 - 2.0 * volatility,
        "value": value,
        "sentiment": sentiment,
        "headlines": head,
    }


# ---------------------------------------------------------------------------
# Debate mechanics
# ---------------------------------------------------------------------------

def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return min(max(x, lo), hi)


def _initial_stance(persona: Persona, features: dict,
                    rng: random.Random) -> tuple[float, str]:
    """Round-1 stance: weighted feature sum + bias + seeded noise."""
    contributions = {
        k: persona.weights.get(k, 0.0) * features[k] for k in FEATURE_KEYS
    }
    base = sum(contributions.values()) + persona.bias
    stance = _clip(base + rng.gauss(0.0, persona.noise_scale))
    dominant = max(contributions, key=lambda k: abs(contributions[k]))
    rationale = (
        f"{dominant} {features[dominant]:+.2f} (w {persona.weights.get(dominant, 0.0):+.2f}) "
        f"dominates; bias {persona.bias:+.2f} -> stance {stance:+.2f}"
    )
    return stance, rationale


def debate_shift(stance: float, swarm_mean: float, herd: float) -> float:
    """One persona's Round-2 move: stance + herd * (mean - stance), clipped.

    herd > 0 moves toward the consensus, herd < 0 moves away from it,
    herd = 0 stays put.
    """
    return _clip(stance + herd * (swarm_mean - stance))


def persona_confidence(stance: float) -> float:
    """A persona's confidence in its own stance: 0.30 + 0.70 * |stance|."""
    return min(max(0.30 + 0.70 * abs(stance), 0.0), 1.0)


# ---------------------------------------------------------------------------
# Aggregation and the gate
# ---------------------------------------------------------------------------

@dataclass
class Aggregation:
    mean_stance: float
    bullish_share: float
    bearish_share: float
    majority_conviction: float  # M in docs/MATH.md
    consensus: float            # A in docs/MATH.md
    dispersion: float           # population stdev, reported for transparency
    confidence: float


def aggregate(stances: list[float]) -> Aggregation:
    """Aggregate final stances into the swarm confidence.

    M (majority conviction) = mean of the stances on the majority side,
    signed toward that side (0 when the mean is exactly 0).
    A (consensus) = |bullish share - bearish share|.
    confidence = clip(0.65 * M + 0.35 * A, 0, 1).
    """
    if not stances:
        raise ValueError("aggregate() needs at least one stance")
    n = len(stances)
    mean = sum(stances) / n
    bulls = [s for s in stances if s > 0]
    bears = [s for s in stances if s < 0]
    bullish_share = len(bulls) / n
    bearish_share = len(bears) / n
    if mean > 0:
        majority = sum(bulls) / len(bulls) if bulls else 0.0
    elif mean < 0:
        majority = -(sum(bears) / len(bears)) if bears else 0.0
    else:
        majority = 0.0
    consensus = abs(bullish_share - bearish_share)
    confidence = min(max(0.65 * majority + 0.35 * consensus, 0.0), 1.0)
    dispersion = statistics.pstdev(stances) if n > 1 else 0.0
    return Aggregation(
        mean_stance=mean,
        bullish_share=bullish_share,
        bearish_share=bearish_share,
        majority_conviction=majority,
        consensus=consensus,
        dispersion=dispersion,
        confidence=confidence,
    )


def gate_for(confidence: float) -> str:
    """The H-QRD Agent 02 mapping: >= 0.70 keeps, below prunes."""
    return KEEP if confidence >= GATE_THRESHOLD else PRUNE


def label_for(mean_stance: float) -> str:
    if mean_stance >= 0.35:
        return "BULLISH"
    if mean_stance >= 0.10:
        return "LEAN BULLISH"
    if mean_stance <= -0.35:
        return "BEARISH"
    if mean_stance <= -0.10:
        return "LEAN BEARISH"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

@dataclass
class PersonaStance:
    persona: str
    display: str
    round1_stance: float
    final_stance: float
    confidence: float
    rationale: str

    def to_dict(self) -> dict:
        return {
            "persona": self.persona,
            "display": self.display,
            "round1_stance": round(self.round1_stance, 4),
            "final_stance": round(self.final_stance, 4),
            "confidence": round(self.confidence, 4),
            "rationale": self.rationale,
        }


@dataclass
class SwarmVerdict:
    asset: str
    mean_stance: float
    bullish_share: float
    bearish_share: float
    confidence: float
    label: str
    gate: str
    headline_score: float
    rounds: int
    seed: int
    stances: list[PersonaStance] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "mean_stance": round(self.mean_stance, 4),
            "bullish_share": round(self.bullish_share, 4),
            "bearish_share": round(self.bearish_share, 4),
            "confidence": round(self.confidence, 4),
            "label": self.label,
            "gate": self.gate,
            "gate_threshold": GATE_THRESHOLD,
            "headline_score": round(self.headline_score, 4),
            "rounds": self.rounds,
            "seed": self.seed,
            "stances": [s.to_dict() for s in self.stances],
        }


# ---------------------------------------------------------------------------
# The swarm run
# ---------------------------------------------------------------------------

def run_swarm(asset: str, signals: dict | None = None,
              headlines: list[str] | None = None, rounds: int = 2,
              seed: int = 42, use_llm: bool = False) -> SwarmVerdict:
    """Run the full debate for one asset and return the aggregated verdict.

    Deterministic: the same (asset, signals, headlines, rounds, seed)
    always produces the same verdict.
    """
    asset = asset.upper()
    headlines = list(headlines or [])
    features = build_features(signals, headlines, use_llm=use_llm)
    rng = random.Random(f"swarm-desk:{seed}:{asset}")

    rationales: dict[str, str] = {}
    current: dict[str, float] = {}
    round1: dict[str, float] = {}
    for persona in PERSONAS:
        stance, rationale = _initial_stance(persona, features, rng)
        round1[persona.name] = stance
        current[persona.name] = stance
        rationales[persona.name] = rationale

    for _ in range(max(0, rounds - 1)):
        swarm_mean = sum(current.values()) / len(current)
        nxt: dict[str, float] = {}
        for persona in PERSONAS:
            shifted = debate_shift(current[persona.name], swarm_mean,
                                   persona.herd)
            noise = rng.gauss(0.0, persona.noise_scale / 2.0)
            nxt[persona.name] = _clip(shifted + noise)
        current = nxt

    agg = aggregate([current[p.name] for p in PERSONAS])
    stances = [
        PersonaStance(
            persona=p.name,
            display=p.display,
            round1_stance=round1[p.name],
            final_stance=current[p.name],
            confidence=persona_confidence(current[p.name]),
            rationale=rationales[p.name],
        )
        for p in PERSONAS
    ]
    return SwarmVerdict(
        asset=asset,
        mean_stance=agg.mean_stance,
        bullish_share=agg.bullish_share,
        bearish_share=agg.bearish_share,
        confidence=agg.confidence,
        label=label_for(agg.mean_stance),
        gate=gate_for(agg.confidence),
        headline_score=features["headlines"],
        rounds=rounds,
        seed=seed,
        stances=stances,
    )
