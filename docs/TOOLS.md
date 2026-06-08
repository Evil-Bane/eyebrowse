# EyeBrowse — MCP Tool Reference

**81 tools** across 18 groups. Every tool accepts an optional `session_id` (a default session is created automatically on first use). Engine: **CloakBrowser** (stealth Chromium) — so the full CDP surface (trusted clicks, network inspection, MHTML, PDF, native video) is available.

## Sessions

- **`browser_new_session`**(persistent, label, headless, humanize, record_har, record_video, har_url_filter, storage_state, extensions, proxy_url, proxy_server, proxy_username, proxy_password, no_proxy) — Create a new stealth browser session and make it current. Returns its id. Runs PROXYLESS by default. Pass `proxy_url` (`http://user:pass@host:port`) or `proxy_server`[+username/password] for a proxy. `no_proxy=True` forces proxyless even if a default proxy is configured. `persistent` keeps cookies/localStorage in a profile dir across runs. `humanize`: per-session cursor humanization (float caps cursor-move seconds, True = default, False = off). `record_har` captures a full network HAR (export with `browser_har_export`); works on both ephemeral and persistent sessions; `har_url_filter` is a glob to scope what it records. `record_video` records the session to a native `.webm` (Chromium only; path via `browser_video_path`, finalized on close). `storage_state` reloads a saved cookies/localStorage JSON. `extensions` is a list of paths to UNPACKED Chromium extension folders to side-load (e.g. a captcha-solver or your own extension); it forces a persistent + headful session (Chromium requirement) and the profile persists so the extension's own config/login survives.
- **`browser_video_path`**() — Path to this session's native video recording (Chromium only; present when `record_video=True`). The `.webm` is finalized when the session closes; the path is known beforehand.
- **`browser_close_session`**() — Close a session and free its browser.
- **`browser_list_sessions`**() — List all open sessions with their current url, tab count, and identity.

## Navigation

- **`browser_navigate`**(url) — Navigate to a URL. Returns the page's ARIA snapshot (with [ref=...] handles). Auto-creates a session if none exists.
- **`browser_navigate_back`**() — Go back one entry in history. Returns the new page's ARIA snapshot.
- **`browser_navigate_forward`**() — Go forward one entry in history. Returns the new page's ARIA snapshot.
- **`browser_reload`**() — Reload the current page. Returns the page's ARIA snapshot.
- **`browser_tabs`**(action, index, url) — Manage tabs. action: `list` | `new` | `select` | `close` (index for select/close, url optional for new). Returns the resulting tab list.
- **`browser_switch_to_popup`**(timeout_ms) — Switch the active page to the most recently opened popup or new tab. Call after triggering an OAuth flow or any `window.open` / `target="_blank"` action. Returns a snapshot of the new page.

## Observe

- **`browser_snapshot`**(depth) — Capture the page's ARIA accessibility tree with [ref=...] handles. Primary way to "see" a page: roles + names + refs without CSS/markup noise. Frame-hosted elements get prefixed refs like `f1e36`; shadow DOM elements appear with plain `eN` refs.
- **`browser_snapshot_frame`**(frame_ref, depth) — Snapshot a specific child frame directly. Use when `browser_snapshot` returns an iframe node with empty/collapsed children. `frame_ref`: a frame id (`f1`), an element ref inside the frame (`f1e36`), or the `<iframe>` element's own ref (`e81`). Returns the frame's ARIA tree with refs rewritten to `fNeM` form so they're directly usable with click/type/etc.
- **`browser_screenshot`**(full_page, ref) — Take a PNG screenshot. Default captures the visible viewport; `full_page=True` captures the entire scrollable page; `ref` captures a single element.
- **`browser_resize`**(width, height) — Resize the page viewport (e.g. 1920x1080). Affects layout and screenshot size.
- **`browser_console_messages`**() — Return console messages collected on the current page (type + text).
- **`browser_wait_for_download`**(save_dir, timeout_ms) — Wait for a file download to complete and return its saved path. Call before (or immediately after) clicking a download button. The first download event is captured, saved to `save_dir`, and the absolute file path is returned.

