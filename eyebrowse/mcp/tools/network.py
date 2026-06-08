"""Network inspection tools (mid-session; XHR/fetch bodies auto-captured)."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_network_requests(
        session_id: str | None = None,
        resource_type: str | None = None,
        url_contains: str | None = None,
    ) -> list[dict]:
        """List network requests seen this session (method, url, status, resource_type).
        Optionally filter by resource_type (e.g. 'xhr', 'fetch', 'document') or url substring.
        For full details including headers and body, use browser_network_request."""
        s = await state.get_engine().ensure_session(session_id)
        return s.get_network_requests(resource_type=resource_type, url_contains=url_contains)

    @mcp.tool()
    async def browser_network_request(
        session_id: str | None = None,
        index: int | None = None,
        url_contains: str | None = None,
    ) -> dict | None:
        """Get one request's full detail: request + response headers, and response body
        (auto-captured for XHR/fetch resource types — body may still be populating for
        very recent requests). Match by list index or url substring (most recent match)."""
        s = await state.get_engine().ensure_session(session_id)
        return s.get_network_request(index=index, url_contains=url_contains)

    @mcp.tool()
    async def browser_ws_messages(
        session_id: str | None = None,
        url_contains: str | None = None,
    ) -> list[dict]:
        """Return all WebSocket connections opened this session and their messages.

        Each entry: {url, closed, messages: [{dir: 'sent'|'received', data: str}]}.
        url_contains: filter to connections whose URL includes this substring.
        Useful for real-time apps (trading dashboards, chat, live data feeds) that
        deliver state over WebSocket rather than HTTP."""
        s = await state.get_engine().ensure_session(session_id)
        return s.get_ws_messages(url_contains=url_contains)
