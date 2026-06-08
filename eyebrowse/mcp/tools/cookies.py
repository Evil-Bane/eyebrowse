"""Cookie tools (granular)."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_cookie_list(url: str | None = None, session_id: str | None = None) -> list[dict]:
        """List cookies in the context (optionally filtered to a url)."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.get_cookies([url] if url else None)

    @mcp.tool()
    async def browser_cookie_get(name: str, session_id: str | None = None) -> dict | None:
        """Get a single cookie by name (or null if absent)."""
        s = await state.get_engine().ensure_session(session_id)
        for c in await s.get_cookies():
            if c.get("name") == name:
                return c
        return None

    @mcp.tool()
    async def browser_cookie_set(
        name: str,
        value: str,
        url: str | None = None,
        domain: str | None = None,
        path: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Set a cookie. Provide either url, or domain+path."""
        s = await state.get_engine().ensure_session(session_id)
        cookie: dict = {"name": name, "value": value}
        if url:
            cookie["url"] = url
        if domain:
            cookie["domain"] = domain
        if path:
            cookie["path"] = path
        await s.add_cookies([cookie])
        return f"set cookie {name}"

    @mcp.tool()
    async def browser_cookie_delete(name: str, session_id: str | None = None) -> str:
        """Delete the cookie with the given name."""
        s = await state.get_engine().ensure_session(session_id)
        await s.delete_cookie(name)
        return f"deleted cookie {name}"

    @mcp.tool()
    async def browser_cookie_clear(session_id: str | None = None) -> str:
        """Remove all cookies in the context."""
        s = await state.get_engine().ensure_session(session_id)
        await s.clear_cookies()
        return "cookies cleared"
