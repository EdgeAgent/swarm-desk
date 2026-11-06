#!/usr/bin/env bash
# Swarm Desk one-command setup (Linux / macOS).
#
#   ./setup.sh
#
# Creates .venv, installs Swarm Desk with its MCP door from this tree,
# verifies the install, runs the test suite when pytest is available,
# and finishes with the 12-asset demo. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

# --- 1. Find a Python new enough (the package needs >= 3.12) ----------
PY=""
for cand in python3.12 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
    echo "ERROR: no Python found on PATH." >&2
    echo "Swarm Desk needs Python 3.12 or newer - install it, then re-run ./setup.sh" >&2
    exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "ERROR: found $("$PY" --version 2>&1), but Swarm Desk needs Python 3.12 or newer." >&2
    echo "Install Python 3.12+ and re-run ./setup.sh" >&2
    exit 1
fi
echo "==> Using $("$PY" --version 2>&1) ($PY)"

# --- 2. Virtualenv (idempotent) ---------------------------------------
if [ ! -x .venv/bin/python ]; then
    echo "==> Creating .venv"
    "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- 3. Install Swarm Desk + the MCP extra from this tree -------------
echo "==> Installing swarm-desk[mcp] from this checkout"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e ".[mcp]"

# --- 4. Verify ---------------------------------------------------------
echo "==> Installed: $(swarm-desk --version)"

# --- 5. Tests when pytest is available (best effort) ------------------
if python -m pytest --version >/dev/null 2>&1 || python -m pip install -q pytest >/dev/null 2>&1; then
    echo "==> Running the test suite"
    python -m pytest tests -q
else
    echo "NOTE: pytest is not available - skipped the test suite."
    echo "      (Optional: pip install pytest, then: python -m pytest tests -q)"
fi

# --- 6. Demo ------------------------------------------------------------
echo "==> Running the demo (12-asset universe, sample data)"
swarm-desk demo

cat <<'EOF'

Done. Swarm Desk is ready - the demo runs above are now in the
experiment ledger (data/ledger.jsonl), which is how predictions earn a
track record.

Next steps:
  swarm-desk run --asset NVDA --momentum 0.8 --volatility 0.3 \
      --headlines "Chipmaker beats estimates as AI demand surges"
  swarm-desk serve --port 8799     # HTTP API
  swarm-desk mcp                   # MCP server (stdio) for agent hosts

Full guide: QUICKSTART.md   Worked agent examples: examples/README.md
EOF
