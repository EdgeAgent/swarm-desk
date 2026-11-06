# Swarm Desk one-command setup (Windows PowerShell).
#
#   .\setup.ps1
#
# Creates .venv, installs Swarm Desk with its MCP door from this tree,
# verifies the install, runs the test suite when pytest is available,
# and finishes with the 12-asset demo. Safe to re-run.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- 1. Find a Python new enough (the package needs >= 3.12) ----------
$python = $null
foreach ($cand in @("python", "py")) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $python = $cand; break }
}
if (-not $python) {
    Write-Error "No Python found on PATH. Swarm Desk needs Python 3.12 or newer - install it from python.org, then re-run .\setup.ps1"
    exit 1
}
& $python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Found an older Python, but Swarm Desk needs Python 3.12 or newer. Install Python 3.12+ and re-run .\setup.ps1"
    exit 1
}
Write-Host "==> Using $(& $python --version)"

# --- 2. Virtualenv (idempotent) ---------------------------------------
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "==> Creating .venv"
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create .venv"; exit 1 }
}
$venvPy = ".venv\Scripts\python.exe"
$swarmDesk = ".venv\Scripts\swarm-desk.exe"

# --- 3. Install Swarm Desk + the MCP extra from this tree -------------
Write-Host "==> Installing swarm-desk[mcp] from this checkout"
& $venvPy -m pip install --upgrade pip | Out-Null
& $venvPy -m pip install -e ".[mcp]"
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

# --- 4. Verify ---------------------------------------------------------
Write-Host "==> Installed: $(& $swarmDesk --version)"

# --- 5. Tests when pytest is available (best effort) ------------------
& $venvPy -m pytest --version *> $null
if ($LASTEXITCODE -ne 0) { & $venvPy -m pip install -q pytest *> $null }
& $venvPy -m pytest --version *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Running the test suite"
    & $venvPy -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { Write-Error "Test suite failed"; exit 1 }
} else {
    Write-Host "NOTE: pytest is not available - skipped the test suite."
    Write-Host "      (Optional: pip install pytest, then: python -m pytest tests -q)"
}

# --- 6. Demo ------------------------------------------------------------
Write-Host "==> Running the demo (12-asset universe, sample data)"
& $swarmDesk demo
if ($LASTEXITCODE -ne 0) { Write-Error "Demo failed"; exit 1 }

Write-Host ""
Write-Host "Done. Swarm Desk is ready - the demo runs above are now in the"
Write-Host "experiment ledger (data\ledger.jsonl), which is how predictions earn a"
Write-Host "track record."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  .venv\Scripts\Activate.ps1   (activate the virtualenv first)"
Write-Host "  swarm-desk run --asset NVDA --momentum 0.8 --volatility 0.3 --headlines `"Chipmaker beats estimates as AI demand surges`""
Write-Host "  swarm-desk serve --port 8799     # HTTP API"
Write-Host "  swarm-desk mcp                   # MCP server (stdio) for agent hosts"
Write-Host ""
Write-Host "Full guide: QUICKSTART.md   Worked agent examples: examples\README.md"
