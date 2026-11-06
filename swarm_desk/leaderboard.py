"""Signal Leaderboard — the desk's honest version of "mimic trading".

Ranks the swarm's personas by their LEDGER track record: predictions
made, outcomes scored, hit rate, average confidence. A persona's
prediction on one ledger entry is its final stance; once that entry's
outcome is scored, the persona scores a HIT when the sign of its stance
matches the realized direction (a flat stance, |stance| < 1e-9, never
counts as a hit or a miss — it made no directional call).

Outcome direction is read flexibly from whatever score_outcome() stored:
a dict with "direction" (+1/-1/"up"/"down") or "return" (signed number),
or a bare signed number / "up" / "down" string.

"Follow the proven leader" (paper-only display concept, never an
execution path): a persona becomes followable only with at least
MIN_SCORED scored predictions AND a hit rate of at least MIN_HIT_RATE.
Until some persona clears both bars the board says so plainly — the
ledger has to EARN a mimic signal. Nothing here touches a broker, a
real trader, or real money.
"""

from __future__ import annotations

MIN_SCORED = 10        # scored predictions before a persona can lead
MIN_HIT_RATE = 0.60    # hit-rate bar for "proven leader" status

NO_LEADER_MESSAGE = ("No proven leader yet — ledger has not earned a "
                     "mimic signal.")


def _outcome_direction(outcome) -> int | None:
    """+1 / -1 realized direction from a stored outcome, or None."""
    if outcome is None:
        return None
    if isinstance(outcome, (int, float)):
        return 1 if outcome > 0 else (-1 if outcome < 0 else None)
    if isinstance(outcome, str):
        o = outcome.strip().lower()
        if o in ("up", "positive", "bullish", "+1"):
            return 1
        if o in ("down", "negative", "bearish", "-1"):
            return -1
        return None
    if isinstance(outcome, dict):
        if "direction" in outcome:
            return _outcome_direction(outcome["direction"])
        if "return" in outcome:
            return _outcome_direction(outcome["return"])
    return None


def persona_leaderboard(entries: list[dict],
                        sources: set[str] | None = None) -> list[dict]:
    """Per-persona track record from ledger entries.

    sources: when given, only entries whose inputs.source is in the set
    are counted (e.g. {"live-test-2026-11-05"} for the frozen real-data
    experiment, excluding demo/cli runs from the track record).
    Rows are sorted by (scored, hit_rate, avg_confidence) descending —
    with nothing scored yet every row is UNSCORED/provisional and the
    order carries no claim of skill.
    """
    stats: dict[str, dict] = {}
    for entry in entries:
        if sources is not None:
            if (entry.get("inputs") or {}).get("source") not in sources:
                continue
        direction = _outcome_direction(entry.get("outcome"))
        for stance in (entry.get("verdict") or {}).get("stances") or []:
            row = stats.setdefault(stance["persona"], {
                "persona": stance["persona"],
                "display": stance.get("display", stance["persona"]),
                "predictions": 0, "scored": 0, "hits": 0,
                "conf_sum": 0.0,
            })
            row["predictions"] += 1
            row["conf_sum"] += float(stance.get("confidence") or 0.0)
            if direction is not None:
                s = float(stance.get("final_stance") or 0.0)
                if abs(s) > 1e-9:
                    row["scored"] += 1
                    if (s > 0) == (direction > 0):
                        row["hits"] += 1
    board = []
    for row in stats.values():
        scored = row["scored"]
        board.append({
            "persona": row["persona"],
            "display": row["display"],
            "predictions": row["predictions"],
            "scored": scored,
            "hits": row["hits"],
            "hit_rate": (row["hits"] / scored) if scored else None,
            "avg_confidence": (row["conf_sum"] / row["predictions"]
                               if row["predictions"] else 0.0),
            "status": "UNSCORED" if scored == 0 else "SCORED",
        })
    board.sort(key=lambda r: (r["scored"],
                              r["hit_rate"] if r["hit_rate"] is not None else -1.0,
                              r["avg_confidence"]),
               reverse=True)
    return board


def mimic_status(board: list[dict], min_scored: int = MIN_SCORED,
                 min_hit_rate: float = MIN_HIT_RATE) -> dict:
    """Would the desk follow anyone yet? Paper-only display verdict."""
    for row in board:
        if (row["scored"] >= min_scored and row["hit_rate"] is not None
                and row["hit_rate"] >= min_hit_rate):
            return {
                "leader": row["persona"],
                "display": row["display"],
                "message": (f"Proven leader (paper-only): {row['display']} — "
                            f"{row['hits']}/{row['scored']} hits "
                            f"({row['hit_rate']:.0%}) over >= {min_scored} "
                            "scored predictions. Following means weighting "
                            "this persona's stance in the paper desk only; "
                            "no auto-execution, no real money."),
            }
    return {"leader": None, "display": None, "message": NO_LEADER_MESSAGE}