## Interact

- **`browser_click`**(ref, button, double) — Click an element by its snapshot ref (e.g. `e12` or `f1e36` for iframe elements). Returns a fresh snapshot.
- **`browser_type`**(ref, text, submit, clear, value) — Type text into a field by ref (top-frame or iframe ref like `f1e20`). `submit=True` presses Enter after. Returns a snapshot. Pass the string as `text`; `value` is accepted as an alias for `text` (a common slip, since `browser_fill_form` fields use `value`) so the call doesn't hard-error.
- **`browser_keyboard_type`**(text, delay) — Type text into the currently focused element — no ref needed. Works on `contenteditable` rich-text editors (TipTap, Quill, ProseMirror) where `browser_type`/`fill()` is a no-op. Pattern: `browser_mouse_click(x, y)` to focus → `browser_keyboard_type(text)`. `delay`: ms between keystrokes.
- **`browser_fill_form`**(fields) — Fill multiple fields at once. Each field: `{ref, value, submit?, clear?}`.
- **`browser_hover`**(ref) — Hover over an element by ref. Returns a snapshot.
- **`browser_select_option`**(ref, values) — Select option(s) in a `<select>` by ref. Returns a snapshot.
- **`browser_press_key`**(key) — Press a keyboard key (e.g. `Enter`, `Escape`, `ArrowDown`, `Tab`). Returns a snapshot.
- **`browser_drag`**(from_ref, to_ref) — Drag one element onto another (by refs). Returns a snapshot.
- **`browser_file_upload`**(ref, paths) — Set files on a file `<input>` by ref (absolute paths). Returns a snapshot.
- **`browser_handle_dialog`**(accept, prompt_text) — Accept or dismiss an open JS dialog (alert/confirm/prompt). `prompt_text` fills a `prompt()` before accepting. Dialogs stay open until handled.
- **`browser_wait_for`**(text, text_gone, selector, url, network_idle, time, timeout_ms) — Wait for a condition then return a fresh snapshot. `text`: visible in any frame (cross-origin iframes included). `text_gone`: text to disappear. `selector`: CSS/Playwright selector. `url`: URL glob for SPA navigation. `network_idle`: no requests for 500ms. `time`: unconditional wait (seconds).
- **`browser_evaluate`**(expression, frame_ref) — Evaluate a JS expression in the page and return the result. `frame_ref` runs JS inside a child frame (`f1`, `f1e36`, or `e81`) — works cross-origin because the code runs in the frame's own context.
- **`browser_scroll`**(direction, amount, ref) — Scroll the page by pixels (up/down/left/right). `ref`: scroll that element into view instead (direction/amount ignored). Use to trigger lazy-loaded content.
- **`browser_scroll_to_bottom`**(max_scrolls, wait_ms) — Scroll to the very bottom of the page, pausing for lazy content each step. Stops when page height stops growing (infinite scroll exhausted or real bottom reached).

## Mouse (coordinate)

- **`browser_mouse_move`**(x, y) — Move the mouse to absolute page coordinates (x, y).
- **`browser_mouse_click`**(x, y, button, clicks) — Click at absolute coordinates (x, y). `button`: left|right|middle; `clicks` for multi-click.
- **`browser_mouse_down`**(button) — Press a mouse button down (at the current position).
- **`browser_mouse_up`**(button) — Release a mouse button (at the current position).
- **`browser_mouse_wheel`**(delta_x, delta_y) — Scroll the mouse wheel by (delta_x, delta_y) pixels.
- **`browser_mouse_drag`**(x1, y1, x2, y2) — Drag from (x1, y1) to (x2, y2) with the left button held.

## Network inspect

