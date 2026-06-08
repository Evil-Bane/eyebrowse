"""A live browser session + the registry that tracks them across MCP calls.

A ``Session`` wraps one browser context/page set and exposes the verb-level actions
(navigate / snapshot / click / type / …). The ``SessionRegistry`` holds them in
memory keyed by id, with a notion of the "current" session so single-session callers
needn't pass an id every time.
"""
from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from ..snapshot import (
    aria_ai_snapshot,
    discover_frame_prefix,
    frame_for_ref,
    frame_prefix_for,
    ref_locator,
)

# Keep in-memory buffers bounded so long-lived sessions don't grow without limit.
_MAX_CONSOLE = 500
_MAX_NETWORK = 1000
_MAX_WS = 200        # max WebSocket connections tracked
_MAX_WS_MSGS = 500   # max messages per WebSocket

# Resource types whose response bodies we auto-capture (small, structured payloads).
_CAPTURE_BODY_TYPES = frozenset({"xhr", "fetch"})


def _frame_payload(payload) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        try:
            return payload.decode("utf-8")
        except Exception:
            return f"<binary {len(payload)} bytes>"
    return str(payload)


class Session:
    def __init__(self, session_id: str, launch: "Any", *, identity=None, proxy=None, label: str | None = None):
        self.id = session_id
        self._launch = launch
        self.cam = launch.cam
        self.browser = launch.browser
        self.context = launch.context
        self.pages = list(launch.pages)
        self.page = self.pages[0]
        self.persistent = launch.persistent
        self.har_path = launch.har_path
        self.identity = identity
        self.proxy = proxy
        self.proxy_from_provider = False  # set by EyeBrowse when proxy came from a ProxyProvider
        self.label = label
        self.console_messages: list[dict] = []
        self.network: list[dict] = []
        self._websockets: list[dict] = []
        self._dialog = None  # most recent open dialog, awaiting handle_dialog
        self._routes: list[str] = []  # active block_urls patterns
        self._closed = False
        # Popup / new-tab tracking (OAuth flows, window.open, target=_blank).
        self._last_new_page = None
        self._new_page_event = asyncio.Event()
        # Download tracking.
        self._last_download = None
        self._download_event = asyncio.Event()

        for p in self.context.pages:
            self._attach_listeners(p)
        # Track new tabs opened by the page (target=_blank, window.open).
        self.context.on("page", self._on_new_page)
        # Mid-session network visibility (headers/status; XHR/fetch bodies auto-captured).
        self.context.on("response", self._on_response)
        # Cap action timeouts (context-level → all pages incl. future tabs) so a blocked
        # click/fill fails fast and the agent recovers, instead of the 30s default hanging the
        # run. Navigation keeps its own longer budget. set_default_* are synchronous (no await).
        try:
            from eyebrowse.config import get_settings

            _to = get_settings()
            self.context.set_default_timeout(_to.action_timeout_ms)
            self.context.set_default_navigation_timeout(_to.navigation_timeout_ms)
        except Exception:
            pass

    # ── listeners ──────────────────────────────────────────────────────────
    def _attach_listeners(self, page) -> None:
        page.on("console", self._on_console)
        page.on("dialog", self._on_dialog)
        page.on("download", self._on_download)
        page.on("websocket", self._on_websocket)

    def _on_dialog(self, dialog) -> None:
        self._dialog = dialog

    def _on_console(self, msg) -> None:
        try:
            self.console_messages.append({"type": msg.type, "text": msg.text})
        except Exception:
            return
        if len(self.console_messages) > _MAX_CONSOLE:
            del self.console_messages[: len(self.console_messages) - _MAX_CONSOLE]

    def _on_new_page(self, page) -> None:
        self._attach_listeners(page)
        self._last_new_page = page
        self._new_page_event.set()

    def _on_download(self, download) -> None:
        self._last_download = download
        self._download_event.set()

    def _on_websocket(self, ws) -> None:
        if len(self._websockets) >= _MAX_WS:
            self._websockets.pop(0)
        entry: dict = {"url": ws.url, "messages": [], "closed": False}
        self._websockets.append(entry)

        # The framesent/framereceived events emit the payload DIRECTLY (str for text
        # frames, bytes for binary) — NOT a frame object. Accessing .payload would
        # raise AttributeError on every frame (verified against Playwright 1.60 source).
        def _on_sent(payload) -> None:
            if len(entry["messages"]) < _MAX_WS_MSGS:
                entry["messages"].append({"dir": "sent", "data": _frame_payload(payload)})

        def _on_received(payload) -> None:
            if len(entry["messages"]) < _MAX_WS_MSGS:
                entry["messages"].append({"dir": "received", "data": _frame_payload(payload)})

        ws.on("framesent", _on_sent)
        ws.on("framereceived", _on_received)
        ws.on("close", lambda *_: entry.__setitem__("closed", True))

    def _on_response(self, resp) -> None:
        try:
            req = resp.request
            entry: dict = {
                "method": req.method,
                "url": resp.url,
                "status": resp.status,
                "resource_type": req.resource_type,
                "request_headers": dict(req.headers),
                "response_headers": dict(resp.headers),
            }
            self.network.append(entry)
            if req.resource_type in _CAPTURE_BODY_TYPES:
                asyncio.ensure_future(self._capture_body(resp, entry))
        except Exception:
            return
        if len(self.network) > _MAX_NETWORK:
            del self.network[: len(self.network) - _MAX_NETWORK]

    async def _capture_body(self, resp, entry: dict) -> None:
        try:
            try:
                await resp.finished()   # wait for body to be fully buffered
            except Exception:
                pass   # may raise Target-closed mid-teardown; still try body()
            body = await resp.body()
            if not body:
                return
            try:
                entry["body"] = body.decode("utf-8", errors="replace")
            except Exception:
                entry["body"] = f"<binary {len(body)} bytes>"
        except Exception:
            pass

    # ── navigation ───────────────────────────────────────────────────────────
    # Chromium reports history navigations to Playwright, so back/forward/reload use the
    # browser's real history natively (they traverse click-driven navigations too, not just
    # navigate()-driven ones).
    async def navigate(self, url: str, *, wait_until: str = "domcontentloaded", timeout_ms: float | None = None) -> str:
        await self.page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        return await self.snapshot()

    async def navigate_back(self) -> str:
        if await self.page.go_back(wait_until="domcontentloaded") is None:
            raise ValueError("No back history in this session.")
        return await self.snapshot()

    async def navigate_forward(self) -> str:
        if await self.page.go_forward(wait_until="domcontentloaded") is None:
            raise ValueError("No forward history in this session.")
        return await self.snapshot()

    async def reload(self) -> str:
        await self.page.reload(wait_until="domcontentloaded")
        return await self.snapshot()

    async def resize(self, width: int, height: int) -> None:
        await self.page.set_viewport_size({"width": width, "height": height})

    # ── observation ────────────────────────────────────────────────────────
    async def snapshot(self, *, depth: int | None = None) -> str:
        return await aria_ai_snapshot(self.page, depth=depth)

    async def snapshot_frame(self, frame_ref: str, *, depth: int | None = None) -> str:
        """Return the ARIA snapshot for a child frame, with directly-actionable refs.

        ``frame_ref`` may be a frame id ('f1'), an element ref inside the frame
        ('f1e36'), or an ``<iframe>`` element ref ('e81'). Use this when
        ``browser_snapshot`` returns an iframe node with empty/collapsed children —
        snapshotting the frame directly is reliable.

        The frame's own snapshot uses bare ``eM`` refs; we rewrite them to ``fNeM`` so
        they resolve correctly via the page's aria-ref engine (i.e. you can pass them
        straight to click/type). If the frame's seq prefix can't be determined, the
        refs are returned frame-local with a note.
        """
        frame = await frame_for_ref(self.page, frame_ref)
        prefix = frame_prefix_for(frame_ref) or await discover_frame_prefix(self.page, frame)
        # In PW 1.60 Frame.aria_snapshot does not exist — only Page.aria_snapshot and
        # Locator.aria_snapshot do.  We snapshot via a body locator scoped to the frame.
        kwargs: dict = {"mode": "ai"}
        if depth is not None:
            kwargs["depth"] = depth
        snap = await frame.locator("body").aria_snapshot(**kwargs)
        if prefix:
            return re.sub(r"\[ref=(e\d+)\]", rf"[ref={prefix}\1]", snap)
        return (
            "# NOTE: refs below are frame-local — the frame's id (fN) could not be "
            "determined.\n# Re-snapshot the full page (browser_snapshot) once the frame "
            "is loaded to get actionable fNeM refs.\n" + snap
        )

    async def screenshot(self, *, full_page: bool = False, ref: str | None = None) -> bytes:
        if ref:
            return await ref_locator(self.page, ref).screenshot(type="png")
        return await self.page.screenshot(type="png", full_page=full_page)

    def get_console_messages(self) -> list[dict]:
        return list(self.console_messages)

    def get_network_requests(self, *, resource_type: str | None = None, url_contains: str | None = None) -> list[dict]:
        out = self.network
        if resource_type:
            out = [r for r in out if r["resource_type"] == resource_type]
        if url_contains:
            out = [r for r in out if url_contains in r["url"]]
        # Strip header/body detail from the list view; full detail via get_network_request.
        return [{k: r[k] for k in ("method", "url", "status", "resource_type")} for r in out]

    def get_network_request(self, *, index: int | None = None, url_contains: str | None = None) -> dict | None:
        if index is not None:
            return self.network[index] if -len(self.network) <= index < len(self.network) else None
        if url_contains is not None:
            for r in reversed(self.network):
                if url_contains in r["url"]:
                    return r
        return None

    def get_ws_messages(self, *, url_contains: str | None = None) -> list[dict]:
        """Return tracked WebSocket connections and their messages."""
        if url_contains:
            return [ws for ws in self._websockets if url_contains in ws["url"]]
        return list(self._websockets)

    async def save_storage_state(self, path: str) -> str:
        await self.context.storage_state(path=path)
        return path

    # ── interaction ──────────────────────────────────────────────────────────
    def _ref(self, ref: str):
        return ref_locator(self.page, ref)

    async def click(self, ref: str, *, button: str = "left", double: bool = False) -> None:
        loc = self._ref(ref)
        if double:
            await loc.dblclick(button=button)
        else:
            await loc.click(button=button)

    # ── CDP (Chrome DevTools Protocol) ─────────────────────────────────────────
    async def cdp_session(self):
        """Open + cache a Chrome DevTools Protocol session for this page."""
        if getattr(self, "_cdp", None) is None:
            try:
                self._cdp = await self.context.new_cdp_session(self.page)
            except Exception as e:  # new_cdp_session is Chromium-only
                raise RuntimeError(
                    "CDP session could not be opened (requires the Chromium engine)"
                ) from e
        return self._cdp

    async def cdp_send(self, method: str, params: dict | None = None):
        """Send a raw CDP command and return its result dict."""
        cdp = await self.cdp_session()
        return await cdp.send(method, params or {})

    async def cdp_click(self, ref: str, *, button: str = "left", clicks: int = 1) -> None:
        """Trusted, cursorless click on an aria-ref element via CDP Input.dispatchMouseEvent.

        No coordinate guessing — the center is computed from the element's own box. Produces a
        TRUSTED event (isTrusted=true), unlike DOM .click()/dispatchEvent. When the session was
        launched with humanize=True (the default), CloakBrowser humanizes the dispatched pointer
        events at the browser level, so the click already carries a realistic cursor trajectory.
        """
        loc = self._ref(ref)
        try:
            await loc.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass
        box = await loc.bounding_box()
        if not box:
            raise ValueError(f"ref {ref!r} has no bounding box (hidden / not laid out)")
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        cdp = await self.cdp_session()
        await cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        await cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": button, "clickCount": clicks})
        await cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": button, "clickCount": clicks})

    async def capture_mhtml(self, output_path: str) -> str:
        """Save the full page (iframes + shadow DOM + resources) as single-file MHTML via CDP."""
        res = await self.cdp_send("Page.captureSnapshot", {"format": "mhtml"})
        data = res.get("data", "") if isinstance(res, dict) else ""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(data)
        return os.path.abspath(output_path)

    async def save_pdf(self, output_path: str) -> str:
        """Save the current page as a PDF (Chromium only)."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        await self.page.pdf(path=output_path)
        return os.path.abspath(output_path)

    async def video_path(self) -> "str | None":
        """Path of the native session video, if record_video was enabled at session creation.
        The .webm is finalized when the session closes; the path is known beforehand."""
        try:
            vid = getattr(self.page, "video", None)
            if vid is not None:
                return await vid.path()
        except Exception:
            return None
        return None

    async def type(self, ref: str, text: str, *, submit: bool = False, clear: bool = True) -> None:
        loc = self._ref(ref)
        if clear:
            await loc.fill(text)
        else:
            await loc.press_sequentially(text)
        if submit:
            await loc.press("Enter")

    async def keyboard_type(self, text: str, *, delay: float | None = None) -> None:
        """Type text into whatever element currently has focus (no ref needed).

        Works on ``contenteditable`` rich-text editors (TipTap, Quill, ProseMirror)
        where ``fill()`` is a no-op.  Pattern: coordinate-click to focus →
        ``keyboard_type`` to insert.
        """
        kwargs: dict = {}
        if delay is not None:
            kwargs["delay"] = delay
        await self.page.keyboard.type(text, **kwargs)

    async def hover(self, ref: str) -> None:
        await self._ref(ref).hover()

    async def select_option(self, ref: str, values: str | list[str]) -> None:
        await self._ref(ref).select_option(values)

    async def press_key(self, key: str) -> None:
        await self.page.keyboard.press(key)

    async def drag(self, from_ref: str, to_ref: str) -> None:
        await self._ref(from_ref).drag_to(self._ref(to_ref))

    async def upload_files(self, ref: str, paths: list[str]) -> None:
        await self._ref(ref).set_input_files(paths)

    async def handle_dialog(self, *, accept: bool = True, prompt_text: str | None = None) -> str:
        dialog = self._dialog
        if dialog is None:
            raise ValueError("No open dialog to handle.")
        self._dialog = None
        if accept:
            await dialog.accept(prompt_text) if prompt_text is not None else await dialog.accept()
            return "accepted"
        await dialog.dismiss()
        return "dismissed"

    async def scroll(self, direction: str = "down", amount: int = 300, *, ref: str | None = None) -> None:
        """Scroll the page or scroll a specific element into view.

        direction: 'up' | 'down' | 'left' | 'right'. amount: pixels.
        If ref is given, scrolls that element into view instead.
        """
        if ref:
            await self._ref(ref).scroll_into_view_if_needed()
            return
        delta_x, delta_y = 0, 0
        if direction == "down":
            delta_y = amount
        elif direction == "up":
            delta_y = -amount
        elif direction == "right":
            delta_x = amount
        elif direction == "left":
            delta_x = -amount
        else:
            raise ValueError(f"direction must be up/down/left/right, got {direction!r}")
        await self.page.mouse.wheel(delta_x, delta_y)

    async def scroll_to_bottom(self, *, max_scrolls: int = 20, wait_ms: int = 500) -> int:
        """Scroll to the page bottom, waiting for lazy-loaded content each step.

        Returns the number of scroll steps taken. Stops early when the page
        height stops growing (infinite-scroll exhausted or real bottom reached).
        """
        for i in range(max_scrolls):
            prev = await self.page.evaluate("() => document.documentElement.scrollHeight")
            await self.page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            await self.page.wait_for_timeout(wait_ms)
            curr = await self.page.evaluate("() => document.documentElement.scrollHeight")
            if curr == prev:
                return i + 1
        return max_scrolls

    # ── cookies ──────────────────────────────────────────────────────────────
    async def get_cookies(self, urls: list[str] | None = None) -> list[dict]:
        return await self.context.cookies(urls)

    async def add_cookies(self, cookies: list[dict]) -> None:
        await self.context.add_cookies(cookies)

    async def clear_cookies(self) -> None:
        await self.context.clear_cookies()

    async def delete_cookie(self, name: str) -> None:
        await self.context.clear_cookies(name=name)

    # ── web storage (local / session) ──────────────────────────────────────
    async def storage_get(self, store: str, key: str):
        return await self.page.evaluate(
            "([s, k]) => (s === 'local' ? localStorage : sessionStorage).getItem(k)", [store, key]
        )

    async def storage_set(self, store: str, key: str, value: str) -> None:
        await self.page.evaluate(
            "([s, k, v]) => (s === 'local' ? localStorage : sessionStorage).setItem(k, v)", [store, key, value]
        )

    async def storage_remove(self, store: str, key: str) -> None:
        await self.page.evaluate(
            "([s, k]) => (s === 'local' ? localStorage : sessionStorage).removeItem(k)", [store, key]
        )

    async def storage_clear(self, store: str) -> None:
        await self.page.evaluate("(s) => (s === 'local' ? localStorage : sessionStorage).clear()", store)

    async def storage_list(self, store: str) -> dict:
        return await self.page.evaluate(
            "(s) => { const st = (s === 'local' ? localStorage : sessionStorage); const o = {}; "
            "for (let i = 0; i < st.length; i++) { const k = st.key(i); o[k] = st.getItem(k); } return o; }",
            store,
        )

    # ── coordinate mouse (vision-style) ──────────────────────────────────────
    async def mouse_move(self, x: float, y: float) -> None:
        await self.page.mouse.move(x, y)

    async def mouse_click(self, x: float, y: float, *, button: str = "left", clicks: int = 1) -> None:
        await self.page.mouse.click(x, y, button=button, click_count=clicks)

    async def mouse_down(self, *, button: str = "left") -> None:
        await self.page.mouse.down(button=button)

    async def mouse_up(self, *, button: str = "left") -> None:
        await self.page.mouse.up(button=button)

    async def mouse_wheel(self, delta_x: float, delta_y: float) -> None:
        await self.page.mouse.wheel(delta_x, delta_y)

    async def mouse_drag(self, x1: float, y1: float, x2: float, y2: float) -> None:
        await self.page.mouse.move(x1, y1)
        await self.page.mouse.down()
        await self.page.mouse.move(x2, y2)
        await self.page.mouse.up()

    # ── network control ──────────────────────────────────────────────────────
    async def block_urls(self, patterns: list[str]) -> None:
        async def _abort(route):
            await route.abort()

        for pattern in patterns:
            await self.context.route(pattern, _abort)
            self._routes.append(pattern)

    async def unblock_urls(self) -> None:
        for pattern in self._routes:
            try:
                await self.context.unroute(pattern)
            except Exception:
                pass
        self._routes.clear()

    async def set_offline(self, offline: bool) -> None:
        await self.context.set_offline(offline)

    async def mock_url(self, pattern: str, *, status: int = 200, body: str = "", content_type: str = "text/plain") -> None:
        async def _fulfill(route):
            await route.fulfill(status=status, body=body, content_type=content_type)

        await self.context.route(pattern, _fulfill)
        self._routes.append(pattern)

    # ── assertions ───────────────────────────────────────────────────────────
    async def verify(self, *, visible_ref=None, hidden_ref=None, text=None, value_ref=None, value=None) -> dict:
        if visible_ref is not None:
            ok = await self._ref(visible_ref).is_visible()
            return {"kind": "element_visible", "ref": visible_ref, "ok": ok}
        if hidden_ref is not None:
            ok = await self._ref(hidden_ref).is_hidden()
            return {"kind": "element_hidden", "ref": hidden_ref, "ok": ok}
        if text is not None:
            ok = await self.page.get_by_text(text).count() > 0
            return {"kind": "text_visible", "text": text, "ok": ok}
        if value_ref is not None:
            actual = await self._ref(value_ref).input_value()
            return {"kind": "value", "ref": value_ref, "expected": value, "actual": actual, "ok": actual == value}
        raise ValueError("verify needs one of: visible_ref, hidden_ref, text, value_ref(+value)")

    # ── debugging visuals / locator ──────────────────────────────────────────
    async def highlight(self, ref: str) -> None:
        await self._ref(ref).evaluate(
            "(el) => { el.setAttribute('data-eb-highlight', '1');"
            " el.style.outline = '3px solid #ff00ff'; el.style.outlineOffset = '1px'; }"
        )

    async def clear_highlights(self) -> None:
        await self.page.evaluate(
            "() => document.querySelectorAll('[data-eb-highlight]').forEach(el => "
            "{ el.style.outline = ''; el.removeAttribute('data-eb-highlight'); })"
        )

    async def generate_locator(self, ref: str) -> str:
        return await self._ref(ref).evaluate(
            """(el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                const parts = [];
                let n = el;
                while (n && n.nodeType === 1 && n.tagName.toLowerCase() !== 'html') {
                    if (n.id) { parts.unshift('#' + CSS.escape(n.id)); break; }
                    let i = 1, sib = n;
                    while ((sib = sib.previousElementSibling)) { if (sib.tagName === n.tagName) i++; }
                    parts.unshift(n.tagName.toLowerCase() + ':nth-of-type(' + i + ')');
                    n = n.parentElement;
                }
                return parts.join(' > ');
            }"""
        )

    # ── tracing ────────────────────────────────────────────────────────────
    async def start_tracing(self, *, screenshots: bool = True, snapshots: bool = True) -> None:
        await self.context.tracing.start(screenshots=screenshots, snapshots=snapshots)

    async def stop_tracing(self, path: str) -> str:
        await self.context.tracing.stop(path=path)
        return path

    # ── emulation ────────────────────────────────────────────────────────────
    async def set_geolocation(self, latitude: float, longitude: float) -> None:
        await self.context.set_geolocation({"latitude": latitude, "longitude": longitude})

    async def set_extra_headers(self, headers: dict) -> None:
        await self.context.set_extra_http_headers(headers)

    async def grant_permissions(self, permissions: list[str], *, origin: str | None = None) -> None:
        """Grant browser permissions (e.g. 'geolocation', 'notifications', 'camera').

        Prevents the native permission prompt from blocking the flow.
        origin: restrict the grant to a specific origin; omit to apply session-wide.
        """
        kwargs: dict = {}
        if origin:
            kwargs["origin"] = origin
        await self.context.grant_permissions(permissions, **kwargs)

    # ── form helpers ─────────────────────────────────────────────────────────
    async def fill_form(self, fields: list[dict]) -> None:
        for f in fields:
            await self.type(
                f["ref"], str(f.get("value", "")),
                submit=bool(f.get("submit", False)),
                clear=bool(f.get("clear", True)),
            )

    async def evaluate(self, expression: str, arg: Any = None, *, frame_ref: str | None = None) -> Any:
        """Evaluate JS in the page (or in a specific frame via frame_ref).

        frame_ref: 'f1' / 'f1e36' / 'e81' (iframe element ref) — runs the expression
        inside that frame's own JS context, which means cross-origin frames work fine
        (the code is not the parent reaching into the frame; it IS the frame).
        """
        if frame_ref:
            frame = await frame_for_ref(self.page, frame_ref)
            return await frame.evaluate(expression, arg)
        return await self.page.evaluate(expression, arg)

    async def wait_for(
        self,
        *,
        text: str | None = None,
        text_gone: str | None = None,
        selector: str | None = None,
        url: str | None = None,
        network_idle: bool = False,
        time: float | None = None,
        timeout_ms: float | None = None,
    ) -> None:
        _to = timeout_ms
        if time is not None:
            await self.page.wait_for_timeout(time * 1000)
            return
        if url is not None:
            await self.page.wait_for_url(url, timeout=_to)
            return
        if network_idle:
            await self.page.wait_for_load_state("networkidle", timeout=_to)
            return
        if text is not None:
            # Search all frames in parallel — handles cross-origin iframes where
            # page.get_by_text() can't pierce the cross-origin boundary.
            frames = self.page.frames
            per_ms = _to or 30000

            async def _check_text(f):
                await f.get_by_text(text).first.wait_for(state="visible", timeout=per_ms)

            tasks = {asyncio.create_task(_check_text(f)) for f in frames}
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    if t.exception() is None:
                        for p in pending:
                            p.cancel()
                        return
            raise TimeoutError(f"Text {text!r} not visible in any frame within {per_ms}ms")

        if text_gone is not None:
            await self.page.get_by_text(text_gone).first.wait_for(state="hidden", timeout=_to)
            return
        if selector is not None:
            await self.page.locator(selector).first.wait_for(timeout=_to)
            return
        raise ValueError("wait_for needs one of: text, text_gone, selector, url, network_idle, time")

    async def switch_to_popup(self, *, timeout_ms: float = 5000) -> str:
        """Switch the active page to the most recently opened popup or new tab.

        Call this after triggering an OAuth flow or any action that opens a new
        window (``window.open``, ``target="_blank"``).  Returns a snapshot of the
        new page.
        """
        last = self._last_new_page
        if last is not None and last in self.context.pages:
            self.page = last
            self._last_new_page = None
        else:
            self._new_page_event.clear()
            try:
                await asyncio.wait_for(self._new_page_event.wait(), timeout=timeout_ms / 1000)
            except asyncio.TimeoutError:
                raise TimeoutError(f"No popup/new tab opened within {timeout_ms:.0f}ms")
            self.page = self._last_new_page
            self._last_new_page = None
        try:
            await self.page.wait_for_load_state("load", timeout=5000)
        except Exception:
            pass
        return await self.snapshot()

    async def wait_for_download(self, *, save_dir: str = "data/downloads", timeout_ms: float = 30000) -> str:
        """Wait for a file download to start and complete. Returns the saved file path.

        Call this before (or just after) clicking a download button. The first
        download event after this call is captured, saved to save_dir, and its
        absolute path is returned.
        """
        last = self._last_download
        if last is not None:
            self._last_download = None
        else:
            self._download_event.clear()
            try:
                await asyncio.wait_for(self._download_event.wait(), timeout=timeout_ms / 1000)
            except asyncio.TimeoutError:
                raise TimeoutError(f"No download started within {timeout_ms:.0f}ms")
            last = self._last_download
            self._last_download = None
        os.makedirs(save_dir, exist_ok=True)
        filename = last.suggested_filename or "download"
        path = os.path.join(save_dir, filename)
        await last.save_as(path)
        return os.path.abspath(path)

    # ── tabs ───────────────────────────────────────────────────────────────
    async def list_tabs(self) -> list[dict]:
        out = []
        for i, p in enumerate(self.context.pages):
            out.append({"index": i, "url": p.url, "title": await p.title(), "current": p is self.page})
        return out

    async def new_tab(self, url: str | None = None) -> int:
        page = await self.context.new_page()
        self._attach_listeners(page)
        self.page = page
        if url:
            await page.goto(url)
        return self.context.pages.index(page)

    async def select_tab(self, index: int) -> None:
        page = self.context.pages[index]
        self.page = page
        await page.bring_to_front()

    async def close_tab(self, index: int) -> None:
        page = self.context.pages[index]
        await page.close()
        if page is self.page:
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                self._attach_listeners(self.page)

    # ── lifecycle ────────────────────────────────────────────────────────────
    def info(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "url": self.page.url if self.page else None,
            "persistent": self.persistent,
            "har": self.har_path,
            "tabs": len(self.context.pages),
            "identity_os": getattr(self.identity, "os", None),
            "proxied": self.proxy is not None,
        }

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.context.close()
        finally:
            try:
                await self.cam.__aexit__(None, None, None)
            except Exception:
                pass


class SessionRegistry:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._counter = 0
        self._current: str | None = None
        self._lock = asyncio.Lock()

    def new_id(self) -> str:
        self._counter += 1
        return f"s{self._counter}"

    def add(self, session: Session) -> None:
        self._sessions[session.id] = session
        self._current = session.id

    def get(self, session_id: str | None = None, *, required: bool = True) -> Session | None:
        sid = session_id or self._current
        if not sid or sid not in self._sessions:
            if required:
                raise KeyError(f"No session {session_id!r} (current={self._current!r})")
            return None
        self._current = sid
        return self._sessions[sid]

    def info(self) -> list[dict]:
        return [
            {**s.info(), "current": s.id == self._current}
            for s in self._sessions.values()
        ]

    async def close(self, session_id: str) -> None:
        async with self._lock:
            s = self._sessions.pop(session_id, None)
            if s is None:
                raise KeyError(f"No session {session_id!r}")
            if self._current == session_id:
                self._current = next(iter(self._sessions), None)
        await s.close()

    async def close_all(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._current = None
        for s in sessions:
            await s.close()
