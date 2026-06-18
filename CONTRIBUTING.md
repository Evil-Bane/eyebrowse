# Contributing to EyeBrowse

Thanks for your interest! EyeBrowse is a low-level, stealthy browser-control **engine** consumed
two ways from one codebase — a Python library and an MCP server. Contributions that keep it small,
fast, and engine-only (no workflow logic) are very welcome.

## Dev setup

```bash
git clone https://github.com/Evil-Bane/eyebrowse && cd eyebrowse
uv sync                      # core engine (add --extra extract for Crawl4AI)
cp .env.example .env         # only if you use a proxy / captcha keys
```

Python is pinned to **3.12** (`>=3.12,<3.13`). The stealth-Chromium binary is fetched lazily by
CloakBrowser on the first browser launch — nothing to install up front.

## Verify your change

```bash
uvx ruff check eyebrowse examples                 # lint (CI runs this)
uv run python -c "import eyebrowse; from eyebrowse.mcp import server"   # import smoke
uv run python examples/direct_usage.py            # library path, end to end
uv run python examples/smoke_otp_combobox.py      # interaction-primitive regression
```

CI (`.github/workflows/ci.yml`) runs lint → import smoke → `uv build` on every push and PR.

## Design rules (please follow)

- **Library-first.** Add a capability to the façade (`eyebrowse/api.py`) or a per-session verb
  (`eyebrowse/engine/session.py`) first, then expose it as a **thin** MCP tool under
  `eyebrowse/mcp/tools/` — the tool wraps, it does not implement. No business/workflow logic in
  the engine *or* the tools.
- **One engine layer.** `engine/engine.py` is the only CloakBrowser-specific file; everything else
  runs on the plain Playwright `page` / `context` / `browser`.
- **Async throughout.** Every I/O path is `async`.
- **Keep the surface honest.** If you change the tool set, update `README.md` and `docs/TOOLS.md`
  (including the tool count) in the same PR.

Engine internals, version-pin rationale, and verified Playwright/CDP behavior live in
[CLAUDE.md](CLAUDE.md) — read it before touching the launch or snapshot paths.

## Pull requests

1. Branch off `master`.
2. Keep PRs focused; bump the version in `pyproject.toml` + `eyebrowse/__init__.py` only for a
   release PR, and add a `CHANGELOG.md` entry.
3. Make sure the checks above pass; the PR template has the checklist.

## Reporting bugs / requesting features

Use the issue templates (bug report / feature request). For anything security-sensitive, see
[SECURITY.md](SECURITY.md).
