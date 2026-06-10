# CLAUDE.md — EyeBrowse build notes

Guidance for working in this repo. EyeBrowse is **a stealthy, LLM-drivable
browser-control engine** consumed two ways from one codebase: as a Python
library (`from eyebrowse import EyeBrowse`) and over MCP (FastMCP, stdio). The engine
holds no workflow logic — consumers decide *what* to do; it provides *what's possible*.

**Engine: CloakBrowser (stealth Chromium, Chrome/146).** A Playwright drop-in —
`launch_async()` / `launch_persistent_context_async()` return a standard Playwright
`Browser` / `BrowserContext`. Everything above the launch primitive runs on the plain
Playwright `page`, so `engine/engine.py` is the ONLY engine-specific layer. Chromium gives us
the full **CDP** surface (trusted cursorless clicks, `Network`/initiator inspection, MHTML,
PDF, native video), exposed as thin tools. CloakBrowser's stealth is its patched binary + an
auto `--fingerprint={seed}` / `--fingerprint-platform` (nothing for us to spoof); we map only
its **native** knobs — `humanize`, `geoip`, `locale`, `timezone`, `proxy`. HAR is
Playwright-native (`record_har_path`), video is Playwright-native (`record_video_dir`) — no
custom recorders. (EyeBrowse was originally built on Camoufox/Firefox; that engine has been
removed — see git history if you need the old launch path.)

## Layout

```
eyebrowse/
  api.py            EyeBrowse façade — the single public entry point
  config.py         pydantic-settings (proxy, captcha keys, stealth defaults)
  snapshot.py       aria_snapshot(mode="ai") + aria-ref= locator resolution
  proxy.py          ProxyConfig + ProxyProvider (pluggable rotation)
  identity.py       Identity + random_identity() (isolated profile dir for rotation)
  extract.py        Crawl4AI raw: feed → markdown (no LLM; lazy, optional `extract` extra)
  engine/
    engine.py       BrowserEngine — CloakBrowser launch primitive (launch_async /
                    launch_persistent_context_async, proxy/options mapping, HAR rule, _Cleanup)
    session.py      Session (verbs incl. CDP: cdp_click/cdp_send/capture_mhtml/save_pdf/
                    video_path) + SessionRegistry (current-session)
  captcha/          base (Anti-Captcha-style polling) + 4 providers + inject.py
  mcp/
    server.py       FastMCP entrypoint (lifespan holds one EyeBrowse), main()
    state.py        process-wide engine handle
    tools/          17 tool-group modules (1:1 over the façade) = 85 tools
examples/direct_usage.py   library usage proof (no MCP)
docs/TOOLS.md              full per-tool reference
```

## Run

```bash
uv sync                          # core engine (pulls cloakbrowser + playwright)
uv sync --extra extract          # + Crawl4AI (heavier; only needed for extract())
# The stealth-Chromium binary is fetched lazily to ~/.cloakbrowser on first launch — nothing to run.
uv run python examples/direct_usage.py        # verify the library path
uv run eyebrowse-mcp                           # run the MCP server (stdio)
claude mcp add eyebrowse uv run eyebrowse-mcp  # register with Claude Code
```

## Pinned versions (lockstep matters)

* **`cloakbrowser>=0.3` → stealth Chromium Chrome/146.** Playwright drop-in; both
  `launch_async`/`launch_persistent_context_async` patch `close()` to also `pw.stop()` (no
  leak). Binary auto-downloaded on first launch to `~/.cloakbrowser/` (override:
  `CLOAKBROWSER_CACHE_DIR` / `CLOAKBROWSER_BINARY_PATH`).
* `playwright>=1.40,<2` (resolved with cloakbrowser → 1.60.0), `mcp>=1.2`. Python 3.12 (pinned `<3.13`).

## Verified API facts (current installs — supersede the original research report)

* **Snapshot/refs:** `page.accessibility` and `Page._snapshot_for_ai` are **gone** in
  Playwright 1.60. Use **`await page.aria_snapshot(mode="ai")`** → YAML ARIA tree with
  `[ref=eN]` handles, and resolve with **`page.locator("aria-ref=eN")`**. This is the
  whole LLM-drivable interaction model (see `snapshot.py`). No DOM injection needed.
