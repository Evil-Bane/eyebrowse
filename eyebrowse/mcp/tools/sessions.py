"""Session lifecycle tools."""
from __future__ import annotations

from ...proxy import ProxyConfig
from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_new_session(
        persistent: bool = False,
        label: str | None = None,
        headless: bool | None = None,
        humanize: "float | bool | None" = None,
        record_har: bool = False,
        record_video: bool = False,
        record_video_width: int | None = None,
        record_video_height: int | None = None,
        har_url_filter: str | None = None,
        storage_state: str | None = None,
        extensions: "list[str] | None" = None,
        proxy_url: str | None = None,
        proxy_server: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        no_proxy: bool = False,
    ) -> str:
        """Create a new stealth browser session and make it current. Returns its id.

        Runs PROXYLESS by default. To use a proxy, pass either proxy_url
        ('http://user:pass@host:port') or proxy_server[+username/password].
        no_proxy=True forces proxyless even if an env/default proxy is configured.

        persistent: keep cookies/localStorage in a profile dir across runs.
        headless: override the configured default (None = use the default).
        humanize: per-session cursor humanization — a float caps cursor-move time in seconds
            (e.g. 0.25 = fast but still humanized), True = default speed, False = off,
            None = use the configured default.
        record_har: capture a full network HAR (export with browser_har_export).
        record_video: record the session to a native .webm (Chromium only); fetch the path with
            browser_video_path. The file is finalized on browser_close_session.
        record_video_width / record_video_height: pin the recording resolution (e.g. 1920 x 1080
            for HD); when omitted Playwright defaults to 800x450.
        har_url_filter: glob to scope what the HAR records (e.g. '**/api/**' or
            '**/students/**') so it excludes login/captcha/static noise; default = all.
        storage_state: path to a saved cookies/localStorage JSON to reload.
        extensions: list of paths to UNPACKED Chromium extension folders to side-load (e.g. a
            captcha-solver or a custom extension). Forces a persistent + headful session
            (Chromium only side-loads extensions that way); the profile persists so the
            extension's own config/login survives.
        Most tools auto-create a default session, so calling this is optional.
        """
        eb = state.get_engine()
        extra: dict = {}
        if headless is not None:
            extra["headless"] = headless
        if humanize is not None:
            extra["humanize"] = humanize
        if proxy_url:
            proxy = ProxyConfig.parse(proxy_url)
        elif proxy_server:
            proxy = ProxyConfig(proxy_server, proxy_username, proxy_password)
        else:
            proxy = None
        session = await eb.new_session(
            persistent=persistent,
            label=label,
            record_har=record_har,
            record_video=record_video,
            record_video_size=(
                (record_video_width, record_video_height)
                if record_video_width and record_video_height
                else None
            ),
            har_url_filter=har_url_filter,
            storage_state=storage_state,
            extensions=extensions,
            proxy=proxy,
            no_proxy=no_proxy,
            **extra,
        )
        return session.id

    @mcp.tool()
    async def browser_video_path(session_id: str | None = None) -> str:
        """Path to this session's native video recording (Chromium only).

        Only present when record_video=true was passed to browser_new_session. The .webm is
        finalized when the session closes (browser_close_session); the path is known beforehand.
        """
        s = await state.get_engine().ensure_session(session_id)
        p = await s.video_path()
        return p or "(no video — pass record_video=true to browser_new_session)"

    @mcp.tool()
    async def browser_close_session(session_id: str) -> str:
        """Close a session and free its browser."""
        await state.get_engine().close_session(session_id)
        return f"closed {session_id}"

    @mcp.tool()
    async def browser_list_sessions() -> list[dict]:
        """List all open sessions with their current url, tab count, and identity."""
        return state.get_engine().list_sessions()
