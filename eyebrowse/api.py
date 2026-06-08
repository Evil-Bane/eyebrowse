"""The public EyeBrowse façade — the single entry point both consumers call.

Claude Code reaches this through the MCP adapter; library consumers import it
directly. The façade owns the engine + session registry and exposes session
lifecycle plus a convenience ``session()`` context manager. Per-session *actions*
live on the returned :class:`~eyebrowse.engine.session.Session` object.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager

from .captcha import CaptchaError, detect_sitekey, get_solver, inject_token
from .config import Settings, get_settings
from .engine import BrowserEngine, Session, SessionRegistry
from .identity import Identity, random_identity
from .proxy import ProxyConfig, ProxyProvider, StaticProxyProvider


class EyeBrowse:
    def __init__(self, settings: Settings | None = None, proxy_provider: ProxyProvider | None = None):
        self.settings = settings or get_settings()
        self.engine = BrowserEngine(self.settings)
        self.registry = SessionRegistry()
        self.proxy_provider = proxy_provider
        self._crawler = None  # cached Crawl4AI AsyncWebCrawler (lazy)

    # ── session lifecycle ────────────────────────────────────────────────────
    async def new_session(
        self,
        *,
        identity: Identity | None = None,
        proxy: "ProxyConfig | str | dict | None" = None,
        no_proxy: bool = False,
        persistent: bool = False,
        user_data_dir: str | None = None,
        record_har: bool = False,
        record_har_path: str | None = None,
        har_url_filter: str | None = None,
        record_video: bool = False,
        storage_state: str | None = None,
        extensions: "list[str] | None" = None,
        label: str | None = None,
        **launch_extra,
    ) -> Session:
        """Launch a new stealth session and register it as the current one.

        proxy: a URL string ('http://user:pass@host:port'), a dict, or a ProxyConfig.
            Omit it to run **proxyless** (the default). no_proxy=True forces proxyless
            even when a provider or env proxy is configured.
        record_har: capture a full network HAR (export with :meth:`export_har`); works on
            both ephemeral and persistent sessions. storage_state: path to a saved
            cookies/localStorage JSON to reload.
        extensions: list of paths to UNPACKED Chromium extension folders to side-load (e.g. a
            captcha-solver or your own extension). Forces a persistent + headful session
            (Chromium requirement). The profile persists so the extension's own config/login
            survives across sessions.
        """
        # Extensions can only be side-loaded into a persistent (headful) context.
        if extensions:
            persistent = True
        # Proxy precedence: explicit arg > configured provider > env proxy > none.
        proxy_from_provider = False
        if no_proxy:
            proxy_cfg = None
        else:
            proxy_cfg = ProxyConfig.coerce(proxy)
            if proxy_cfg is None and self.proxy_provider is not None:
                proxy_cfg = await self.proxy_provider.acquire()
                proxy_from_provider = proxy_cfg is not None
            if proxy_cfg is None:
                proxy_cfg = ProxyConfig.from_settings(self.settings)

        # A persistent session needs a profile dir; mint one if not supplied.
        if persistent and not user_data_dir:
            if identity and identity.user_data_dir:
                user_data_dir = identity.user_data_dir
            else:
                identity = identity or random_identity(profiles_dir=self.settings.profiles_dir)
                user_data_dir = identity.user_data_dir

        # Auto-name a HAR file under the data dir when record_har is requested.
        if record_har and not record_har_path:
            har_dir = os.path.join(self.settings.data_dir, "har")
            os.makedirs(har_dir, exist_ok=True)
            record_har_path = os.path.join(har_dir, f"{secrets.token_hex(4)}.har")

        # Native video: record the whole session to a .webm, written on context close
        # (standard Playwright record_video_dir on Chromium).
        record_video_dir = None
        if record_video:
            record_video_dir = os.path.join(self.settings.data_dir, "videos", secrets.token_hex(4))
            os.makedirs(record_video_dir, exist_ok=True)

        context_options: dict = {}
        if storage_state:
            context_options["storage_state"] = storage_state

        launch = await self.engine.launch(
            proxy=proxy_cfg,
            identity=identity,
            persistent=persistent,
            user_data_dir=user_data_dir,
            record_har_path=record_har_path,
            record_har_url_filter=har_url_filter,
            record_video_dir=record_video_dir,
            extensions=extensions,
            context_options=context_options or None,
            extra=launch_extra or None,
        )
        session = Session(self.registry.new_id(), launch, identity=identity, proxy=proxy_cfg, label=label)
        session.proxy_from_provider = proxy_from_provider
        self.registry.add(session)
        return session

    async def export_har(self, session_id: str | None = None, output_path: str | None = None) -> str:
        """Finalize and return the HAR path for a recording session.

        Playwright only flushes the HAR when the context closes, so this **closes the
        session**. The session must have been created with ``record_har=True``.
        output_path: if given, copy the finished HAR to that path and return it.
        """
        import shutil

        session = self.registry.get(session_id)
        if not session.har_path:
            raise ValueError("Session was not created with record_har=True; no HAR to export.")
        har_path = session.har_path
        await self.close_session(session.id)
        self._brand_har(har_path)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            shutil.copy2(har_path, output_path)
            return output_path
        return har_path

    @staticmethod
    def _brand_har(har_path: str) -> None:
        """Relabel the HAR's creator to EyeBrowse (Playwright's recorder writes 'Playwright')."""
        try:
            import json

            from eyebrowse import __version__

            with open(har_path, encoding="utf-8") as fh:
                data = json.load(fh)
            data.setdefault("log", {})["creator"] = {
                "name": "EyeBrowse",
                "version": __version__,
                "comment": "Captured via Playwright's native HAR recorder (Chromium/CloakBrowser).",
            }
            with open(har_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
        except Exception:
            pass

    def get_session(self, session_id: str | None = None) -> Session:
        return self.registry.get(session_id)

    async def ensure_session(self, session_id: str | None = None) -> Session:
        """Return the named/current session, auto-creating a default if none exists."""
        existing = self.registry.get(session_id, required=False)
        if existing is not None:
            return existing
        return await self.new_session()

    async def close_session(self, session_id: str) -> None:
        session = self.registry.get(session_id, required=False)
        await self.registry.close(session_id)
        # Return a provider-leased proxy to the pool (no-op for explicit/env proxies).
        if (
            session is not None
            and getattr(session, "proxy_from_provider", False)
            and self.proxy_provider is not None
            and session.proxy is not None
        ):
            try:
                await self.proxy_provider.release(session.proxy)
            except Exception:
                pass

    def list_sessions(self) -> list[dict]:
        return self.registry.info()

    # ── identity / proxy helpers (M3 rotation) ──────────────────────────────────
    def make_identity(self, *, with_profile: bool = True) -> Identity:
        return random_identity(profiles_dir=self.settings.profiles_dir, with_profile=with_profile)

    def set_proxy_provider(self, provider: ProxyProvider | None) -> None:
        """Set the default proxy source for subsequent sessions."""
        self.proxy_provider = provider

    def set_static_proxy(self, server: str, username: str | None = None, password: str | None = None) -> None:
        """Convenience: pin one proxy as the default for subsequent sessions."""
        self.proxy_provider = StaticProxyProvider(ProxyConfig(server, username, password))

    async def rotate_identity(
        self,
        *,
        persistent: bool = False,
        proxy: "ProxyConfig | str | dict | None" = None,
        no_proxy: bool = False,
        label: str | None = None,
        **launch_extra,
    ) -> Session:
        """Start a fresh identity: novel fingerprint (OS/screen) + isolated storage,
        paired with a proxy (explicit > provider > env), or proxyless. Returns the Session."""
        identity = self.make_identity(with_profile=persistent)
        return await self.new_session(
            identity=identity,
            proxy=proxy,
            no_proxy=no_proxy,
            persistent=persistent,
            label=label or "identity",
            **launch_extra,
        )

    # ── captcha (M4, API-mode) ──────────────────────────────────────────────
    async def solve_captcha(
        self,
        *,
        session_id: str | None = None,
        kind: str = "turnstile",
        website_key: str | None = None,
        website_url: str | None = None,
        provider: str | None = None,
        page_action: str | None = None,
        min_score: float | None = None,
        funcaptcha_subdomain: str | None = None,
        funcaptcha_data: str | None = None,
        timeout: float = 120.0,
    ) -> str:
        """Solve a captcha on the current page via an API-mode solver, inject the token.

        kind: 'turnstile' | 'recaptcha_v2' | 'recaptcha_v3' | 'hcaptcha' | 'funcaptcha'.
        website_key is auto-detected from the DOM if omitted (for FunCaptcha that's the
        public key). provider defaults to settings.captcha_provider. Returns the token.

        recaptcha_v3: pass ``page_action`` (must match the site's grecaptcha.execute action)
        and optionally ``min_score``. funcaptcha: ``funcaptcha_subdomain`` (Arkose surl) and
        ``funcaptcha_data`` (the dynamic 'blob' JSON string) are passed through when needed.
        """
        session = await self.ensure_session(session_id)
        page = session.page
        url = website_url or page.url
        if website_key is None:
            website_key = await detect_sitekey(page, kind)
            if not website_key:
                raise CaptchaError("Could not auto-detect a sitekey; pass website_key explicitly.")
        solver = get_solver(provider, self.settings)
        if kind == "turnstile":
            token = await solver.solve_turnstile(website_url=url, website_key=website_key, timeout=timeout)
        elif kind in ("recaptcha", "recaptcha_v2"):
            token = await solver.solve_recaptcha_v2(website_url=url, website_key=website_key, timeout=timeout)
        elif kind == "hcaptcha":
            token = await solver.solve_hcaptcha(website_url=url, website_key=website_key, timeout=timeout)
        elif kind == "recaptcha_v3":
            token = await solver.solve_recaptcha_v3(
                website_url=url, website_key=website_key,
                page_action=page_action, min_score=min_score, timeout=timeout,
            )
        elif kind == "funcaptcha":
            token = await solver.solve_funcaptcha(
                website_url=url, website_public_key=website_key,
                api_js_subdomain=funcaptcha_subdomain, data=funcaptcha_data, timeout=timeout,
            )
        else:
            raise CaptchaError(f"Unsupported captcha kind {kind!r}")
        await inject_token(page, token, kind)
        return token

    # ── extraction (M5, Crawl4AI raw: feed) ──────────────────────────────────
    async def _get_crawler(self):
        """Lazily start and cache one Crawl4AI crawler (it warms a browser on start)."""
        if self._crawler is None:
            try:
                from crawl4ai import AsyncWebCrawler
            except ImportError as exc:
                raise RuntimeError(
                    "extract() needs the optional extraction stack. Install it with: "
                    "uv sync --extra extract"
                ) from exc

            self._crawler = AsyncWebCrawler()
            await self._crawler.start()
        return self._crawler

    async def extract(
        self,
        *,
        session_id: str | None = None,
        output_path: str | None = None,
        threshold: float = 0.48,
    ) -> object:
        """Extract the current page as clean, token-efficient markdown (Crawl4AI raw: feed).

        No LLM is used — the agent consuming this reasons over the markdown itself. If
        ``output_path`` is given, the markdown is written there and ``{path, chars}`` is
        returned (so the agent can fetch it from a path it chose); otherwise the markdown
        string is returned directly.
        """
        from . import extract as _extract

        session = await self.ensure_session(session_id)
        html = await session.page.content()
        crawler = await self._get_crawler()
        markdown = await _extract.to_markdown(crawler, html, threshold=threshold)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(markdown)
            return {"path": output_path, "chars": len(markdown)}
        return markdown

    # ── convenience CM for direct-library use ──────────────────────────────────
    @asynccontextmanager
    async def session(self, **kwargs):
        s = await self.new_session(**kwargs)
        try:
            yield s
        finally:
            await self.close_session(s.id)

    async def aclose(self) -> None:
        await self.registry.close_all()
        if self._crawler is not None:
            try:
                await self._crawler.close()
            except Exception:
                pass
            self._crawler = None