* **Screenshot:** return Playwright's raw PNG bytes via `Image(data=bytes, format="png")`
  — never `PIL.tobytes()` (raw pixels → corrupt image).
* **CloakBrowser launch:** `await launch_async(**opts)` → standard Playwright **Browser**
  (ephemeral); `await launch_persistent_context_async(user_data_dir, **opts)` → **BrowserContext**.
  Native opts mapped in `BrowserEngine.build_options`: `headless`, `humanize` (bool; `human_preset`
  for finer control), `geoip` (derives tz/locale/WebRTC from the proxy IP), `proxy` (a single URL
  string `scheme://user:pass@host:port` — see `_proxy_to_url`), `locale`, `timezone`. HAR/video are
  set on `new_context(record_har_path=…, record_video_dir=…)` for the ephemeral path (standard
  Playwright). Cleanup unified via the `_Cleanup` shim (ephemeral → `browser.close()`; persistent →
  no-op, the context's patched `close()` owns teardown).

## Key constraints (encoded in code — don't "simplify" away)

* **Launch is serialized** behind a semaphore in `BrowserEngine`. Chromium doesn't need it for
  correctness, but it cheaply serializes the one-time CloakBrowser binary download on first launch
  (and keeps one code path). Interactions after launch are parallel-safe.
* **HAR works on BOTH ephemeral and persistent (verified).** `record_har_*` is honored by
  `launch_persistent_context_async` too — the earlier "persistent strips `record_har_*`" claim was
  wrong. Verified: persistent + `record_har`, and persistent + `record_har` + a side-loaded
  extension, both produce a populated HAR (1 and 6 entries against example.com). This matters
  because **extensions force a persistent context**, yet a consumer may still want HAR — that combo
  now works. Playwright only flushes the HAR on context close, so `export_har()` still **closes the
  session**. (HAR is the native Playwright/Chromium HAR. For the initiator-rich Chrome DevTools HAR
  with JS call stacks, use `browser_cdp_send` against the `Network.*` domain.)
* **Extensions ⇒ persistent + headful.** `new_session(extensions=[paths])` side-loads UNPACKED
  Chromium extensions via `--load-extension` (+ `--disable-extensions-except`). Chromium only loads
  them in a persistent context launched headful, so `extensions` auto-forces `persistent=True` +
  `headless=False` and mints a temp profile dir if none is given. The engine just loads what it's
  handed — *which* extension (and any API key it needs) is the consumer's concern. Verify a load via
  `context.service_workers` (MV3 background → `chrome-extension://<id>/...`).
* **Built-in captcha = API-mode only.** EyeBrowse's *own* `solve_captcha` uses no browser extension
  (an extension raises bot-score and is a heavy, fragile dependency). Solvers fetch a token over
  HTTP; `captcha/inject.py` writes it into the response field and overrides the widget's getResponse.
  (Orthogonally, a consumer *can* side-load a solver extension via the generic `extensions=` feature
  above if they accept that tradeoff — that's a consumer decision, not the engine's built-in path.) Kinds: `turnstile`, `recaptcha_v2`, `recaptcha_v3`,
  `hcaptcha`, `funcaptcha` — all four providers speak the Anti-Captcha
  `createTask`/`getTaskResult` dialect, so adding a kind = (1) a task-type
  string in `base.py` (per-provider override where it differs — CapSolver uses `…ProxyLess`
  casing, CapMonster's FunCaptcha is `FunCaptchaTask`), (2) kind-aware detect/inject in
  `inject.py`, (3) routing in `api.solve_captcha` + the MCP tool. Notes: hCaptcha →
  `h-captcha-response` + override `hcaptcha.getResponse`; reCAPTCHA v3 is invisible
  (no widget) → detect the sitekey from `api.js?render=…`, inject into `g-recaptcha-response`
  and override `grecaptcha.execute` (needs `page_action`); FunCaptcha/Arkose uses
  `websitePublicKey` + a dynamic `blob` (`data`) and a hidden `fc-token`/`verification-token`
  field (no getResponse global). **reCAPTCHA v3 is score-based and gates on IP/session
  reputation** — a fresh browser on a flagged IP fails regardless of stealth; pair with a
  clean residential proxy.
* **Stealth defaults:** `geoip=True`, `humanize=True`. For identity rotation, rotate IP + geo
  (geoip) + a fresh profile together (CloakBrowser mints a novel `--fingerprint` per launch
  automatically). `humanize` is `bool` (a float is accepted for back-compat but coerced to a
  bool); `human_preset` ('default'/'careful') is CloakBrowser's finer control. `locale`/`timezone`
  default to None → derived from the proxy exit IP via geoip.
* **Windows:** runs headful/headless natively (no Xvfb).

## MCP tool surface — 85 tools (grouped in `mcp/tools/`)

- **sessions**: `browser_new_session` / `browser_close_session` / `browser_list_sessions` / `browser_video_path`
- **navigate**: `browser_navigate` / `browser_navigate_back` / `browser_navigate_forward` / `browser_reload` / `browser_tabs` / `browser_switch_to_popup`
- **observe**: `browser_snapshot` / `browser_snapshot_frame` / `browser_find` / `browser_screenshot` / `browser_resize` / `browser_console_messages` / `browser_wait_for_download`
- **interact**: `browser_click` / `browser_type` / `browser_keyboard_type` / `browser_fill_form` / `browser_hover` / `browser_select_option` / `browser_select_combobox` / `browser_set_input` / `browser_type_otp` / `browser_press_key` / `browser_drag` / `browser_file_upload` / `browser_handle_dialog` / `browser_wait_for` / `browser_evaluate` / `browser_scroll` / `browser_scroll_to_bottom`
- **mouse (coordinate)**: `browser_mouse_move` / `browser_mouse_click` / `browser_mouse_down` / `browser_mouse_up` / `browser_mouse_wheel` / `browser_mouse_drag`
- **network**: `browser_network_requests` / `browser_network_request` / `browser_ws_messages`
- **netcontrol**: `browser_block_urls` / `browser_unblock_urls` / `browser_set_offline` / `browser_mock_url`
- **cookies**: `browser_cookie_list` / `browser_cookie_get` / `browser_cookie_set` / `browser_cookie_delete` / `browser_cookie_clear`
- **localStorage**: `browser_localstorage_list` / `_get` / `_set` / `_remove` / `_clear`
- **sessionStorage**: `browser_sessionstorage_list` / `_get` / `_set` / `_remove` / `_clear`
- **state**: `browser_storage_state` / `browser_har_export`
- **identity / proxy**: `browser_new_identity` / `browser_set_proxy`
- **verify**: `browser_verify_element_visible` / `browser_verify_element_hidden` / `browser_verify_text_visible` / `browser_verify_value`
- **devtools**: `browser_highlight` / `browser_clear_highlights` / `browser_generate_locator` / `browser_start_tracing` / `browser_stop_tracing`
- **emulate**: `browser_set_geolocation` / `browser_set_extra_headers` / `browser_grant_permissions`
- **cdp**: `browser_cdp_click` (trusted cursorless click on a ref via `Input.dispatchMouseEvent`) / `browser_cdp_send` (raw CDP method, e.g. `Network.*`, `Performance.*`, `Emulation.setEmulatedMedia`) / `browser_capture_mhtml` (`Page.captureSnapshot` → single-file `.mhtml`) / `browser_pdf_save` (`page.pdf()`)
- **captcha**: `browser_solve_captcha` / `browser_totp_generate` · **extract**: `browser_extract`

## Behavior notes (verified — affect implementation choices)

* **`page.evaluate` world.** On standard Chromium, `page.evaluate` runs in the page's **main
  world** (page globals are reachable). To reliably touch the page's widget globals and fire a
  site callback regardless of world, inject a `<script>` element — its `textContent` executes in
  the page world. `captcha/inject.py` relies on this: stage 1 sets the DOM response field via
  `page.evaluate`, stage 2 injects a `<script>` that overrides
  `grecaptcha/turnstile/hcaptcha.getResponse` AND **fires the site's `data-callback` /
  `___grecaptcha_cfg` callback** — without that page-world step the token sits unused and
  callback-gated forms (most reCAPTCHA v2) never accept it.
* **Cross-origin iframes:** `aria_snapshot(mode="ai")` assigns frame-prefixed refs like
  `f1e36`. **`fN` is `"f"+frame.seq`** (a creation-order counter), **NOT** an index into
  `page.frames` (which is DFS order) — they diverge on dynamic/nested pages, so never do
  `page.frames[N]`. `ref_locator` hands the whole ref to Playwright's `aria-ref=` engine,
  which jumps to the frame by seq via `_jumpToAriaRefFrameIfNeeded`
  (`frameManager.frames().find(f => f.seq === N)`). For a real `Frame` (evaluate /
  snapshot_frame) we resolve an element via aria-ref then read `owner_frame()` /
  `content_frame()` — see `snapshot.py:frame_for_ref`. `browser_evaluate(frame_ref=...)`
  runs JS **inside** the frame, so it works on CROSS-ORIGIN frames (the frame's own
  context is reachable; only top-frame `contentDocument` access is blocked). If the page
  snapshot collapses a frame to empty (usually a load-timing issue), `wait_for(network_idle)`
  then re-snapshot, or use `browser_snapshot_frame('f1')`. Nested frames (`f1f2eM`) are
  NOT supported — Playwright's own ref regex is single-level `^f\d+e\d+$`.
* **Shadow DOM:** `aria_snapshot` traverses open shadow roots automatically via the
  accessibility tree. Shadow-hosted elements get plain `eN` refs; `aria-ref=eN` resolves
  through shadow boundaries natively — no extra handling needed.
* **Rich text editors (TipTap, Quill, ProseMirror):** `fill()` is a no-op on
  `contenteditable` divs. Pattern: `browser_mouse_click(x, y)` to focus the editor →
  `browser_keyboard_type(text)` to insert. `browser_type` with a ref also works if the
  snapshot returns a meaningful ref for the editor element.
* **History navigation** uses the browser's real history natively (`page.go_back` /
  `go_forward` / `reload`) — so back/forward traverse click-driven navigations too, not just
  `navigate()`-driven ones.
* **Interaction options.** Both ref-clicks are trusted (`isTrusted=true`) and accurate (the point
  is computed from the element's box — no pixel guessing), and **both are humanized by CloakBrowser
  when `humanize=True`** (the default): CloakBrowser humanizes the dispatched pointer events at the
  binary level, so even a single CDP `Input.dispatchMouseEvent` is expanded into a realistic cursor
  trajectory (verified: a plain `cdp_click` makes the page see ~27 `mousemove` events). The real
  difference is the **actionability wait**: `browser_click` is `locator.click()` — it waits for the
  element to be visible/stable/enabled/receiving-events, so it's robust but slower; `browser_cdp_click`
  **skips that wait** and dispatches straight at the box, so it's **faster** (good as a fast default)
  but can fire a touch early on a mid-animation element. Neither bypasses a *covering* overlay (the
  topmost element at the point still receives the click) — dismiss the overlay first. Coordinate mouse
  (`page.mouse.*`) also works but guesses pixels — last resort for canvas/off-DOM.
* **Viewport** defaults to maximize-to-the-randomized-spoofed-screen (large screenshots, full
  per-session fingerprint entropy, `inner <= screen`). Pin a fixed size via
  `EYEBROWSE_VIEWPORT_WIDTH/HEIGHT` only if you need predictable dimensions.
* **HAR export closes the session** (Playwright flushes the buffer on context close only).
  Non-destructive checkpoint pattern: `browser_storage_state` → `browser_har_export` →
  `browser_new_session(storage_state=...)`.
* **Native video:** `record_video=True` on `browser_new_session` records the session to a `.webm`
  via Playwright's `record_video_dir`, finalized on context close; the path is known up-front via
  `browser_video_path`. For a GIF, convert the `.webm` afterward (e.g. with ffmpeg).
* **CDP escape hatch:** `browser_cdp_send` reaches anything not wrapped — `Network.getResponseBody`
  / `getRequestPostData` (+ `_initiator` call stacks), `Performance.getMetrics`,
  `Emulation.setEmulatedMedia` (color-scheme/reduced-motion) / `setDeviceMetricsOverride` /
  `emulateNetworkConditions`, etc.

## Secrets

`.env` (gitignored; see `.env.example`). Proxy + stealth settings use the `EYEBROWSE_`
prefix; captcha keys use provider-conventional names (`CAPSOLVER_API_KEY`, …). Never
hardcode. Extraction is markdown-only and uses **no LLM** — so no LLM provider keys are
ever read (the consuming agent does any structuring).

## Conventions

Library-first: add capability to the façade/engine, then expose it as a thin MCP tool
(no logic in the tool). Keep `Session` the home of per-session verbs. Async throughout.
