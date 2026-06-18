<div align="center">

# 👁️ EyeBrowse

### A stealthy, LLM-drivable browser engine — one codebase, two faces.

A **Python library** *and* an **MCP server** for driving a real, hard-to-detect browser, so
legitimate automation isn't false-flagged or IP-banned by Cloudflare, DataDome, Akamai, or
PerimeterX. Built on **CloakBrowser** — a stealth **Chromium** (Chrome/146) that's a Playwright
drop-in — so EyeBrowse gets the full **Chrome DevTools Protocol**: trusted cursorless clicks,
deep network inspection, MHTML, PDF, and native video.

[![CI](https://github.com/Evil-Bane/eyebrowse/actions/workflows/ci.yml/badge.svg)](https://github.com/Evil-Bane/eyebrowse/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/eyebrowse?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/eyebrowse/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
<br/>
[![MCP tools](https://img.shields.io/badge/MCP-85_tools-7c3aed.svg)](docs/TOOLS.md)
[![Engine: CloakBrowser](https://img.shields.io/badge/engine-CloakBrowser%20(stealth%20Chromium)-4285F4.svg)](https://pypi.org/project/cloakbrowser/)
[![Code style: Ruff](https://img.shields.io/badge/lint-ruff-261230.svg?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-22c55e.svg)](CONTRIBUTING.md)

![EyeBrowse driving a real browser](https://raw.githubusercontent.com/Evil-Bane/eyebrowse/master/docs/demo.gif)

<sub>▶ Higher-quality MP4: <a href="https://github.com/Evil-Bane/eyebrowse/blob/master/docs/demo.mp4">docs/demo.mp4</a> — a real EyeBrowse session captured with native video (<code>examples/make_demo.py</code>)</sub>

</div>

---

## Why EyeBrowse?

- 🥷 **Stealth by default** — engine-level fingerprint spoofing (`geoip` + `humanize` on out of the box, novel fingerprint per launch); `navigator.webdriver` masked; viewport auto-sized to the spoofed screen. No `puppeteer-extra` band-aids — the anti-detection is *compiled into the browser*.
- 🤖 **Built for LLMs** — pages are read as an **ARIA tree with `[ref=…]` handles**; the model acts by ref (`click`/`type`/`hover`), not by brittle CSS or raw pixels. Cross-origin iframes, shadow DOM, popups — handled.
- ⚡ **Chrome DevTools Protocol** — **trusted, cursorless clicks** by node ref (`Input.dispatchMouseEvent`), raw `Network`/`Performance`/`Emulation` access, **MHTML** snapshots, **PDF** export, and **native video** — all reachable as tools.
- 🧰 **Library *and* MCP from one codebase** — a clean Python API (`EyeBrowse` + `Session`), mirrored 1:1 by a thin **MCP server** (**85 `browser_*` tools**) for Claude Code and any MCP client.
- 🪟 **Never boxed in** — the curated high-level API doesn't hide Playwright: reach `session.page` / `.context` / `.browser` for anything it doesn't wrap.
- 🔋 **Batteries included** — multi-session, proxy + identity rotation, API-mode captcha solvers, native video, full **HAR** capture, and clean-markdown extraction.

> **Scope.** EyeBrowse is a low-level browser *engine* — it holds **no workflow logic**.
> Consumers decide *what* to do; the engine provides *what's possible*.

## Contents

[Quickstart](#quickstart) · [Install](#install) · [Features](#features) · [Compare](#how-eyebrowse-compares) · [Library](#use-as-a-library) · [MCP](#use-over-mcp) · [Proxy & identity](#proxy--identity-optional) · [Extraction](#extraction) · [Recording](#recording) · [How it works](#how-it-works) · [Caveats](#caveats) · [Tools](docs/TOOLS.md) · [License](#license)

## Quickstart

```bash
pip install eyebrowse
# The stealth-Chromium binary downloads automatically on first launch — nothing else to run.
```

```python
import asyncio
from eyebrowse import EyeBrowse

async def main():
    eb = EyeBrowse()                          # stealth defaults: geoip · humanize
    async with eb.session() as s:
        await s.navigate("https://example.com")
        print(await s.snapshot())             # ARIA tree with [ref=...] handles
        await s.click("e6")                   # act on a ref from the snapshot
    await eb.aclose()

asyncio.run(main())
```

…or wire it into **Claude Code** (or any MCP client) — see [Use over MCP](#use-over-mcp).

## Install

**From PyPI**

```bash
pip install eyebrowse                 # or: uv pip install eyebrowse
# CloakBrowser fetches its Chromium binary lazily on first launch — nothing to run.
pip install "eyebrowse[extract]"     # optional: + Crawl4AI markdown extraction (heavier)
```

**From source (development)**

```bash
git clone https://github.com/Evil-Bane/eyebrowse && cd eyebrowse
uv sync                              # core engine  (add --extra extract for Crawl4AI)
cp .env.example .env                 # only if you use a proxy / captcha keys
```

Python 3.12 (pinned `<3.13`). Engine: `cloakbrowser>=0.3` (stealth Chromium, Chrome/146), on
`playwright 1.60` and `mcp 1.27`.

## Features

| | |
|---|---|
| 🥷 **Stealth** | CloakBrowser's patched-Chromium fingerprint spoofing (novel `--fingerprint` per launch); `geoip` + `humanize` by default; `webdriver` masked; viewport matched to the spoofed screen. |
| 🤖 **LLM interaction** | `aria_snapshot(mode="ai")` → ARIA tree + `[ref]` handles; click / type / hover / select / drag / file-upload / dialogs / keyboard; coordinate mouse too. |
| ⚡ **CDP** | **trusted cursorless click** by ref, raw CDP (`Network` / `Performance` / `Emulation`), **MHTML** capture, **PDF** export. |
| 🪟 **Frames & DOM** | cross-origin iframe routing by ref, shadow-DOM piercing, popup/new-tab switching, `evaluate` inside any frame. |
| 🗂 **Multi-session** | independent stealth sessions, each with its own context / identity / proxy. |
| 🌐 **Network** | inspect requests/responses (incl. XHR/fetch bodies & WebSocket frames), block URLs, mock responses, go offline, full **HAR** export. |
| 💾 **State** | cookies, localStorage & sessionStorage (CRUD), `storage_state` save/reload. |
| 🪪 **Identity rotation** | fresh fingerprint + isolated profile + paired proxy; pluggable residential `ProxyProvider`. |
| 🧩 **Captcha** | pluggable **API-mode** solvers (CapSolver / 2Captcha / CapMonster / NextCaptcha) + TOTP — no browser extension. |
| 📄 **Extraction** | Crawl4AI `raw:` feed → clean, token-efficient **markdown** (no LLM, no API keys). |
| 🎥 **Capture** | screenshots, Playwright tracing, and **native video** (`.webm`). |
| ✅ **Verify & debug** | assertions, element highlighting, locator generation, geolocation/header emulation. |

Full per-tool reference: **[docs/TOOLS.md](docs/TOOLS.md)** (85 tools across 18 groups).

## How EyeBrowse compares

|                                                   |     EyeBrowse      | Playwright&nbsp;MCP |    browser-use     | playwright-stealth |
| :------------------------------------------------ | :----------------: | :-----------------: | :----------------: | :----------------: |
| Anti-detection **compiled into the browser**      |         ✅         |         ❌          |         ❌         |   ⚠️ JS patches    |
| LLM-native ARIA **`[ref]`** interaction model     |         ✅         |         ✅          |         ✅         |         ❌         |
| Ships an **MCP server**                            |   ✅ (85 tools)    |         ✅          |     ⚠️ partial     |         ❌         |
| One codebase: Python **library *and* MCP**        |         ✅         |     MCP-only        |     lib-only       |     lib-only       |
| Full **CDP** (trusted clicks · network · MHTML · PDF · video) | ✅     |     ⚠️ partial      |         ❌         |     ⚠️ partial     |
| **Captcha** (API-mode) + TOTP                     |         ✅         |         ❌          |         ❌         |         ❌         |
| **Proxy + identity rotation** built in            |         ✅         |         ❌          |     ⚠️ partial     |         ❌         |
| Cross-origin iframes · shadow DOM · popups        |         ✅         |         ✅          |     ⚠️ partial     |        n/a         |

<sub>Fair-use note: each project targets a different niche — this compares them on the axes EyeBrowse optimizes for (stealth + LLM-drivable + one library/MCP codebase), not as an overall ranking.</sub>

## Use as a library

```python
import asyncio
from eyebrowse import EyeBrowse

async def main():
    eb = EyeBrowse()                           # stealth defaults
    try:
        async with eb.session() as s:          # a stealth session (auto-closed)
            await s.navigate("https://example.com")
            print(await s.snapshot())          # ARIA tree with [ref=...] handles
            await s.click("e6")                # act on a ref
            await s.type("e8", "hello", submit=True)
            png = await s.screenshot(full_page=True)
            title = await s.page.title()        # full Playwright power when you need it
    finally:
        await eb.aclose()

asyncio.run(main())
```

Run the included proof: `uv run python examples/direct_usage.py`.

## Use over MCP

EyeBrowse ships an MCP server (`eyebrowse-mcp`, FastMCP over stdio). Add it to any MCP client.

**Claude Code (CLI):**

```bash
claude mcp add eyebrowse -- eyebrowse-mcp
```

**Any MCP client (JSON config):**

```json
{
  "mcpServers": {
    "eyebrowse": {
      "command": "eyebrowse-mcp"
    }
  }
}
```

Then drive the loop: `browser_navigate(url)` → read the snapshot → act by ref
(`browser_click` / `browser_type` / …). A default session is auto-created, so most tools just
work. Full list: **[docs/TOOLS.md](docs/TOOLS.md)**.

## Proxy & identity (optional)

Runs **proxyless by default** (`geoip` still aligns locale/timezone to your real IP). Add a proxy
only when you want one:

```python
await eb.new_session(proxy="http://user:pass@residential.example:8080")
await eb.rotate_identity(proxy="socks5://host:1080")   # fresh fingerprint + paired IP
await eb.new_session(no_proxy=True)                     # force proxyless
```

Set a default once via `EYEBROWSE_PROXY_*` in `.env`, `eb.set_static_proxy(...)`, or a custom
`ProxyProvider` for rotation. Over MCP: `browser_new_session(proxy_url=…)` /
`browser_new_identity(proxy_url=…)` / `browser_set_proxy(…)`.

> **reCAPTCHA v3 / reputation gates** are score-based and key off IP + session reputation — a
> fresh browser on a flagged IP fails regardless of stealth. Pair EyeBrowse with a clean
> residential proxy.

## Extraction

`eb.extract()` (or `browser_extract`) hands the rendered HTML to Crawl4AI's `raw:` feed and
returns clean, pruned **markdown** — **no LLM is called and no LLM keys are ever read**; the
consuming agent does any structuring.

```python
md  = await eb.extract()                            # markdown string
res = await eb.extract(output_path="data/page.md")  # → {"path": ..., "chars": ...}
```

## Recording

**Native video** — Playwright records the whole session to a `.webm`, written on close. The path
is known up-front; the file finalizes when the session closes:

```python
s = await eb.new_session(record_video=True)
# ... drive the browser ...
print(await s.video_path())          # path is known up-front; file finalizes on close
await eb.close_session(s.id)
```

Over MCP: `browser_new_session(record_video=True)` → `browser_video_path`. Want a GIF for a README?
Convert the `.webm` with ffmpeg (`ffmpeg -i demo.webm demo.gif`). The demo at the top was captured
this way — see **`examples/make_demo.py`**.

## How it works

```
CONSUMERS                         ENGINE (library: eyebrowse/)
 Claude Code  ──MCP──▶  mcp/  ──▶  EyeBrowse façade (public API)
 your code   ─ import ──────────▶   ├─ BrowserEngine (CloakBrowser / stealth Chromium)
 any MCP client                     ├─ proxy / identity rotation (pluggable)
                                    ├─ captcha solvers (pluggable, API-mode)
                                    └─ Crawl4AI (raw: feed) → clean markdown
```

The façade (`EyeBrowse` + `Session`) is the product; the MCP adapter is a thin 1:1 wrapper over
it. The high-level API is curated and LLM-friendly — *not* a reimplementation of all of Playwright
— and the raw `page` / `context` / `browser` objects are always one attribute away. The launcher
is the only engine-specific layer; everything else is plain Playwright.

## Caveats

Worth knowing:

- **`evaluate`** runs in the page's main world (page globals reachable). To override a page's
  widget globals and fire a site callback (e.g. for captcha), EyeBrowse injects a `<script>` so the
  code runs in the page world — see `captcha/inject.py`.
- **HAR export closes the session** — Playwright only flushes the HAR buffer when the context
  closes. Use the checkpoint pattern: `browser_storage_state` → `browser_har_export` →
  `browser_new_session(storage_state=...)`. For the initiator-rich Chrome HAR (JS call stacks),
  reach the `Network.*` domain via `browser_cdp_send`.
- **Native video is `.webm`** — convert to GIF/MP4 with ffmpeg if you need another format.

## Project layout

```
eyebrowse/
  api.py            EyeBrowse façade — the single public entry point
  config.py         settings / secrets (pydantic-settings)
  snapshot.py       aria_snapshot(mode="ai") + aria-ref= resolution
  proxy.py          ProxyConfig + pluggable ProxyProvider
  identity.py       Identity + random_identity() (isolated profile dir)
  extract.py        Crawl4AI raw: feed → markdown (lazy, optional dep)
  engine/           engine.py (CloakBrowser launch) + session.py (verbs + registry)
  captcha/          solver ABC + 4 providers + DOM detect/inject
  mcp/              FastMCP server + state + tools/ (18 groups · 85 tools)
examples/direct_usage.py   library proof (no MCP)
examples/make_demo.py      the native-video demo above
docs/TOOLS.md              full tool reference
```

Build notes, version-pin rationale, and verified engine behavior live in **[CLAUDE.md](CLAUDE.md)**.

## Use responsibly

EyeBrowse drives a real browser with anti-detection features. Use it only against sites you
own or are explicitly authorized to automate, and within their terms and applicable law.

## License

[MIT](LICENSE) © Evil-Bane

<div align="center">
<br/>

**Found EyeBrowse useful?** ⭐ Star the repo — it genuinely helps.

<sub>Built with Python · Playwright · CloakBrowser · FastMCP · the Model Context Protocol</sub>

</div>
