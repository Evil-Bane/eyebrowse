"""Browser launch primitive (CloakBrowser — stealth Chromium).

Owns *only* how a stealthy browser/context is brought up — not what's done with it.
Constraints encoded here:

* **HAR ⇒ ephemeral.** ``launch_persistent_context_async`` strips ``record_har_*`` in
  Playwright, so HAR is only valid on an ephemeral ``browser.new_context(...)``.
* **Return-type duality.** ``launch_persistent_context_async`` yields a ``BrowserContext``;
  ``launch_async`` yields a ``Browser`` (then we make our own context).

CloakBrowser is a Playwright drop-in: both launchers return standard Playwright objects and
patch ``close()`` to also stop the bundled Playwright (no leak). Its stealth is the patched
Chromium binary + an auto ``--fingerprint`` seed — nothing for us to spoof; we only map its
native knobs (``headless``, ``humanize``, ``geoip``, ``proxy``, ``locale``, ``timezone``).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class LaunchResult:
    cam: Any  # cleanup context manager (closed by the session via cam.__aexit__())
    browser: Any | None  # Browser (ephemeral) or None (persistent)
    context: Any  # BrowserContext
    pages: list  # initial page(s)
    persistent: bool
    har_path: str | None


class _Cleanup:
    """Cleanup context manager matching what the session closes via ``cam.__aexit__()``.

    Ephemeral: close the Browser (CloakBrowser patches ``browser.close`` to also stop its
    Playwright). Persistent: no-op — the persistent context's ``close()`` (also patched)
    already stopped Playwright.
    """

    def __init__(self, browser):
        self._browser = browser

    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass


def _proxy_to_url(proxy) -> "str | None":
    """Normalize EyeBrowse's proxy (ProxyConfig / dict / str) to a URL string for CloakBrowser."""
    if proxy is None:
        return None
    if isinstance(proxy, str):
        return proxy
    pw = proxy.to_playwright() if hasattr(proxy, "to_playwright") else proxy
    if not isinstance(pw, dict):
        return None
    server = pw.get("server") or ""
    user, pwd = pw.get("username"), pw.get("password")
    if user and pwd and "://" in server:
        scheme, rest = server.split("://", 1)
        return f"{scheme}://{user}:{pwd}@{rest}"
    return server or None


class BrowserEngine:
    def __init__(self, settings):
        self.settings = settings
        # Serialize launch + initial context creation. Cheap insurance, and it also serializes
        # the one-time CloakBrowser binary download on first launch.
        self._launch_lock = asyncio.Semaphore(1)

    def build_options(self, *, proxy=None, extra: dict | None = None) -> dict[str, Any]:
        s = self.settings
        opts: dict[str, Any] = {
            "headless": s.headless,
            "humanize": bool(s.humanize),  # CloakBrowser takes a bool (+ human_preset)
            # CloakBrowser derives timezone/locale (+ WebRTC IP) from the proxy exit when geoip=True.
            "geoip": s.geoip,
        }
        proxy_url = _proxy_to_url(proxy)
        if proxy_url:
            opts["proxy"] = proxy_url
        if getattr(s, "locale", None):
            opts["locale"] = s.locale
        if getattr(s, "timezone", None):
            opts["timezone"] = s.timezone
        if extra:
            opts.update(extra)
        # A per-session override may pass humanize as a float (cursor-time cap, legacy) — coerce.
        opts["humanize"] = bool(opts.get("humanize", True))
        return opts

    async def launch(
        self,
        *,
        proxy=None,
        identity=None,  # accepted for API parity; CloakBrowser auto-fingerprints per launch
        persistent: bool = False,
        user_data_dir: str | None = None,
        record_har_path: str | None = None,
        record_har_url_filter: str | None = None,
        record_video_dir: str | None = None,
        context_options: dict | None = None,
        extra: dict | None = None,
    ) -> LaunchResult:
        if persistent and record_har_path:
            raise ValueError(
                "HAR recording requires an ephemeral context and cannot be combined "
                "with persistent=True (Playwright strips record_har_* from "
                "launch_persistent_context). For HAR + a logged-in profile, run an "
                "upstream mitmproxy instead."
            )

        from cloakbrowser import launch_async, launch_persistent_context_async

        s = self.settings
        opts = self.build_options(proxy=proxy, extra=extra)
        viewport = None
        if s.viewport_width and s.viewport_height:
            viewport = {"width": s.viewport_width, "height": s.viewport_height}

        async with self._launch_lock:
            if persistent:
                kw = dict(opts)
                if viewport is not None:
                    kw["viewport"] = viewport
                if record_video_dir:
                    kw["record_video_dir"] = record_video_dir
                context = await launch_persistent_context_async(user_data_dir, **kw)
                browser = None
                pages = list(context.pages) or [await context.new_page()]
                cam = _Cleanup(None)  # context.close() (patched) stops Playwright
            else:
                browser = await launch_async(**opts)
                ctx_opts = dict(context_options or {})
                if viewport is not None:
                    ctx_opts.setdefault("viewport", viewport)
                if record_har_path:
                    ctx_opts.update(
                        record_har_path=record_har_path,
                        record_har_mode="full",
                        record_har_content="embed",
                    )
                    ctx_opts.setdefault("record_har_url_filter", record_har_url_filter or "**/*")
                if record_video_dir:
                    ctx_opts["record_video_dir"] = record_video_dir
                context = await browser.new_context(**ctx_opts)
                pages = [await context.new_page()]
                cam = _Cleanup(browser)

        # With no explicit viewport configured, maximize each page to the (randomized,
        # spoofed) screen: large screenshots without pinning the fingerprint.
        if not viewport:
            for pg in pages:
                await self._maximize_to_screen(pg)

        return LaunchResult(
            cam=cam,
            browser=browser,
            context=context,
            pages=pages,
            persistent=persistent,
            har_path=record_har_path,
        )

    @staticmethod
    async def _maximize_to_screen(page) -> None:
        """Size the viewport to the spoofed screen's available area, with a small width
        margin so window.innerWidth (which includes the ~16px scrollbar) stays <= screen."""
        try:
            dims = await page.evaluate("() => [screen.availWidth, screen.availHeight]")
            if dims and dims[0] and dims[1]:
                w = max(800, int(dims[0]) - 20)
                h = max(600, int(dims[1]))
                await page.set_viewport_size({"width": w, "height": h})
        except Exception:
            pass
