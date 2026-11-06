"""Agent personas for Swarm Desk.

Each persona is a small, fully documented reasoning style: a set of weights
over the five engine features, a standing bias, a noise scale, and a herd
coefficient that controls how the persona reacts to the Round-1 consensus
during the Round-2 debate.

Feature keys (see engine.build_features):
    momentum   trend strength, -1..+1
    calm       1 - 2 * volatility, so calm markets score positive
    value      valuation signal, -1 (expensive) .. +1 (undervalued)
    sentiment  broad market sentiment, -1..+1
    headlines  aggregated headline keyword score, -1..+1

Herd coefficient sign convention (Round 2):
    herd > 0   the persona shifts toward the swarm mean (herder / follower)
    herd < 0   the persona shifts away from the swarm mean (contrarian)
    herd = 0   the persona ignores the crowd entirely
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    """One swarm agent archetype."""

    name: str
    display: str
    style: str  # human-readable description of the reasoning style
    weights: dict  # feature -> weight
    bias: float  # standing tilt added to every stance, -1..+1
    noise_scale: float  # std-dev of the seeded noise on this persona's stance
    herd: float  # Round-2 consensus coefficient (see module docstring)


PERSONAS: tuple[Persona, ...] = (
    Persona(
        name="bull_analyst",
        display="Bull Analyst",
        style=(
            "Sell-side optimist. Reads momentum, sentiment and headlines as "
            "confirmation that the story is working; carries a standing "
            "positive bias and leans with the crowd when it agrees with him."
        ),
        weights={"momentum": 0.30, "calm": 0.05, "value": 0.10,
                 "sentiment": 0.25, "headlines": 0.30},
        bias=0.22,
        noise_scale=0.08,
        herd=0.15,
    ),
    Persona(
        name="bear_analyst",
        display="Bear Analyst",
        style=(
            "Sell-side sceptic. Uses the exact same lens as the bull analyst "
            "but carries a standing negative bias: the same evidence reads "
            "as a reason to stay cautious. Herds mildly with consensus."
        ),
        weights={"momentum": 0.30, "calm": 0.05, "value": 0.10,
                 "sentiment": 0.25, "headlines": 0.30},
        bias=-0.22,
        noise_scale=0.08,
        herd=0.10,
    ),
    Persona(
        name="momentum_trader",
        display="Momentum Trader",
        style=(
            "Trend follower. Momentum dominates everything; slightly "
            "penalises turbulent (low-calm) tapes. In debate he is a strong "
            "herder - if the swarm confirms the trend, he presses it."
        ),
        weights={"momentum": 0.65, "calm": -0.10, "value": 0.00,
                 "sentiment": 0.15, "headlines": 0.20},
        bias=0.00,
        noise_scale=0.12,
        herd=0.35,
    ),
    Persona(
        name="value_investor",
        display="Value Investor",
        style=(
            "Price-versus-worth investor. Valuation dominates; momentum is "
            "nearly ignored and calm tapes are mildly preferred. Slightly "
            "contrarian in debate - crowd excitement does not move him."
        ),
        weights={"momentum": 0.05, "calm": 0.15, "value": 0.65,
                 "sentiment": 0.00, "headlines": 0.15},
        bias=0.04,
        noise_scale=0.05,
        herd=-0.10,
    ),
    Persona(
        name="risk_manager",
        display="Risk Manager",
        style=(
            "Capital-preservation first. The calm feature dominates: a "
            "volatile tape is a negative stance almost regardless of the "
            "story. Small standing negative bias, very low noise."
        ),
        weights={"momentum": 0.10, "calm": 0.55, "value": 0.10,
                 "sentiment": 0.05, "headlines": 0.05},
        bias=-0.08,
        noise_scale=0.04,
        herd=0.05,
    ),
    Persona(
        name="retail_sentiment_watcher",
        display="Retail Sentiment Watcher",
        style=(
            "Tracks the crowd itself: broad sentiment and headline tone "
            "dominate. The noisiest persona in the swarm and the strongest "
            "herder - in debate he moves hard toward whatever the swarm "
            "already believes."
        ),
        weights={"momentum": 0.10, "calm": 0.00, "value": 0.00,
                 "sentiment": 0.55, "headlines": 0.35},
        bias=0.08,
        noise_scale=0.18,
        herd=0.50,
    ),
    Persona(
        name="contrarian",
        display="Contrarian",
        style=(
            "Fades the crowd. Momentum, sentiment and headlines enter with "
            "negative weights - strong trends and euphoric coverage push "
            "him the other way. In debate he shifts against consensus more "
            "than anyone else in the swarm."
        ),
        weights={"momentum": -0.30, "calm": 0.10, "value": 0.25,
                 "sentiment": -0.30, "headlines": -0.10},
        bias=0.00,
        noise_scale=0.10,
        herd=-0.60,
    ),
    Persona(
        name="news_hawk",
        display="News Hawk",
        style=(
            "Headline-driven. The aggregated headline score is almost the "
            "whole decision; everything else is garnish. Moderate herder - "
            "a swarm that agrees with the news flow reinforces him."
        ),
        weights={"momentum": 0.05, "calm": 0.00, "value": 0.00,
                 "sentiment": 0.15, "headlines": 0.80},
        bias=0.00,
        noise_scale=0.10,
        herd=0.20,
    ),
    Persona(
        name="quant_statistician",
        display="Quant Statistician",
        style=(
            "Balanced model. Spreads weight evenly across momentum, calm "
            "and value with small sentiment/headline terms, carries no "
            "bias, has the lowest noise in the swarm, and ignores the "
            "crowd completely in debate (herd = 0)."
        ),
        weights={"momentum": 0.25, "calm": 0.25, "value": 0.25,
                 "sentiment": 0.10, "headlines": 0.15},
        bias=0.00,
        noise_scale=0.03,
        herd=0.00,
    ),
)

PERSONA_BY_NAME = {p.name: p for p in PERSONAS}

FEATURE_KEYS = ("momentum", "calm", "value", "sentiment", "headlines")
