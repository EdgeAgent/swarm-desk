"""Swarm Desk - a swarm-sentiment engine for the H-QRD Trading Desk.

A small swarm of persona agents debates one asset over two rounds and the
engine aggregates the debate into a single confidence number in 0..1,
mapped onto the H-QRD Agent 02 prune gate (confidence >= 0.70 keeps the
asset, anything below is a prune candidate).

Offline-first: the default engine is deterministic signal rules and needs
no API keys, no network, and nothing beyond the Python standard library.
"""

from .engine import SwarmVerdict, gate_for, run_swarm
from .personas import PERSONAS

__version__ = "0.1.1"

__all__ = ["PERSONAS", "SwarmVerdict", "gate_for", "run_swarm", "__version__"]
