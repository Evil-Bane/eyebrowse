<#
EyeBrowse setup — run from the project root on a fresh machine (e.g. your RDP).
Rebuilds the venv, fetches the CloakBrowser stealth-Chromium binary, and registers the MCP server.

    powershell -ExecutionPolicy Bypass -File .\setup.ps1            # everything (default)
    powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Minimal   # core engine only (skip Crawl4AI)

By default this installs EVERYTHING — the core engine plus the Crawl4AI extraction
stack (and its chromium binary) — so browser_extract works out of the box. Pass
-Minimal to skip extraction if you want the lean install.

Prereqs: uv (https://docs.astral.sh/uv/). The `claude` CLI is optional — if it's not on
PATH (e.g. Claude Code is installed only as the VS Code/Antigravity extension), this
script writes a project-scoped .mcp.json instead, which the extension picks up.
Do NOT copy .venv/ data/ reference/ __pycache__/ from the source machine — they are
rebuilt here. Keeping uv.lock gives a reproducible, identical install.
#>
param([switch]$Minimal)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
Write-Host "== EyeBrowse setup in $root ==" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install it from https://docs.astral.sh/uv/ then re-run."
}

if ($Minimal) {
    Write-Host "1/3  Installing core dependencies (uv sync)..." -ForegroundColor Yellow
    uv sync
} else {
    Write-Host "1/3  Installing ALL dependencies incl. Crawl4AI (uv sync --extra extract)..." -ForegroundColor Yellow
    uv sync --extra extract
    Write-Host "      Installing Crawl4AI's chromium binary (needed for its raw: feed)..." -ForegroundColor DarkYellow
    uv run playwright install chromium
}

Write-Host "2/3  Fetching the CloakBrowser stealth-Chromium binary..." -ForegroundColor Yellow
uv run python -m cloakbrowser install

Write-Host "3/3  Registering the eyebrowse MCP server..." -ForegroundColor Yellow
$exe = Join-Path $root ".venv\Scripts\eyebrowse-mcp.exe"
if (-not (Test-Path $exe)) { throw "Missing $exe (did 'uv sync' succeed?)" }

if (Get-Command claude -ErrorAction SilentlyContinue) {
    # CLI present — register at user scope (persists across every folder).
    try { claude mcp remove eyebrowse -s user } catch {}   # drop any old registration
    claude mcp add eyebrowse -s user -- "$exe"
    Write-Host "`n== Registered servers ==" -ForegroundColor Cyan
    claude mcp list
} else {
    # No `claude` CLI (e.g. VS Code / Antigravity extension only) — write project-scoped
    # .mcp.json, which the extension auto-discovers when this folder is opened.
    Write-Host "      'claude' CLI not on PATH — writing project-scoped .mcp.json instead." -ForegroundColor DarkYellow
    # Build via hashtable + ConvertTo-Json (NOT a here-string — here-strings fail to parse
    # in Windows PowerShell 5.1 when the .ps1 has LF-only line endings). ConvertTo-Json
    # also escapes the backslashes in the .exe path for us.
    $config = [ordered]@{
        mcpServers = [ordered]@{
            eyebrowse = [ordered]@{
                command = $exe
                type    = "stdio"
            }
        }
    }
    $config | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $root ".mcp.json") -Encoding utf8
    Write-Host "      Wrote .mcp.json -> $(Join-Path $root '.mcp.json')" -ForegroundColor Green
}

Write-Host "`nDone. If you want proxy/captcha, copy your .env (or fill it from .env.example)." -ForegroundColor Green
Write-Host "Then RESTART Claude Code (or Reload Window) -- 'eyebrowse' should show Connected with all tools." -ForegroundColor Green