- **`browser_network_requests`**(resource_type, url_contains) — List network requests seen this session (method, url, status, resource_type). Filter by `resource_type` (e.g. `xhr`, `fetch`, `document`) or url substring.
- **`browser_network_request`**(index, url_contains) — Get one request's full detail: request + response headers, and response body (auto-captured for xhr/fetch). Match by list index or url substring (most recent match).
- **`browser_ws_messages`**(url_contains) — Return all WebSocket connections opened this session and their messages (`dir: sent|received`, `data`). Filter by url substring. Use to observe live app state, chat, or real-time events.

## Network control

- **`browser_block_urls`**(patterns) — Abort requests matching glob patterns (e.g. `**/*.png`, `**/ads/**`). Useful to save proxy bandwidth or strip trackers/images.
- **`browser_unblock_urls`**() — Remove all URL routes added via `browser_block_urls` or `browser_mock_url`.
- **`browser_set_offline`**(offline) — Toggle the context's network offline/online (to test offline behavior).
- **`browser_mock_url`**(pattern, status, body, content_type) — Fulfill requests matching a glob pattern with a canned response (response mocking / fault injection). Cleared by `browser_unblock_urls`.

## Cookies

- **`browser_cookie_list`**(url) — List cookies in the context (optionally filtered to a url).
- **`browser_cookie_get`**(name) — Get a single cookie by name (or null if absent).
- **`browser_cookie_set`**(name, value, url, domain, path) — Set a cookie. Provide either `url`, or `domain`+`path`.
- **`browser_cookie_delete`**(name) — Delete the cookie with the given name.
- **`browser_cookie_clear`**() — Remove all cookies in the context.

## localStorage

- **`browser_localstorage_list`**() — List all localStorage key/value pairs for the current origin.
- **`browser_localstorage_get`**(key) — Get a localStorage value by key (null if absent).
- **`browser_localstorage_set`**(key, value) — Set a localStorage key to a value.
- **`browser_localstorage_remove`**(key) — Remove a localStorage key.
- **`browser_localstorage_clear`**() — Clear all localStorage for the current origin.

## sessionStorage

- **`browser_sessionstorage_list`**() — List all sessionStorage key/value pairs for the current origin.
- **`browser_sessionstorage_get`**(key) — Get a sessionStorage value by key (null if absent).
- **`browser_sessionstorage_set`**(key, value) — Set a sessionStorage key to a value.
- **`browser_sessionstorage_remove`**(key) — Remove a sessionStorage key.
- **`browser_sessionstorage_clear`**() — Clear all sessionStorage for the current origin.

## State

- **`browser_storage_state`**(path) — Save cookies + localStorage to a JSON file. Reload it later via `browser_new_session(storage_state=path)`. Returns the file path.
- **`browser_har_export`**(output_path) — Finalize and return the HAR file path for a recording session. **Closes the session** — Playwright only flushes the HAR when the context closes. Session must have been created with `record_har=True`. `output_path`: optional path to copy the HAR file to before closing (checkpoint pattern: capture the HAR while keeping your state by copying the file, then optionally continuing work in the same session).

## Identity / Proxy

- **`browser_new_identity`**(persistent, label, proxy_url, proxy_server, proxy_username, proxy_password, no_proxy) — Start a fresh browser identity in a new session: novel fingerprint (randomized OS + screen) with isolated storage, optionally paired with a proxy. Proxyless by default. `persistent=True` mints a reusable profile dir. Returns the new session info.
- **`browser_set_proxy`**(server, username, password) — Pin a proxy as the default for subsequent sessions/identities. (Proxies are bound at launch; existing sessions are unaffected.)

## Verify

- **`browser_verify_element_visible`**(ref) — Assert an element (by ref) is visible. Returns `{ok, ...}`.
- **`browser_verify_element_hidden`**(ref) — Assert an element (by ref) is hidden/absent. Returns `{ok, ...}`.
- **`browser_verify_text_visible`**(text) — Assert some visible text appears on the page. Returns `{ok, ...}`.
- **`browser_verify_value`**(ref, value) — Assert an input/element (by ref) has the expected value. Returns `{ok, ...}`.

## Devtools / capture

