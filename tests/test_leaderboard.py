"""Leaderboard tests: persona track record + the mimic bar."""

from swarm_desk.leaderboard import (
    MIN_HIT_RATE,
    MIN_SCORED,
    NO_LEADER_MESSAGE,
    mimic_status,
    persona_leaderboard,
)


def _entry(asset, stances, outcome=None, source="live-test-x"):
    return {
        "asset": asset,
        "inputs": {"source": source},
        "verdict": {"stances": [
            {"persona": p, "display": d, "final_stance": s, "confidence": c}
            for p, d, s, c in stances
        ]},
        "outcome": outcome,
    }


def test_unscored_board_is_provisional():
    entries = [
        _entry("NVDA", [("bull", "Bull", 0.8, 0.9), ("bear", "Bear", -0.5, 0.6)]),
        _entry("PG", [("bull", "Bull", 0.4, 0.7), ("bear", "Bear", -0.2, 0.5)]),
    ]
    board = persona_leaderboard(entries)
    assert {r["persona"] for r in board} == {"bull", "bear"}
    for row in board:
        assert row["predictions"] == 2
        assert row["scored"] == 0
        assert row["hit_rate"] is None
        assert row["status"] == "UNSCORED"
    bull = next(r for r in board if r["persona"] == "bull")
    assert abs(bull["avg_confidence"] - 0.8) < 1e-9
    status = mimic_status(board)
    assert status["leader"] is None
    assert status["message"] == NO_LEADER_MESSAGE


def test_source_filter_excludes_demo():
    entries = [
        _entry("NVDA", [("bull", "Bull", 0.8, 0.9)], source="demo"),
        _entry("PG", [("bull", "Bull", 0.4, 0.7)], source="live-test-x"),
    ]
    board = persona_leaderboard(entries, sources={"live-test-x"})
    assert board[0]["predictions"] == 1


def test_hits_and_misses_from_numeric_outcome():
    entries = [
        _entry("NVDA", [("bull", "Bull", 0.8, 0.9), ("bear", "Bear", -0.5, 0.6)],
               outcome=0.04),   # asset rose: bull hit, bear miss
        _entry("PG", [("bull", "Bull", 0.4, 0.7), ("bear", "Bear", -0.2, 0.5)],
               outcome=-0.01),  # asset fell: bull miss, bear hit
        _entry("V", [("bull", "Bull", 0.0, 0.3), ("bear", "Bear", -0.3, 0.5)],
               outcome=0.02),   # flat stance: neither scored for bull
    ]
    board = {r["persona"]: r for r in persona_leaderboard(entries)}
    assert board["bull"]["scored"] == 2 and board["bull"]["hits"] == 1
    assert board["bull"]["hit_rate"] == 0.5
    assert board["bear"]["scored"] == 3 and board["bear"]["hits"] == 1
    assert board["bull"]["status"] == "SCORED"


def test_outcome_dict_forms():
    entries = [
        _entry("NVDA", [("bull", "Bull", 0.8, 0.9)], outcome={"return": -0.03}),
        _entry("PG", [("bull", "Bull", 0.8, 0.9)], outcome={"direction": "up"}),
    ]
    board = persona_leaderboard(entries)
    assert board[0]["scored"] == 2 and board[0]["hits"] == 1


def test_mimic_bar_requires_scored_and_hit_rate():
    row = {"persona": "bull", "display": "Bull", "predictions": 99,
           "scored": MIN_SCORED, "hits": MIN_SCORED,
           "hit_rate": 1.0, "avg_confidence": 0.9, "status": "SCORED"}
    weak = dict(row, persona="bear", display="Bear", hit_rate=0.5)
    status = mimic_status([row, weak])
    assert status["leader"] == "bull"
    assert mimic_status([weak])["leader"] is None
    thin = dict(row, scored=MIN_SCORED - 1)
    assert mimic_status([thin])["leader"] is None
    assert MIN_HIT_RATE == 0.60
