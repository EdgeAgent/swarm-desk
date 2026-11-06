"""OPTIONAL LLM headline read. Nothing in Swarm Desk requires this.

When (and only when) all three environment variables are set, the engine
can blend its deterministic keyword headline score with a model read of
the headlines:

    SWARM_LLM_API_KEY    API key for any OpenAI-compatible endpoint
    SWARM_LLM_BASE_URL   e.g. https://openrouter.ai/api/v1
    SWARM_LLM_MODEL      e.g. a model id the endpoint serves

Any failure - missing config, network error, bad response - returns
None and the engine falls back to the pure keyword score. Tests never
call this module's network path.
"""

from __future__ import annotations

import json
import os
import urllib.request


def llm_configured() -> bool:
    return all(os.environ.get(k) for k in (
        "SWARM_LLM_API_KEY", "SWARM_LLM_BASE_URL", "SWARM_LLM_MODEL"))


def llm_headline_score(headlines: list[str]) -> float | None:
    """Ask the configured model for a -1..+1 sentiment read, or None."""
    if not headlines or not llm_configured():
        return None
    prompt = (
        "Rate the overall market sentiment of these headlines for the "
        "asset they describe. Reply with ONLY a JSON object like "
        '{"score": 0.5} where score is between -1 (very bearish) and '
        "1 (very bullish).\n\n" + "\n".join(f"- {h}" for h in headlines)
    )
    body = json.dumps({
        "model": os.environ["SWARM_LLM_MODEL"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(
        os.environ["SWARM_LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['SWARM_LLM_API_KEY']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
        score = float(json.loads(text)["score"])
    except Exception:
        return None
    return min(max(score, -1.0), 1.0)