- **`browser_highlight`**(ref) — Draw a magenta outline around an element (by ref) — handy before a screenshot.
- **`browser_clear_highlights`**() — Remove all highlight outlines added via `browser_highlight`.
- **`browser_generate_locator`**(ref) — Return a stable CSS selector for an element (by ref) for use in code/tests.
- **`browser_start_tracing`**() — Start a Playwright trace (screenshots + DOM snapshots) for later inspection.
- **`browser_stop_tracing`**(path) — Stop tracing and write a `trace.zip` (open with `playwright show-trace`). Returns the path.

> For a video recording of a session, create it with `record_video=True` on `browser_new_session` and fetch the `.webm` with `browser_video_path` (see Sessions).

## Emulate

- **`browser_set_geolocation`**(latitude, longitude) — Override the geolocation the page reads (note: `geoip=True` already aligns geo to the IP; this is an extra override).
- **`browser_set_extra_headers`**(headers) — Set extra HTTP headers sent with every request in this session.
- **`browser_grant_permissions`**(permissions, origin) — Pre-grant browser permissions (e.g. `geolocation`, `notifications`, `camera`, `microphone`) so the native prompt never blocks the flow. `origin`: restrict to a specific origin; omit to apply session-wide.

## CDP (Chromium / CloakBrowser only)

These wrap the Chrome DevTools Protocol via Playwright's `new_cdp_session()`. Each raises a clear error on Camoufox/Firefox.

- **`browser_cdp_click`**(ref, button, double) — Click an element (by snapshot ref) with a **trusted, cursorless** event via CDP `Input.dispatchMouseEvent` (`isTrusted=true`, no real cursor to contend with, no pixel guessing — the point is computed from the element's box). Use when an overlay/animation would block a normal click or you want to avoid moving the humanized cursor; passes bot-detection that flags DOM `.click()` (`isTrusted=false`). Returns a fresh snapshot.
- **`browser_cdp_send`**(method, params) — Send a raw CDP command and return the JSON result. Full DevTools surface: `Network.getResponseBody`/`getRequestPostData` (incl. request `_initiator` call stacks), `Performance.getMetrics`, `Emulation.setEmulatedMedia` (color-scheme/reduced-motion) / `setDeviceMetricsOverride` / `emulateNetworkConditions`, `Security.*`, etc. `params` is a JSON object for the method.
- **`browser_capture_mhtml`**(output_path) — Capture the page as a single-file **MHTML** archive (iframes + shadow DOM + external resources) via CDP `Page.captureSnapshot`. Returns the saved path.
- **`browser_pdf_save`**(output_path) — Render the page to a **PDF** via `page.pdf()`. Returns the saved path.

## Captcha

- **`browser_solve_captcha`**(kind, website_key, provider, page_action, min_score, funcaptcha_subdomain, funcaptcha_data, timeout) — Solve a captcha on the current page and inject the token (no extension). `kind`: `turnstile` | `recaptcha_v2` | `recaptcha_v3` | `hcaptcha` | `funcaptcha`. `website_key` auto-detected from DOM if omitted (for FunCaptcha that's the public key). `provider` defaults to the configured one (needs that provider's API key). **recaptcha_v3:** pass `page_action` (must match the site's `grecaptcha.execute` action) + optional `min_score` (0.1–0.9); the token is injected and `grecaptcha.execute` is overridden to return it. **funcaptcha (Arkose):** `funcaptcha_subdomain` (the Arkose `surl`) + `funcaptcha_data` (the dynamic `blob` JSON) are passed through when a site needs them. Returns the solved token.
- **`browser_totp_generate`**(secret, digits, interval) — Generate a TOTP (time-based one-time password) from a base32 shared secret. `digits`: code length (default 6). `interval`: time step in seconds (default 30). Use for two-factor login flows where you have the TOTP seed. Returns the current code as a string.

## Extract

- **`browser_extract`**(output_path) — Extract the current page as clean, token-efficient markdown (no LLM involved). Returns the markdown string. If `output_path` is given, writes to file and returns `{path, chars}` instead. You (the agent) do any further structuring.
